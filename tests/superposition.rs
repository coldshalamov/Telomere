use rand::seq::SliceRandom;
use rand::{thread_rng, Rng};
use telomere::superposition::SuperpositionManager;
use telomere::types::Candidate;
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

#[test]
fn superposed_label_promotion() {
    let mut mgr = SuperpositionManager::new();
    let a = Candidate { seed_index: 1, arity: 1, bit_len: 24 };
    let b = Candidate { seed_index: 2, arity: 1, bit_len: 29 };
    let c = Candidate { seed_index: 3, arity: 1, bit_len: 31 };

    mgr.insert_superposed(0, a.clone()).unwrap();
    mgr.insert_superposed(0, b.clone()).unwrap();
    mgr.insert_superposed(0, c).unwrap();

    let better = Candidate { seed_index: 4, arity: 1, bit_len: 23 };
    mgr.insert_superposed(0, better.clone()).unwrap();

    let list = mgr.all_superposed().into_iter().find(|(i, _)| *i == 0).unwrap().1;
    assert_eq!(list.len(), 3);
    assert_eq!(list[0].0, 'A');
    assert_eq!(list[0].1.bit_len, better.bit_len);
    assert_eq!(list[1].0, 'B');
    assert_eq!(list[1].1.bit_len, a.bit_len);
    assert_eq!(list[2].0, 'C');
    assert_eq!(list[2].1.bit_len, b.bit_len);
}

#[test]
fn superposed_prune_many() {
    let mut rng = thread_rng();
    let mut mgr = SuperpositionManager::new();
    for i in 0..100u64 {
        let len = rng.gen_range(8..40);
        mgr.insert_superposed(0, Candidate { seed_index: i, arity: 1, bit_len: len }).unwrap();
    }
    mgr.prune_end_of_pass();
    let list = mgr.all_superposed().into_iter().find(|(i, _)| *i == 0).unwrap().1;
    assert!(list.len() <= 3);
    assert_eq!(list[0].0, 'A');
    let best = list[0].1.bit_len;
    for (_, c) in &list {
        assert!(c.bit_len - best <= 8);
    }
    let mut sorted = list.clone();
    sorted.sort_by(|a, b| a.1.bit_len.cmp(&b.1.bit_len).then(a.1.seed_index.cmp(&b.1.seed_index)));
    assert_eq!(list, sorted);
}

use proptest::prop_assert_eq;

proptest::proptest! {
    #[test]
    fn order_independent(mut vals in proptest::collection::vec((8usize..40usize, 0u64..1000u64), 1..20)) {
        let original = vals.clone();
        let mut mgr1 = SuperpositionManager::new();
        for (len, seed) in original.iter() {
            mgr1.insert_superposed(0, Candidate { seed_index:*seed, arity:1, bit_len:*len }).unwrap();
        }
        mgr1.prune_end_of_pass();
        let out1 = mgr1.all_superposed();

        vals.shuffle(&mut thread_rng());
        let mut mgr2 = SuperpositionManager::new();
        for (len, seed) in vals {
            mgr2.insert_superposed(0, Candidate { seed_index:seed, arity:1, bit_len:len }).unwrap();
        }
        mgr2.prune_end_of_pass();
        prop_assert_eq!(out1, mgr2.all_superposed());
    }
}
