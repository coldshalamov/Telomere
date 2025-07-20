//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
//!
//! A [`Block`] represents a candidate span of bytes along with metadata
//! used during compression.  The table groups blocks by bit length and
//! tracks alternative branches.  High level APIs expose functions for
//! grouping, pruning and collapsing branches as the search progresses.

use sha2::{Digest, Sha256};
use std::collections::HashMap;

/// Status of a candidate branch within a [`Block`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum BranchStatus {
    Active,
    Pruned,
    Collapsed,
}

#[derive(Debug, Clone)]
pub struct Block {
    /// Original order in the stream
    pub global_index: usize,
    /// Current size of this block in bits
    pub bit_length: usize,
    /// Raw bytes making up this block
    pub data: Vec<u8>,
    /// SHA-256 digest of the raw data
    pub digest: [u8; 32],
    /// Optional arity if this block was compressed later
    pub arity: Option<usize>,
    /// Optional seed index associated with compressed form
    pub seed_index: Option<usize>,
    /// Branch label when multiple candidates exist for the same index
    pub branch_label: char,
    /// Current status of this branch
    pub status: BranchStatus,
}

/// Represents an update to a specific block in the table.
#[derive(Debug, Clone)]
pub struct BlockChange {
    /// Global index of the block being replaced
    pub original_index: usize,
    /// Replacement block (bit length determines new group)
    pub new_block: Block,
}

/// BlockTable groups blocks by their bit length.
///
/// A table exists for every even-numbered bit length encountered during
/// compression. Tables persist for the lifetime of a run and are only
/// cleared when empty. Practical block sizes range from 8 to 512 bits
/// which yields at most 256 individual tables.
#[derive(Debug, Clone, Default)]
pub struct BlockTable {
    groups: HashMap<usize, Vec<Block>>,
}

impl BlockTable {
    /// Create a new empty table
    pub fn new() -> Self {
        Self {
            groups: HashMap::new(),
        }
    }

    /// Return the number of active groups
    pub fn group_count(&self) -> usize {
        self.groups.len()
    }

    /// Access a mutable group for the provided even bit length,
    /// creating it if necessary.
    pub fn group_mut(&mut self, len: usize) -> &mut Vec<Block> {
        assert!(len % 2 == 0, "bit length must be even");
        self.groups.entry(len).or_default()
    }

    /// Iterate over all groups
    pub fn iter(&self) -> impl Iterator<Item = (&usize, &Vec<Block>)> {
        self.groups.iter()
    }

    /// Get a reference to a specific group
    pub fn get(&self, len: &usize) -> Option<&Vec<Block>> {
        self.groups.get(len)
    }

    /// Iterate mutably over all groups
    pub fn iter_mut(&mut self) -> impl Iterator<Item = (&usize, &mut Vec<Block>)> {
        self.groups.iter_mut()
    }

    /// Return all candidate branches for a given global index sorted by label.
    pub fn branches_for(&self, index: usize) -> Vec<&Block> {
        let mut branches: Vec<&Block> = Vec::new();
        for group in self.groups.values() {
            for block in group.iter().filter(|b| b.global_index == index) {
                branches.push(block);
            }
        }
        branches.sort_by(|a, b| a.branch_label.cmp(&b.branch_label));
        branches
    }

    /// Calculate difference in bit length between longest and shortest branch.
    pub fn bit_length_delta(&self, index: usize) -> Option<usize> {
        let branches = self.branches_for(index);
        if branches.is_empty() {
            None
        } else {
            let min = branches.iter().map(|b| b.bit_length).min().unwrap_or(0);
            let max = branches.iter().map(|b| b.bit_length).max().unwrap_or(0);
            Some(max - min)
        }
    }

    /// Clear empty groups of allocated memory without removing them.
    pub fn clear_empty(&mut self) {
        for vec in self.groups.values_mut() {
            if vec.is_empty() {
                vec.shrink_to_fit();
            }
        }
    }
}

