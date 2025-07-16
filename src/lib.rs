mod block;
mod bundle;
mod compress;
mod compress_stats;
mod file_header;
mod tlmr;
/// Gloss table support has been removed for the MVP.  The original
/// implementation used precomputed decompressed strings to accelerate
/// seed matching.  Future versions may reintroduce a `gloss` module.
mod header;
mod live_window;
mod path;
mod seed_detect;
mod seed_logger;
mod sha_cache;
mod stats;

pub use block::{
    apply_block_changes, collapse_branches, detect_bundles, finalize_table, group_by_bit_length,
    prune_branches, run_all_passes, split_into_blocks, Block, BlockChange, BlockTable, BranchStatus,
};
pub use bundle::{apply_bundle, BlockStatus, MutableBlock};
pub use compress::{compress, compress_block, TruncHashTable};
pub use compress_stats::{write_stats_csv, CompressionStats};
pub use file_header::{decode_file_header, encode_file_header};
pub use header::{decode_header, encode_header, Header, HeaderError};
pub use tlmr::{decode_tlmr_header, encode_tlmr_header, truncated_hash, TlmrError, TlmrHeader};
pub use live_window::{print_window, LiveStats};
pub use path::*;
pub use seed_detect::{detect_seed_matches, MatchRecord};
pub use seed_logger::{
    log_seed, log_seed_to, resume_seed_index, resume_seed_index_from, HashEntry, ResourceLimits,
};
pub use sha_cache::*;
pub use stats::Stats;

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
/// region is prefixed with a normal header. Arity values
/// `29`–`32` denote literal passthrough data and are followed by one to three
/// full blocks or a final tail. All other arities would require seed-based
/// decoding which is not implemented here.
pub fn decompress_with_limit(input: &[u8], limit: usize) -> Result<Vec<u8>, TlmrError> {
    if input.len() < 3 {
        return Err(TlmrError::TooShort);
    }
    let header = decode_tlmr_header(input)?;
    let mut offset = 3usize;
    let block_size = header.block_size;
    let last_block_size = header.last_block_size;
    let mut out = Vec::new();
    loop {
        let slice = input.get(offset..).ok_or(TlmrError::InvalidField)?;
        let (_, arity, bits) = decode_header(slice).map_err(|_| TlmrError::InvalidField)?;
        offset += (bits + 7) / 8;
        if arity == 32 {
            if offset + last_block_size > input.len() || out.len() + last_block_size > limit {
                return Err(TlmrError::InvalidField);
            }
            out.extend_from_slice(&input[offset..offset + last_block_size]);
            offset += last_block_size;
            break;
        } else if (29..=31).contains(&arity) {
            let blocks = arity - 28;
            let bytes = blocks * block_size;
            if offset + bytes > input.len() || out.len() + bytes > limit {
                return Err(TlmrError::InvalidField);
            }
            out.extend_from_slice(&input[offset..offset + bytes]);
            offset += bytes;
        } else {
            return Err(TlmrError::InvalidField);
        }
        if offset == input.len() {
            if last_block_size != block_size {
                return Err(TlmrError::InvalidField);
            }
            break;
        }
    }
    if offset != input.len() {
        return Err(TlmrError::InvalidField);
    }
    let hash = truncated_hash(&out);
    if hash != header.output_hash {
        return Err(TlmrError::OutputHashMismatch);
    }
    Ok(out)
}

/// Convenience wrapper without a limit.
pub fn decompress(input: &[u8]) -> Vec<u8> {
    decompress_with_limit(input, usize::MAX).unwrap_or_default()
}
