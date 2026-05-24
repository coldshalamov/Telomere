//! Validation tests: truncated and corrupted streams must be rejected.
use telomere::{compress_multi_pass_with_config, decompress_with_limit, Config};

fn fast_cfg(block_size: usize) -> Config {
    Config {
        block_size,
        max_seed_len: 1,
        hash_bits: 13,
        ..Config::default()
    }
}

#[test]
fn test_invalid_truncated_file_fails() {
    let data: Vec<u8> = (0u8..20).collect();
    let cfg = fast_cfg(3);
    let (mut input, _) = compress_multi_pass_with_config(&data, &cfg, 1, false).unwrap();
    input.truncate(4); // simulate truncated stream after file header
    assert!(decompress_with_limit(&input, &cfg, 100).is_err());
}

#[test]
fn test_wrong_hash_fails_decompression() {
    // Flip a bit in the output_hash portion of the TlmrHeader.
    let data: Vec<u8> = (0u8..10).collect();
    let cfg = fast_cfg(3);
    let (mut input, _) = compress_multi_pass_with_config(&data, &cfg, 1, false).unwrap();
    input[2] ^= 0x01; // flip LSB in the hash field
    assert!(decompress_with_limit(&input, &cfg, 100).is_err());
}
