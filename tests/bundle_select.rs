use telomere::{select_bundles, BundleRecord};

#[test]
fn accept_non_overlapping_bundles() {
    let records = vec![
        BundleRecord {
            seed_index: 1,
            bundle_length: 3,
            block_indices: vec![10, 11, 12],
            original_bits: 72,
        },
        BundleRecord {
            seed_index: 2,
            bundle_length: 2,
            block_indices: vec![20, 21],
            original_bits: 48,
        },
    ];
    let accepted = select_bundles(records);
    assert_eq!(accepted.len(), 2);
    assert!(!accepted[0].superposed);
    assert!(!accepted[1].superposed);
}

#[test]
fn reject_overlap_with_multiple_bundles() {
    let records = vec![
        BundleRecord {
            seed_index: 1,
            bundle_length: 2,
            block_indices: vec![10, 11],
            original_bits: 48,
        },
        BundleRecord {
            seed_index: 2,
            bundle_length: 2,
            block_indices: vec![13, 14],
            original_bits: 48,
        },
        BundleRecord {
            seed_index: 3,
            bundle_length: 2,
            block_indices: vec![11, 13],
            original_bits: 48,
        },
    ];
    let accepted = select_bundles(records);
    assert_eq!(accepted.len(), 2);
}

#[test]
fn reject_non_subset_overlap() {
    let records = vec![
        BundleRecord {
            seed_index: 1,
            bundle_length: 3,
            block_indices: vec![10, 11, 12],
            original_bits: 72,
        },
        BundleRecord {
            seed_index: 2,
            bundle_length: 3,
            block_indices: vec![11, 12, 13],
            original_bits: 72,
        },
    ];
    let accepted = select_bundles(records);
    assert_eq!(accepted.len(), 1);
}

#[test]
fn reject_large_bit_delta() {
    let records = vec![
        BundleRecord {
            seed_index: 1,
            bundle_length: 3,
            block_indices: vec![10, 11, 12],
            original_bits: 72,
        },
        BundleRecord {
            seed_index: 2,
            bundle_length: 2,
            block_indices: vec![10, 11],
            original_bits: 81,
        },
    ];
    let accepted = select_bundles(records);
    assert_eq!(accepted.len(), 1);
}

#[test]
fn accept_superposition_when_within_delta() {
    let records = vec![
        BundleRecord {
            seed_index: 1,
            bundle_length: 3,
            block_indices: vec![10, 11, 12],
            original_bits: 72,
        },
        BundleRecord {
            seed_index: 2,
            bundle_length: 2,
            block_indices: vec![10, 11],
            original_bits: 80,
        },
    ];
    let accepted = select_bundles(records);
    assert_eq!(accepted.len(), 2);
    assert!(!accepted[0].superposed);
    assert!(accepted[1].superposed);
}
