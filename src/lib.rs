mod block;
mod bundle;
mod compress;
mod compress_stats;
mod file_header;
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
/// Files begin with an EVQL header describing the original length and block
/// size. Each subsequent region is prefixed with a normal header. Arity values
/// `29`–`32` denote literal passthrough data and are followed by one to three
/// full blocks or a final tail. All other arities would require seed-based
/// decoding which is not implemented here.
pub fn decompress_with_limit(input: &[u8], limit: usize) -> Option<Vec<u8>> {
    if input.is_empty() {
        return Some(Vec::new());
    }
    let (mut offset, orig_size, block_size) = decode_file_header(input)?;
    let mut out = Vec::new();
    while out.len() < orig_size {
        let slice = input.get(offset..)?;
        let (header, bits) = decode_header(slice).ok()?;
        offset += (bits + 7) / 8;
        match header {
            Header::Literal => {
                let bytes = block_size;
                if out.len() + bytes > orig_size
                    || offset + bytes > input.len()
                    || out.len() + bytes > limit
                {
                    return None;
                }
                out.extend_from_slice(&input[offset..offset + bytes]);
                offset += bytes;
            }
            Header::LiteralLast => {
                let bytes = orig_size - out.len();
                if offset + bytes > input.len() || out.len() + bytes > limit {
                    return None;
                }
                out.extend_from_slice(&input[offset..offset + bytes]);
                offset += bytes;
                break;
            }
            _ => {
                return None;
            }
        }
    }
    if out.len() == orig_size {
        Some(out)
    } else {
        None
    }
}

/// Convenience wrapper without a limit.
pub fn decompress(input: &[u8]) -> Vec<u8> {
    decompress_with_limit(input, usize::MAX).unwrap_or_default()
}
