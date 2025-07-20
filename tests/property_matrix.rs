use proptest::prelude::*;
use telomere::superposition::SuperpositionManager;
use telomere::types::Candidate;
use telomere::{compress, compress_multi_pass, decompress, Config};

proptest! {
    #![proptest_config(ProptestConfig { cases: 16, .. ProptestConfig::default() })]
    // Round-trip fuzz across bundling modes
    #[test]
    fn roundtrip_fuzz(data in proptest::collection::vec(any::<u8>(), 32..257),
                      block in 2usize..8,
                      passes in 1usize..4,
                      bundling in proptest::bool::ANY) {
        let compressed = if bundling {
            compress_multi_pass(&data, block, passes).unwrap().0
        } else {
            compress(&data, block).unwrap()
        };
        let cfg = Config { block_size: block, ..Config::default() };
        let out = decompress(&compressed, &cfg).unwrap();
        prop_assert_eq!(out.as_slice(), data.as_slice());
        prop_assert!(compressed.len() <= data.len() + 8);
    }
}

proptest! {
    #![proptest_config(ProptestConfig { cases: 16, .. ProptestConfig::default() })]
    // Superposition pruning keeps only the smallest candidate
    #[test]
    fn superposition_minimality(bit_lens in proptest::collection::vec(8usize..64, 1..8)) {
        let mut mgr = SuperpositionManager::new(1);
        for (i, len) in bit_lens.iter().enumerate() {
            mgr.push_unpruned(0, Candidate { seed_index: i as u64, arity: 1, bit_len: *len });
        }
        mgr.prune_end_of_pass();
        let list = mgr.all_superposed().into_iter().find(|(i, _)| *i == 0).unwrap().1;
        let min = *bit_lens.iter().min().unwrap();
        prop_assert_eq!(list.len(), 1);
        prop_assert_eq!(list[0].1.bit_len, min);
    }
}

proptest! {
    #![proptest_config(ProptestConfig { cases: 16, .. ProptestConfig::default() })]
    // Compressing the same data twice yields identical output
    #[test]
    fn bundler_idempotence(data in proptest::collection::vec(any::<u8>(), 32..257),
                           block in 2usize..8,
                           passes in 1usize..4) {
        let (first, _) = compress_multi_pass(&data, block, passes).unwrap();
        let (second, _) = compress_multi_pass(&data, block, passes).unwrap();
        prop_assert_eq!(first, second);
    }
}

proptest! {
    #![proptest_config(ProptestConfig { cases: 16, .. ProptestConfig::default() })]
    // Bit flips invalidate the compressed stream
    #[test]
    fn fuzzed_headers(data in proptest::collection::vec(any::<u8>(), 32..128),
                      block in 2usize..8,
                      bit in 0usize..1000) {
        let compressed = compress(&data, block).unwrap();
        if compressed.is_empty() { return Ok(()); }
        let total_bits = compressed.len() * 8;
        let idx = bit % total_bits;
        let mut corrupt = compressed.clone();
        corrupt[idx / 8] ^= 1 << (idx % 8);
        let cfg = Config { block_size: block, ..Config::default() };
        prop_assert!(decompress(&corrupt, &cfg).is_err());
    }
}
