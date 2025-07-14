use inchworm::{
    decompress_with_limit,
    encode_header,
};

#[test]
fn passthrough_decompresses() {
    let block_size = 3;
    let header = encode_header(0, 37); // passthrough 1 block
    let literal = vec![0x11; 1 * block_size];
    let mut data = header.clone();
    data.extend_from_slice(&literal);
    let out = decompress_with_limit(&data, block_size, literal.len()).unwrap();
    assert_eq!(out, literal);
}

#[test]
fn passthrough_respects_limit() {
    let block_size = 3;
    let header = encode_header(0, 38); // passthrough 2 blocks
    let literal = vec![0x22; 2 * block_size];
    let mut data = header.clone();
    data.extend_from_slice(&literal);
    assert!(decompress_with_limit(&data, block_size, literal.len() - 1).is_none());
}

#[test]
fn passthrough_prefix_safe() {
    let block_size = 3;
    let header = encode_header(0, 39); // passthrough 3 blocks
    let literal = vec![0x33; 3 * block_size - 1]; // intentionally 1 byte short
    let mut data = header.clone();
    data.extend_from_slice(&literal);
    assert!(decompress_with_limit(&data, block_size, usize::MAX).is_none());
}

#[test]
fn passthrough_literals_basic() {
    let block_size = 3;
    let literals: Vec<u8> = (0u8..(block_size as u8 * 2)).collect();
    let mut data = encode_header(0, 38); // passthrough 2 blocks
    data.extend_from_slice(&literals);
    let out = decompress_with_limit(&data, block_size, 100).unwrap();
    assert_eq!(out, literals);
}

#[test]
fn passthrough_final_tail() {
    let block_size = 3;
    let literals: Vec<u8> = (0u8..5).collect();
    let mut data = encode_header(0, 40); // final tail
    data.extend_from_slice(&literals);
    let out = decompress_with_limit(&data, block_size, 100).unwrap();
    assert_eq!(out, literals);
}
