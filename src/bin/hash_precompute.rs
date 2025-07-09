use inchworm::G;
use sha2::{Digest, Sha256};
use std::fs::File;
use std::io::{BufWriter, Write};

/// Entry written to the binary hash table file.
#[repr(C)]
#[derive(Debug)]
struct HashEntry {
    hash: [u8; 32],
    seed_len: u8,
    seed: [u8; 3],
}

fn main() -> std::io::Result<()> {
    let file = File::create("hash_table.bin")?;
    let mut writer = BufWriter::new(file);

    // Iterate over seed lengths 1, 2, and 3
    for len in 1..=3 {
        let max = 1 << (len * 8);
        println!("Generating {}-byte seeds ({} total)...", len, max);

        for i in 0..max {
            let seed = match len {
                1 => vec![(i & 0xFF) as u8],
                2 => vec![(i >> 8) as u8, (i & 0xFF) as u8],
                3 => vec![(i >> 16) as u8, ((i >> 8) & 0xFF) as u8, (i & 0xFF) as u8],
                _ => unreachable!(),
            };

            // Use G(seed) if defined, fallback to SHA-256
            let out = G(&seed);
            let mut padded_seed = [0u8; 3];
            padded_seed[..len].copy_from_slice(&seed);

            let entry = HashEntry {
                hash: out,
                seed_len: len,
                seed: padded_seed,
            };

            // Write raw bytes to file
            writer.write_all(bytemuck::bytes_of(&entry))?;
        }
    }

    writer.flush()?;
    println!("Hash table written to hash_table.bin");
    Ok(())
}
