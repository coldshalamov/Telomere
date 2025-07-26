#![cfg_attr(not(feature = "gpu"), deny(unsafe_code))]
//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
//!
//! The crate is intentionally minimal and only supports literal
//! passthrough compression at the moment.  APIs may evolve as the
//! generative search is implemented.

mod block;
mod bundle;
mod bundler;
mod compress;
mod compress_stats;
mod error;
mod file_header;
mod tlmr;
// Gloss table support has been removed for the MVP.  The original
// implementation used precomputed decompressed strings to accelerate
// seed matching.  Future versions may reintroduce a `gloss` module.
mod block_indexer;
mod bundle_select;
mod candidate;
mod config;
mod gpu;
mod hash_reader;
mod header;
mod hybrid;
pub mod io_utils;
mod live_window;
mod path;
mod seed;
mod seed_detect;
mod seed_index;
mod seed_logger;
mod sha_cache;
mod stats;
pub mod superposition;
mod tile;
pub mod types;

pub use block::{
    apply_block_changes, collapse_branches, detect_bundles, finalize_table, group_by_bit_length,
    prune_branches, run_all_passes, split_into_blocks, Block, BlockChange, BlockTable,
    BranchStatus,
};
pub use block_indexer::{brute_force_seed_tables, IndexedBlock, SeedMatch};
pub use bundle::{apply_bundle, BlockStatus, MutableBlock};
pub use bundle_select::{select_bundles, AcceptedBundle, BundleRecord};
pub use bundler::bundle_one_layer;
pub use candidate::{prune_candidates, Block as CandidateBlock, Candidate};
pub use compress::{
    compress, compress_block, compress_block_with_config, compress_multi_pass,
    compress_multi_pass_with_config, compress_with_config, TruncHashTable,
};
pub use compress_stats::{write_stats_csv, CompressionStats};
pub use config::Config;
pub use error::TelomereError;
pub use file_header::{decode_file_header, encode_file_header};
pub use gpu::GpuSeedMatcher;
pub use hash_reader::lookup_seed;
pub use header::{
    decode_arity_bits, decode_header, decode_sigma_bits, decode_span, encode_arity_bits,
    encode_header, encode_sigma_bits, BitReader, Header,
};
pub use hybrid::{compress_hybrid, CpuMatchRecord, GpuMatchRecord};
pub use io_utils::*;
pub use live_window::{print_window, LiveStats};
pub use path::*;
pub use seed::{expand_seed, find_seed_match};
pub use seed_detect::{detect_seed_matches, MatchRecord};
pub use seed_index::{index_to_seed, seed_to_index};
pub use seed_logger::{
    log_seed, log_seed_to, resume_seed_index, resume_seed_index_from, HashEntry, ResourceLimits,
};
pub use sha_cache::*;
pub use stats::Stats;
pub use tile::{chunk_blocks, flush_chunk, load_chunk, BlockChunk, TileMap};
pub use tlmr::{decode_tlmr_header, encode_tlmr_header, truncated_hash, TlmrError, TlmrHeader};

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
/// Files begin with a 3-byte Telomere header describing protocol version,
/// block size, last block size and a truncated output hash. Each subsequent
/// region is prefixed with a normal header. The decoder is strict; no extra bits
/// or unaligned headers are permitted.
pub fn decompress_with_limit(
    input: &[u8],
    config: &Config,
    limit: usize,
) -> Result<Vec<u8>, TelomereError> {
    if input.len() < 3 {
        return Err(TelomereError::Header("header too short".into()));
    }
    let header = decode_tlmr_header(input)?;
    if header.version != 0 || header.block_size != config.block_size || config.hash_bits != 13 {
        return Err(TelomereError::Header("file header mismatch".into()));
    }
    let mut offset = 3usize;
    let mut bits_consumed = 24usize;
    let block_size = header.block_size;
    let last_block_size = header.last_block_size;
    let mut out = Vec::new();
    loop {
        if offset == input.len() {
            break;
        }
        let slice = input
            .get(offset..)
            .ok_or_else(|| TelomereError::Header("orphan/truncated bits".into()))?;
        let (header, bits) = decode_header(slice)
            .map_err(|_| TelomereError::Header("orphan/truncated bits".into()))?;
        let byte_len = (bits + 7) / 8;
        match header {
            Header::Literal => {
                offset += byte_len;
                bits_consumed += byte_len * 8;
                let remaining = input.len() - offset;
                let bytes = if remaining == last_block_size {
                    last_block_size
                } else {
                    block_size
                };
                if out.len() + bytes > limit || offset + bytes > input.len() {
                    return Err(TelomereError::Header("invalid header field".into()));
                }
                out.extend_from_slice(&input[offset..offset + bytes]);
                offset += bytes;
                bits_consumed += bytes * 8;
            }
            Header::Arity(_) => {
                let mut reader = BitReader::from_slice(slice);
                let span = decode_span(&mut reader, config)
                    .map_err(|_| TelomereError::Header("orphan/truncated bits".into()))?;
                let span_bits = reader.bits_read();
                let bytes = span.len();
                if out.len() + bytes > limit {
                    return Err(TelomereError::Header("invalid header field".into()));
                }
                out.extend_from_slice(&span);
                offset += (span_bits + 7) / 8;
                bits_consumed += ((span_bits + 7) / 8) * 8;
            }
        }
        if offset == input.len() {
            // No more data left to decode.
            break;
        }
    }
    if bits_consumed != input.len() * 8 {
        return Err(TelomereError::Header("orphan/truncated bits".into()));
    }
    let hash = truncated_hash(&out);
    if hash != header.output_hash {
        return Err(TelomereError::Header("output hash mismatch".into()));
    }
    Ok(out)
}

/// Convenience wrapper without a limit.
pub fn decompress(input: &[u8], config: &Config) -> Result<Vec<u8>, TelomereError> {
    decompress_with_limit(input, config, usize::MAX)
}
