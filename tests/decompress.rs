//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
use telomere::{
    compress, decompress_with_limit, encode_header, encode_tlmr_header, truncated_hash, Header,
    TlmrHeader, Config,
};

fn cfg(block: usize) -> Config {
    Config { block_size: block, hash_bits: 13, ..Config::default() }
}

#[test]
fn basic_roundtrip() {
    let block_size = 4;
    let data: Vec<u8> = (0u8..20).collect();
    let buf = compress(&data, block_size).unwrap();
    let out = decompress_with_limit(&buf, &cfg(block_size), usize::MAX).unwrap();
    assert_eq!(out, data);
}

#[test]
fn limit_enforced() {
    let block_size = 3;
    let data: Vec<u8> = (0u8..10).collect();
    let buf = compress(&data, block_size).unwrap();
    assert!(decompress_with_limit(&buf, &cfg(block_size), data.len() - 1).is_err());
}

#[test]
fn passthrough_decompresses() {
    let block_size = 3;
    let header = encode_header(&Header::Literal).unwrap();
    let literal = vec![0x11; block_size];
    let tlmr = encode_tlmr_header(&TlmrHeader {
        version: 0,
        block_size,
        last_block_size: block_size,
        output_hash: truncated_hash(&literal),
    });
    let mut data = tlmr.to_vec();
    data.extend_from_slice(&header);
    data.extend_from_slice(&literal);
    let out = decompress_with_limit(&data, &cfg(block_size), usize::MAX).unwrap();
    assert_eq!(out, literal);
}

#[test]
fn passthrough_respects_limit() {
    let block_size = 3;
    let header = encode_header(&Header::Literal).unwrap();
    let literal = vec![0x22; block_size];
    let tlmr = encode_tlmr_header(&TlmrHeader {
        version: 0,
        block_size,
        last_block_size: block_size,
        output_hash: truncated_hash(&literal),
    });
    let mut data = tlmr.to_vec();
    data.extend_from_slice(&header);
    data.extend_from_slice(&literal);
    assert!(decompress_with_limit(&data, &cfg(block_size), literal.len() - 1).is_err());
}

#[test]
fn passthrough_prefix_safe() {
    let block_size = 3;
    let header = encode_header(&Header::Literal).unwrap();
    let literal = vec![0x33; 3 * block_size - 1];
    let tlmr = encode_tlmr_header(&TlmrHeader {
        version: 0,
        block_size,
        last_block_size: (literal.len() % block_size).max(1),
        output_hash: truncated_hash(&literal),
    });
    let mut data = tlmr.to_vec();
    data.extend_from_slice(&header);
    data.extend_from_slice(&literal);
    assert!(decompress_with_limit(&data, &cfg(block_size), usize::MAX).is_err());
}

#[test]
fn passthrough_literals_basic() {
    let block_size = 3;
    let literals: Vec<u8> = (0u8..(block_size as u8 * 2)).collect();
    let tlmr = encode_tlmr_header(&TlmrHeader {
        version: 0,
        block_size,
        last_block_size: block_size,
        output_hash: truncated_hash(&literals),
    });
    let mut data = tlmr.to_vec();
    data.extend_from_slice(&encode_header(&Header::Literal).unwrap());
    data.extend_from_slice(&literals[..block_size]);
    data.extend_from_slice(&encode_header(&Header::Literal).unwrap());
    data.extend_from_slice(&literals[block_size..]);
    let out = decompress_with_limit(&data, &cfg(block_size), 100).unwrap();
    assert_eq!(out, literals);
}

#[test]
fn passthrough_final_tail() {
    let block_size = 3;
    let literals: Vec<u8> = (0u8..5).collect();
    let tlmr = encode_tlmr_header(&TlmrHeader {
        version: 0,
        block_size,
        last_block_size: literals.len(),
        output_hash: truncated_hash(&literals),
    });
    let mut data = tlmr.to_vec();
    data.extend_from_slice(&encode_header(&Header::Literal).unwrap());
    data.extend_from_slice(&literals);
    let out = decompress_with_limit(&data, &cfg(block_size), 100).unwrap();
    assert_eq!(out, literals);
}

#[test]
fn unsupported_header_fails() {
    let block_size = 3;
    // Use a non-literal header which should fail
    let header = encode_header(&Header::Arity(3)).unwrap();
    let literal = vec![0u8; block_size];
    let tlmr = encode_tlmr_header(&TlmrHeader {
        version: 0,
        block_size,
        last_block_size: block_size,
        output_hash: truncated_hash(&literal),
    });
    let mut data = tlmr.to_vec();
    data.extend_from_slice(&header);
    data.extend_from_slice(&literal);
    assert!(decompress_with_limit(&data, &cfg(block_size), usize::MAX).is_err());
}

#[test]
fn empty_stream_fails() {
    assert!(decompress_with_limit(&[], &cfg(3), usize::MAX).is_err());
}

#[test]
fn bad_header_error_variant() {
    let err = decompress_with_limit(&[0u8; 3], &cfg(3), 10).unwrap_err();
    match err {
        telomere::TelomereError::Decode(_) => {}
        _ => panic!("wrong error type"),
    }
}

#[test]
fn empty_roundtrip() {
    let block_size = 4usize;
    let data: Vec<u8> = Vec::new();
    let buf = compress(&data, block_size).unwrap();
    let out = telomere::decompress(&buf, &cfg(block_size)).unwrap();
    assert!(out.is_empty());
}
