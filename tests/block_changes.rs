use inchworm::{Block, BlockChange, group_by_bit_length, apply_block_changes};

#[test]
fn apply_single_change() {
    let blocks = vec![
        Block { global_index: 0, bit_length: 8, data: vec![1], arity: None, seed_index: None },
        Block { global_index: 1, bit_length: 8, data: vec![2], arity: None, seed_index: None },
    ];
    let mut table = group_by_bit_length(blocks);
    assert_eq!(table.get(&8).unwrap().len(), 2);

    let new = Block { global_index: 0, bit_length: 16, data: vec![3,4], arity: None, seed_index: Some(0) };
    let change = BlockChange { original_index: 1, new_block: new };

    apply_block_changes(&mut table, vec![change]);

    assert_eq!(table.get(&8).unwrap().len(), 1);
    assert_eq!(table.get(&16).unwrap().len(), 1);
    let block = &table.get(&16).unwrap()[0];
    assert_eq!(block.global_index, 1);
}
