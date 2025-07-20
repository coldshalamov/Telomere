use proptest::prelude::*;
use telomere::{compress_with_config, Config};

proptest! {
    #[test]
    fn seed_length_scaling(data in proptest::collection::vec(any::<u8>(), 1..64)) {
        let mut cfg3 = Config::default();
        cfg3.block_size = 3;
        cfg3.max_seed_len = 3;

        let mut cfg4 = cfg3.clone();
        cfg4.max_seed_len = 4;

        let mut cfg5 = cfg3.clone();
        cfg5.max_seed_len = 5;

        let out3 = compress_with_config(&data, &cfg3).unwrap();
        let out4 = compress_with_config(&data, &cfg4).unwrap();
        let out5 = compress_with_config(&data, &cfg5).unwrap();

        prop_assert!(out4.len() <= out3.len());
        prop_assert!(out5.len() <= out4.len());
        if out4.len() == out3.len() {
            prop_assert_eq!(out4, out3);
        }
    }
}
