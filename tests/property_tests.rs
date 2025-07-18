use proptest::prelude::*;
use telomere::{compress, decompress};

proptest! {
    #[test]
    fn roundtrip_random(data in any::<Vec<u8>>()) {
        let config = Config::default();
        let compressed = compress(&data, &config).unwrap();
        let output = decompress(&compressed, &config).unwrap();
        prop_assert_eq!(output, data);
    }
}
