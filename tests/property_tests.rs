use proptest::prelude::*;
use telomere::{compress, decompress};

proptest! {
    #[test]
    fn roundtrip_random(data in any::<Vec<u8>>()) {
        let compressed = compress(&data, 3);
        let output = decompress(&compressed);
        prop_assert_eq!(output, data);
    }
}
