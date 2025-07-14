mod block;
mod bundle;
mod compress;
mod compress_stats;
mod header;
mod live_window;
mod path;
mod decompress;
mod seed_detect;
mod seed_logger;
mod sha_cache;
mod stats;

pub use block::{
    apply_block_changes, detect_bundles, group_by_bit_length, split_into_blocks, Block,
    BlockChange, BlockTable,
};
pub use bundle::{apply_bundle, BlockStatus, MutableBlock};
pub use compress::{compress, compress_block, TruncHashTable};
pub use compress_stats::{write_stats_csv, CompressionStats};
pub use header::{decode_header, encode_header, Header, HeaderError};
pub use live_window::{print_window, LiveStats};
pub use path::*;
pub use seed_detect::{detect_seed_matches, MatchRecord};
pub use seed_logger::{log_seed, resume_seed_index, HashEntry};
pub use sha_cache::*;
pub use stats::Stats;

pub const BLOCK_SIZE: usize = 3;

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
/// MVP: Only supports literal decompression, no gloss/seed paths.
pub fn decompress_region_with_limit(
    region: &Region,
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
                let expected = if header.arity == 40 {
                    data.len()
                } else {
                    (header.arity - 36) * BLOCK_SIZE
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
/// MVP: Only supports literal headers.
pub fn decompress_with_limit(
    input: &[u8],
    limit: usize,
) -> Option<Vec<u8>> {
    let mut offset = 0usize;
    let mut out = Vec::new();
    while offset < input.len() {
        let (seed, arity, bits) = decode_header(&input[offset..]).ok()?;
        offset += (bits + 7) / 8;
        if arity >= 37 && arity <= 39 {
            let blocks = arity - 36;
            let bytes = blocks * BLOCK_SIZE;
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
    Some(out)
}

/// Convenience wrapper without a limit.
pub fn decompress(input: &[u8]) -> Vec<u8> {
    decompress_with_limit(input, usize::MAX).unwrap_or_default()
}
