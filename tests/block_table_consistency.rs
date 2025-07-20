//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
use telomere::{finalize_table, group_by_bit_length, split_into_blocks, Block, BranchStatus};

#[test]
fn block_table_roundtrip() {
    let input: Vec<u8> = (0u8..16).collect();
    let blocks = split_into_blocks(&input, 8);
    let table = group_by_bit_length(blocks.clone());
    let final_vec = finalize_table(table.clone());
    let table2 = group_by_bit_length(final_vec.clone());
    let final_vec2 = finalize_table(table2);
    assert_eq!(final_vec.len(), final_vec2.len());
    for (a, b) in final_vec.iter().zip(final_vec2.iter()) {
        assert_eq!(a.global_index, b.global_index);
        assert_eq!(a.bit_length, b.bit_length);
        assert_eq!(a.data, b.data);
        assert_eq!(a.status, BranchStatus::Active);
        assert_eq!(b.status, BranchStatus::Active);
    }
}
