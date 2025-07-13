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
}
