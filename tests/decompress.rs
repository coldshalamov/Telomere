use inchworm::{compress, decompress_with_limit, encode_header, encode_tlmr_header, TlmrHeader, truncated_hash};

#[test]
fn basic_roundtrip() {
    let block_size = 4;
    let data: Vec<u8> = (0u8..20).collect();
    let buf = compress(&data, block_size);
    let out = decompress_with_limit(&buf, usize::MAX).unwrap();
    assert_eq!(out, data);
}

#[test]
fn limit_enforced() {
    let block_size = 3;
    let data: Vec<u8> = (0u8..10).collect();
    let buf = compress(&data, block_size);
    assert!(decompress_with_limit(&buf, data.len() - 1).is_err());
}

#[test]
fn passthrough_decompresses() {
    let block_size = 3;
    let header = encode_header(0, 29);
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
    let out = decompress_with_limit(&data, usize::MAX).unwrap();
    assert_eq!(out, literal);
}

#[test]
fn passthrough_respects_limit() {
    let block_size = 3;
    let header = encode_header(0, 30);
    let literal = vec![0x22; 2 * block_size];
    let tlmr = encode_tlmr_header(&TlmrHeader {
        version: 0,
        block_size,
        last_block_size: block_size,
        output_hash: truncated_hash(&literal),
    });
    let mut data = tlmr.to_vec();
    data.extend_from_slice(&header);
    data.extend_from_slice(&literal);
    assert!(decompress_with_limit(&data, literal.len() - 1).is_err());
}

#[test]
fn passthrough_prefix_safe() {
    let block_size = 3;
    let header = encode_header(0, 31);
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
    assert!(decompress_with_limit(&data, usize::MAX).is_err());
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
    data.extend_from_slice(&encode_header(0, 30));
    data.extend_from_slice(&literals);
    let out = decompress_with_limit(&data, 100).unwrap();
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
    data.extend_from_slice(&encode_header(0, 32));
    data.extend_from_slice(&literals);
    let out = decompress_with_limit(&data, 100).unwrap();
    assert_eq!(out, literals);
}

#[test]
fn unsupported_header_fails() {
    let block_size = 3;
    // Use a non-literal arity that the decoder does not handle
    let header = encode_header(1, 5);
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
    assert!(decompress_with_limit(&data, usize::MAX).is_err());
}
