#![cfg_attr(not(feature = "gpu"), deny(unsafe_code))]
// Legacy code cleanup is tracked in TASK_CHECKLIST.md section 7.
// These clippy lints affect older modules scheduled for refactoring.
#![allow(clippy::needless_borrows_for_generic_args)]
#![allow(clippy::manual_div_ceil)]
#![allow(clippy::manual_is_multiple_of)]
#![allow(clippy::manual_ignore_case_cmp)]
#![allow(clippy::while_let_loop)]
#![allow(clippy::unnecessary_map_or)]
#![allow(clippy::same_item_push)]
#![allow(clippy::needless_range_loop)]
#![allow(clippy::for_kv_map)]
#![allow(clippy::io_other_error)]
#![allow(clippy::manual_flatten)]
#![allow(clippy::needless_option_as_deref)]
#![allow(clippy::empty_line_after_doc_comments)]
#![allow(clippy::new_without_default)]
//! Telomere: stateless lossless generative compression via BLAKE3/SHA-256 seed expansion.
//!
//! Core protocol: partition input into fixed-size blocks; for each block find the
//! shortest seed `s` such that `H(s)` matches the block; emit a compact Lotus header
//! encoding `(arity, seed)` in place of the raw bytes. Multi-pass recursion on headers
//! drives convergence toward negative delta on structured data.

mod block;
mod block_indexer;
mod bundle;
mod bundle_select;
mod bundler;
mod candidate;
mod compress;
mod compress_stats;
mod config;
mod error;
mod file_header;
mod gpu;
mod hash_reader;
pub mod hasher;
mod header;
mod hybrid;
pub mod io_utils;
mod live_window;
mod lotus_core;
mod path;
mod seed;
mod seed_detect;
mod seed_index;
mod seed_logger;
mod stats;
pub mod superposition;
mod tile;
mod tlmr;
pub mod types;

pub use block::{
    print_table_summary, split_into_blocks, BlockId, BlockRef, BlockStore, BranchStatus,
};
pub use block_indexer::{brute_force_seed_tables, IndexedBlock, SeedMatch};

pub use bundle::{apply_bundle, BlockStatus, MutableBlock};
pub use bundle_select::{select_bundles, AcceptedBundle, BundleRecord};
pub use bundler::bundle_one_layer;
pub use candidate::{prune_candidates, Block as CandidateBlock, Candidate};
pub use compress::{
    compress, compress_block, compress_block_with_config, compress_multi_pass,
    compress_multi_pass_with_config, compress_with_config, compress_with_run_summary,
    TruncHashTable,
};
pub use compress_stats::{write_stats_csv, CompressionStats, PassStats, RunSummary};
pub use config::{Config, HasherKind};
pub use error::TelomereError;
pub use file_header::{decode_file_header, encode_file_header};
pub use gpu::GpuSeedMatcher;
pub use hash_reader::lookup_seed;
pub use header::{
    decode_header, decode_lotus_header, encode_header, encode_lotus_arity_bits,
    encode_lotus_header, pack_bits, BitReader, DecodedHeader, Header,
};
pub use hybrid::{compress_hybrid, CpuMatchRecord, GpuMatchRecord};
pub use io_utils::*;
pub use live_window::{print_window, LiveStats};
pub use lotus_core::{lotus_decode_u64, lotus_encode_u64_framed, EncodedLotus, LotusError};
pub use path::*;
pub use seed::find_seed_match;
pub use seed_detect::{detect_seed_matches, MatchRecord};
pub use seed_index::{index_to_seed, seed_to_index};
pub use seed_logger::{
    log_seed, log_seed_to, resume_seed_index, resume_seed_index_from, HashEntry, ResourceLimits,
};
pub use stats::Stats;
pub use tile::{chunk_blocks, flush_chunk, load_chunk, BlockChunk, TileMap};
pub use tlmr::{
    decode_tlmr_header, encode_tlmr_header, truncated_hash, truncated_hash_bits, TlmrError,
    TlmrHeader, LOTUS_PRESET_VERSION, TLMR_FORMAT_VERSION, TLMR_HEADER_LEN,
};

pub fn print_compression_status(original: usize, compressed: usize) {
    let ratio = 100.0 * (1.0 - compressed as f64 / original as f64);
    eprintln!(
        "Compression: {} → {} bytes ({:.2}%)",
        original, compressed, ratio
    );
}

#[derive(Debug, Clone)]
pub enum Region {
    Raw(Vec<u8>),
    Compressed(Vec<u8>, Header),
}

