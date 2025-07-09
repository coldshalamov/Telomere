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

    // (Compression logic would normally run here and replace Raw regions with
    // compressed seeds. The stubbed implementation skips this step.)

    // Convert any remaining Raw regions into literal passthroughs using the
    // reserved arity codes. Consecutive raw blocks are grouped up to three
    // blocks per passthrough.
    let mut final_chain = Vec::new();
    let mut i = 0;
    while i < chain.len() {
        match &chain[i] {
            Region::Raw(bytes) => {
                let mut collected = bytes.clone();
                let mut blocks = 1usize;
                while blocks < 3 && i + blocks < chain.len() {
                    if let Region::Raw(next) = &chain[i + blocks] {
                        collected.extend_from_slice(next);
                        blocks += 1;
                    } else {
                        break;
                    }
                }
                let arity = match blocks {
                    1 => 38,
                    2 => 39,
                    _ => 40,
                };
                final_chain.push(Region::Compressed(collected, Header { seed_index: 0, arity }));
                i += blocks;
            }
            other => {
                final_chain.push(other.clone());
                i += 1;
            }
        }
    }

    // Serialize the chain by emitting headers in order. Seeds are ignored by the
    // current decoder implementation so they are not written to the output.
    let mut out = Vec::new();
    for region in final_chain {
        if let Region::Compressed(_, header) = region {
            out.extend(encode_header(header.seed_index, header.arity));
        }
    }

    out
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
        let region = Region::Compressed(Vec::new(), header);
        let remaining = max_bytes.checked_sub(out.len())?;
        let bytes = decompress_region_with_limit(&region, gloss, remaining)?;
        out.extend_from_slice(&bytes);
    }
    Some(out)
}

pub fn decompress(data: &[u8], gloss: &GlossTable) -> Vec<u8> {
    decompress_with_limit(data, gloss, usize::MAX).expect("decompression failed")
}
