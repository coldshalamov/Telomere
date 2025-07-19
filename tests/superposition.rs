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
    let mut mgr = SuperpositionManager::new();

    let base = Candidate {
        seed_index: 1,
        arity: 1,
        bit_len: 24,
        pass_seen: 0,
    };
    let b = Candidate {
        seed_index: 2,
        arity: 1,
        bit_len: 29,
        pass_seen: 0,
    };
    let c = Candidate {
        seed_index: 3,
        arity: 1,
        bit_len: 31,
        pass_seen: 0,
    };

    assert!(mgr.insert_superposed(42, base.clone()).is_ok());
    assert!(mgr.insert_superposed(42, b.clone()).is_ok());
    assert!(mgr.insert_superposed(42, c.clone()).is_ok());

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
        pass_seen: 0,
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
