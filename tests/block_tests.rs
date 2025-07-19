use telomere::{split_into_blocks, group_by_bit_length, collapse_branches, Block, BranchStatus};

#[test]
fn test_block_splitting_correctness() {
    // Splitting should produce three full blocks of 3 bytes and one final 1 byte block
    let input: Vec<u8> = (0u8..10).collect();
    let blocks = split_into_blocks(&input, 24); // 24 bits = 3 bytes per block
    assert_eq!(blocks.len(), 4);
    assert_eq!(blocks[0].data, vec![0, 1, 2]);
    assert_eq!(blocks[3].data, vec![9]);
}

#[test]
fn test_block_bit_length_grouping() {
    // Different bytes but identical length should group under the same bit length key
    let input_a = vec![1u8, 2, 3];
    let input_b = vec![0xFFu8; 3];
    let mut blocks = split_into_blocks(&input_a, 24);
    blocks.extend(split_into_blocks(&input_b, 24));
    let table = group_by_bit_length(blocks);
    assert!(table.get(&24).map_or(false, |g| g.len() >= 2));
}

#[test]
fn test_collapse_branches_keeps_shortest() {
    // When collapsing from index 0 only the shortest branch for that index should remain
    let blocks = vec![
        Block {
            global_index: 0,
            bit_length: 16,
            data: vec![0, 1],
            digest: [0u8; 32],
            arity: None,
            seed_index: None,
            branch_label: 'A',
            status: BranchStatus::Active,
        },
        Block {
            global_index: 0,
            bit_length: 8,
            data: vec![2],
            digest: [0u8; 32],
            arity: None,
            seed_index: None,
            branch_label: 'B',
            status: BranchStatus::Active,
        },
        Block {
            global_index: 1,
            bit_length: 8,
            data: vec![3],
            digest: [0u8; 32],
            arity: None,
            seed_index: None,
            branch_label: 'A',
            status: BranchStatus::Active,
        },
    ];
    let mut table = group_by_bit_length(blocks);
    collapse_branches(&mut table, 0);
    // index 0 should retain only one branch with 8 bits
    let branches = table.branches_for(0);
    assert_eq!(branches.len(), 1);
    assert_eq!(branches[0].bit_length, 8);
}
