//! Property-based roundtrip tests (proptest). Fast path: max_seed_len=1.
use proptest::prelude::*;
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
    #[test]
    fn roundtrip_random(data in proptest::collection::vec(any::<u8>(), 0..64), bs in 1usize..8) {
        let cfg = fast_cfg(bs);
        let (compressed, _) = compress_multi_pass_with_config(&data, &cfg, 1, false).unwrap();
        let output = decompress(&compressed, &cfg).unwrap();
        prop_assert_eq!(output, data);
    }
}
