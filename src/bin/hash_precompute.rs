use serde::Serialize;
use bincode;
use sha2::{Digest, Sha256};
use std::fs::File;
use std::io::{BufWriter, Write};

/// Entry written to the binary hash table file.
#[repr(C)]
#[derive(Debug, Serialize)]
struct HashEntry {
    hash: [u8; 32],
    seed_len: u8,
    seed: [u8; 4],
}

fn main() {
    let file = File::create("hash_table.bin").unwrap();
    let mut writer = BufWriter::new(file);

    // Iterate over seed lengths 1, 2, and 3
    for len in 1..=4 {
        let max = match len {
    1 => 1 << 8,
    2 => 1 << 16,
    3 => 1 << 24,
    4 => 894_784_853, // 30 GB cap
    _ => unreachable!(),
};
        println!("Generating {}-byte seeds ({} total)...", len, max);

        for i in 0..max {
            let seed = match len {
    1 => vec![(i & 0xFF) as u8],
    2 => vec![(i >> 8) as u8, (i & 0xFF) as u8],
    3 => vec![(i >> 16) as u8, ((i >> 8) & 0xFF) as u8, (i & 0xFF) as u8],
    4 => vec![
        (i >> 24) as u8,
        (i >> 16) as u8,
        (i >> 8) as u8,
        (i & 0xFF) as u8,
    ],
    _ => unreachable!(),
};


            // Compute SHA-256 of the seed
            let out: [u8; 32] = Sha256::digest(&seed).into();
            let mut padded_seed = [0u8; 4];
            padded_seed[..len].copy_from_slice(&seed);

            let entry = HashEntry {
                hash: out,
                seed_len: len as u8,
                seed: padded_seed,
            };

            let serialized = bincode::serialize(&entry).unwrap();
            writer.write_all(&serialized).unwrap();
        }
    }

    writer.flush().unwrap();
    println!("Hash table written to hash_table.bin");
}
