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

use sha2::{Digest, Sha256};
use std::collections::HashMap;

/// Extend BlockTable with table mutations
/// Each bit length gets a vector of Blocks
pub type BlockTable = HashMap<usize, Vec<Block>>;

/// BlockChange captures updates to a block during simulation
#[derive(Debug, Clone)]
pub struct BlockChange {
    /// Index of the block in its original order
    pub original_index: usize,
    /// Replacement block after mutation
    pub new_block: Block,
}

/// Given a flat list of [`Block`]s, return a [`BlockTable`]
/// where blocks are grouped by their bit length.
///
/// This is primarily used when simulating the compression pipeline
/// after splitting raw input into blocks.
pub fn group_by_bit_length(blocks: Vec<Block>) -> BlockTable {
    let mut table: BlockTable = HashMap::new();
    for block in blocks {
        table.entry(block.bit_length).or_default().push(block);
    }
    table
}

/// Split raw input into fixed-sized blocks measured in bits.
///
/// Each returned [`Block`] will have `bit_length` equal to `block_size_bits`
/// except for the final block which may be shorter when the input length is not
/// perfectly divisible by the requested block size. The raw byte data of each
/// block is stored directly without any bit-level slicing or padding.
pub fn split_into_blocks(input: &[u8], block_size_bits: usize) -> Vec<Block> {
    assert!(block_size_bits > 0, "block size must be non-zero");

    // Number of whole bytes that contain the requested number of bits. We round
    // up so blocks always contain enough data even when not byte aligned.
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
///
/// Each block is hashed and looked up in `seed_table`. When a match is found the
/// block is marked as compressed by setting `seed_index` and `arity`, its
/// `bit_length` is updated to 16 bits and it is moved into the `16` bit group.
/// Returns the total number of blocks that were successfully matched.
pub fn simulate_pass(table: &mut BlockTable, seed_table: &HashMap<String, usize>) -> usize {
    // Collect the keys so we can iterate in descending order without holding
    // mutable borrows while inserting into the table.
    let mut lengths: Vec<usize> = table.keys().cloned().collect();
    lengths.sort_unstable_by(|a, b| b.cmp(a));

    let mut matches = 0usize;

    for len in lengths {
        // Take the current group to avoid double borrowing of `table` when we
        // insert matched blocks into other groups.
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

/// Detect potential bundled blocks after a pass.
///
/// This function is currently a stub that does nothing. It exists so future
/// improvements can analyze the `BlockTable` for bundle opportunities between
/// simulation passes.
pub fn detect_bundles(_table: &mut BlockTable) {}

/// Apply any changes discovered during bundle detection.
///
/// The default implementation is a no-op until bundling logic is implemented.
pub fn apply_block_changes(_table: &mut BlockTable) {}

/// Run compression passes until no additional matches are found.
///
/// After each call to [`simulate_pass`], this function runs `detect_bundles`
/// followed by `apply_block_changes`. The resulting [`BlockTable`] is returned
/// once a pass yields zero matches.
pub fn run_all_passes(mut table: BlockTable, seed_table: &HashMap<String, usize>) -> BlockTable {
    loop {
        let matches = simulate_pass(&mut table, seed_table);
        if matches == 0 {
            break;
        }
        detect_bundles(&mut table);
        apply_block_changes(&mut table);
    }
    table
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
        table
            .entry(block.bit_length)
            .or_default()
            .push(block.clone());
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
            Block {
                global_index: 0,
                bit_length: 8,
                data: vec![0],
                arity: None,
                seed_index: None,
            },
            Block {
                global_index: 1,
                bit_length: 16,
                data: vec![1, 2],
                arity: None,
                seed_index: None,
            },
            Block {
                global_index: 2,
                bit_length: 8,
                data: vec![3],
                arity: None,
                seed_index: None,
            },
        ];
        let table = group_by_bit_length(blocks);
        assert_eq!(table.get(&8).unwrap().len(), 2);
        assert_eq!(table.get(&16).unwrap().len(), 1);
    }

    #[test]
    fn run_all_passes_no_matches() {
        let blocks = vec![
            Block {
                global_index: 0,
                bit_length: 8,
                data: vec![1],
                arity: None,
                seed_index: None,
            },
            Block {
                global_index: 1,
                bit_length: 8,
                data: vec![2],
                arity: None,
                seed_index: None,
            },
        ];
        let table = group_by_bit_length(blocks.clone());
        let seed_table: HashMap<String, usize> = HashMap::new();
        let out = run_all_passes(table, &seed_table);
        assert_eq!(out.get(&8).unwrap().len(), blocks.len());
        assert!(out.get(&16).is_none());
    }
}
