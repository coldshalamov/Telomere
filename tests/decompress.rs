//! Decompressor tests — literal streams, error conditions, roundtrips.
//! All manually-crafted streams use Blake3Expander for output_hash so the
//! decompressor's hash verification matches.
use telomere::{
    compress_multi_pass_with_config, decompress, decompress_with_limit,
    encode_header, encode_tlmr_header, truncated_hash, Config, Header, TlmrHeader,
};
use telomere::hasher::Blake3Expander;

fn fast_cfg(block_size: usize) -> Config {
    Config { block_size, max_seed_len: 1, hash_bits: 13, ..Config::default() }
}

fn expander() -> Blake3Expander { Blake3Expander }

#[test]
fn basic_roundtrip() {
    let block_size = 4;
    let data: Vec<u8> = (0u8..20).collect();
    let cfg = fast_cfg(block_size);
    let (buf, _) = compress_multi_pass_with_config(&data, &cfg, 1, false).unwrap();
    let out = decompress_with_limit(&buf, &cfg, usize::MAX).unwrap();
    assert_eq!(out, data);
}

#[test]
fn limit_enforced() {
    let cfg = fast_cfg(3);
    let data: Vec<u8> = (0u8..10).collect();
    let (buf, _) = compress_multi_pass_with_config(&data, &cfg, 1, false).unwrap();
    assert!(decompress_with_limit(&buf, &cfg, data.len() - 1).is_err());
}

#[test]
fn passthrough_decompresses() {
    let block_size = 3;
    let literal = vec![0x11; block_size];
    let tlmr = encode_tlmr_header(&TlmrHeader {
        version: 0,
        block_size,
        last_block_size: block_size,
        output_hash: truncated_hash(&literal, &expander()),
    });
    let mut data = tlmr.to_vec();
    data.extend_from_slice(&encode_header(&Header::Literal).unwrap());
    data.extend_from_slice(&literal);
    let cfg = fast_cfg(block_size);
    let out = decompress_with_limit(&data, &cfg, usize::MAX).unwrap();
    assert_eq!(out, literal);
}

#[test]
fn passthrough_respects_limit() {
    let block_size = 3;
    let literal = vec![0x22; block_size];
    let tlmr = encode_tlmr_header(&TlmrHeader {
        version: 0,
        block_size,
        last_block_size: block_size,
        output_hash: truncated_hash(&literal, &expander()),
    });
    let mut data = tlmr.to_vec();
    data.extend_from_slice(&encode_header(&Header::Literal).unwrap());
    data.extend_from_slice(&literal);
    let cfg = fast_cfg(block_size);
    assert!(decompress_with_limit(&data, &cfg, literal.len() - 1).is_err());
}

#[test]
fn passthrough_literals_basic() {
    let block_size = 3;
    let literals: Vec<u8> = (0u8..(block_size as u8 * 2)).collect();
    let tlmr = encode_tlmr_header(&TlmrHeader {
        version: 0,
        block_size,
        last_block_size: block_size,
        output_hash: truncated_hash(&literals, &expander()),
    });
    let mut data = tlmr.to_vec();
    data.extend_from_slice(&encode_header(&Header::Literal).unwrap());
    data.extend_from_slice(&literals[..block_size]);
    data.extend_from_slice(&encode_header(&Header::Literal).unwrap());
    data.extend_from_slice(&literals[block_size..]);
    let cfg = fast_cfg(block_size);
    let out = decompress_with_limit(&data, &cfg, 100).unwrap();
    assert_eq!(out, literals);
}

#[test]
fn invalid_header_bytes_fail() {
    // A stream that's only 2 bytes (too short for TlmrHeader) must fail.
    let cfg = fast_cfg(3);
    assert!(decompress_with_limit(&[0u8; 2], &cfg, usize::MAX).is_err());
}

#[test]
fn mismatched_block_size_fails() {
    // Header says block_size=1 but config expects block_size=3.
    let cfg = fast_cfg(3);
    let err = decompress_with_limit(&[0u8; 3], &cfg, usize::MAX).unwrap_err();
    // Should be a Header error (version/block_size mismatch).
    assert!(matches!(err, telomere::TelomereError::Header(_) | telomere::TelomereError::HeaderCodec(_)));
}

#[test]
fn empty_stream_fails() {
    let cfg = fast_cfg(3);
    assert!(decompress_with_limit(&[], &cfg, usize::MAX).is_err());
}

#[test]
fn empty_roundtrip() {
    let cfg = fast_cfg(4);
    let (buf, _) = compress_multi_pass_with_config(&[], &cfg, 1, false).unwrap();
    let out = decompress(&buf, &cfg).unwrap();
    assert!(out.is_empty());
}
