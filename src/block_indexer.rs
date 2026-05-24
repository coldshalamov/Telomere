//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
use std::collections::HashMap;

use crate::hasher::SeedExpander;
use crate::{index_to_seed, TelomereError};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SeedMatch {
    /// Index of the block that matched.
    pub block_index: usize,
    /// Seed enumeration index that generated the match.
    pub seed_index: usize,
    /// Length in bytes of the matched block.
    pub block_len: usize,
}

#[derive(Debug, Clone)]
pub struct IndexedBlock {
    /// Position of this block within the input stream.
    pub index: usize,
    /// Size of the block in bytes.
    pub len: usize,
    /// All seed indices that expand exactly to this block.
    pub matches: Vec<usize>,
}

pub fn brute_force_seed_tables(
    data: &[u8],
    max_block_size: usize,
    max_seed_len: usize,
    expander: &dyn SeedExpander,
) -> Result<HashMap<usize, Vec<IndexedBlock>>, TelomereError> {
    let mut tables: HashMap<usize, Vec<IndexedBlock>> = HashMap::new();
    let mut limit: u128 = 0;
    for len in 1..=max_seed_len {
        limit += 1u128 << (8 * len);
    }

    // Safety
    if limit > usize::MAX as u128 {
        limit = usize::MAX as u128;
    }

    for block_size in 1..=max_block_size {
        let mut blocks = Vec::new();
        let mut offset = 0usize;
        let mut idx = 0usize;
        while offset < data.len() {
            let end = (offset + block_size).min(data.len());
            let slice = &data[offset..end];
            let mut matches = Vec::new();
            for s_idx in 0..limit {
                let seed = index_to_seed(s_idx as usize, max_seed_len)?;
                if expander.prefix_matches(&seed, slice, slice.len() * 8) {
                    matches.push(s_idx as usize);
                }
            }
            blocks.push(IndexedBlock {
                index: idx,
                len: slice.len(),
                matches,
            });
            offset += block_size;
            idx += 1;
        }
        tables.insert(block_size, blocks);
    }
    Ok(tables)
}
