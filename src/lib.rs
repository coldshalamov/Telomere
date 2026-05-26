// The sorted index backend uses memmap2 for large tier files. The only unsafe
// operation is the file mapping call, isolated in seed_expansion_index.rs.
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
//! Telomere: experimental stateless lossless generative compression via
//! BLAKE3/SHA-256 seed expansion.
//!
//! The stable `.tlmr` v1 path partitions input into fixed-size blocks and emits
//! a compact Lotus `(arity, seed)` record only when a deterministic seed
//! expansion is smaller than the matched span. Unmatched bytes are stored as
//! literals. Experimental `.tlmr` v2 indexed and streaming paths add explicit
//! recursive layers and seed-span records, but they do not claim universal or
//! open-ended convergence.

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
mod gpu;
mod hash_reader;
pub mod hasher;
mod header;
mod hybrid;
mod indexed;
pub mod io_utils;
mod live_window;
mod path;
mod public_preset;
mod seed;
mod seed_detect;
mod seed_expansion_index;
mod seed_index;
mod seed_logger;
mod stats;
mod streaming;
pub mod superposition;
mod tile;
mod tlmr;
mod tlmr_v2;
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
};
pub use compress_stats::{write_stats_csv, CompressionStats, PassStats, RunSummary};
pub use config::{Config, HasherKind};
pub use error::TelomereError;
pub use gpu::GpuSeedMatcher;
pub use hash_reader::lookup_seed;
pub use header::{
    decode_header, decode_lotus_header, decode_v1_record_from_reader, encode_header,
    encode_lotus_header, encode_v1_record_into_writer, pack_bits, v1_record_bit_len, BitReader,
    DecodedHeader, Header, LOTUS_ARITY_J_BITS, LOTUS_ARITY_LITERAL_VALUE, LOTUS_ARITY_TIERS,
    LOTUS_J_BITS, LOTUS_TIERS,
};
pub use hybrid::{compress_hybrid, CpuMatchRecord, GpuMatchRecord};
pub use indexed::{
    compress_indexed_v2_with_chunked_span_step_and_telemetry, compress_indexed_v2_with_index,
    compress_indexed_v2_with_span_step_and_telemetry, compress_indexed_v2_with_telemetry,
    estimate_target_table_chunk_upper_bound_for_tiers, estimate_target_table_upper_bound_for_tiers,
    select_weighted_candidates_for_tests, IndexedCandidate, IndexedLayerTelemetry,
    IndexedTelemetry, IndexedTierTelemetry, SelectedSpanTelemetry,
};
pub use io_utils::*;
pub use live_window::{print_window, LiveStats};
pub use path::*;
pub use public_preset::{
    public_preset_selective_decode_framed, public_preset_selective_framed,
    PublicPresetTransformStats, PUBLIC_PRESET_CODEWORD_LEN, PUBLIC_PRESET_SELECTIVE_MIN_TOKEN_LEN,
    PUBLIC_PRESET_SELECTIVE_VERSION,
};
pub use seed::find_seed_match;
pub use seed_detect::{detect_seed_matches, MatchRecord};
pub use seed_expansion_index::{
    build_seed_index_to_dir, read_index_manifest, IndexConfig, IndexManifest,
    MmapSeedExpansionIndex, SeedExpansionIndex, SeedHit, SeedLookup, TierSpec, INDEX_VERSION,
    SEED_ORDER_VERSION,
};
pub use seed_index::{index_to_seed, seed_to_index};
pub use seed_logger::{
    log_seed, log_seed_to, resume_seed_index, resume_seed_index_from, HashEntry, ResourceLimits,
};
pub use stats::Stats;
pub use streaming::{
    compress_streaming_v2, compress_streaming_v2_with_chunked_span_step_and_telemetry,
    compress_streaming_v2_with_public_preset_selective_and_telemetry,
    compress_streaming_v2_with_public_preset_selective_config_and_telemetry,
    compress_streaming_v2_with_seed_limit_and_telemetry,
    compress_streaming_v2_with_span_step_and_telemetry, compress_streaming_v2_with_telemetry,
    estimate_streaming_target_chunk_upper_bound, estimate_streaming_target_table_upper_bound,
    find_streaming_candidates, find_streaming_candidates_chunked_with_span_step,
    find_streaming_candidates_chunked_with_span_step_and_seed_limit,
    find_streaming_candidates_profit_window_with_span_step,
    find_streaming_candidates_with_span_step,
    find_streaming_candidates_with_span_step_and_seed_limit, seed_limit_from_bits,
    PublicPresetStreamingTelemetry, StreamingLayerTelemetry, StreamingTelemetry,
    StreamingTierTelemetry,
};
pub use tile::{chunk_blocks, flush_chunk, load_chunk, BlockChunk, TileMap};
pub use tlmr::{
    decode_tlmr_header, decode_tlmr_header_with_len, encode_tlmr_header, tlmr_header_byte_len,
    truncated_hash, truncated_hash_bits, TlmrHeader, LOTUS_PRESET_VERSION, TLMR_FORMAT_VERSION,
    V1_MAGIC_VERSION_LEN,
};
pub use tlmr_v2::{
    decode_layer_descriptor_from, decode_tlmr_v2_header, decode_tlmr_v2_layer_descriptors,
    decode_v2_header_and_descriptors, encode_header_into_writer, encode_layer_descriptor_into,
    encode_tlmr_v2_header, encode_v2_file, encode_v2_file_with_bit_len, v2_literal_record,
    v2_literal_record_into_writer, v2_seed_span_record, v2_seed_span_record_bit_len,
    v2_seed_span_record_byte_len, v2_seed_span_record_into_writer, EncodedV2Record, TlmrV2Header,
    TlmrV2LayerDescriptor, LOTUS_PRESET_V2, TLMR_V2_FORMAT_VERSION, V2_MAGIC_VERSION_LEN,
    V2_RECORD_TAG_LITERAL, V2_RECORD_TAG_SEED_SPAN, V2_SEED_ORDER_VERSION,
    V2_TIER_POLICY_PUBLIC_PRESET_SELECTIVE, V2_TIER_POLICY_SEED_SPAN,
};

