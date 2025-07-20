//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
use telomere::{compress, decompress_with_limit, Config};

fn cfg() -> Config {
    Config { block_size: 3, hash_bits: 13, ..Config::default() }
}

#[test]
fn test_invalid_truncated_file_fails() {
    // Truncating a valid compressed file should trigger a decode error
    let data: Vec<u8> = (0u8..20).collect();
    let mut input = compress(&data, 3).unwrap();
    input.truncate(4); // simulate a truncated stream
    assert!(decompress_with_limit(&input, &cfg(), 100).is_err());
}

#[test]
fn test_wrong_hash_fails_decompression() {
    // Corrupting any byte should lead to a hash mismatch during decompression
    let data: Vec<u8> = (0u8..10).collect();
    let mut input = compress(&data, 3).unwrap();
    input[2] ^= 0xFF; // flip a byte in the stream
    assert!(decompress_with_limit(&input, &cfg(), 100).is_err());
}
