use crate::header::{Header, encode_header};
use crate::path::{CompressionPath, PathGloss};
use std::time::Instant;
use crate::BLOCK_SIZE;
use sha2::{Digest, Sha256};
use std::collections::HashSet;
use csv;
use hex;
use std::fs::File;
use std::io::Write;
use serde_json;

/// In-memory table storing truncated SHA-256 prefixes.
///
/// This is used to skip seed attempts that would produce a digest
/// matching a span we have already observed. The number of bits stored
/// for each entry is configurable via `bits`.
#[derive(Default)]
pub struct TruncHashTable {
    /// Number of bits from the hash digest to store.
    pub bits: u8,
    /// Set of truncated digests.
    pub set: HashSet<u64>,
}

impl TruncHashTable {
    /// Create a new empty table for the given prefix width.
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

    /// Insert an arbitrary byte slice into the table by hashing it and
    /// storing the truncated prefix of the digest.
    pub fn insert_bytes(&mut self, bytes: &[u8]) {
        let digest = Sha256::digest(bytes);
        let arr: [u8; 32] = digest.into();
        let key = self.prefix(&arr);
        self.set.insert(key);
    }

    /// Returns true if the hashed prefix of the provided bytes already
    /// exists in the table.
    pub fn contains_bytes(&self, bytes: &[u8]) -> bool {
        let digest = Sha256::digest(bytes);
        let arr: [u8; 32] = digest.into();
        let key = self.prefix(&arr);
        self.set.contains(&key)
    }
}

/// Attempt to compress a block of data.
///
/// Returns the selected `Header` along with the number of bytes
/// consumed if a compression opportunity is found. `None` indicates
/// that the input should remain uncompressed.
/// The provided `gloss` stores previously successful compression paths.
/// `counter` is used to assign unique identifiers to new paths.
pub fn compress_block(
    input: &[u8],
    gloss: &mut PathGloss,
    counter: &mut u64,
    fallback: Option<&mut FallbackSeeds>,
    current_pass: u64,
) -> Option<(Header, usize)> {
    if input.len() < BLOCK_SIZE {
        return None;
    }

    let span_hash: [u8; 32] = Sha256::digest(&input[..BLOCK_SIZE]).into();

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
                        break; // stop replay after 3 mismatched steps
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
            hashes.push(Sha256::digest(slice).into());
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

    // --- Bayesian fallback logic ---
    // Evaluate potential future reuse of this span's first block as a seed.
    if let Some(fb) = fallback {
        let span = &input[..consumed];
        let digest: [u8; 32] = Sha256::digest(span).into();
        let seed = &span[..BLOCK_SIZE.min(span.len())];
        let header_bits = encode_header(0, blocks).len() * 8;
        let excess = (header_bits + seed.len() * 8) as f64 - (span.len() * 8) as f64;
        let belief = (-fb.lambda * excess).exp();
        if belief > fb.theta {
            let entry = crate::gloss::BeliefSeed {
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

    Some((Header { seed_index: 0, arity: blocks }, consumed))
}

/// Manage probabilistic fallback seeds using Bayesian scoring.
pub struct FallbackSeeds {
    pub map: crate::gloss::BeliefMap,
    lambda: f64,
    theta: f64,
    block_len: usize,
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

    /// Should be called at start of a compression pass.
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

    /// Record a failed compression attempt for `seed`.
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
}

/// Write the current belief map to a CSV file for debugging.
pub fn dump_gloss_to_csv(map: &crate::gloss::BeliefMap, path: &str) -> std::io::Result<()> {
    let mut wtr = csv::Writer::from_path(path)?;
    wtr.write_record(&["SeedHex", "Score", "Pass", "BundlingHits", "GlossHits"])?;

    for entry in map.iter().map(|(_, e)| e) {
        let seed_hex = hex::encode(&entry.seed);
        wtr.write_record(&[
            seed_hex,
            format!("{:.4}", entry.belief),
            entry.last_used.to_string(),
            entry.bundling_hits.to_string(),
            entry.gloss_hits.to_string(),
        ])?;
    }

    wtr.flush()?;
    Ok(())
}

/// Write the current belief map to a JSON file for debugging.
pub fn dump_beliefmap_json(map: &crate::gloss::BeliefMap, path: &str) -> std::io::Result<()> {
    let entries: Vec<_> = map.iter().map(|(_, e)| e).collect();
    let json = serde_json::to_string_pretty(&entries)?;
    let mut file = File::create(path)?;
    file.write_all(json.as_bytes())?;
    Ok(())
}
