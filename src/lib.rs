//! Core logic for the Inchworm compression system.

use sha2::{Digest, Sha256};

pub mod bloom;

/// Representation of a chain element during compression and decompression.
#[derive(Clone)]
pub enum Region {
    /// Literal 7-byte block that could not be compressed.
    Raw(Vec<u8>),
    /// Compressed seed and associated header.
    Compressed(Vec<u8>, Header),
}

impl Region {
    /// Return the encoded length of this region when written to the output stream.
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
    pub fn pack(self) -> [u8; HEADER_SIZE] {
        let raw: u32 = ((self.seed_len as u32) << 22)
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

/// Safe decoder: returns None instead of panicking on bad input.
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

fn decompress_region_safe(region: &Region) -> Option<Vec<u8>> {
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

fn decompress_safe(mut data: &[u8]) -> Option<Vec<u8>> {
    let mut out = Vec::new();
    let mut offset = 0;
    while offset < data.len() {
        let (region, consumed) = decode_region_safe(&data[offset..])?;
        offset += consumed;
        out.extend_from_slice(&decompress_region_safe(&region)?);
    }
    Some(out)
}

/// Gloss table entries for 1- and 2-byte seeds that decompress to valid output.
pub struct GlossEntry {
    pub seed: Vec<u8>,
    pub header: Header,
    pub decompressed: Vec<u8>,
}

pub struct GlossTable {
    pub entries: Vec<GlossEntry>,
}

impl GlossTable {
    pub fn generate() -> Self {
        let mut entries = Vec::new();
        for seed_len in 1..=2u8 {
            let max = 1u64 << (8 * seed_len as u64);
            for seed_val in 0..max {
                let seed_bytes = &seed_val.to_be_bytes()[8 - seed_len as usize..];
                let digest = Sha256::digest(seed_bytes);
                for len in 0..=digest.len() {
                    if let Some(bytes) = decompress_safe(&digest[..len]) {
                        let blocks = bytes.len() / BLOCK_SIZE;
                        if bytes.len() % BLOCK_SIZE != 0 || !(2..=4).contains(&blocks) {
                            continue;
                        }
                        let header = Header {
                            seed_len: seed_len - 1,
                            nest_len: len as u32,
                            arity: blocks as u8 - 1,
                        };
                        if let Some(out) = decompress_region_safe(&Region::Compressed(seed_bytes.to_vec(), header)) {
                            entries.push(GlossEntry {
                                seed: seed_bytes.to_vec(),
                                header,
                                decompressed: out,
                            });
                        }
                    }
                }
            }
        }
        Self { entries }
    }
}
