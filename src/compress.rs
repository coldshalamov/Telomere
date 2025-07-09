use crate::header::Header;
use crate::path::{CompressionPath, PathGloss};
use crate::BLOCK_SIZE;
use sha2::{Digest, Sha256};

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
) -> Option<(Header, usize)> {
    if input.len() < BLOCK_SIZE {
        return None;
    }

    let span_hash: [u8; 32] = Sha256::digest(&input[..BLOCK_SIZE]).into();

    if let Some((idx, path)) = gloss.match_span(&span_hash) {
        if path.total_gain >= 2 * path.seeds.len() as u32 {
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
                gloss.increment_replayed(idx);
                let header = Header {
                    seed_index: path.path_id as usize,
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
            path_id: *counter,
            seeds,
            span_hashes: hashes,
            total_gain: consumed as u32,
            replayed: 0,
        };
        *counter += 1;
        gloss.add_path(path);
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

