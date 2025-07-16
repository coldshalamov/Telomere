use telomere::{apply_block_changes, group_by_bit_length, Block, BlockChange, BranchStatus};

#[test]
fn apply_single_change() {
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
    let mut table = group_by_bit_length(blocks);
    assert_eq!(table.get(&8).unwrap().len(), 2);

    let new = Block {
        global_index: 0,
        bit_length: 16,
        data: vec![3, 4],
        digest: [0u8; 32],
        arity: None,
        seed_index: Some(0),
        branch_label: 'A',
        status: BranchStatus::Active,
    };
    let change = BlockChange {
        original_index: 1,
        new_block: new,
    };

    apply_block_changes(&mut table, vec![change]);

    assert_eq!(table.get(&8).unwrap().len(), 1);
    assert_eq!(table.get(&16).unwrap().len(), 1);
    let block = &table.get(&16).unwrap()[0];
    assert_eq!(block.global_index, 1);
}
