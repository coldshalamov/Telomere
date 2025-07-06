//! Core logic for the Inchworm compression system.

use sha2::{Digest, Sha256};
use serde::{Deserialize, Serialize};
use memmap2::Mmap;
use std::fs::File;
use std::path::Path;

/// Representation of a chain element during compression and decompression.
#[derive(Clone)]
pub enum Region {
    /// Literal 7-byte block that could not be compressed.
    Raw(Vec<u8>),
    /// Compressed seed and associated header.
    Compressed(Vec<u8>, Header),
}

impl Region {
    /// Return the encoded length of this region when written to the output
    /// stream.
    pub fn encoded_len(&self) -> usize {
        match self {
            Region::Raw(_) => 1 + HEADER_SIZE + BLOCK_SIZE,
            Region::Compressed(seed, _) => seed.len() + HEADER_SIZE,
        }
    }
}

/// Fixed block size in bytes.
pub const BLOCK_SIZE: usize = 7;
/// Size of an encoded header in bytes.
pub const HEADER_SIZE: usize = 3;
/// Reserved seed byte used for literal fallbacks.
pub const FALLBACK_SEED: u8 = 0xA5;

/// Cached expansion table used to speed up compression.
#[derive(Serialize, Deserialize, Default, Clone)]
pub struct GlossTable {
    /// Placeholder data for future optimisation.
    pub entries: Vec<Vec<u8>>,
}

impl GlossTable {
    /// Build an empty gloss table. In a full implementation this would
    /// perform expensive analysis of training data.
    pub fn build() -> Self {
        Self { entries: Vec::new() }
    }

    /// Load a gloss table from disk using memory mapping.
    pub fn load<P: AsRef<Path>>(path: P) -> std::io::Result<Self> {
        let file = File::open(path)?;
        unsafe {
            let mmap = Mmap::map(&file)?;
            Ok(bincode::deserialize(&mmap).expect("invalid gloss table"))
        }
    }

    /// Serialize this table to disk with bincode.
    pub fn save<P: AsRef<Path>>(&self, path: P) -> std::io::Result<()> {
        let data = bincode::serialize(self).expect("failed to serialize gloss");
        std::fs::write(path, data)
    }
}

/// Header information packed into three bytes.
#[derive(Debug, Clone, Copy)]
pub struct Header {
    /// Seed length encoded as 0..3 for 1..4 bytes.
    pub seed_len: u8,
    /// Number of bytes to recursively unpack from the hash output.
    pub nest_len: u32,
    /// Arity encoded as 0..3 for 1..4 blocks.
    pub arity: u8,
}

impl Header {
    /// Pack a header into three bytes.
    pub fn pack(self) -> [u8; HEADER_SIZE] {
        let raw: u32 = ((self.seed_len as u32) << 22)
            | ((self.nest_len as u32) << 2)
            | (self.arity as u32);
        raw.to_be_bytes()[1..4].try_into().unwrap()
    }

    /// Unpack a header from three bytes.
    pub fn unpack(bytes: [u8; HEADER_SIZE]) -> Self {
        let raw = u32::from_be_bytes([0, bytes[0], bytes[1], bytes[2]]);
        Self {
            seed_len: ((raw >> 22) & 0b11) as u8,
            nest_len: ((raw >> 2) & 0x000F_FFFF) as u32,
            arity: (raw & 0b11) as u8,
        }
    }
}

/// Check whether the given seed/header pair represents a literal fallback block.
pub fn is_fallback(seed: &[u8], header: [u8; HEADER_SIZE]) -> bool {
    seed == [FALLBACK_SEED] && header == [0; HEADER_SIZE]
}

/// Encode a region into its byte representation.
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

/// Decode a single region from the front of the input byte slice.
pub fn decode_region(data: &[u8]) -> (Region, usize) {
    for n in 1..=4 {
        if data.len() < n + HEADER_SIZE {
            continue;
        }
        let seed = &data[..n];
        let header_bytes: [u8; HEADER_SIZE] = data[n..n + HEADER_SIZE].try_into().unwrap();
        let header = Header::unpack(header_bytes);
        if header.seed_len as usize + 1 == n {
            let consumed = n + HEADER_SIZE;
            if is_fallback(seed, header_bytes) {
                let end = consumed + BLOCK_SIZE;
                let block = data[consumed..end].to_vec();
                return (Region::Raw(block), consumed + BLOCK_SIZE);
            } else {
                return (Region::Compressed(seed.to_vec(), header), consumed);
            }
        }
    }
    panic!("invalid encoded region");
}

