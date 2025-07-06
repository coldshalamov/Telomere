use std::path::PathBuf;
use std::fs;

use inchworm::{GlossEntry, GlossTable, Header};

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
