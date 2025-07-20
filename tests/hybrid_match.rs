//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
use telomere::{CpuMatchRecord, GpuMatchRecord};

#[test]
fn cpu_match_record_fields_are_consistent() {
    let rec = CpuMatchRecord {
        seed_index: 17,
        bundle_length: 3,
        block_indices: vec![10, 11, 12],
        original_bits: 72,
    };
    assert_eq!(rec.bundle_length, rec.block_indices.len());
    assert_eq!(rec.original_bits, 72);
}

#[test]
fn gpu_match_record_fields_are_consistent() {
    let rec = GpuMatchRecord {
        seed_index: 5,
        bundle_length: 2,
        block_indices: vec![44, 45],
        original_bits: 48,
    };
    assert_eq!(rec.block_indices.len(), 2);
    assert_eq!(rec.original_bits, 48);
}
