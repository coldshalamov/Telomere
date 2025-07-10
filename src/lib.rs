mod bloom;
mod compress;
mod compress_stats;
mod gloss;
mod header;
mod sha_cache;
mod path;
mod seed_logger;
mod gloss_prune_hook;

pub use bloom::*;
pub use compress::TruncHashTable;
pub use compress_stats::CompressionStats;
pub use gloss::*;
pub use header::{Header, encode_header, decode_header, HeaderError};
pub use sha_cache::*;
pub use path::*;
pub use seed_logger::{resume_seed_index, log_seed, HashEntry};
pub use gloss_prune_hook::run as gloss_prune_hook;

pub const BLOCK_SIZE: usize = 7;

pub fn print_compression_status(original: usize, compressed: usize) {
    let ratio = 100.0 * (1.0 - compressed as f64 / original as f64);
    eprintln!("Compression: {} → {} bytes ({:.2}%)", original, compressed, ratio);
}

#[derive(Debug, Clone)]
pub enum Region {
    Raw(Vec<u8>),
    Compressed(Vec<u8>, Header),
}

// … FULL compress(), decompress(), decompress_with_limit(), etc.

use sha2::{Digest, Sha256};
use std::collections::HashMap;
use std::ops::RangeInclusive;

/// Compress the input using literal passthrough encoding.
/// This trimmed example simply groups up to three blocks
/// of input per header and appends a final tail.
pub fn compress(
    data: &[u8],
    _lens: RangeInclusive<u8>,
    _limit: Option<u64>,
    _status: u64,
    _hashes: &mut u64,
    _json: bool,
    _gloss: Option<&GlossTable>,
    _verbosity: u8,
    _gloss_only: bool,
    _coverage: Option<&mut [bool]>,
    _partials: Option<&mut Vec<u8>>,
    _filter: Option<&mut TruncHashTable>,
) -> Vec<u8> {
    let mut out = Vec::new();
    let mut offset = 0usize;
    while offset + BLOCK_SIZE <= data.len() {
        let remaining_blocks = (data.len() - offset) / BLOCK_SIZE;
        let blocks = remaining_blocks.min(3);
        let header = encode_header(0, 36 + blocks);
        out.extend_from_slice(&header);
        let bytes = blocks * BLOCK_SIZE;
        out.extend_from_slice(&data[offset..offset + bytes]);
        offset += bytes;
    }
    let header = encode_header(0, 40);
    out.extend_from_slice(&header);
    if offset < data.len() {
        out.extend_from_slice(&data[offset..]);
    }
    out
}

/// Decompress a single region respecting a byte limit.
pub fn decompress_region_with_limit(
    region: &Region,
    table: &GlossTable,
    limit: usize,
) -> Option<Vec<u8>> {
    match region {
        Region::Raw(bytes) => {
            if bytes.len() <= limit { Some(bytes.clone()) } else { None }
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
                if header.seed_index >= table.entries.len() {
                    return None;
                }
                let entry = &table.entries[header.seed_index];
                if entry.decompressed.len() > limit {
                    return None;
                }
                Some(entry.decompressed.clone())
            }
        }
    }
}

/// Decompress a full byte stream with an optional limit.
pub fn decompress_with_limit(
    input: &[u8],
    table: &GlossTable,
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
            if seed >= table.entries.len() {
                return None;
            }
            let entry = &table.entries[seed];
            if out.len() + entry.decompressed.len() > limit {
                return None;
            }
            out.extend_from_slice(&entry.decompressed);
        }
    }
    Some(out)
}

/// Convenience wrapper without a limit.
pub fn decompress(input: &[u8], table: &GlossTable) -> Vec<u8> {
    decompress_with_limit(input, table, usize::MAX).unwrap_or_default()
}

/// Seed-first compression demonstration.
pub fn seed_first_compress(
    data: &[u8],
    seeds: &[Vec<u8>],
    hash_table: &HashMap<Vec<u8>, [u8; 32]>,
) -> Vec<u8> {
    #[derive(Clone)]
    struct Cand { seed_idx: usize, seed_len: usize, len: usize }
    let mut cands: HashMap<usize, Cand> = HashMap::new();
    for (idx, seed) in seeds.iter().enumerate() {
        let digest = hash_table
            .get(seed)
            .cloned()
            .unwrap_or_else(|| Sha256::digest(seed).into());
        let out_bytes = digest.as_slice();
        let mut pos = 0usize;
        while let Some(p) = data[pos..].windows(out_bytes.len()).position(|w| w == out_bytes) {
            let off = pos + p;
            let entry = cands.entry(off).or_insert(Cand { seed_idx: idx, seed_len: seed.len(), len: out_bytes.len() });
            if seed.len() < entry.seed_len || out_bytes.len() > entry.len {
                *entry = Cand { seed_idx: idx, seed_len: seed.len(), len: out_bytes.len() };
            }
            pos = off + 1;
        }
    }
    let mut out = Vec::new();
    let mut pos = 0usize;
    while pos < data.len() {
        if let Some(c) = cands.get(&pos) {
            let blocks = (c.len + BLOCK_SIZE - 1) / BLOCK_SIZE;
            let header = encode_header(c.seed_idx, blocks);
            out.extend_from_slice(&header);
            pos += c.len;
            continue;
        }
        if pos + BLOCK_SIZE > data.len() {
            let header = encode_header(0, 40);
            out.extend_from_slice(&header);
            out.extend_from_slice(&data[pos..]);
            return out;
        }
        let remaining_blocks = (data.len() - pos) / BLOCK_SIZE;
        let blocks = remaining_blocks.min(3).max(1);
        let header = encode_header(0, 36 + blocks);
        out.extend_from_slice(&header);
        let bytes = blocks * BLOCK_SIZE;
        out.extend_from_slice(&data[pos..pos + bytes]);
        pos += bytes;
    }
    let header = encode_header(0, 40);
    out.extend_from_slice(&header);
    out
}
