//! Verify that compression is deterministic: same input + config → identical output.
use telomere::{compress_multi_pass_with_config, decode_tlmr_header, Config};

fn fast_cfg(block_size: usize) -> Config {
    Config {
        block_size,
        max_seed_len: 1,
        hash_bits: 13,
        ..Config::default()
    }
}

#[test]
fn test_compression_deterministic() {
    let input: Vec<u8> = (0u8..50).collect();
    let cfg = fast_cfg(3);
    let (out1, _) = compress_multi_pass_with_config(&input, &cfg, 1, false).unwrap();
    let (out2, _) = compress_multi_pass_with_config(&input, &cfg, 1, false).unwrap();
    assert_eq!(
        out1, out2,
        "identical inputs must produce identical compressed output"
    );
}

#[test]
fn test_compression_does_not_modify_input() {
    let original: Vec<u8> = (0u8..30).collect();
    let input_copy = original.clone();
    let cfg = fast_cfg(4);
    let _ = compress_multi_pass_with_config(&input_copy, &cfg, 1, false).unwrap();
    assert_eq!(original, input_copy);
}

#[test]
fn test_different_configs_different_output() {
    let input: Vec<u8> = vec![0u8; 12];
    let cfg3 = fast_cfg(3);
    let cfg4 = fast_cfg(4);
    let (out3, _) = compress_multi_pass_with_config(&input, &cfg3, 1, false).unwrap();
    let (out4, _) = compress_multi_pass_with_config(&input, &cfg4, 1, false).unwrap();
    let hdr3 = decode_tlmr_header(&out3).unwrap();
    let hdr4 = decode_tlmr_header(&out4).unwrap();
    assert_ne!(
        hdr3.block_size, hdr4.block_size,
        "different block sizes produce different file headers"
    );
}