/// Given a flat list of [`Block`]s, return a [`BlockTable`]
pub fn group_by_bit_length(blocks: Vec<Block>) -> BlockTable {
    let mut table = BlockTable::new();
    for block in blocks {
        table.group_mut(block.bit_length).push(block);
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
            digest: Sha256::digest(slice).into(),
            arity: None,
            seed_index: None,
            branch_label: 'A',
            status: BranchStatus::Active,
        });

        offset += block_size_bytes;
        index += 1;
    }

    blocks
}

/// Simulate a compression pass using a prebuilt seed table.
pub fn simulate_pass(table: &mut BlockTable, seed_table: &HashMap<String, usize>) -> usize {
    let mut lengths: Vec<usize> = table.iter().map(|(k, _)| *k).collect();
    lengths.sort_unstable_by(|a, b| b.cmp(a));

    let mut matches = 0usize;

    for len in lengths {
        let mut group = std::mem::take(table.group_mut(len));
        let mut remaining = Vec::new();
        for mut block in group.into_iter() {
            let digest = Sha256::digest(&block.data);
            let hex = hex::encode(digest);
            if let Some(&seed_idx) = seed_table.get(&hex) {
                block.seed_index = Some(seed_idx);
                block.arity = Some(1);
                block.bit_length = 16;
                block.digest = digest.into();
                block.branch_label = 'A';
                block.status = BranchStatus::Active;
                table.group_mut(16).push(block);
                matches += 1;
            } else {
                remaining.push(block);
            }
        }
        if !remaining.is_empty() {
            *table.group_mut(len) = remaining;
        }
    }

    matches
}

/// Apply a batch of block modifications to the table.
pub fn apply_block_changes(table: &mut BlockTable, changes: Vec<BlockChange>) {
    for mut change in changes {
        // Remove the old block
        for (_, group) in table.iter_mut() {
            while let Some(pos) = group
                .iter()
                .position(|b| b.global_index == change.original_index)
            {
                group.remove(pos);
            }
        }

        change.new_block.global_index = change.original_index;
        table
            .group_mut(change.new_block.bit_length)
            .push(change.new_block);
    }
}

/// Print a short summary of how many blocks exist for each bit length.
pub fn print_table_summary(table: &BlockTable) {
    let mut blocks: Vec<&Block> = table.iter().flat_map(|(_, g)| g.iter()).collect();
    blocks.sort_by(|a, b| match a.global_index.cmp(&b.global_index) {
        std::cmp::Ordering::Equal => a.branch_label.cmp(&b.branch_label),
        other => other,
    });
    for b in blocks {
        println!(
            "{}{}: {} bits ({:?})",
            b.global_index, b.branch_label, b.bit_length, b.status
        );
    }
}

/// Prune superposed branches whose bit-length delta exceeds eight bits.
pub fn prune_branches(table: &mut BlockTable) {
    use std::collections::HashMap;

    let mut by_index: HashMap<usize, Vec<(usize, usize)>> = HashMap::new();
    for (len, group) in table.iter() {
        for (idx, block) in group.iter().enumerate() {
            by_index
                .entry(block.global_index)
                .or_default()
                .push((*len, idx));
        }
    }

    let mut remove_map: HashMap<usize, Vec<usize>> = HashMap::new();
    for (_idx, branches) in by_index {
        if branches.len() <= 1 {
            continue;
        }
        let min_len = branches.iter().map(|b| b.0).min().unwrap_or(0);
        let max_len = branches.iter().map(|b| b.0).max().unwrap_or(0);
        if max_len - min_len > 8 {
            for (len, pos) in branches.iter().filter(|b| b.0 == max_len) {
                remove_map.entry(*len).or_default().push(*pos);
            }
        }
    }

    for (len, mut positions) in remove_map {
        if let Some(group) = table.groups.get_mut(&len) {
            positions.sort_unstable_by(|a, b| b.cmp(a));
            positions.dedup();
            for pos in positions {
                if pos < group.len() {
                    group.remove(pos);
                }
            }
        }
    }
}

