//! Research-only GPU feature backend.
//!
//! The production compressor is CPU/rayon only. The `gpu` feature remains as a
//! buildable research hook, but it deliberately uses the same deterministic CPU
//! matching semantics until a real OpenCL backend has parity tests and measured
//! wins on target hardware.

use crate::block::{BlockId, BlockStore};
use crate::hasher::SeedExpander;
use crate::{GpuMatchRecord, TelomereError};

struct ResearchBlock {
    data: Vec<u8>,
    global_index: usize,
    bit_length: usize,
}

#[derive(Default)]
pub struct GpuSeedMatcher {
    tile: Vec<ResearchBlock>,
}

impl GpuSeedMatcher {
    pub fn new() -> Self {
        Self { tile: Vec::new() }
    }

    pub fn load_tile(&mut self, store: &BlockStore, blocks: &[BlockId]) {
        self.tile = blocks
            .iter()
            .map(|&id| {
                let b_ref = store.get_block(id);
                ResearchBlock {
                    data: store.get_data(id).to_vec(),
                    global_index: b_ref.global_index as usize,
                    bit_length: b_ref.bit_len as usize,
                }
            })
            .collect();
    }

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
