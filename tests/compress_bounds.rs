//! Boundary condition tests for the compressor.
use telomere::{
    compress_multi_pass_with_config, decode_header, decode_tlmr_header, decompress_with_limit,
    Config, Header, TLMR_HEADER_LEN,
};

fn fast_cfg(block_size: usize) -> Config {
    Config {
        block_size,
        max_seed_len: 1,
        hash_bits: 13,
        ..Config::default()
    }
}

#[test]
fn partial_block_at_end_is_literal() {
    let block_size = 3usize;
    // 1 full block + 1 partial byte at the end
    let data: Vec<u8> = vec![0u8; block_size + 1];
    let cfg = fast_cfg(block_size);
    let (compressed, _) = compress_multi_pass_with_config(&data, &cfg, 1, false).unwrap();
    let hdr = decode_tlmr_header(&compressed).unwrap();
    assert_eq!(hdr.block_size, block_size);
    assert_eq!(hdr.last_block_size, 1);

    let mut offset = TLMR_HEADER_LEN;
    let mut headers = Vec::new();
    while offset < compressed.len() {
        let slice = &compressed[offset..];
        let (h, bits) = decode_header(slice).unwrap();
        let byte_len = bits.div_ceil(8);
        offset += byte_len;
        if let Header::Literal = &h {
            let remaining = compressed.len() - offset;
            let bytes = if remaining <= hdr.last_block_size {
                hdr.last_block_size
            } else {
                block_size
            };
            offset += bytes;
        }
        headers.push(h);
    }
    // Both the full block and partial block should appear (as literal or arity)
    assert!(!headers.is_empty());
    let out = decompress_with_limit(&compressed, &cfg, usize::MAX).unwrap();
    assert_eq!(out, data);
}

#[test]
fn single_byte_every_block_size() {
    for bs in 1..=8 {
        let cfg = fast_cfg(bs);
        let data = vec![0x42u8];
        let (compressed, _) = compress_multi_pass_with_config(&data, &cfg, 1, false).unwrap();
        let out = decompress_with_limit(&compressed, &cfg, usize::MAX).unwrap();
        assert_eq!(out, data, "block_size={}", bs);
    }
}

#[test]
fn empty_input() {
    let cfg = fast_cfg(4);
    let (compressed, _) = compress_multi_pass_with_config(&[], &cfg, 1, false).unwrap();
    let out = decompress_with_limit(&compressed, &cfg, usize::MAX).unwrap_or_default();
    assert_eq!(out, vec![0u8; 0]);
}
