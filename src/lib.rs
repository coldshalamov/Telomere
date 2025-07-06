//! Core logic for the Inchworm compression system.

use sha2::{Digest, Sha256};
use serde::{Deserialize, Serialize};
use serde_json::json;
use std::collections::HashMap;
use std::ops::RangeInclusive;
use std::time::Instant;
use std::fs::File;
use std::path::Path;
use memmap2::Mmap;

mod sha_cache;
mod bloom;
mod gloss;
pub use gloss::{GlossEntry, GlossTable};

use bloom::Bloom;

pub const BLOCK_SIZE: usize = 7;
pub const HEADER_SIZE: usize = 3;
pub const FALLBACK_SEED: u8 = 0xA5;

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

fn decompress_region(region: &Region) -> Vec<u8> {
    decompress_region_safe(region).expect("invalid region")
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

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq)]
pub struct GlossEntry {
    pub seed: Vec<u8>,
    pub header: Header,
    pub decompressed: Vec<u8>,
}

#[derive(Serialize, Deserialize, Default, Clone, PartialEq, Debug)]
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
                        if let Some(out) = decompress_region_safe(
                            &Region::Compressed(seed_bytes.to_vec(), header),
                        ) {
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

    pub fn build() -> Self {
        Self { entries: Vec::new() }
    }

    pub fn find(&self, bytes: &[u8]) -> Option<&GlossEntry> {
        self.entries.iter().find(|e| e.decompressed == bytes)
    }

    pub fn load<P: AsRef<Path>>(path: P) -> std::io::Result<Self> {
        let file = File::open(path)?;
        unsafe {
            let mmap = Mmap::map(&file)?;
            Ok(bincode::deserialize(&mmap).expect("invalid gloss table"))
        }
    }

    pub fn save<P: AsRef<Path>>(&self, path: P) -> std::io::Result<()> {
        let data = bincode::serialize(self).expect("failed to serialize gloss");
        std::fs::write(path, data)
    }
}

