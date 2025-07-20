use rand::Rng;
use telomere::{compress, decompress_with_limit, Config};

fn cfg(bs: usize) -> Config {
    Config { block_size: bs, hash_bits: 13, ..Config::default() }
}

#[test]
fn truncated_header_fails() {
    let block = 4usize;
    let data: Vec<u8> = (0u8..20).collect();
    let mut compressed = compress(&data, block).unwrap();
    compressed.truncate(compressed.len() - 1);
    assert!(decompress_with_limit(&compressed, &cfg(block), usize::MAX).is_err());
}

#[test]
fn orphan_bytes_fail() {
    let block = 3usize;
    let data: Vec<u8> = (0u8..10).collect();
    let mut compressed = compress(&data, block).unwrap();
    compressed.extend_from_slice(&[0xAA, 0xBB]);
    assert!(decompress_with_limit(&compressed, &cfg(block), usize::MAX).is_err());
}

#[test]
fn single_bit_flip_fuzz() {
    let block = 4usize;
    let data: Vec<u8> = (0u8..32).collect();
    let compressed = compress(&data, block).unwrap();
    let total_bits = compressed.len() * 8;
    let mut rng = rand::thread_rng();
    let mut failures = 0u32;
    let trials = 100u32;
    for _ in 0..trials {
        let mut buf = compressed.clone();
        let bit = rng.gen_range(0..total_bits);
        let byte_idx = bit / 8;
        let mask = 1u8 << (7 - (bit % 8));
        buf[byte_idx] ^= mask;
        if decompress_with_limit(&buf, &cfg(block), usize::MAX).is_err() {
            failures += 1;
        }
    }
    assert!(failures as f64 / trials as f64 >= 0.9);
}
