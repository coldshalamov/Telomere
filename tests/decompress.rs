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
        header: Header { seed_index: 0, arity: 1 },
        decompressed: b"hello!!!".to_vec(),
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
        header: Header { seed_index: 0, arity: 1 },
        decompressed: vec![1,2,3,4,5],
    };
    let table = GlossTable { entries: vec![entry] };
    let region = Region::Compressed(vec![0xBB], Header { seed_index: 0, arity: 1 });
    assert!(decompress_region_with_limit(&region, &table, 4).is_none());
}

#[test]
fn passthrough_decompresses() {
    let table = GlossTable { entries: Vec::new() };
    let header = encode_header(0, 38);
    let literal = vec![0x11; 38 * BLOCK_SIZE];
    let mut data = header.clone();
    data.extend_from_slice(&literal);
    let out = decompress_with_limit(&data, &table, literal.len()).unwrap();
    assert_eq!(out, literal);
}

#[test]
fn passthrough_respects_limit() {
    let table = GlossTable { entries: Vec::new() };
    let header = encode_header(0, 38);
    let literal = vec![0x22; 38 * BLOCK_SIZE];
    let mut data = header.clone();
    data.extend_from_slice(&literal);
    assert!(decompress_with_limit(&data, &table, literal.len() - 1).is_none());
}

#[test]
fn passthrough_prefix_safe() {
    let table = GlossTable { entries: Vec::new() };
    let header = encode_header(0, 38);
    let literal = vec![0x33; 38 * BLOCK_SIZE - 1];
    let mut data = header.clone();
    data.extend_from_slice(&literal);
    assert!(decompress_with_limit(&data, &table, usize::MAX).is_none());
}
