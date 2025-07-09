use inchworm::{GlossEntry, GlossTable, Header, Region, decompress_region_with_limit};

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
