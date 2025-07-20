//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
use rand::Rng;
use telomere::{compress, decompress_with_limit};

#[test]
fn random_roundtrip() {
    let mut rng = rand::thread_rng();
    for _ in 0..10 {
        let len = rng.gen_range(1..200);
        let block = rng.gen_range(2..8);
        let data: Vec<u8> = (0..len).map(|_| rng.gen()).collect();
        let out = compress(&data, block).unwrap();
        let decompressed = decompress_with_limit(&out, usize::MAX).unwrap();
        assert_eq!(data, decompressed);
    }
}

#[test]
fn adversarial_roundtrip() {
    // First bytes of SHA-256 of seed 0x00
    let pattern: [u8; 8] = [0x6e, 0x34, 0x0b, 0x9c, 0xff, 0xb3, 0x7a, 0x98];
    let mut data = pattern.to_vec();
    data.extend_from_slice(&[1, 2, 3, 4]);
    let out = compress(&data, 4).unwrap();
    assert!(decompress_with_limit(&out, usize::MAX).is_err());
}
