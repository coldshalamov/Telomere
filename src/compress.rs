use crate::header::{Header, encode_header};
use crate::path::{CompressionPath, PathGloss};
use crate::compress_stats::CompressionStats;
use crate::BLOCK_SIZE;
use sha2::{Digest, Sha256};
use std::time::Instant;
use std::collections::{HashSet, HashMap};


/// In-memory table storing truncated SHA-256 prefixes.
use serde::{Serialize, Deserialize};

#[derive(Default, Serialize, Deserialize)]
pub struct TruncHashTable {
    pub bits: u8,
    pub set: HashSet<u64>,
}

impl TruncHashTable {
    pub fn new(bits: u8) -> Self {
        assert!(bits > 0 && bits <= 64, "bits must be between 1 and 64");
        Self {
            bits,
            set: HashSet::new(),
        }
    }

    fn prefix(&self, digest: &[u8; 32]) -> u64 {
        let mut bytes = [0u8; 8];
        bytes.copy_from_slice(&digest[..8]);
        let mut val = u64::from_be_bytes(bytes);
        if self.bits < 64 {
            val >>= 64 - self.bits as u64;
        }
        val
    }

    pub fn insert_bytes(&mut self, bytes: &[u8]) {
        let digest = Sha256::digest(bytes);
        let arr: [u8; 32] = digest.into();
        let key = self.prefix(&arr);
        self.set.insert(key);
    }

    pub fn contains_bytes(&self, bytes: &[u8]) -> bool {
        let digest = Sha256::digest(bytes);
        let arr: [u8; 32] = digest.into();
        let key = self.prefix(&arr);
        self.set.contains(&key)
    }

    /// Load a serialized table from disk using bincode encoding.
    pub fn load<P: AsRef<std::path::Path>>(path: P) -> std::io::Result<Self> {
        let bytes = std::fs::read(path)?;
        bincode::deserialize(&bytes)
            .map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))
    }

    /// Persist the table to disk using bincode encoding.
    pub fn save<P: AsRef<std::path::Path>>(&self, path: P) -> std::io::Result<()> {
        let bytes = bincode::serialize(self)
            .map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))?;
        std::fs::write(path, bytes)
    }
}

pub fn compress_block(
    input: &[u8],
    gloss: &mut PathGloss,
    counter: &mut u64,
    fallback: Option<&mut FallbackSeeds>,
    current_pass: u64,
    mut stats: Option<&mut CompressionStats>,
    hash_table: Option<&HashMap<Vec<u8>, [u8; 32]>>,
) -> Option<(Header, usize)> {
    if input.len() < BLOCK_SIZE {
        return None;
    }

    if let Some(s) = stats.as_mut() {
        s.tick_block();
    }


    let first_seed = &input[..BLOCK_SIZE];
    let span_hash: [u8; 32] = if let Some(table) = hash_table {
        table
            .get(first_seed)
            .cloned()
            .unwrap_or_else(|| {
                eprintln!("Fallback SHA256 used for seed: {:?}", first_seed);
                Sha256::digest(first_seed).into()
            })
    } else {
        Sha256::digest(first_seed).into()
    };

    if let Some((idx, path)) = gloss.match_span(&span_hash) {
        if path.total_gain >= 2 * path.seeds.len() as u64 {
            let mut matched_blocks = 0usize;
            let mut matched = true;
            for (step, seed) in path.seeds.iter().enumerate() {
                let start = step * BLOCK_SIZE;
                let end = start + seed.len();
                if end > input.len() || input[start..end] != seed[..] {
                    matched = false;
                    if step >= 3 {
                        break;
                    }
                    break;
                } else {
                    matched_blocks += 1;
                }
            }
            if matched && matched_blocks > 0 {
                let path_id = path.id;
                gloss.increment_replayed(idx);
                let header = Header {
                    seed_index: path_id as usize,
                    arity: matched_blocks,
                };
                if let Some(s) = stats.as_mut() {
                    let span_len = matched_blocks * BLOCK_SIZE;
                    let span = &input[..span_len.min(input.len())];
                    let seed = &input[..BLOCK_SIZE.min(input.len())];
                    s.maybe_log(span, seed, true);
                    s.log_match(true, matched_blocks);
                }
                return Some((header, matched_blocks * BLOCK_SIZE));
            }
        }
    }

    let blocks = (input.len() / BLOCK_SIZE).min(3);
    let consumed = blocks * BLOCK_SIZE;

    if blocks >= 2 {
        let mut seeds = Vec::new();
        let mut hashes = Vec::new();
        for i in 0..blocks {
            let start = i * BLOCK_SIZE;
            let end = start + BLOCK_SIZE;
            let slice = &input[start..end];
            seeds.push(slice.to_vec());
            let digest = if let Some(table) = hash_table {
                table
                    .get(slice)
                    .cloned()
                    .unwrap_or_else(|| {
                        eprintln!("Fallback SHA256 used for seed: {:?}", slice);
                        Sha256::digest(slice).into()
                    })
            } else {
                Sha256::digest(slice).into()
            };
            hashes.push(digest);
        }
        let path = CompressionPath {
            id: *counter,
            created_at: Instant::now(),
            seeds,
            span_hashes: hashes,
            total_gain: consumed as u64,
            replayed: 0,
        };
        *counter += 1;
        gloss.add_path(path);
    }

    if let Some(fb) = fallback {
        let span = &input[..consumed];
        let digest: [u8; 32] = Sha256::digest(span).into();
        let seed = &span[..BLOCK_SIZE.min(span.len())];
        let header_bits = encode_header(0, blocks).len() * 8;
        let excess = (header_bits + seed.len() * 8) as f64 - (span.len() * 8) as f64;
        let belief = (-fb.lambda * excess).exp();
        if belief > fb.theta {
            let entry = crate::gloss::BeliefSeed {
    id: *counter as usize,
    seed: seed.to_vec(),
    belief,
    last_used: current_pass,
    bundling_hits: 0,
    gloss_hits: 0,
};


            fb.map.insert(digest, entry);
            fb.trim();

            let path = CompressionPath {
                id: *counter,
                created_at: Instant::now(),
                seeds: vec![seed.to_vec()],
                span_hashes: vec![digest],
                total_gain: 0,
                replayed: 0,
            };
            *counter += 1;
            gloss.add_path(path);
        }
    }

    if let Some(s) = stats.as_mut() {
        let span = &input[..consumed.min(input.len())];
        let seed = &input[..BLOCK_SIZE.min(input.len())];
        s.maybe_log(span, seed, false);
        s.log_match(false, blocks);
    }

    Some((Header { seed_index: 0, arity: 36 + blocks }, consumed))
}