pub fn print_stats(
    chain: &[Region],
    original_bytes: usize,
    original_regions: usize,
    hashes: u64,
    brute_matches: u64,
    gloss_matches: u64,
    json_out: bool,
    verbosity: u8,
    start: Instant,
    final_stats: bool,
) {
    if verbosity == 0 && !(final_stats && json_out) {
        return;
    }

    let encoded = chain.iter().map(|r| r.encoded_len()).sum::<usize>();
    let ratio = encoded as f64 * 100.0 / original_bytes as f64;
    let hashes_per_byte = if encoded == 0.0 { 0.0 } else { hashes as f64 / encoded as f64 };
    let elapsed = start.elapsed().as_secs_f64();
    let mb = original_bytes as f64 / (1024.0 * 1024.0);
    let time_per_mb = if mb == 0.0 { 0.0 } else { elapsed / mb };
    let hashes_per_sec = if elapsed == 0.0 { 0.0 } else { hashes as f64 / elapsed };
    let total_matches = brute_matches + gloss_matches;

    if final_stats && json_out {
        let obj = json!({
            "input_bytes": original_bytes,
            "output_bytes": encoded,
            "compression_ratio": ratio,
            "total_hashes": hashes,
            "hashes_per_byte": hashes_per_byte,
            "gloss_hits": gloss_matches,
            "bruteforce_hits": brute_matches,
            "time_per_mb": time_per_mb,
            "hashes_per_sec": hashes_per_sec,
        });
        println!("{}", obj);
    } else if final_stats {
        eprintln!("Compression complete!");
        eprintln!("Input: {} bytes", original_bytes);
        eprintln!("Output: {} bytes", encoded);
        eprintln!("Ratio: {:.2}%", ratio);
        eprintln!("Gloss hits: {}", gloss_matches);
        eprintln!("Brute hits: {}", brute_matches);
        eprintln!("Total hashes: {}", hashes);
        eprintln!("Hashes/sec: {:.0}", hashes_per_sec);
        eprintln!("Time/MB: {:.2}s", time_per_mb);
        eprintln!("Hashes/byte: {:.1}", hashes_per_byte);
    } else if verbosity > 0 {
        eprintln!(
            "[{:.2}M hashes] {} matches ({} gloss) | Chain: {} → {} regions | {} → {} bytes ({:.2}%)",
            hashes as f64 / 1_000_000.0,
            total_matches,
            gloss_matches,
            original_regions,
            chain.len(),
            original_bytes,
            encoded,
            ratio
        );
    }
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

    loop {
        let mut matched = false;

        'outer: for start_i in 0..chain.len() {
            for arity in (2..=4u8).rev() {
                if start_i + arity as usize > chain.len() {
                    continue;
                }

                let slice = &chain[start_i..start_i + arity as usize];
                let target = decompress_regions(slice);

                if let Some(table) = gloss {
                    if let Some(entry) = table.find(&target) {
                        if verbosity >= 2 {
                            eprintln!(
                                "gloss match: seed={} arity={} nest={} index={}",
                                hex::encode(&entry.seed),
                                arity,
                                entry.header.nest_len,
                                start_i
                            );
                        }
                        chain.splice(
                            start_i..start_i + arity as usize,
                            [Region::Compressed(entry.seed.clone(), entry.header)],
                        );
                        gloss_matches += 1;
                        matched = true;
                        break 'outer;
                    }
                }

                for seed_len in seed_len_range.clone() {
                    let max = 1u64 << (8 * seed_len as u64);
                    let limit = seed_limit.unwrap_or(max).min(max);

                    for seed in 0..limit {
                        *hash_counter += 1;
                        if *hash_counter % status_interval == 0 {
                            print_stats(
                                &chain,
                                original_bytes,
                                original_regions,
                                *hash_counter,
                                brute_matches,
                                gloss_matches,
                                json_out,
                                verbosity,
                                start,
                                false,
                            );
                        }

                        let seed_bytes = &seed.to_be_bytes()[8 - seed_len as usize..];
                        let digest: [u8; 32] = if seed_len <= 2 {
                            if let Some(d) = sha_cache.get(seed_bytes) {
                                *d
                            } else {
                                let arr: [u8; 32] = Sha256::digest(seed_bytes).into();
                                sha_cache.insert(seed_bytes.to_vec(), arr);
                                arr
                            }
                        } else {
                            Sha256::digest(seed_bytes).into()
                        };

                        if digest[..].starts_with(&target) {
                            let nest = encoded_len_of_regions(slice) as u32;
                            let header = Header {
                                seed_len: seed_len - 1,
                                nest_len: nest,
                                arity: arity - 1,
                            };
                            if verbosity >= 2 {
                                eprintln!(
                                    "match: seed={} len={} arity={} nest={} index={}",
                                    hex::encode(seed_bytes),
                                    seed_len,
                                    arity,
                                    nest,
                                    start_i
                                );
                            }
                            chain.splice(
                                start_i..start_i + arity as usize,
                                [Region::Compressed(seed_bytes.to_vec(), header)],
                            );
                            matched = true;
                            brute_matches += 1;
                            break 'outer;
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

    print_stats(
        &chain,
        original_bytes,
        original_regions,
        *hash_counter,
        brute_matches,
        gloss_matches,
        json_out,
        verbosity,
        start,
        true,
    );

    encoded
}

pub fn decompress(mut data: &[u8]) -> Vec<u8> {
    let mut out = Vec::new();
    let mut offset = 0;

    while offset < data.len() {
        let (region, consumed) =
            decode_region_safe(&data[offset..]).expect("invalid compressed data");
        offset += consumed;
        out.extend_from_slice(&decompress_region(&region));
    }

    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;

    fn simple_compress(data: &[u8]) -> Vec<u8> {
        let mut out = Vec::new();
        for chunk in data.chunks(BLOCK_SIZE) {
            out.extend_from_slice(&encode_region(&Region::Raw(chunk.to_vec())));
        }
        out
    }

    #[test]
    fn generate_gloss() {
        let table = GlossTable::generate();
        assert!(!table.entries.is_empty());
    }

    #[test]
    fn gloss_save_load_roundtrip() {
        let table = GlossTable::generate();
        let path = std::env::temp_dir().join("gloss_test.bin");
        table.save(&path).unwrap();
        let loaded = GlossTable::load(&path).unwrap();
        assert_eq!(table.entries.len(), loaded.entries.len());
        let _ = fs::remove_file(path);
    }

    #[test]
    fn roundtrip_small_buffer() {
        let data: Vec<u8> = (0u8..14).collect();
        let encoded = simple_compress(&data);
        let decoded = decompress_safe(&encoded).unwrap();
        assert_eq!(decoded, data);
    }

    #[test]
    fn malformed_region() {
        assert!(decode_region_safe(&[0x01]).is_none());
        let good = encode_region(&Region::Raw(vec![0; BLOCK_SIZE]));
        let truncated = &good[..good.len() - 1];
        assert!(decode_region_safe(truncated).is_none());
    }

    #[test]
    fn json_stats_output() {
        let chain = vec![Region::Raw(vec![0; BLOCK_SIZE])];
        let result = std::panic::catch_unwind(|| {
            print_stats(&chain, BLOCK_SIZE, 1, 0, 0, 0, true, 1, Instant::now(), true);
        });
        assert!(result.is_ok());
    }
}
