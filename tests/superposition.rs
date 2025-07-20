//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
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
fn superposed_insert_and_promote() {
    use telomere::superposition::InsertResult;

    let mut mgr = SuperpositionManager::new();

    let base = Candidate {
        seed_index: 1,
        arity: 1,
        bit_len: 24,
    };
    let b = Candidate {
        seed_index: 2,
        arity: 1,
        bit_len: 29,
    };
    let c = Candidate {
        seed_index: 3,
        arity: 1,
        bit_len: 31,
    };

    assert_eq!(
        mgr.insert_superposed(42, base.clone()).unwrap(),
        InsertResult::Inserted('A')
    );
    assert_eq!(
        mgr.insert_superposed(42, b.clone()).unwrap(),
        InsertResult::Inserted('B')
    );
    assert_eq!(
        mgr.insert_superposed(42, c.clone()).unwrap(),
        InsertResult::Inserted('C')
    );

    let list = mgr
        .all_superposed()
        .into_iter()
        .find(|(i, _)| *i == 42)
        .unwrap()
        .1;
    assert_eq!(list.len(), 3);

    let fail = Candidate {
        seed_index: 4,
        arity: 1,
        bit_len: 35,
    };
    assert!(mgr.insert_superposed(42, fail).is_err());

    mgr.collapse_superpositions();
    let list = mgr
        .all_superposed()
        .into_iter()
        .find(|(i, _)| *i == 42)
        .unwrap()
        .1;
    assert!(list.iter().all(|(_, c)| c.bit_len <= 32));

    let promoted = mgr.promote_superposed(42, 'B');
    assert_eq!(promoted.unwrap().bit_len, b.bit_len);
    assert!(mgr.best_superposed(42).is_none());
}

#[test]
fn superposed_delta_pruning() {
    use telomere::superposition::InsertResult;

    let mut mgr = SuperpositionManager::new();
    let a = Candidate {
        seed_index: 1,
        arity: 1,
        bit_len: 24,
    };
    let b = Candidate {
        seed_index: 2,
        arity: 1,
        bit_len: 31,
    };
    let big = Candidate {
        seed_index: 3,
        arity: 1,
        bit_len: 34,
    };

    assert_eq!(
        mgr.insert_superposed(7, a.clone()).unwrap(),
        InsertResult::Inserted('A')
    );
    assert_eq!(
        mgr.insert_superposed(7, b.clone()).unwrap(),
        InsertResult::Inserted('B')
    );
    // This insertion should prune the C candidate immediately
    assert_eq!(
        mgr.insert_superposed(7, big).unwrap(),
        InsertResult::Pruned(Vec::new())
    );

    let list = mgr
        .all_superposed()
        .into_iter()
        .find(|(i, _)| *i == 7)
        .unwrap()
        .1;
    assert_eq!(list.len(), 2);
    assert!(list.iter().any(|(l, _)| *l == 'A'));
    assert!(list.iter().any(|(l, _)| *l == 'B'));
}

#[test]
fn superposed_promotion_clears_all() {
    let mut mgr = SuperpositionManager::new();
    let a = Candidate {
        seed_index: 1,
        arity: 1,
        bit_len: 24,
    };
    let b = Candidate {
        seed_index: 2,
        arity: 1,
        bit_len: 29,
    };
    let c = Candidate {
        seed_index: 3,
        arity: 1,
        bit_len: 30,
    };

    mgr.insert_superposed(99, a).unwrap();
    mgr.insert_superposed(99, b.clone()).unwrap();
    mgr.insert_superposed(99, c).unwrap();

    let res = mgr.promote_superposed(99, 'B');
    assert_eq!(res.unwrap().bit_len, b.bit_len);
    assert!(mgr.best_superposed(99).is_none());
}

