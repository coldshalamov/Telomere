mod bloom;
mod compress;
mod compress_stats;
mod gloss;
mod header;
mod sha_cache;
mod path;
mod seed_logger;
mod gloss_prune_hook;
mod live_window;
mod stats;
mod block;

pub use bloom::*;
pub use compress::{TruncHashTable, compress_block, dump_beliefmap_json, dump_gloss_to_csv};
pub use compress_stats::{CompressionStats, write_stats_csv};
pub use gloss::*;
pub use header::{Header, encode_header, decode_header, HeaderError};
pub use sha_cache::*;
pub use path::*;
pub use seed_logger::{resume_seed_index, log_seed, HashEntry};
pub use gloss_prune_hook::run as gloss_prune_hook;
pub use live_window::{LiveStats, print_window};
pub use stats::Stats;
pub use block::{
    Block,
    BlockTable,
    BlockChange,
    detect_bundles,
    split_into_blocks,
    group_by_bit_length,
    apply_block_changes,
};

use sha2::{Digest, Sha256};
use std::collections::HashMap;
use std::ops::RangeInclusive;
use crate::compress::FallbackSeeds;

pub const BLOCK_SIZE: usize = 3;

pub fn print_compression_status(original: usize, compressed: usize) {
    let ratio = 100.0 * (1.0 - compressed as f64 / original as f64);
    eprintln!("Compression: {} → {} bytes ({:.2}%)", original, compressed, ratio);
}

#[derive(Debug, Clone)]
pub enum Region {
    Raw(Vec<u8>),
    Compressed(Vec<u8>, Header),
}

/// Compress the input using seed-aware block compression.
pub fn compress(
    data: &[u8],
    _lens: RangeInclusive<u8>,
    _limit: Option<u64>,
    _status: u64,
    _hashes: &mut u64,
    json: bool,
    _gloss: Option<&GlossTable>,
    verbosity: u8,
    _gloss_only: bool,
    _coverage: Option<&mut [bool]>,
    _partials: Option<&mut Vec<u8>>,
    _filter: Option<&mut TruncHashTable>,
) -> Vec<u8> {
    let mut out = Vec::new();
    let mut offset = 0usize;
    let mut counter = 0u64;
    let mut gloss = PathGloss::default();
    let mut fallback = FallbackSeeds::new(0.01, 0.001, BLOCK_SIZE);
    let mut stats = CompressionStats::new();

    while offset + BLOCK_SIZE <= data.len() {
        stats.tick_block();
        let span = &data[offset..];

        if let Some((header, used)) = crate::compress::compress_block(
            span,
            &mut gloss,
            &mut counter,
            Some(&mut fallback),
            0,
            Some(&mut stats),
            None,
        ) {
            let seed_bytes = fallback
                .reverse_index(header.seed_index)
                .unwrap_or_else(|| b"<unknown>".to_vec());

            if header.seed_index == 0 && header.arity <= 3 {
                let passthrough_header = encode_header(0, 36 + header.arity);
                out.extend_from_slice(&passthrough_header);
                out.extend_from_slice(&span[..used]);
            } else {
                out.extend_from_slice(&encode_header(header.seed_index, header.arity));
                out.extend_from_slice(&span[..used]);
            }

            offset += used;
        } else {
            let blocks = ((data.len() - offset) / BLOCK_SIZE).min(3).max(1);
            let bytes = blocks * BLOCK_SIZE;
            let passthrough_header = encode_header(0, 36 + blocks);
            out.extend_from_slice(&passthrough_header);
            out.extend_from_slice(&data[offset..offset + bytes]);
            offset += bytes;
        }
    }

    if offset < data.len() {
        let header = encode_header(0, 40);
        out.extend_from_slice(&header);
        out.extend_from_slice(&data[offset..]);
    }

    let _ = crate::compress::dump_beliefmap_json(&fallback.map, "belief_fallback.json");
    if verbosity >= 2 {
        let _ = crate::compress::dump_gloss_to_csv(&fallback.map, "belief_fallback.csv");
    }

    if !json {
        stats.report();
    }
    let _ = write_stats_csv(&stats, "stats_kolyma.csv");

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

/// Reconstruct a region of data from a compressed form (seed + header).
pub fn unpack_region(header_bytes: &[u8], seed: &[u8]) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let (seed_index, arity, _extra) = decode_header(header_bytes)?;
    let hash_output = sha2::Sha256::digest(seed);
    let span_len = arity_to_span_len(arity as u32)?;

    if span_len > hash_output.len() {
        return Err("Arity too large for available hash output".into());
    }

    Ok(hash_output[..span_len].to_vec())
}

/// Map arity value to span length in bytes.
pub fn arity_to_span_len(arity: u32) -> Result<usize, Box<dyn std::error::Error>> {
    Ok(3 * (arity as usize + 1))
}
