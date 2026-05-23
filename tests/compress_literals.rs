//! Tests for literal encoding and file structure.
use telomere::{compress_multi_pass_with_config, decode_tlmr_header, decompress_with_limit, Config};

fn fast_cfg(block_size: usize) -> Config {
    Config {
        block_size,
        max_seed_len: 1,
        hash_bits: 13,
        ..Config::default()
    }
}

#[test]
fn compress_writes_valid_header() {
    let block_size = 3usize;
    let data: Vec<u8> = (0u8..50).collect();
    let cfg = fast_cfg(block_size);
    let (out, _) = compress_multi_pass_with_config(&data, &cfg, 1, false).unwrap();

    // File header must be parseable and match config.
    let file_hdr = decode_tlmr_header(&out).unwrap();
    assert_eq!(file_hdr.block_size, block_size);
    let expected_last = if data.len() % block_size == 0 {
        block_size
    } else {
        data.len() % block_size
    };
    assert_eq!(file_hdr.last_block_size, expected_last);

    // Roundtrip must hold.
    let decompressed = decompress_with_limit(&out, &cfg, usize::MAX).unwrap();
    assert_eq!(decompressed, data);
}

#[test]
fn compress_empty_input_is_header_only() {
    let block_size = 4usize;
    let cfg = fast_cfg(block_size);
    let (out, _) = compress_multi_pass_with_config(&[], &cfg, 1, false).unwrap();
    // Empty input → only the 3-byte TlmrHeader.
    assert_eq!(out.len(), 3, "empty input should produce only file header");
    let decompressed = decompress_with_limit(&out, &cfg, usize::MAX).unwrap_or_default();
    assert!(decompressed.is_empty());
}

#[test]
fn all_same_byte_roundtrip() {
    // All-zeros: high probability of 1-byte seed match for the first block.
    let block_size = 1usize;
    let data = vec![0u8; 16];
    let cfg = fast_cfg(block_size);
    let (out, _) = compress_multi_pass_with_config(&data, &cfg, 1, false).unwrap();
    let decompressed = decompress_with_limit(&out, &cfg, usize::MAX).unwrap();
    assert_eq!(decompressed, data);
}
