use sha2::{Digest, Sha256};
use std::fs::File;
use std::io::{BufWriter, Write};
use std::path::Path;

// Each entry: [3 bytes hash prefix][1 byte seed length][4 bytes seed (padded to 4 bytes)]
#[derive(Clone)]
struct Entry {
    prefix: [u8; 3],
    len: u8,
    seed: [u8; 4],
}

fn main() {
    let mut entries = Vec::new();

    // 1-byte seeds
    for i in 0u8..=255 {
        let seed = [i];
        let digest = Sha256::digest(&seed);
        let prefix = [digest[0], digest[1], digest[2]];
        let mut padded = [0u8; 4];
        padded[0] = i;
        entries.push(Entry {
            prefix,
            len: 1,
            seed: padded,
        });
    }

    // 2-byte seeds
    for hi in 0u8..=255 {
        for lo in 0u8..=255 {
            let seed = [hi, lo];
            let digest = Sha256::digest(&seed);
            let prefix = [digest[0], digest[1], digest[2]];
            let mut padded = [0u8; 4];
            padded[0] = hi;
            padded[1] = lo;
            entries.push(Entry {
                prefix,
                len: 2,
                seed: padded,
            });
        }
    }

    // Sort by prefix
    entries.sort_by(|a, b| a.prefix.cmp(&b.prefix));

    // Write to file
    let path = Path::new("hash_table.bin");
    let file = File::create(path).unwrap();
    let mut writer = BufWriter::new(file);
    for entry in &entries {
        writer.write_all(&entry.prefix).unwrap();
        writer.write_all(&[entry.len]).unwrap();
        writer.write_all(&entry.seed).unwrap();
    }
    println!("Done writing 1- and 2-byte seed hash table.");
}
