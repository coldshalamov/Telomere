use sha2::{Digest, Sha256};
use std::collections::HashMap;

use crate::{index_to_seed, TelomereError};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SeedMatch {
    pub block_index: usize,
    pub seed_index: usize,
    pub block_len: usize,
}

#[derive(Debug, Clone)]
pub struct IndexedBlock {
    pub index: usize,
    pub len: usize,
    pub matches: Vec<usize>,
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

pub fn brute_force_seed_tables(
    data: &[u8],
    max_block_size: usize,
    max_seed_len: usize,
) -> Result<HashMap<usize, Vec<IndexedBlock>>, TelomereError> {
    let mut tables: HashMap<usize, Vec<IndexedBlock>> = HashMap::new();
    let mut limit: u128 = 0;
    for len in 1..=max_seed_len {
        limit += 1u128 << (8 * len);
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
                if expand_seed(&seed, slice.len()) == slice {
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

