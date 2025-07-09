use inchworm::{
    GlossEntry,
    GlossTable,
    Header,
    Region,
    decompress_region_with_limit,
    decompress_with_limit,
    BLOCK_SIZE,
    encode_header,
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
fn passthrough_literals() {
    let literals: Vec<u8> = (0u8..(BLOCK_SIZE as u8 * 2)).collect();
    let mut data = encode_header(0, 39); // passthrough 2 blocks
    data.extend_from_slice(&literals);
    let table = GlossTable::default();
    let out = decompress_with_limit(&data, &table, 100).unwrap();
    assert_eq!(out, literals);
}