/// Collapse all branches from the given index onward, keeping the shortest.
pub fn collapse_branches(table: &mut BlockTable, start_index: usize) {
    use std::collections::HashMap;

    let mut by_index: HashMap<usize, Vec<(usize, usize)>> = HashMap::new();
    for (len, group) in table.iter() {
        for (idx, block) in group.iter().enumerate() {
            if block.global_index >= start_index {
                by_index
                    .entry(block.global_index)
                    .or_default()
                    .push((*len, idx));
            }
        }
    }

    let mut remove_map: HashMap<usize, Vec<usize>> = HashMap::new();
    for (_idx, branches) in by_index {
        if branches.len() <= 1 {
            continue;
        }
        let min_len = branches.iter().map(|b| b.0).min().unwrap_or(0);
        for (len, pos) in branches.into_iter().filter(|b| b.0 != min_len) {
            remove_map.entry(len).or_default().push(pos);
        }
    }

    for (len, mut positions) in remove_map {
        if let Some(group) = table.groups.get_mut(&len) {
            positions.sort_unstable_by(|a, b| b.cmp(a));
            positions.dedup();
            for pos in positions {
                if pos < group.len() {
                    group.remove(pos);
                }
            }
        }
    }
}

/// Finalize the table into a single block per global index.
pub fn finalize_table(mut table: BlockTable) -> Vec<Block> {
    use std::collections::HashMap;

    let mut map: HashMap<usize, Block> = HashMap::new();
    for (_, group) in table.groups.drain() {
        for block in group.into_iter() {
            map.entry(block.global_index)
                .and_modify(|b| {
                    if block.bit_length < b.bit_length {
                        *b = block.clone();
                    }
                })
                .or_insert(block);
        }
    }
    let mut out: Vec<Block> = map.into_iter().map(|(_, b)| b).collect();
    out.sort_by_key(|b| b.global_index);
    out
}

/// Detect potential bundled blocks after a pass (stub).
pub fn detect_bundles(_table: &mut BlockTable) {}

/// Run compression passes until no additional matches are found.
pub fn run_all_passes(mut table: BlockTable, seed_table: &HashMap<String, usize>) -> BlockTable {
    loop {
        let matches = simulate_pass(&mut table, seed_table);
        if matches == 0 {
            break;
        }
        detect_bundles(&mut table);
        apply_block_changes(&mut table, vec![]);
        table.clear_empty();
    }
    table
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn table_groups_by_length() {
        let mut table = BlockTable::new();
        let block = Block {
            global_index: 0,
            bit_length: 8,
            data: vec![0xAB],
            digest: [0u8; 32],
            arity: None,
            seed_index: None,
            branch_label: 'A',
            status: BranchStatus::Active,
        };
        table.group_mut(block.bit_length).push(block.clone());
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
                digest: [0u8; 32],
                arity: None,
                seed_index: None,
                branch_label: 'A',
                status: BranchStatus::Active,
            },
            Block {
                global_index: 1,
                bit_length: 16,
                data: vec![1, 2],
                digest: [0u8; 32],
                arity: None,
                seed_index: None,
                branch_label: 'A',
                status: BranchStatus::Active,
            },
            Block {
                global_index: 2,
                bit_length: 8,
                data: vec![3],
                digest: [0u8; 32],
                arity: None,
                seed_index: None,
                branch_label: 'A',
                status: BranchStatus::Active,
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
                digest: [0u8; 32],
                arity: None,
                seed_index: None,
                branch_label: 'A',
                status: BranchStatus::Active,
            },
            Block {
                global_index: 1,
                bit_length: 8,
                data: vec![2],
                digest: [0u8; 32],
                arity: None,
                seed_index: None,
                branch_label: 'A',
                status: BranchStatus::Active,
            },
        ];
        let table = group_by_bit_length(blocks.clone());
        let seed_table: HashMap<String, usize> = HashMap::new();
        let out = run_all_passes(table, &seed_table);
        assert_eq!(out.get(&8).unwrap().len(), blocks.len());
        assert!(out.get(&16).map_or(true, |v| v.is_empty()));
    }
}
