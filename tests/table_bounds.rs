//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
use std::collections::HashMap;
use telomere::{group_by_bit_length, run_all_passes, split_into_blocks};

#[test]
fn table_counts_within_bounds() {
    let seed_table: HashMap<String, usize> = HashMap::new();
    let max_tables = 256usize;
    for size in [1usize, 8, 16, 32, 64, 128] {
        let data: Vec<u8> = (0..size as u8).collect();
        for bits in (8..=64).step_by(8) {
            let blocks = split_into_blocks(&data, bits);
            let table = group_by_bit_length(blocks);
            let out = run_all_passes(table, &seed_table);
            assert!(out.group_count() <= max_tables);
        }
    }
}
