use bincode;
use serde::Serialize;
use sha2::{Digest, Sha256};
use std::fs::File;
use std::io::{BufWriter, Write};
use std::path::Path;
use telomere::io_utils::{io_cli_error, simple_cli_error};

/// 8-byte record stored in the hash table.
///
/// Each entry stores the first three bytes of the seed's SHA-256 digest,
/// the seed length, and the zero-padded seed bytes.
#[repr(C)]
#[derive(Clone, Copy, Debug, Serialize)]
struct HashEntry {
    hash_prefix: [u8; 3],
    seed_len: u8,
    seed: [u8; 4],
}

fn main() {
    if let Err(e) = run() {
        eprintln!("Error: {e}");
        std::process::exit(1);
    }
}

fn run() -> Result<(), Box<dyn std::error::Error>> {
    let mut entries = Vec::<HashEntry>::new();

    // Only 1- and 2-byte seeds as requested
    for len in 1u8..=2 {
        let count: u64 = 1u64 << (len * 8);
        for i in 0..count {
            let mut seed = [0u8; 4];
            for b in 0..len {
                seed[(len - 1 - b) as usize] = ((i >> (8 * b)) & 0xFF) as u8;
            }

            let digest = Sha256::digest(&seed[..len as usize]);
            let mut prefix = [0u8; 3];
            prefix.copy_from_slice(&digest[..3]);

            entries.push(HashEntry {
                hash_prefix: prefix,
                seed_len: len,
                seed,
            });
        }
    }

    // Sort entries by hash prefix ascending
    entries.sort_unstable_by(|a, b| a.hash_prefix.cmp(&b.hash_prefix));

    let path = Path::new("hash_table.bin");
    let file = File::create(path).map_err(|e| io_cli_error("creating output file", path, e))?;
    let mut writer = BufWriter::new(file);

    for entry in entries {
        let serialized = bincode::serialize(&entry)
            .map_err(|e| simple_cli_error(&format!("serialization failed: {e}")))?;
        writer
            .write_all(&serialized)
            .map_err(|e| io_cli_error("writing output file", path, e))?;
    }

    writer.flush().map_err(|e| io_cli_error("flushing output file", path, e))?;

    println!("Done writing 1- and 2-byte seed hash table.");

    Ok(())
}
