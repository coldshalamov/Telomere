use inchworm::{apply_bundle, BlockStatus, MutableBlock};

#[test]
fn apply_bundle_marks_and_inserts() {
    // create a simple table of eight active blocks
    let mut table: Vec<MutableBlock> = (0..8)
        .map(|i| MutableBlock {
            origin_index: i,
            position: i,
            bit_length: 8,
            data: vec![i as u8],
            arity: None,
            seed_index: None,
            status: BlockStatus::Active,
        })
        .collect();

    // bundle blocks 2..=4
    apply_bundle(&mut table, &[2, 3, 4], 1, 3, 16);

    // original blocks 2..=4 should be marked removed
    for idx in 2..=4 {
        assert_eq!(table[idx].status, BlockStatus::Removed);
    }

    // a new active block is appended with expected fields
    let new_block = table.last().unwrap();
    assert_eq!(new_block.origin_index, 2);
    assert_eq!(new_block.position, 2);
    assert_eq!(new_block.bit_length, 16);
    assert_eq!(new_block.arity, Some(3));
    assert_eq!(new_block.seed_index, Some(1));
    assert_eq!(new_block.status, BlockStatus::Active);
}

#[test]
fn test_bundle_applies_and_marks_removed() {
    let mut table: Vec<MutableBlock> = (0..4)
        .map(|i| MutableBlock {
            origin_index: i,
            position: i,
            bit_length: 8,
            data: vec![i as u8],
            arity: None,
            seed_index: None,
            status: BlockStatus::Active,
        })
        .collect();

    apply_bundle(&mut table, &[1, 2], 42, 2, 16);

    assert_eq!(table[1].status, BlockStatus::Removed);
    assert_eq!(table[2].status, BlockStatus::Removed);
    let new_block = table.last().unwrap();
    assert_eq!(new_block.seed_index, Some(42));
    assert_eq!(new_block.arity, Some(2));
    assert_eq!(new_block.bit_length, 16);
}