/// Decompress a single region respecting a byte limit.
///
/// Only raw regions are supported. Compressed regions are ignored as
/// seed-driven decoding is not yet implemented.
pub fn decompress_region_with_limit(
    region: &Region,
    _block_size: usize,
    limit: usize,
) -> Option<Vec<u8>> {
    match region {
        Region::Raw(bytes) => {
            if bytes.len() <= limit {
                Some(bytes.clone())
            } else {
                None
            }
        }
        Region::Compressed(_data, _header) => None,
    }
}

/// Decompress a full byte stream with an optional limit.
///
/// Files begin with a fixed `.tlmr` v1 header describing protocol version,
/// Lotus preset, hasher, block shape, search limits, layer count, lengths, and
/// a truncated output hash. Each subsequent region is prefixed with a normal
/// Lotus header. Version 1 is intentionally one-layer-decodable.
pub fn decompress_with_limit(
    input: &[u8],
    config: &Config,
    limit: usize,
) -> Result<Vec<u8>, TelomereError> {
    let header = decode_tlmr_header(input)?;
    if config.memory_limit == 0 {
        return Err(TelomereError::Config(
            "memory_limit must be greater than zero".into(),
        ));
    }
    let payload_len: usize = header
        .payload_len
        .try_into()
        .map_err(|_| TelomereError::Header("payload length out of range".into()))?;
    if input.len() != TLMR_HEADER_LEN + payload_len {
        return Err(TelomereError::Header("payload length mismatch".into()));
    }
    let original_len: usize = header
        .original_len
        .try_into()
        .map_err(|_| TelomereError::Header("original length out of range".into()))?;
    if original_len > limit {
        return Err(TelomereError::Header("output limit exceeded".into()));
    }
    if original_len > config.memory_limit {
        return Err(TelomereError::Header("memory limit exceeded".into()));
    }
    let header_config = Config {
        block_size: header.block_size,
        max_seed_len: header.max_seed_len,
        max_arity: header.max_arity,
        hash_bits: header.hash_bits,
        hasher: header.hasher,
        seed_expansions: std::collections::HashMap::new(),
        enable_superposition: false,
        memory_limit: config.memory_limit,
    };
    header_config.validate()?;

    let mut offset = TLMR_HEADER_LEN;
    let block_size = header.block_size;
    let mut out = Vec::new();

    let expander = header_config.get_expander();

    loop {
        if offset == input.len() {
            break;
        }
        let slice = input
            .get(offset..)
            .ok_or_else(|| TelomereError::Header("orphan/truncated bits".into()))?;
        let (decoded, bits) = decode_lotus_header(slice)
            .map_err(|_| TelomereError::Header("orphan/truncated bits".into()))?;
        let byte_len = (bits + 7) / 8;

        if decoded.is_literal {
            offset += byte_len;
            let remaining_output = original_len.saturating_sub(out.len());
            let bytes = remaining_output.min(block_size);
            if out.len() + bytes > limit || offset + bytes > input.len() {
                return Err(TelomereError::Header("invalid header field".into()));
            }
            out.extend_from_slice(&input[offset..offset + bytes]);
            offset += bytes;
        } else {
            if decoded.payload_bits.len() % 8 != 0 {
                return Err(TelomereError::Header(
                    "non-byte-aligned seed payloads are not supported".into(),
                ));
            }
            let encoded_seed_bytes = pack_bits(&decoded.payload_bits);
            if encoded_seed_bytes.is_empty() || encoded_seed_bytes.len() > header.max_seed_len {
                return Err(TelomereError::Header("invalid seed payload length".into()));
            }
            let arity = decoded.arity as usize;
            if arity == 0 || arity > header.max_arity as usize {
                return Err(TelomereError::Header("invalid header field".into()));
            }
            let span_len = arity * block_size;

            if out.len() + span_len > limit || out.len() + span_len > original_len {
                return Err(TelomereError::Header("invalid header field".into()));
            }

            let current_len = out.len();
            out.resize(current_len + span_len, 0);
            expander.expand_into(&encoded_seed_bytes, &mut out[current_len..]);

            offset += byte_len;
        }
        if offset == input.len() {
            break;
        }
    }
    if out.len() != original_len {
        return Err(TelomereError::Header("output length mismatch".into()));
    }
    let hash = truncated_hash_bits(&out, expander.as_ref(), header.hash_bits);
    if hash != header.output_hash {
        return Err(TelomereError::Header("output hash mismatch".into()));
    }
    Ok(out)
}

/// Convenience wrapper without a limit.
pub fn decompress(input: &[u8], config: &Config) -> Result<Vec<u8>, TelomereError> {
    decompress_with_limit(input, config, usize::MAX)
}
