use telomere::{compress, decompress_with_limit, encode_file_header, encode_header, Header};

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
    assert!(decompress_with_limit(&buf, data.len() - 1).is_none());
}

#[test]
fn passthrough_decompresses() {
    let block_size = 3;
    let header = encode_header(&Header::Literal);
    let literal = vec![0x11; block_size];
    let mut data = encode_file_header(literal.len(), block_size);
    data.extend_from_slice(&header);
    data.extend_from_slice(&literal);
    let out = decompress_with_limit(&data, usize::MAX).unwrap();
    assert_eq!(out, literal);
}

#[test]
fn passthrough_respects_limit() {
    let block_size = 3;
    let header = encode_header(&Header::Literal);
    let literal = vec![0x22; block_size];
    let mut data = encode_file_header(literal.len(), block_size);
    data.extend_from_slice(&header);
    data.extend_from_slice(&literal);
    assert!(decompress_with_limit(&data, literal.len() - 1).is_none());
}

#[test]
fn passthrough_prefix_safe() {
    let block_size = 3;
    let header = encode_header(&Header::Literal);
    let literal = vec![0x33; 3 * block_size - 1];
    let mut data = encode_file_header(literal.len(), block_size);
    data.extend_from_slice(&header);
    data.extend_from_slice(&literal);
    assert!(decompress_with_limit(&data, usize::MAX).is_none());
}

#[test]
fn passthrough_literals_basic() {
    let block_size = 3;
    let literals: Vec<u8> = (0u8..(block_size as u8 * 2)).collect();
    let mut data = encode_file_header(literals.len(), block_size);
    data.extend_from_slice(&encode_header(&Header::Literal));
    data.extend_from_slice(&literals[..block_size]);
    data.extend_from_slice(&encode_header(&Header::LiteralLast));
    data.extend_from_slice(&literals[block_size..]);
    let out = decompress_with_limit(&data, 100).unwrap();
    assert_eq!(out, literals);
}

#[test]
fn passthrough_final_tail() {
    let block_size = 3;
    let literals: Vec<u8> = (0u8..5).collect();
    let mut data = encode_file_header(literals.len(), block_size);
    data.extend_from_slice(&encode_header(&Header::LiteralLast));
    data.extend_from_slice(&literals);
    let out = decompress_with_limit(&data, 100).unwrap();
    assert_eq!(out, literals);
}

#[test]
fn unsupported_header_fails() {
    let block_size = 3;
    // Use a non-literal arity that the decoder does not handle
    let header = encode_header(&Header::Standard { seed_index: 1, arity: 2 });
    let literal = vec![0u8; block_size];
    let mut data = encode_file_header(literal.len(), block_size);
    data.extend_from_slice(&header);
    data.extend_from_slice(&literal);
    assert!(decompress_with_limit(&data, usize::MAX).is_none());
}
