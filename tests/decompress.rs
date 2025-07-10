use inchworm::{
    GlossEntry,
    GlossTable,
    Header,
    Region,
    decompress_region_with_limit,
    decompress_with_limit,
    encode_header,
    BLOCK_SIZE,
};

#[test]
fn region_decompresses_from_gloss() {
    let entry = GlossEntry {
        seed: vec![0xAA],
        decompressed: b"hello!!!".to_vec(),
        score: 0.0,
        pass: 0,
    };
    let table = GlossTable { entries: vec![entry.clone()] };
    let region = Region::Compressed(vec![0xAA], Header { seed_index: 0, arity: 1 });
    let out = decompress_region_with_limit(&region, &table, 32).unwrap();
    assert_eq!(out, entry.decompressed);
}

#[test]
fn region_decompress_limit_exceeded() {
    let entry = GlossEntry {
        seed: vec![0xBB],
        decompressed: vec![1,2,3,4,5],
        score: 0.0,
        pass: 0,
    };
    let table = GlossTable { entries: vec![entry] };
    let region = Region::Compressed(vec![0xBB], Header { seed_index: 0, arity: 1 });
    assert!(decompress_region_with_limit(&region, &table, 4).is_none());
}

#[test]
fn passthrough_decompresses() {
    let table = GlossTable { entries: Vec::new() };
    let header = encode_header(0, 37); // passthrough 1 block
    let literal = vec![0x11; 1 * BLOCK_SIZE];
    let mut data = header.clone();
    data.extend_from_slice(&literal);
    let out = decompress_with_limit(&data, &table, literal.len()).unwrap();
    assert_eq!(out, literal);
}

#[test]
fn passthrough_respects_limit() {
    let table = GlossTable { entries: Vec::new() };
    let header = encode_header(0, 38); // passthrough 2 blocks
    let literal = vec![0x22; 2 * BLOCK_SIZE];
    let mut data = header.clone();
    data.extend_from_slice(&literal);
    assert!(decompress_with_limit(&data, &table, literal.len() - 1).is_none());
}

#[test]
fn passthrough_prefix_safe() {
    let table = GlossTable { entries: Vec::new() };
    let header = encode_header(0, 39); // passthrough 3 blocks
    let literal = vec![0x33; 3 * BLOCK_SIZE - 1]; // intentionally 1 byte short
    let mut data = header.clone();
    data.extend_from_slice(&literal);
    assert!(decompress_with_limit(&data, &table, usize::MAX).is_none());
}

#[test]
fn passthrough_literals_basic() {
    let literals: Vec<u8> = (0u8..(BLOCK_SIZE as u8 * 2)).collect();
    let mut data = encode_header(0, 38); // passthrough 2 blocks
    data.extend_from_slice(&literals);
    let table = GlossTable::default();
    let out = decompress_with_limit(&data, &table, 100).unwrap();
    assert_eq!(out, literals);
}

#[test]
fn passthrough_final_tail() {
    let literals: Vec<u8> = (0u8..5).collect();
    let mut data = encode_header(0, 40); // final tail
    data.extend_from_slice(&literals);
    let table = GlossTable::default();
    let out = decompress_with_limit(&data, &table, 100).unwrap();
    assert_eq!(out, literals);
}
