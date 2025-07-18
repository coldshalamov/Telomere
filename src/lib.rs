//! Telomere compression library exposing low level building blocks.
//!
//! The crate is intentionally minimal and only supports literal
//! passthrough compression at the moment.  APIs may evolve as the
//! generative search is implemented.

mod block;
mod bundle;
mod compress;
mod compress_stats;
mod file_header;
mod tlmr;
mod error;
// Gloss table support has been removed for the MVP.  The original
// implementation used precomputed decompressed strings to accelerate
// seed matching.  Future versions may reintroduce a `gloss` module.
mod candidate;
mod hash_reader;
mod header;
pub mod io_utils;
mod live_window;
mod path;
mod seed_detect;
mod seed_index;
mod seed_logger;
mod sha_cache;
mod stats;
use sha2::{Digest, Sha256};

pub use block::{
    apply_block_changes, collapse_branches, detect_bundles, finalize_table, group_by_bit_length,
    prune_branches, run_all_passes, split_into_blocks, Block, BlockChange, BlockTable,
    BranchStatus,
};
pub use bundle::{apply_bundle, BlockStatus, MutableBlock};
pub use candidate::{prune_candidates, Block as CandidateBlock, Candidate};
pub use compress::{compress, compress_block, compress_multi_pass, TruncHashTable};
pub use compress_stats::{write_stats_csv, CompressionStats};
pub use file_header::{decode_file_header, encode_file_header};
pub use hash_reader::lookup_seed;
pub use header::{
    decode,
    decode_header,
    encode_header,
    BitReader,
    Config,
    Header,
    HeaderError,
    TelomereError,
};
pub use io_utils::*;
pub use live_window::{print_window, LiveStats};
pub use path::*;
pub use seed_detect::{detect_seed_matches, MatchRecord};
pub use seed_index::{index_to_seed, seed_to_index};
pub use seed_logger::{
    log_seed, log_seed_to, resume_seed_index, resume_seed_index_from, HashEntry, ResourceLimits,
};
pub use sha_cache::*;
pub use stats::Stats;
pub use tlmr::{decode_tlmr_header, encode_tlmr_header, truncated_hash, TlmrError, TlmrHeader};
pub use error::TelomereError;

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

/// Generate `len` bytes by repeatedly hashing `seed` with SHA-256.
fn expand_seed(seed: &[u8], len: usize) -> Vec<u8> {
    let mut out = Vec::with_capacity(len);
    let mut cur = seed.to_vec();
    while out.len() < len {
        let digest: [u8; 32] = Sha256::digest(&cur).into();
        out.extend_from_slice(&digest);
        cur = digest.to_vec();
    }
    out.truncate(len);
    out
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
/// region is prefixed with a normal header.
pub fn decompress_with_limit(input: &[u8], limit: usize) -> Result<Vec<u8>, TelomereError> {
    if input.len() < 3 {
        return Err(TelomereError::Decode("header too short".into()));
    }
    let header = decode_tlmr_header(input).map_err(|e| TelomereError::Decode(format!("{e}")))?;
    let mut offset = 3usize;
    let block_size = header.block_size;
    let last_block_size = header.last_block_size;
    let mut out = Vec::new();
    loop {
        let slice = input.get(offset..).ok_or_else(|| TelomereError::Decode("invalid header field".into()))?;
        let (header, bits) = decode_header(slice).map_err(|_| TelomereError::Decode("invalid header field".into()))?;
        offset += (bits + 7) / 8;
        match header {
            Header::Standard { seed_index, arity } => {
                let needed = arity * block_size;
                if out.len() + needed > limit {
                    return Err(TelomereError::Decode("invalid header field".into()));
                }
                let seed = index_to_seed(seed_index, 2)?;
                let generated = expand_seed(&seed, needed);
                out.extend_from_slice(&generated);
            }
            Header::Literal => {
                let bytes = block_size;
                if out.len() + bytes > limit || offset + bytes > input.len() {
                    return Err(TelomereError::Decode("invalid header field".into()));
                }
                out.extend_from_slice(&input[offset..offset + bytes]);
                offset += bytes;
            }
            Header::LiteralLast => {
                let bytes = last_block_size;
                if out.len() + bytes > limit || offset + bytes > input.len() {
                    return Err(TelomereError::Decode("invalid header field".into()));
                }
                out.extend_from_slice(&input[offset..offset + bytes]);
                offset += bytes;
                break;
            }
        }
        if offset == input.len() {
            // No more data left to decode.
            break;
        }
    }
    let hash = truncated_hash(&out);
    if hash != header.output_hash {
        return Err(TelomereError::Decode("output hash mismatch".into()));
    }
    Ok(out)
}

/// Convenience wrapper without a limit.
pub fn decompress(input: &[u8]) -> Vec<u8> {
    decompress_with_limit(input, usize::MAX).unwrap_or_default()
}