#[test]
fn superposed_insert_limit() {
    let mut mgr = SuperpositionManager::new();
    let a = Candidate {
        seed_index: 1,
        arity: 1,
        bit_len: 24,
    };
    let b = Candidate {
        seed_index: 2,
        arity: 1,
        bit_len: 26,
    };
    let c = Candidate {
        seed_index: 3,
        arity: 1,
        bit_len: 28,
    };
    let d = Candidate {
        seed_index: 4,
        arity: 1,
        bit_len: 30,
    };

    assert!(mgr.insert_superposed(5, a).is_ok());
    assert!(mgr.insert_superposed(5, b).is_ok());
    assert!(mgr.insert_superposed(5, c).is_ok());
    assert!(mgr.insert_superposed(5, d).is_err());
}

#[test]
fn superposed_fourth_prunes_longest() {
    use telomere::superposition::InsertResult;

    let mut mgr = SuperpositionManager::new();
    let a = Candidate {
        seed_index: 1,
        arity: 1,
        bit_len: 24,
    };
    let b = Candidate {
        seed_index: 2,
        arity: 1,
        bit_len: 30,
    };
    let c = Candidate {
        seed_index: 3,
        arity: 1,
        bit_len: 31,
    };
    let better = Candidate {
        seed_index: 4,
        arity: 1,
        bit_len: 25,
    };

    assert_eq!(
        mgr.insert_superposed(11, a.clone()).unwrap(),
        InsertResult::Inserted('A')
    );
    assert_eq!(
        mgr.insert_superposed(11, b.clone()).unwrap(),
        InsertResult::Inserted('B')
    );
    assert_eq!(
        mgr.insert_superposed(11, c.clone()).unwrap(),
        InsertResult::Inserted('C')
    );

    // New candidate is better than the current worst (31) and should replace it.
    assert_eq!(
        mgr.insert_superposed(11, better.clone()).unwrap(),
        InsertResult::Pruned(vec!['C'])
    );

    let list = mgr
        .all_superposed()
        .into_iter()
        .find(|(i, _)| *i == 11)
        .unwrap()
        .1;
    assert_eq!(list.len(), 3);
    assert!(list
        .iter()
        .any(|(l, c)| *l == 'A' && c.bit_len == a.bit_len));
    assert!(list
        .iter()
        .any(|(l, c)| *l == 'B' && c.bit_len == b.bit_len));
    assert!(list
        .iter()
        .any(|(l, c)| *l == 'C' && c.bit_len == better.bit_len));
}

#[test]
fn prune_end_of_pass_keeps_shortest() {
    let mut mgr = SuperpositionManager::new();
    mgr.push_unpruned(
        0,
        Candidate {
            seed_index: 1,
            arity: 1,
            bit_len: 30,
        },
    );
    mgr.push_unpruned(
        0,
        Candidate {
            seed_index: 2,
            arity: 1,
            bit_len: 28,
        },
    );
    mgr.push_unpruned(
        0,
        Candidate {
            seed_index: 3,
            arity: 1,
            bit_len: 28,
        },
    );
    mgr.prune_end_of_pass();
    let list = mgr
        .all_superposed()
        .into_iter()
        .find(|(i, _)| *i == 0)
        .unwrap()
        .1;
    assert_eq!(list.len(), 1);
    assert_eq!(list[0].1.bit_len, 28);
}

proptest::proptest! {
    #[test]
    fn superposition_invariants(bit_lens in proptest::collection::vec(8usize..40, 1..10)) {
        let mut mgr = SuperpositionManager::new();
        for (idx, len) in bit_lens.into_iter().enumerate() {
            let _ = mgr.insert_superposed(0, Candidate { seed_index: idx as u64, arity: 1, bit_len: len });
            if let Some((_, list)) = mgr.all_superposed().into_iter().find(|(i, _)| *i == 0) {
                assert!(list.len() <= 3);
                if list.len() > 1 {
                    let min = list.iter().map(|(_, c)| c.bit_len).min().unwrap();
                    let max = list.iter().map(|(_, c)| c.bit_len).max().unwrap();
                    assert!(max - min <= 8);
                }
                let mut labels = std::collections::HashSet::new();
                for (l, _) in list.iter() {
                    assert!(labels.insert(*l));
                    assert!(*l == 'A' || *l == 'B' || *l == 'C');
                }
            }
        }
    }
}
