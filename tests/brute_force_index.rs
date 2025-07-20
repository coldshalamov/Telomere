//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
use telomere::brute_force_seed_tables;

#[test]
fn seed_zero_matches_across_block_sizes() {
    // SHA-256 of seed 0 starts with 6e 34 0b
    let data = [0x6e, 0x34, 0x0b];
    let tables = brute_force_seed_tables(&data, 3, 1).expect("indexing");
    // block size 1: three blocks
    let bs1 = tables.get(&1).unwrap();
    assert_eq!(bs1.len(), 3);
    assert!(bs1[0].matches.contains(&0));
    // block size 2: two blocks (last is partial)
    let bs2 = tables.get(&2).unwrap();
    assert_eq!(bs2.len(), 2);
    assert!(bs2[0].matches.contains(&0));
    // block size 3: one block
    let bs3 = tables.get(&3).unwrap();
    assert_eq!(bs3.len(), 1);
    assert!(bs3[0].matches.contains(&0));
}

#[test]
fn final_partial_block_included() {
    let data = [1u8, 2, 3, 4];
    let tables = brute_force_seed_tables(&data, 3, 1).expect("indexing");
    // for block size 3 there should be two entries, second is partial len 1
    let bs3 = tables.get(&3).unwrap();
    assert_eq!(bs3.len(), 2);
    assert_eq!(bs3[1].len, 1);
}
