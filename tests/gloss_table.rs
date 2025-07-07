use std::path::PathBuf;
use std::fs;

use inchworm::{
    GlossEntry,
    GlossTable,
    Header,
    encode_region,
    Region,
    BLOCK_SIZE,
    decompress_with_limit,
    decompress_region_with_limit,
};

#[test]
fn save_load_roundtrip() {
    // create a simple table with one entry
    let entry = GlossEntry {
        seed: vec![0xAA],
        header: Header { seed_len: 0, nest_len: 0, arity: 0 },
        decompressed: vec![1,2,3,4,5,6,7],
    };
    let table = GlossTable { entries: vec![entry.clone()] };

    let mut path = std::env::temp_dir();
    path.push("gloss_table_test.bin");
    table.save(&path).unwrap();
    let loaded = GlossTable::load(&path).unwrap();
    fs::remove_file(&path).ok();

    assert_eq!(table, loaded);
}

#[test]
fn limit_enforced() {
    let region = Region::Raw(vec![0; BLOCK_SIZE]);
    let encoded = encode_region(&region);
    assert!(decompress_with_limit(&encoded, BLOCK_SIZE, 0).is_some());
    assert!(decompress_with_limit(&encoded, BLOCK_SIZE - 1, 0).is_none());

    let long = Region::Raw(vec![0; 35]);
    assert!(decompress_region_with_limit(&long, 32, 0).is_none());
}
