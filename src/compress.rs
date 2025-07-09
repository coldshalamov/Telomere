use crate::header::Header;

/// Attempt to compress a block of data.
///
/// Returns the selected `Header` along with the number of bytes
/// consumed if a compression opportunity is found. `None` indicates
/// that the input should remain uncompressed.
pub fn compress_block(_input: &[u8]) -> Option<(Header, usize)> {
    // Compression logic to be implemented
    None
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

