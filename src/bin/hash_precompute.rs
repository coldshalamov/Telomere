//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
use bytemuck::{Pod, Zeroable};
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

unsafe impl Zeroable for HashEntry {}
unsafe impl Pod for HashEntry {}

fn main() {
    if let Err(e) = run() {
        eprintln!("Error: {e}");
        std::process::exit(1);
    }
}

fn run() -> Result<(), Box<dyn std::error::Error>> {
    let mut entries = Vec::<HashEntry>::new();

    // Pre-allocate space for all entries. When including 3-byte seeds this
    // amounts to roughly 135 MB of memory for 16,843,008 entries.
    let generate_three_byte = true; // placeholder
    let total: usize = (1u64 << 8 | 1u64 << 16) as usize
        + if generate_three_byte {
            (1u64 << 24) as usize
        } else {
            0
        };
    entries
        .try_reserve_exact(total)
        .map_err(|e| simple_cli_error(&format!("unable to reserve memory: {e}")))?;

    // Generate all 1- and 2-byte seeds
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

    if generate_three_byte {
        // Generating 3-byte seeds significantly increases memory usage.
        let len = 3u8;
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
    // The resulting file is around 135 MB when 3-byte seeds are generated.
    let file = File::create(path).map_err(|e| io_cli_error("creating output file", path, e))?;
    let mut writer = BufWriter::new(file);

    // Write all entries at once using bytemuck for speed.
    let bytes: &[u8] = bytemuck::cast_slice(&entries);
    writer
        .write_all(bytes)
        .map_err(|e| io_cli_error("writing output file", path, e))?;
    writer
        .flush()
        .map_err(|e| io_cli_error("flushing output file", path, e))?;

    println!("Done writing seed hash table ({} entries).", entries.len());

    Ok(())
}