/// Recursively decode a region into its literal bytes.
pub fn decompress_region(region: &Region) -> Vec<u8> {
    match region {
        Region::Raw(bytes) => bytes.clone(),
        Region::Compressed(seed, header) => {
            let digest = Sha256::digest(seed);
            if header.arity == 0 {
                digest[..BLOCK_SIZE].to_vec()
            } else {
                let len = header.nest_len as usize;
                decompress(&digest[..len])
            }
        }
    }
}

fn decompress_regions(regions: &[Region]) -> Vec<u8> {
    let mut out = Vec::new();
    for r in regions {
        out.extend_from_slice(&decompress_region(r));
    }
    out
}

fn encoded_len_of_regions(regions: &[Region]) -> usize {
    regions.iter().map(|r| r.encoded_len()).sum()
}

/// Compress input data according to the Inchworm algorithm.
///
/// This implementation performs a brute-force search over seeds of length 1..=4
/// bytes. It is intentionally literal and does not employ heuristics or
/// pattern-based optimisation. The search space is extremely large for real
/// inputs, so callers may wish to limit the number of seeds explored via the
/// `seed_limit` parameter for demonstrations or testing.
use std::ops::RangeInclusive;

pub fn print_stats(chain: &[Region], original_bytes: usize, hashes: u64) {
    let encoded = encoded_len_of_regions(chain);
    let ratio = encoded as f64 * 100.0 / original_bytes as f64;
    let hashes_per_byte = if encoded == 0 {
        0.0
    } else {
        hashes as f64 / encoded as f64
    };

    eprintln!("Compression complete!");
    eprintln!("Input: {} bytes", original_bytes);
    eprintln!("Output: {} bytes", encoded);
    eprintln!("Ratio: {:.2}%", ratio);
    eprintln!("Total hashes: {}", hashes);
    eprintln!("Hashes/byte: {:.1}", hashes_per_byte);
}

pub fn compress(
    data: &[u8],
    seed_len_range: RangeInclusive<u8>,
    seed_limit: Option<u64>,
    status_interval: u64,
    hash_counter: &mut u64,
) -> Vec<u8> {
    let mut chain: Vec<Region> = data
        .chunks(BLOCK_SIZE)
        .map(|b| Region::Raw(b.to_vec()))
        .collect();
    let original_regions = chain.len();
    let original_bytes = data.len();
    let mut matches = 0u64;

    loop {
        let mut matched = false;

        'search: for seed_len in seed_len_range.clone() {
            let max = 1u64 << (8 * seed_len as u64);
            let limit = seed_limit.unwrap_or(max).min(max);

            for seed in 0..limit {
                *hash_counter += 1;
                if *hash_counter % status_interval == 0 {
                    let enc = encoded_len_of_regions(&chain);
                    let ratio = enc as f64 * 100.0 / original_bytes as f64;
                    eprintln!(
                        "[{:.2}M hashes] {} matches | Chain: {} \u2192 {} regions | {} \u2192 {} bytes ({:.2}%)",
                        *hash_counter as f64 / 1_000_000.0,
                        matches,
                        original_regions,
                        chain.len(),
                        original_bytes,
                        enc,
                        ratio
                    );
                }

                let seed_bytes = &seed.to_be_bytes()[8 - seed_len as usize..];
                let digest = Sha256::digest(seed_bytes);

                for start in 0..chain.len() {
                    for arity in (2..=4u8).rev() {
                        if start + arity as usize > chain.len() {
                            continue;
                        }
                        let slice = &chain[start..start + arity as usize];
                        let target = decompress_regions(slice);
                        if digest.starts_with(&target) {
                            let nest = encoded_len_of_regions(slice) as u32;
                            let header = Header {
                                seed_len: seed_len - 1,
                                nest_len: nest,
                                arity: arity - 1,
                            };
                            eprintln!(
                                "match: seed={} len={} arity={} nest={} index={}",
                                hex::encode(seed_bytes),
                                seed_len,
                                arity,
                                nest,
                                start
                            );
                            let region = Region::Compressed(seed_bytes.to_vec(), header);
                            chain.splice(start..start + arity as usize, [region]);
                            matched = true;
                            matches += 1;
                            break 'search;
                        }
                    }
                }
            }
        }

        if !matched {
            break;
        }
    }

    let mut encoded = Vec::new();
    for r in &chain {
        encoded.extend_from_slice(&encode_region(r));
    }

    print_stats(&chain, original_bytes, *hash_counter);

    encoded
}

/// Recursively decode data produced by `compress`.
pub fn decompress(mut data: &[u8]) -> Vec<u8> {
    let mut out = Vec::new();
    let mut offset = 0;

    while offset < data.len() {
        let (region, consumed) = decode_region(&data[offset..]);
        offset += consumed;
        out.extend_from_slice(&decompress_region(&region));
    }

    out
}

