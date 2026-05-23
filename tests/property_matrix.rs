//! Property matrix: roundtrip and superposition tests with fast config.
use proptest::prelude::*;
use telomere::superposition::SuperpositionManager;
use telomere::types::Candidate;
use telomere::{compress_multi_pass_with_config, decompress, Config};

fn fast_cfg(block_size: usize) -> Config {
    Config {
        block_size,
        max_seed_len: 1,
        hash_bits: 13,
        ..Config::default()
    }
}

proptest! {
    #![proptest_config(ProptestConfig { cases: 32, .. ProptestConfig::default() })]
    #[test]
    fn roundtrip_fuzz(
        data in proptest::collection::vec(any::<u8>(), 0..64),
        block in 1usize..8,
        passes in 1usize..4,
    ) {
        let cfg = fast_cfg(block);
        let (compressed, _) = compress_multi_pass_with_config(&data, &cfg, passes, false).unwrap();
        let out = decompress(&compressed, &cfg).unwrap();
        prop_assert_eq!(out.as_slice(), data.as_slice());
    }
}

proptest! {
    #![proptest_config(ProptestConfig { cases: 32, .. ProptestConfig::default() })]
    #[test]
    fn superposition_minimality(bit_lens in proptest::collection::vec(8usize..64, 1..8)) {
        let mut mgr = SuperpositionManager::new(1);
        for (i, len) in bit_lens.iter().enumerate() {
            mgr.push_unpruned(0, Candidate { seed_index: i as u64, arity: 1, bit_len: *len });
        }
        mgr.prune_end_of_pass();
        let list = mgr.all_superposed().into_iter().find(|(i, _)| *i == 0).unwrap().1;
        let min = *bit_lens.iter().min().unwrap();
        // After pruning, best candidate should be the one with minimum bit_len.
        prop_assert_eq!(list[0].1.bit_len, min);
    }
}

proptest! {
    #![proptest_config(ProptestConfig { cases: 16, .. ProptestConfig::default() })]
    #[test]
    fn bundler_idempotence(
        data in proptest::collection::vec(any::<u8>(), 0..64),
        block in 1usize..8,
        passes in 1usize..3,
    ) {
        let cfg = fast_cfg(block);
        let (first, _) = compress_multi_pass_with_config(&data, &cfg, passes, false).unwrap();
        let (second, _) = compress_multi_pass_with_config(&data, &cfg, passes, false).unwrap();
        prop_assert_eq!(first, second);
    }
}
