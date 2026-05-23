//! Tests that verify seed decompression is consistent with compression.
//! Uses Blake3Expander (same as default Config) to generate test data.
use telomere::hasher::{Blake3Expander, SeedExpander};
use telomere::{compress_multi_pass_with_config, decompress_with_limit, index_to_seed, Config};

fn fast_cfg(block_size: usize) -> Config {
    Config {
        block_size,
        max_seed_len: 1,
        hash_bits: 13,
        ..Config::default()
    }
}

fn expand(seed: &[u8], len: usize) -> Vec<u8> {
    let mut out = vec![0u8; len];
    Blake3Expander.expand_into(seed, &mut out);
    out
}

#[test]
fn seed_indices_roundtrip() {
    // For each of the first 10 1-byte seeds, generate a 1-byte block from BLAKE3
    // and verify that compress → decompress is an identity.
    let block = 1usize;
    let cfg = fast_cfg(block);
    for idx in 0..10usize {
        let seed = index_to_seed(idx, cfg.max_seed_len).unwrap();
        let data = expand(&seed, block);
        let (compressed, _) = compress_multi_pass_with_config(&data, &cfg, 1, false).unwrap();
        let out = decompress_with_limit(&compressed, &cfg, usize::MAX).unwrap();
        assert_eq!(out, data, "idx={}", idx);
    }
}

#[test]
fn expand_then_compress_roundtrip() {
    // Generate 8 bytes using BLAKE3([0x05]) and verify roundtrip.
    let block = 2usize;
    let cfg = fast_cfg(block);
    let data = expand(&[0x05], 8);
    let (compressed, _) = compress_multi_pass_with_config(&data, &cfg, 1, false).unwrap();
    let out = decompress_with_limit(&compressed, &cfg, usize::MAX).unwrap();
    assert_eq!(out, data);
}