pub struct FallbackSeeds {
    pub map: crate::gloss::BeliefMap,
    lambda: f64,
    theta: f64,
    block_len: usize,
}

use std::ops::RangeInclusive;

pub fn compress(
    data: &[u8],
    _lens: RangeInclusive<u8>,
    _seed_limit: Option<u64>,
    _passes: u64,
    _counter: &mut u64,
    _json_out: bool,
    _verbosity: u8,
    _gloss_only: bool,
    _coverage: Option<&mut Vec<bool>>,
    _partials: Option<&mut Vec<u8>>,
    _hash_table: Option<&mut TruncHashTable>,
) -> Vec<u8> {
    let mut out = Vec::new();
    let mut offset = 0usize;
    while offset + BLOCK_SIZE <= data.len() {
        let remaining_blocks = (data.len() - offset) / BLOCK_SIZE;
        let blocks = remaining_blocks.min(3);
        out.extend(encode_header(0, 36 + blocks));
        out.extend_from_slice(&data[offset..offset + blocks * BLOCK_SIZE]);
        offset += blocks * BLOCK_SIZE;
    }
    if offset < data.len() {
        out.extend(encode_header(0, 40));
        out.extend_from_slice(&data[offset..]);
    } else {
        out.extend(encode_header(0, 40));
    }
    out
}

impl FallbackSeeds {
    pub fn new(lambda: f64, theta: f64, block_len: usize) -> Self {
        Self {
            map: crate::gloss::BeliefMap::new(10_000),
            lambda,
            theta,
            block_len,
        }
    }

    pub fn new_pass(&mut self) {
        self.trim();
        crate::gloss_prune_hook::run(&mut self.map);
    }

    fn trim(&mut self) {
        while self.map.len() > 10_000 {
            if let Some((&key, _)) = self
                .map
                .iter()
                .min_by(|a, b| {
                    let ba = a.1.belief;
                    let bb = b.1.belief;
                    ba.partial_cmp(&bb)
                        .unwrap_or(std::cmp::Ordering::Equal)
                        .then_with(|| a.1.last_used.cmp(&b.1.last_used))
                })
            {
                self.map.remove(&key);
            } else {
                break;
            }
        }
    }

    pub fn record_failure(&mut self, digest: [u8; 32], seed: &[u8], evidence: f64, pass: u64) {
        if seed.len() > 4 {
            return;
        }
        if let Some(entry) = self.map.get_mut(&digest) {
            let p = entry.belief;
            let et = evidence;
            entry.belief = (et * p) / (et * p + (1.0 - et) * (1.0 - p));
            entry.last_used = pass;
            entry.bundling_hits += 1;
        } else {
            let prior = (-self.lambda * ((seed.len() as isize - self.block_len as isize) as f64)).exp();
            let s = crate::gloss::BeliefSeed {
    id: 0, // not used for record_failure-based entries
    seed: seed.to_vec(),
    belief: prior,
    last_used: pass,
    bundling_hits: 1,
    gloss_hits: 0,
};

            if prior > self.theta {
                self.map.insert(digest, s);
                self.trim();
            }
        }
    }
    pub fn reverse_index(&self, index: usize) -> Option<Vec<u8>> {
        self.map.iter().find_map(|(_, entry)| {
            if entry.id == index {
                Some(entry.seed.clone())
            } else {
                None
            }
        })
    }

}

