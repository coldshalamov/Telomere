use sha2::{Digest, Sha256};
use std::collections::HashMap;

use crate::bundle::{BlockStatus, MutableBlock};

/// A record of a block that matched a known seed prefix.
#[derive(Debug, Clone)]
pub struct MatchRecord {
    pub block_pos: usize,    // MutableBlock.position
    pub origin_index: usize, // Back-reference to ImmutableBlock
    pub full_seed: Vec<u8>,  // Full seed that matched
}

/// Scan the mutable table and collect all blocks matching truncated seeds.
pub fn detect_seed_matches(
    blocks: &[MutableBlock],
    seed_table: &HashMap<Vec<u8>, Vec<u8>>, // truncated -> full seed
    trunc_bits: u8,
) -> Vec<MatchRecord> {
    let mut matches = Vec::new();
    for block in blocks.iter().filter(|b| b.status == BlockStatus::Active) {
        let hash = Sha256::digest(&block.data);
        let trunc = &hash[..(trunc_bits as usize / 8)];
        if let Some(full_seed) = seed_table.get(trunc) {
            matches.push(MatchRecord {
                block_pos: block.position,
                origin_index: block.origin_index,
                full_seed: full_seed.clone(),
            });
        }
    }
    matches
}
