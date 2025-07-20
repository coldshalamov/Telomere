use proptest::prelude::*;
use telomere::{compress, decompress, Config};

fn cfg(bs: usize) -> Config {
    Config { block_size: bs, hash_bits: 13, ..Config::default() }
}

proptest! {
    #[test]
    fn roundtrip_random(data in any::<Vec<u8>>()) {
        // Use block_size 3 (or change if a different default is needed)
        let compressed = compress(&data, 3).unwrap();
        let output = decompress(&compressed, &cfg(3)).unwrap();
        prop_assert_eq!(output, data);
    }
}
