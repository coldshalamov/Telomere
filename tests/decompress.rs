use inchworm::{
    Header,
    Region,
    decompress_region_with_limit,
    decompress_with_limit,
    encode_header,
    BLOCK_SIZE,
};

#[test]
fn region_decompresses_raw() {
    let region = Region::Raw(b"hello".to_vec());
    let out = decompress_region_with_limit(&region, 10).unwrap();
    assert_eq!(out, b"hello");
}

#[test]
fn region_decompress_limit_exceeded() {
    let region = Region::Raw(vec![1, 2, 3, 4, 5]);
    assert!(decompress_region_with_limit(&region, 4).is_none());
}

#[test]
fn passthrough_decompresses() {
    let header = encode_header(0, 37); // passthrough 1 block
    let literal = vec![0x11; 1 * BLOCK_SIZE];
    let mut data = header.clone();
    data.extend_from_slice(&literal);
    let out = decompress_with_limit(&data, literal.len()).unwrap();
    assert_eq!(out, literal);
}

#[test]
fn passthrough_respects_limit() {
    let header = encode_header(0, 38); // passthrough 2 blocks
    let literal = vec![0x22; 2 * BLOCK_SIZE];
    let mut data = header.clone();
    data.extend_from_slice(&literal);
    assert!(decompress_with_limit(&data, literal.len() - 1).is_none());
}

#[test]
fn passthrough_prefix_safe() {
    let header = encode_header(0, 39); // passthrough 3 blocks
    let literal = vec![0x33; 3 * BLOCK_SIZE - 1]; // intentionally 1 byte short
    let mut data = header.clone();
    data.extend_from_slice(&literal);
    assert!(decompress_with_limit(&data, usize::MAX).is_none());
}

#[test]
fn passthrough_literals_basic() {
    let literals: Vec<u8> = (0u8..(BLOCK_SIZE as u8 * 2)).collect();
    let mut data = encode_header(0, 38); // passthrough 2 blocks
    data.extend_from_slice(&literals);
    let out = decompress_with_limit(&data, 100).unwrap();
    assert_eq!(out, literals);
}

#[test]
fn passthrough_final_tail() {
    let literals: Vec<u8> = (0u8..5).collect();
    let mut data = encode_header(0, 40); // final tail
    data.extend_from_slice(&literals);
    let out = decompress_with_limit(&data, 100).unwrap();
    assert_eq!(out, literals);
}
