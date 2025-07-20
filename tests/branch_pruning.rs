//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
use telomere::{collapse_branches, finalize_table, group_by_bit_length, prune_branches, Block};

#[test]
fn prune_removes_longest() {
    let blocks = vec![
        Block {
            global_index: 0,
            bit_length: 8,
            data: vec![0],
            digest: [0u8; 32],
            arity: None,
            seed_index: None,
            branch_label: 'A',
            status: telomere::BranchStatus::Active,
        },
        Block {
            global_index: 0,
            bit_length: 24,
            data: vec![1, 2, 3],
            digest: [0u8; 32],
            arity: None,
            seed_index: None,
            branch_label: 'A',
            status: telomere::BranchStatus::Active,
        },
        Block {
            global_index: 1,
            bit_length: 8,
            data: vec![4],
            digest: [0u8; 32],
            arity: None,
            seed_index: None,
            branch_label: 'B',
            status: telomere::BranchStatus::Active,
        },
    ];
    let mut table = group_by_bit_length(blocks);
    prune_branches(&mut table);
    // index 0 should only have 8-bit block
    assert_eq!(
        table
            .get(&8)
            .unwrap()
            .iter()
            .filter(|b| b.global_index == 0)
            .count(),
        1
    );
    assert!(table
        .get(&24)
        .map_or(true, |v| v.iter().all(|b| b.global_index != 0)));
}

#[test]
fn collapse_from_index() {
    let blocks = vec![
        Block {
            global_index: 0,
            bit_length: 8,
            data: vec![0],
            digest: [0u8; 32],
            arity: None,
            seed_index: None,
            branch_label: 'A',
            status: telomere::BranchStatus::Active,
        },
        Block {
            global_index: 0,
            bit_length: 16,
            data: vec![1, 2],
            digest: [0u8; 32],
            arity: None,
            seed_index: None,
            branch_label: 'B',
            status: telomere::BranchStatus::Active,
        },
        Block {
            global_index: 1,
            bit_length: 8,
            data: vec![3],
            digest: [0u8; 32],
            arity: None,
            seed_index: None,
            branch_label: 'A',
            status: telomere::BranchStatus::Active,
        },
        Block {
            global_index: 1,
            bit_length: 16,
            data: vec![4, 5],
            digest: [0u8; 32],
            arity: None,
            seed_index: None,
            branch_label: 'B',
            status: telomere::BranchStatus::Active,
        },
    ];
    let mut table = group_by_bit_length(blocks);
    collapse_branches(&mut table, 0);
    assert_eq!(
        table
            .get(&8)
            .unwrap()
            .iter()
            .filter(|b| b.global_index == 0)
            .count(),
        1
    );
    assert!(table
        .get(&16)
        .map_or(true, |v| v.iter().all(|b| b.global_index != 0)));
    assert_eq!(
        table
            .get(&8)
            .unwrap()
            .iter()
            .filter(|b| b.global_index == 1)
            .count(),
        1
    );
}

#[test]
fn finalize_unique_blocks() {
    let blocks = vec![
        Block {
            global_index: 0,
            bit_length: 16,
            data: vec![0, 1],
            digest: [0u8; 32],
            arity: None,
            seed_index: None,
            branch_label: 'A',
            status: telomere::BranchStatus::Active,
        },
        Block {
            global_index: 0,
            bit_length: 8,
            data: vec![2],
            digest: [0u8; 32],
            arity: None,
            seed_index: None,
            branch_label: 'B',
            status: telomere::BranchStatus::Active,
        },
        Block {
            global_index: 1,
            bit_length: 8,
            data: vec![3],
            digest: [0u8; 32],
            arity: None,
            seed_index: None,
            branch_label: 'A',
            status: telomere::BranchStatus::Active,
        },
    ];
    let table = group_by_bit_length(blocks);
    let final_blocks = finalize_table(table);
    assert_eq!(final_blocks.len(), 2);
    assert_eq!(final_blocks[0].global_index, 0);
    assert_eq!(final_blocks[0].bit_length, 8);
    assert_eq!(final_blocks[1].global_index, 1);
}
