//! Property-based launch tests: roundtrip across many input sizes and configs.
//! Uses max_seed_len=1 for speed. Focuses on roundtrip correctness, not compression ratio.
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
    #![proptest_config(ProptestConfig { cases: 32, .. ProptestConfig::default() })]
    #[test]
    fn launch_roundtrip(
        data in proptest::collection::vec(any::<u8>(), 0..64),
        block in 1usize..8,
        passes in 1usize..4,
    ) {
        let cfg = fast_cfg(block);
        let (compressed, _) = compress_multi_pass_with_config(&data, &cfg, passes, false).unwrap();
        let decompressed = decompress(&compressed, &cfg).unwrap();
        prop_assert_eq!(decompressed.as_slice(), data.as_slice());
        // Compressed stream must at least contain the 3-byte TlmrHeader.
        prop_assert!(compressed.len() >= 3);
    }
}
