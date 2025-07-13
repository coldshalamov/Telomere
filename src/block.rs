use std::collections::HashMap;
use sha2::{Digest, Sha256};

#[derive(Debug, Clone)]
pub struct Block {
    /// Original order in the stream
    pub global_index: usize,
    /// Current size of this block in bits
    pub bit_length: usize,
    /// Raw bytes making up this block
    pub data: Vec<u8>,
    /// Optional arity if this block was compressed later
    pub arity: Option<usize>,
    /// Optional seed index associated with compressed form
    pub seed_index: Option<usize>,
}

/// BlockTable groups blocks by their bit length
pub type BlockTable = HashMap<usize, Vec<Block>>;

/// Represents a change to the block table discovered during compression or bundling.
#[derive(Debug, Clone)]
pub enum BlockChange {
    /// Replaces a single block with a new version (used in hashing matches).
    Replace {
        original_index: usize,
        new_block: Block,
    },
    /// Compresses a group of adjacent blocks into one (used in bundling).
    Bundle {
        start_index: usize,
        count: usize,
        new_bit_length: usize,
    },
}

/// Given a flat list of [`Block`]s, return a [`BlockTable`]
/// where blocks are grouped by their bit length.
pub fn group_by_bit_length(blocks: Vec<Block>) -> BlockTable {
    let mut table: BlockTable = HashMap::new();
    for block in blocks {
        table.entry(block.bit_length).or_default().push(block);
    }
    table
}

/// Split raw input into fixed-sized blocks measured in bits.
pub fn split_into_blocks(input: &[u8], block_size_bits: usize) -> Vec<Block> {
    assert!(block_size_bits > 0, "block size must be non-zero");

    let block_size_bytes = (block_size_bits + 7) / 8;
    let mut blocks = Vec::new();
    let mut offset = 0usize;
    let mut index = 0usize;

    while offset < input.len() {
        let end = (offset + block_size_bytes).min(input.len());
        let slice = &input[offset..end];
        let bits = if end - offset == block_size_bytes {
            block_size_bits
        } else {
            (end - offset) * 8
        };

        blocks.push(Block {
            global_index: index,
            bit_length: bits,
            data: slice.to_vec(),
            arity: None,
            seed_index: None,
        });

        offset += block_size_bytes;
        index += 1;
    }

    blocks
}

/// Simulate a compression pass using a prebuilt seed table.
pub fn simulate_pass(table: &mut BlockTable, seed_table: &HashMap<String, usize>) -> usize {
    let mut lengths: Vec<usize> = table.keys().cloned().collect();
    lengths.sort_unstable_by(|a, b| b.cmp(a));

    let mut matches = 0usize;

    for len in lengths {
        if let Some(mut group) = table.remove(&len) {
            let mut remaining = Vec::new();
            for mut block in group.into_iter() {
                let digest = Sha256::digest(&block.data);
                let hex = hex::encode(digest);
                if let Some(&seed_idx) = seed_table.get(&hex) {
                    block.seed_index = Some(seed_idx);
                    block.arity = Some(1);
                    block.bit_length = 16;
                    table.entry(16).or_default().push(block);
                    matches += 1;
                } else {
                    remaining.push(block);
                }
            }
            if !remaining.is_empty() {
                table.insert(len, remaining);
            }
        }
    }

    matches
}

/// Detect adjacent blocks that match a compressible pattern (stub for now).
pub fn detect_bundles(_table: &BlockTable) -> Vec<BlockChange> {
    Vec::new()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn table_groups_by_length() {
        let mut table: BlockTable = HashMap::new();
        let block = Block {
            global_index: 0,
            bit_length: 8,
            data: vec![0xAB],
            arity: None,
            seed_index: None,
        };
        table.entry(block.bit_length).or_default().push(block.clone());
        assert_eq!(table.get(&8).unwrap()[0].global_index, 0);
    }

    #[test]
    fn split_basic() {
        let input = vec![1u8, 2, 3, 4, 5];
        let blocks = split_into_blocks(&input, 16);
        assert_eq!(blocks.len(), 3);
        assert_eq!(blocks[0].global_index, 0);
        assert_eq!(blocks[0].bit_length, 16);
        assert_eq!(blocks[0].data, vec![1u8, 2]);
        assert_eq!(blocks[1].global_index, 1);
        assert_eq!(blocks[1].bit_length, 16);
        assert_eq!(blocks[1].data, vec![3u8, 4]);
        assert_eq!(blocks[2].global_index, 2);
        assert_eq!(blocks[2].bit_length, 8);
        assert_eq!(blocks[2].data, vec![5u8]);
    }

    #[test]
    fn split_exact() {
        let input = vec![1u8, 2, 3, 4];
        let blocks = split_into_blocks(&input, 16);
        assert_eq!(blocks.len(), 2);
        assert!(blocks.iter().all(|b| b.bit_length == 16));
    }

    #[test]
    fn group_blocks() {
        let blocks = vec![
            Block { global_index: 0, bit_length: 8, data: vec![0], arity: None, seed_index: None },
            Block { global_index: 1, bit_length: 16, data: vec![1, 2], arity: None, seed_index: None },
            Block { global_index: 2, bit_length: 8, data: vec![3], arity: None, seed_index: None },
        ];
        let table = group_by_bit_length(blocks);
        assert_eq!(table.get(&8).unwrap().len(), 2);
        assert_eq!(table.get(&16).unwrap().len(), 1);
    }
}
