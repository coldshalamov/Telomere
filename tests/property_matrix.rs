use proptest::prelude::*;
use telomere::{compress, decompress, select_bundles, BundleRecord, superposition::SuperpositionManager, types::Candidate};

proptest! {
    #![proptest_config(ProptestConfig { cases: 1, .. ProptestConfig::default() })]
    #[test]
    fn roundtrip_fuzz(data in proptest::collection::vec(any::<u8>(), 32..65),
                      block in 2usize..5,
                      _passes in 1usize..2) {
        let orig_len = data.len();
        let compressed = compress(&data, block).unwrap();
        let decoded = decompress(&compressed).unwrap();
        prop_assert_eq!(decoded, data.clone());
        prop_assert!(compressed.len() <= orig_len + 8);
    }
}

proptest! {
    #![proptest_config(ProptestConfig { cases: 1, .. ProptestConfig::default() })]
    #[test]
    fn superposition_minimality(bitlens in proptest::collection::vec(8usize..40, 1..6)) {
        let mut mgr = SuperpositionManager::new();
        for (i, len) in bitlens.iter().enumerate() {
            mgr.push_unpruned(0, Candidate { seed_index: i as u64, arity: 1, bit_len: *len });
        }
        mgr.prune_end_of_pass();
        if let Some((_idx, list)) = mgr.all_superposed().into_iter().find(|(i, _)| *i == 0) {
            prop_assert_eq!(list.len(), 1);
            let min = *bitlens.iter().min().unwrap();
            prop_assert_eq!(list[0].1.bit_len, min);
        }
    }
}

proptest! {
    #![proptest_config(ProptestConfig { cases: 1, .. ProptestConfig::default() })]
    #[test]
    fn bundler_idempotence(records in proptest::collection::vec(
            (1usize..10usize, 1usize..4usize, proptest::collection::vec(0usize..20usize, 1..4), 8usize..80usize), 1..5)) {
        let recs: Vec<BundleRecord> = records.into_iter().map(|(seed,bundle_len,idxs,bits)| BundleRecord {
            seed_index: seed,
            bundle_length: bundle_len,
            block_indices: idxs,
            original_bits: bits,
        }).collect();
        let first = select_bundles(recs.clone());
        let second = select_bundles(recs);
        prop_assert_eq!(first.len(), second.len());
        for (a, b) in first.iter().zip(second.iter()) {
            prop_assert_eq!(a.seed_index, b.seed_index);
            prop_assert_eq!(a.bundle_length, b.bundle_length);
            prop_assert_eq!(&a.block_indices, &b.block_indices);
            prop_assert_eq!(a.original_bits, b.original_bits);
            prop_assert_eq!(a.superposed, b.superposed);
        }
    }
}

proptest! {
    #![proptest_config(ProptestConfig { cases: 1, .. ProptestConfig::default() })]
    #[test]
    fn fuzzed_headers(data in proptest::collection::vec(any::<u8>(), 32..64), bit in any::<u16>()) {
        let compressed = compress(&data, 3).unwrap();
        let total_bits = compressed.len() * 8;
        if total_bits == 0 {
            return Ok(());
        }
        let flip = (bit as usize) % total_bits;
        let mut corrupted = compressed.clone();
        corrupted[flip / 8] ^= 1u8 << (flip % 8);
        match decompress(&corrupted) {
            Ok(out) => prop_assert_ne!(out, data),
            Err(_) => prop_assert!(true),
        }
    }
}
