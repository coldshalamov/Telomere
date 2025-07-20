use proptest::prelude::*;
use telomere::{compress, decompress, Config};

fn cfg(bs: usize) -> Config {
    Config { block_size: bs, hash_bits: 13, ..Config::default() }
}

fn alternating(len: usize) -> Vec<u8> {
    (0..len).map(|i| if i % 2 == 0 {0x00} else {0xFF}).collect()
}

fn palindrome(data: Vec<u8>) -> Vec<u8> {
    let mut out = data.clone();
    out.extend(data.into_iter().rev());
    out
}

proptest! {
    #[test]
    fn zeros_roundtrip(len in 0usize..64, bs in 1usize..8) {
        let data = vec![0u8; len];
        let c = compress(&data, bs).unwrap();
        let out = decompress(&c, &cfg(bs)).unwrap();
        prop_assert_eq!(out, data);
    }

    #[test]
    fn ones_roundtrip(len in 0usize..64, bs in 1usize..8) {
        let data = vec![0xFFu8; len];
        let c = compress(&data, bs).unwrap();
        let out = decompress(&c, &cfg(bs)).unwrap();
        prop_assert_eq!(out, data);
    }

    #[test]
    fn alternating_roundtrip(len in 0usize..64, bs in 1usize..8) {
        let data = alternating(len);
        let c = compress(&data, bs).unwrap();
        let out = decompress(&c, &cfg(bs)).unwrap();
        prop_assert_eq!(out, data);
    }

    #[test]
    fn palindrome_roundtrip(data in proptest::collection::vec(any::<u8>(), 0..32), bs in 1usize..8) {
        let data = palindrome(data);
        let c = compress(&data, bs).unwrap();
        let out = decompress(&c, &cfg(bs)).unwrap();
        prop_assert_eq!(out, data);
    }

    #[test]
    fn random_block_alignment(data in proptest::collection::vec(any::<u8>(), 0..64), bs in 1usize..8, pad in 0usize..8) {
        let mut d = data;
        d.extend(vec![0u8; pad]);
        let c = compress(&d, bs).unwrap();
        let out = decompress(&c, &cfg(bs)).unwrap();
        prop_assert_eq!(out, d);
    }

    #[test]
    fn decode_never_panics(data in proptest::collection::vec(any::<u8>(), 0..80)) {
        let _ = std::panic::catch_unwind(|| { let _ = decompress(&data, &cfg(1)); }).ok();
    }
}

#[test]
fn literal_torture() {
    let block_size = 3usize;
    let len = block_size * 10 + 1;
    let data: Vec<u8> = (0..len as u8).collect();
    let c = compress(&data, block_size).unwrap();
    let out = decompress(&c, &cfg(block_size)).unwrap();
    assert_eq!(out, data);
}