pub fn print_compression_status(original: usize, compressed: usize) {
    let ratio = 100.0 * (1.0 - compressed as f64 / original as f64);
    eprintln!(
        "Compression: {} → {} bytes ({:.2}%)",
        original, compressed, ratio
    );
}

/// Decompress a full byte stream with an optional limit.
///
/// Files begin with a variable-length `.tlmr` v1 header (Lotus-encoded after
/// the raw 5-byte magic+version prefix) describing protocol version, Lotus
/// preset, hasher, block shape, search limits, layer count, lengths, and a
/// truncated output hash. Each subsequent record is prefixed with a Lotus
/// record header (J1D1 arity + J3D2 seed index). Version 1 is intentionally
/// one-layer-decodable.
pub fn decompress_with_limit(
    input: &[u8],
    config: &Config,
    limit: usize,
) -> Result<Vec<u8>, TelomereError> {
    if input.len() >= 5
        && input[0..4] == crate::tlmr::TLMR_MAGIC
        && input[4] == TLMR_V2_FORMAT_VERSION
    {
        let memory_limit = if config.memory_limit == 0 {
            return Err(TelomereError::Config(
                "memory_limit must be greater than zero".into(),
            ));
        } else {
            config.memory_limit
        };
        return tlmr_v2::decompress_v2_with_limit(input, limit, memory_limit);
    }

    let (header, payload_start) = tlmr::decode_tlmr_header_with_len(input)?;
    if config.memory_limit == 0 {
        return Err(TelomereError::Config(
            "memory_limit must be greater than zero".into(),
        ));
    }
    let payload_bit_len: usize = header
        .payload_bit_len
        .try_into()
        .map_err(|_| TelomereError::Header("payload length out of range".into()))?;
    let payload_byte_len = payload_bit_len.div_ceil(8);
    let expected_total = payload_start
        .checked_add(payload_byte_len)
        .ok_or_else(|| TelomereError::Header("payload length overflow".into()))?;
    if input.len() != expected_total {
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

    let block_size = header.block_size;
    let mut out = Vec::new();

    let expander = header_config.get_expander();

    // V1 payload is a single Lotus bit-stream of concatenated records.
    // Per-record byte padding has been eliminated; the only intra-payload
    // padding is the 0..7 alignment pad inside each literal record so its
    // raw bytes land on a byte boundary. The final byte of the file may
    // contain up to 7 trailing pad bits.
    let payload = &input[payload_start..];
    let mut reader = lotus::BitReader::new(payload);
    let last_block_size = header.last_block_size;
    while out.len() < original_len {
        if reader.bits_consumed() > payload_bit_len {
            return Err(TelomereError::Header("orphan/truncated bits".into()));
        }
        let (decoded, _) = decode_v1_record_from_reader(&mut reader)
            .map_err(|_| TelomereError::Header("orphan/truncated bits".into()))?;

        if decoded.is_literal {
            // Mirror encoder padding: skip 0..7 bits to byte boundary, then
            // read raw bytes.
            while reader.bits_consumed() % 8 != 0 {
                let pad = reader
                    .read_bits(1)
                    .map_err(|e| TelomereError::Header(format!("literal pad: {e}")))?;
                if pad != 0 {
                    return Err(TelomereError::Header("nonzero v1 literal pad bit".into()));
                }
            }
            let remaining_output = original_len.saturating_sub(out.len());
            // A literal block is one block, sized by `last_block_size` when
            // it is the final block, otherwise by `block_size`.
            let bytes = if remaining_output <= last_block_size {
                remaining_output
            } else {
                block_size
            };
            if out.len() + bytes > limit || out.len() + bytes > original_len {
                return Err(TelomereError::Header("invalid header field".into()));
            }
            let start = out.len();
            out.resize(start + bytes, 0);
            for slot in &mut out[start..start + bytes] {
                *slot = reader
                    .read_bits(8)
                    .map_err(|e| TelomereError::Header(format!("literal byte: {e}")))?
                    as u8;
            }
        } else {
            let seed_index = usize::try_from(decoded.seed_index)
                .map_err(|_| TelomereError::Header("invalid seed index".into()))?;
            let encoded_seed_bytes = crate::index_to_seed(seed_index, header.max_seed_len)
                .map_err(|_| TelomereError::Header("invalid seed index".into()))?;
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
        }
    }

    // After reconstructing the full output, the bit reader should be at exactly
    // payload_bit_len. Anything beyond that (in the same byte) must be zero
    // pad. There must be no further bits.
    let consumed = reader.bits_consumed();
    if consumed > payload_bit_len {
        return Err(TelomereError::Header("payload bit overflow".into()));
    }
    let trailing = payload_bit_len - consumed;
    if trailing > 7 {
        return Err(TelomereError::Header("excess v1 trailing pad bits".into()));
    }
    for _ in 0..trailing {
        let pad = reader
            .read_bits(1)
            .map_err(|e| TelomereError::Header(format!("trailing pad: {e}")))?;
        if pad != 0 {
            return Err(TelomereError::Header("nonzero v1 trailing pad bit".into()));
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
