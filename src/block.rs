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

use std::collections::HashMap;

/// BlockTable groups blocks by their bit length
pub type BlockTable = HashMap<usize, Vec<Block>>;

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
}
