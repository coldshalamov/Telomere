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
pub use block::{Block, BlockTable, BlockChange, split_into_blocks, group_by_bit_length};

use sha2::Digest;


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

use std::collections::HashMap;
use std::ops::RangeInclusive;
use sha2::Sha256;


use crate::compress::FallbackSeeds;
use crate::path::PathGloss;

/// Compress the input using seed-aware block compression.
pub fn compress(
    data: &[u8],
    _lens: RangeInclusive<u8>,
    _limit: Option<u64>,
    mut live: LiveStats,
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

        live.maybe_log(span, &[], false);



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

    live.maybe_log(span, &seed_bytes, true);

    if header.seed_index == 0 && header.arity <= 3 {
        // It's a fallback — treat as literal passthrough
        let passthrough_header = encode_header(0, 36 + header.arity); // 37/38/39
        out.extend_from_slice(&passthrough_header);
        out.extend_from_slice(&span[..used]);
    } else {
        // Valid compression match
        out.extend_from_slice(&encode_header(header.seed_index, header.arity));
        out.extend_from_slice(&span[..used]);
    }

    offset += used;
} else {
    // Fully failed to compress — fallback to literal
    let blocks = ((data.len() - offset) / BLOCK_SIZE).min(3).max(1);
    let bytes = blocks * BLOCK_SIZE;
    let passthrough_header = encode_header(0, 36 + blocks); // 37–39
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

    // Dump fallback belief scores
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


/// Reconstruct a region of data from a compressed form (seed + header).
/// No gloss is used — full stateless unpacking.
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
/// You may update this to follow your dynamic toggle spec.
pub fn arity_to_span_len(arity: u32) -> Result<usize, Box<dyn std::error::Error>> {
    // Placeholder: arity 0 = 3 bytes, grows by 3 each step
    Ok(3 * (arity as usize + 1))
}


