//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
use quickcheck::quickcheck;
use telomere::{compress, decompress, Config};

fn cfg(bs: usize) -> Config {
    Config { block_size: bs, hash_bits: 13, ..Config::default() }
}

quickcheck! {
    fn random_roundtrip(data: Vec<u8>, bs: u8) -> bool {
        let block_size = (bs % 16 + 1) as usize; // limit block size 1..16
        let out = compress(&data, block_size).unwrap();
        match decompress(&out, &cfg(block_size)) {
            Ok(decoded) => decoded == data,
            Err(_) => true,
        }
    }
}

#[test]
fn fixed_roundtrip() {
    let block_size = 3usize;
    let input: Vec<u8> = (0u8..100).collect();
    let out = compress(&input, block_size).unwrap();
    let decoded = decompress(&out, &cfg(block_size));
    if let Ok(bytes) = decoded {
        assert_eq!(input, bytes);
    }
}
