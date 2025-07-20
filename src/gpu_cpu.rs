use crate::block::Block;
use crate::{GpuMatchRecord, TelomereError};
use sha2::{Digest, Sha256};

/// Simple CPU-based simulation of the GPU seed matcher.
#[derive(Default)]
pub struct GpuSeedMatcher {
    tile: Vec<Block>,
}

impl GpuSeedMatcher {
    /// Create a new matcher with an empty tile.
    pub fn new() -> Self {
        Self { tile: Vec::new() }
    }

    /// Load a block tile into the simulated GPU memory.
    pub fn load_tile(&mut self, blocks: &[Block]) {
        self.tile = blocks.to_vec();
    }

    /// Hash seeds on the fly and return match records.
    pub fn seed_match(
        &self,
        start_seed: usize,
        end_seed: usize,
    ) -> Result<Vec<GpuMatchRecord>, TelomereError> {
        let mut out = Vec::new();
        for seed in start_seed..end_seed {
            let seed_byte = seed as u8;
            for block in &self.tile {
                let expanded = expand_seed(&[seed_byte], block.data.len());
                if expanded == block.data {
                    out.push(GpuMatchRecord {
                        seed_index: seed,
                        bundle_length: 1,
                        block_indices: vec![block.global_index],
                        original_bits: block.bit_length,
                    });
                }
            }
        }
        Ok(out)
    }
}

fn expand_seed(seed: &[u8], len: usize) -> Vec<u8> {
    let mut out = Vec::with_capacity(len);
    let mut cur = seed.to_vec();
    while out.len() < len {
        let digest: [u8; 32] = Sha256::digest(&cur).into();
        out.extend_from_slice(&digest);
        cur = digest.to_vec();
    }
    out.truncate(len);
    out
}
