use proptest::prelude::*;
use telomere::{compress_multi_pass, decompress, truncated_hash, Config};

fn cfg(bs: usize) -> Config {
    Config { block_size: bs, hash_bits: 13, ..Config::default() }
}

proptest! {
    #![proptest_config(ProptestConfig { cases: 10, .. ProptestConfig::default() })]
    #[test]
    fn launch_roundtrip(data in proptest::collection::vec(any::<u8>(), 32..513),
                        block in 2usize..8,
                        passes in 3usize..6) {
        let (compressed, _) = compress_multi_pass(&data, block, passes).unwrap();
        let decompressed = decompress(&compressed, &cfg(block)).unwrap();
        prop_assert_eq!(decompressed.as_slice(), data.as_slice());
        prop_assert!(compressed.len() <= data.len() + 8);
        let hash = truncated_hash(&decompressed);
        prop_assert_eq!(hash, truncated_hash(&data));
    }
}
