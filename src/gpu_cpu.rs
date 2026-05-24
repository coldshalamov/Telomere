use crate::block::{BlockId, BlockStore};
use crate::hasher::SeedExpander;
use crate::{GpuMatchRecord, TelomereError};

struct SimulatedBlock {
    data: Vec<u8>,
    global_index: usize,
    bit_length: usize,
}

/// Simple CPU-based simulation of the GPU seed matcher.
#[derive(Default)]
pub struct GpuSeedMatcher {
    tile: Vec<SimulatedBlock>,
}

impl GpuSeedMatcher {
    /// Create a new matcher with an empty tile.
    pub fn new() -> Self {
        Self { tile: Vec::new() }
    }

    /// Load a block tile into the simulated GPU memory.
    pub fn load_tile(&mut self, store: &BlockStore, blocks: &[BlockId]) {
        self.tile = blocks
            .iter()
            .map(|&id| {
                let b_ref = store.get_block(id);
                let data = store.get_data(id).to_vec();
                SimulatedBlock {
                    data,
                    global_index: b_ref.global_index as usize,
                    bit_length: b_ref.bit_len as usize,
                }
            })
            .collect();
    }

    /// Hash seeds on the fly and return match records.
    pub fn seed_match(
        &self,
        start_seed: usize,
        end_seed: usize,
        expander: &dyn SeedExpander,
    ) -> Result<Vec<GpuMatchRecord>, TelomereError> {
        let mut out = Vec::new();
        for seed in start_seed..end_seed {
            let seed_byte = seed as u8;
            for block in &self.tile {
                // Use expander to check for match.
                // Assuming seed is just 1 byte as per original logic.
                if expander.prefix_matches(&[seed_byte], &block.data, block.bit_length) {
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
