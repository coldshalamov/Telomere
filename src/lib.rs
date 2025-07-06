//! Core logic for the Inchworm compression system.

use sha2::{Digest, Sha256};
use serde::{Deserialize, Serialize};
use serde_json::json;
use std::ops::RangeInclusive;

mod sha_cache;
mod bloom;
mod gloss;
pub use gloss::{GlossEntry, GlossTable};

use sha_cache::ShaCache;
use bloom::Bloom;

/// Fixed block size in bytes.
pub const BLOCK_SIZE: usize = 7;
/// Size of an encoded header in bytes.
pub const HEADER_SIZE: usize = 3;
/// Reserved seed byte used for literal fallbacks.
pub const FALLBACK_SEED: u8 = 0xA5;

/// A single compressed or literal block.
#[derive(Clone)]
pub enum Region {
    Raw(Vec<u8>),
    Compressed(Vec<u8>, Header),
}

impl Region {
    pub fn encoded_len(&self) -> usize {
        match self {
            Region::Raw(_) => 1 + HEADER_SIZE + BLOCK_SIZE,
            Region::Compressed(seed, _) => seed.len() + HEADER_SIZE,
        }
    }
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
pub struct Header {
    pub seed_len: u8,
    pub nest_len: u32,
    pub arity: u8,
}

impl Header {
    pub fn pack(self) -> [u8; HEADER_SIZE] {
        let raw = ((self.seed_len as u32) << 22)
            | ((self.nest_len as u32) << 2)
            | (self.arity as u32);
        raw.to_be_bytes()[1..4].try_into().unwrap()
    }

    pub fn unpack(bytes: [u8; HEADER_SIZE]) -> Self {
        let raw = u32::from_be_bytes([0, bytes[0], bytes[1], bytes[2]]);
        Self {
            seed_len: ((raw >> 22) & 0b11) as u8,
            nest_len: ((raw >> 2) & 0x000F_FFFF) as u32,
            arity: (raw & 0b11) as u8,
        }
    }
}

pub fn is_fallback(seed: &[u8], header: [u8; HEADER_SIZE]) -> bool {
    seed == [FALLBACK_SEED] && header == [0; HEADER_SIZE]
}

pub fn encode_region(region: &Region) -> Vec<u8> {
    match region {
        Region::Raw(bytes) => {
            let mut out = Vec::with_capacity(1 + HEADER_SIZE + BLOCK_SIZE);
            out.push(FALLBACK_SEED);
            out.extend_from_slice(&[0; HEADER_SIZE]);
            out.extend_from_slice(bytes);
            out
        }
        Region::Compressed(seed, header) => {
            let mut out = Vec::with_capacity(seed.len() + HEADER_SIZE);
            out.extend_from_slice(seed);
            out.extend_from_slice(&header.pack());
            out
        }
    }
}

fn decode_region_safe(data: &[u8]) -> Option<(Region, usize)> {
    for n in 1..=4 {
        if data.len() < n + HEADER_SIZE {
            continue;
        }
        let seed = &data[..n];
        let header_bytes: [u8; HEADER_SIZE] = data[n..n + HEADER_SIZE].try_into().ok()?;
        let header = Header::unpack(header_bytes);
        if header.seed_len as usize + 1 == n {
            let consumed = n + HEADER_SIZE;
            if is_fallback(seed, header_bytes) {
                if data.len() < consumed + BLOCK_SIZE {
                    return None;
                }
                let block = data[consumed..consumed + BLOCK_SIZE].to_vec();
                return Some((Region::Raw(block), consumed + BLOCK_SIZE));
            } else {
                return Some((Region::Compressed(seed.to_vec(), header), consumed));
            }
        }
    }
    None
}

pub(crate) fn decompress_region_safe(region: &Region) -> Option<Vec<u8>> {
    match region {
        Region::Raw(bytes) => Some(bytes.clone()),
        Region::Compressed(seed, header) => {
            let digest = Sha256::digest(seed);
            if header.arity == 0 {
                Some(digest[..BLOCK_SIZE].to_vec())
            } else {
                let len = header.nest_len as usize;
                if len > digest.len() {
                    return None;
                }
                decompress_safe(&digest[..len])
            }
        }
    }
}

pub(crate) fn decompress_safe(mut data: &[u8]) -> Option<Vec<u8>> {
    let mut out = Vec::new();
    let mut offset = 0;
    while offset < data.len() {
        let (region, consumed) = decode_region_safe(&data[offset..])?;
        offset += consumed;
        out.extend_from_slice(&decompress_region_safe(&region)?);
    }
    Some(out)
}


pub fn print_stats(
    chain: &[Region],
    original_bytes: usize,
    original_regions: usize,
    hashes: u64,
    matches: u64,
    json_out: bool,
    final_stats: bool,
) {
    let encoded = chain.iter().map(|r| r.encoded_len()).sum::<usize>();
    let ratio = encoded as f64 * 100.0 / original_bytes as f64;
    let hashes_per_byte = if encoded == 0 {
        0.0
    } else {
        hashes as f64 / encoded as f64
    };

    if final_stats && json_out {
        let obj = json!({
            "input_bytes": original_bytes,
            "output_bytes": encoded,
            "compression_ratio": ratio,
            "total_hashes": hashes,
            "hashes_per_byte": hashes_per_byte,
        });
        println!("{}", obj);
    } else if final_stats {
        eprintln!("Compression complete!");
        eprintln!("Input: {} bytes", original_bytes);
        eprintln!("Output: {} bytes", encoded);
        eprintln!("Ratio: {:.2}%", ratio);
        eprintln!("Total hashes: {}", hashes);
        eprintln!("Hashes/byte: {:.1}", hashes_per_byte);
    } else {
        eprintln!(
            "[{:.2}M hashes] {} matches | Chain: {} → {} regions | {} → {} bytes ({:.2}%)",
            hashes as f64 / 1_000_000.0,
            matches,
            original_regions,
            chain.len(),
            original_bytes,
            encoded,
            ratio
        );
    }
}
