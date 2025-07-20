//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
use bytemuck::{Pod, Zeroable};
use sha2::{Digest, Sha256};
use std::cmp::Ordering;
use std::fs;
use std::io::Read;
use std::path::Path;
use telomere::io_utils::{io_cli_error, simple_cli_error};

#[repr(C)]
#[derive(Clone, Copy)]
struct HashEntry {
    hash_prefix: [u8; 3],
    seed_len: u8,
    seed: [u8; 4],
}

unsafe impl Zeroable for HashEntry {}
unsafe impl Pod for HashEntry {}

fn main() {
    if let Err(e) = run() {
        eprintln!("{e}");
        std::process::exit(1);
    }
}

fn run() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 2 {
        return Err(simple_cli_error(&format!("Usage: {} <input_file|hex|->", args[0])).into());
    }

    let input_bytes = if args[1] == "-" {
        let mut buf = String::new();
        std::io::stdin().read_to_string(&mut buf)?;
        hex::decode(buf.trim()).map_err(|_| simple_cli_error("invalid hex input"))?
    } else {
        let path = Path::new(&args[1]);
        if path.exists() {
            fs::read(path).map_err(|e| io_cli_error("reading input file", path, e))?
        } else {
            hex::decode(args[1].trim()).map_err(|_| simple_cli_error("invalid hex input"))?
        }
    };

    let digest = Sha256::digest(&input_bytes);
    let prefix = [digest[0], digest[1], digest[2]];
    let prefix_hex = format!("{:02x}{:02x}{:02x}", prefix[0], prefix[1], prefix[2]);

    let table_path = Path::new("hash_table.bin");
    let bytes =
        fs::read(table_path).map_err(|e| io_cli_error("reading hash table", table_path, e))?;
    if bytes.len() % std::mem::size_of::<HashEntry>() != 0 {
        return Err(simple_cli_error("corrupt hash table file").into());
    }

    let entries: &[HashEntry] = bytemuck::cast_slice(&bytes);

    // binary search for matching prefix
    let mut left = 0usize;
    let mut right = entries.len();
    let mut found = None;
    while left < right {
        let mid = (left + right) / 2;
        match entries[mid].hash_prefix.cmp(&prefix) {
            Ordering::Less => left = mid + 1,
            Ordering::Greater => right = mid,
            Ordering::Equal => {
                found = Some(mid);
                break;
            }
        }
    }

    let mut matches: Vec<&HashEntry> = Vec::new();
    if let Some(idx) = found {
        let mut i = idx;
        while i > 0 && entries[i - 1].hash_prefix == prefix {
            i -= 1;
        }
        while i < entries.len() && entries[i].hash_prefix == prefix {
            matches.push(&entries[i]);
            i += 1;
        }
    }

    matches.sort_by(|a, b| {
        a.seed_len
            .cmp(&b.seed_len)
            .then_with(|| a.seed.cmp(&b.seed))
    });

    for entry in &matches {
        let len = entry.seed_len as usize;
        if len > 4 || len == 0 {
            continue;
        }
        let seed_hex: String = entry.seed[..len]
            .iter()
            .map(|b| format!("{:02x}", b))
            .collect();
        let bit_len = seed_bit_length(&entry.seed[..len]);
        println!("{prefix_hex}  {}  {seed_hex}  {bit_len}", entry.seed_len);
    }

    println!(
        "Total matching seeds for prefix {prefix_hex}: {}",
        matches.len()
    );

    Ok(())
}

fn seed_bit_length(seed: &[u8]) -> u32 {
    for (i, &b) in seed.iter().enumerate() {
        if b != 0 {
            return (seed.len() - i - 1) as u32 * 8 + (8 - b.leading_zeros());
        }
    }
    0
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_seed_bit_length() {
        assert_eq!(seed_bit_length(&[0x00, 0x01]), 1);
        assert_eq!(seed_bit_length(&[0x00, 0x80]), 8);
        assert_eq!(seed_bit_length(&[0x01, 0x00]), 9);
        assert_eq!(seed_bit_length(&[0x7F, 0x00]), 15);
        assert_eq!(seed_bit_length(&[0x80, 0x00]), 16);
    }
}
