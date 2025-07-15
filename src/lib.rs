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
pub use seed_logger::{log_seed, resume_seed_index, HashEntry};
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
/// Only literal passthrough data is supported. Headers may use the
/// single-byte arity codes 29–32 or the standard encoded headers.
pub fn decompress_region_with_limit(
    region: &Region,
    block_size: usize,
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
        Region::Compressed(data, header) => {
            if header.is_literal() {
                let expected = if header.arity == 32 || header.arity == 40 {
                    data.len()
                } else if header.arity >= 29 && header.arity <= 31 {
                    (header.arity - 28) * block_size
                } else {
                    (header.arity - 36) * block_size
                };
                if data.len() != expected || data.len() > limit {
                    return None;
                }
                Some(data.clone())
            } else {
                // Seed-backed decompression disabled in MVP.
                None
            }
        }
    }
}

/// Decompress a full byte stream with an optional limit.
///
/// Literal passthrough blocks may use either the variable-length header
/// scheme (arities 37–40) or the reserved single-byte codes 29–32.
/// Codes 29–31 represent one to three literal blocks while code 32
/// marks a terminal tail smaller than `block_size` bytes.
pub fn decompress_with_limit(input: &[u8], limit: usize) -> Option<Vec<u8>> {
    if input.is_empty() {
        return Some(Vec::new());
    }
    let (mut offset, orig_size, block_size) = decode_file_header(input)?;
    let mut out = Vec::new();
    while offset < input.len() {
        // Fast path for reserved single-byte literals and terminal blocks.
        if matches!(input[offset], 29..=32) {
            let code = input[offset];
            offset += 1;
            if code == 32 {
                let tail = &input[offset..];
                if out.len() + tail.len() > limit {
                    return None;
                }
                out.extend_from_slice(tail);
                offset = input.len();
                break;
            } else {
                let blocks = (code as usize) - 28;
                let bytes = blocks * block_size;
                if offset + bytes > input.len() || out.len() + bytes > limit {
                    return None;
                }
                out.extend_from_slice(&input[offset..offset + bytes]);
                offset += bytes;
                continue;
            }
        }

        let (_, arity, bits) = decode_header(&input[offset..]).ok()?;
        offset += (bits + 7) / 8;
        if arity >= 37 && arity <= 39 {
            let blocks = arity - 36;
            let bytes = blocks * block_size;
            if offset + bytes > input.len() || out.len() + bytes > limit {
                return None;
            }
            out.extend_from_slice(&input[offset..offset + bytes]);
            offset += bytes;
        } else if arity == 40 {
            let tail = &input[offset..];
            if out.len() + tail.len() > limit {
                return None;
            }
            out.extend_from_slice(tail);
            offset = input.len();
            break;
        } else {
            // Seed-backed decompression disabled in MVP.
            return None;
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
