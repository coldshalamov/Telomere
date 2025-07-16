use telomere::{apply_block_changes, group_by_bit_length, Block, BlockChange, BranchStatus};

#[test]
fn branches_sorted_and_delta() {
    let blocks = vec![
        Block {
            global_index: 0,
            bit_length: 16,
            data: vec![1, 2],
            digest: [0u8; 32],
            arity: None,
            seed_index: None,
            branch_label: 'B',
            status: BranchStatus::Active,
        },
        Block {
            global_index: 0,
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
    let branches = table.branches_for(0);
    assert_eq!(branches.len(), 2);
    assert_eq!(branches[0].branch_label, 'A');
    assert_eq!(branches[1].branch_label, 'B');
    assert_eq!(table.bit_length_delta(0), Some(8));
}

#[test]
fn block_change_clears_branches() {
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
            global_index: 0,
            bit_length: 16,
            data: vec![2, 3],
            digest: [0u8; 32],
            arity: None,
            seed_index: None,
            branch_label: 'B',
            status: BranchStatus::Active,
        },
    ];
    let mut table = group_by_bit_length(blocks);
    let change = BlockChange {
        original_index: 0,
        new_block: Block {
            global_index: 0,
            bit_length: 12,
            data: vec![4, 5],
            digest: [0u8; 32],
            arity: None,
            seed_index: Some(1),
            branch_label: 'C',
            status: BranchStatus::Active,
        },
    };
    apply_block_changes(&mut table, vec![change]);
    let branches = table.branches_for(0);
    assert_eq!(branches.len(), 1);
    assert_eq!(branches[0].branch_label, 'C');
}
