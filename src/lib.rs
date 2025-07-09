use std::collections::HashMap;
use std::ops::RangeInclusive;
use std::time::Instant;

use sha2::{Digest, Sha256};

mod bloom;
mod gloss;
mod header;
mod sha_cache;

pub use bloom::*;
pub use gloss::*;
pub use header::{Header, encode_header, decode_header, HeaderError};
pub use sha_cache::*;

const BLOCK_SIZE: usize = 7;

#[derive(Debug, Clone)]
pub enum Region {
    Raw(Vec<u8>),
    Compressed(Vec<u8>, Header),
}

pub fn compress(
    data: &[u8],
    seed_len_range: RangeInclusive<u8>,
    seed_limit: Option<u64>,
    status_interval: u64,
    hash_counter: &mut u64,
    json_out: bool,
    gloss: Option<&GlossTable>,
    verbosity: u8,
    gloss_only: bool,
    mut coverage: Option<&mut [bool]>,
    mut partials: Option<&mut Vec<(Vec<u8>, Header)>>,
) -> Vec<u8> {
    let start = Instant::now();
    let mut chain: Vec<Region> = data
        .chunks(BLOCK_SIZE)
        .map(|b| Region::Raw(b.to_vec()))
        .collect();
    let original_regions = chain.len();
    let original_bytes = data.len();
    let mut brute_matches = 0u64;
    let mut gloss_matches = 0u64;
    let mut sha_cache: HashMap<Vec<u8>, [u8; 32]> = HashMap::new();
    let mut arity_counts: HashMap<u8, u64> = HashMap::new();

    // (Compression logic continues unchanged from the rest of your project...)

    // Placeholder for rest of the function
    // (You would retain your full existing compression logic here)

    // Dummy return to allow compiling
    Vec::new()
}

pub fn decompress_region_with_limit(
    region: &Region,
    gloss: &GlossTable,
    max_bytes: usize,
) -> Option<Vec<u8>> {
    match region {
        Region::Raw(bytes) => {
            if bytes.len() > max_bytes {
                None
            } else {
                Some(bytes.clone())
            }
        }
        Region::Compressed(_, header) => {
            let entry = gloss.entries.get(header.seed_index)?;
            if entry.header.arity != header.arity {
                return None;
            }
            if entry.decompressed.len() > max_bytes {
                None
            } else {
                Some(entry.decompressed.clone())
            }
        }
    }
}

pub fn decompress_with_limit(
    mut data: &[u8],
    gloss: &GlossTable,
    max_bytes: usize,
) -> Option<Vec<u8>> {
    let mut out = Vec::new();
    let mut offset = 0usize;
    while offset < data.len() {
        let (seed_idx, arity, bits) = decode_header(&data[offset..]).ok()?;
        let header = Header { seed_index: seed_idx, arity };
        offset += (bits + 7) / 8;
        if header.is_literal() {
            let blocks = header.arity - 37;
            let byte_count = blocks * BLOCK_SIZE;
            if offset + byte_count > data.len() {
                return None;
            }
            let remaining = max_bytes.checked_sub(out.len())?;
            if byte_count > remaining {
                return None;
            }
            out.extend_from_slice(&data[offset..offset + byte_count]);
            offset += byte_count;
        } else {
            let region = Region::Compressed(Vec::new(), header);
            let remaining = max_bytes.checked_sub(out.len())?;
            let bytes = decompress_region_with_limit(&region, gloss, remaining)?;
            out.extend_from_slice(&bytes);
        }
    }
    Some(out)
}

pub fn decompress(data: &[u8], gloss: &GlossTable) -> Vec<u8> {
    decompress_with_limit(data, gloss, usize::MAX).expect("decompression failed")
}
