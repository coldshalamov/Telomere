use bytemuck::{Pod, Zeroable};
use std::fs;
use std::path::Path;
use telomere::io_utils::{io_cli_error, simple_cli_error};

/*
hash_dump.rs is a CLI utility for examining the contents of hash_table.bin.
Each entry in hash_table.bin is a struct with:
  - hash_prefix: [u8; 3]  // first 3 bytes of SHA-256(seed)
  - seed_len: u8          // number of seed bytes (1, 2, or 3)
  - seed: [u8; 4]         // big-endian, padded to 4 bytes

We want to:
- Print out all entries with seed bit-length in [min_bits, max_bits] (inclusive)
- Defaults: min_bits = 1, max_bits = 256
- Each line: prefix (hex), seed length, seed (hex), bit-length
- Skip any entry where seed_len == 0 (should not occur, but robust)
- Print a summary line at the end: "Total matching seeds: N"
- Use seed_bit_length() to compute the number of bits in a seed (position of most-significant 1 in the seed, big-endian, zero-based +1)
- Take min_bits and max_bits as optional command-line args, positional, in that order
- If only one arg is given, treat as max_bits (min_bits = 1)
- If neither is given, use defaults

seed_bit_length() example:
  - [0x00, 0x01] => 1
  - [0x00, 0x80] => 8
  - [0x01, 0x00] => 9
  - [0x7F, 0x00] => 15
  - [0x80, 0x00] => 16

Assume hash_table.bin is little-endian on disk and matches the struct above.
*/

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
    let (min_bits, max_bits) = match args.len() {
        1 => (1u32, 256u32),
        2 => (
            1u32,
            args[1]
                .parse()
                .map_err(|_| simple_cli_error("invalid max_bits"))?,
        ),
        3 => (
            args[1]
                .parse()
                .map_err(|_| simple_cli_error("invalid min_bits"))?,
            args[2]
                .parse()
                .map_err(|_| simple_cli_error("invalid max_bits"))?,
        ),
        _ => {
            return Err(
                simple_cli_error(&format!("Usage: {} [min_bits] [max_bits]", args[0])).into(),
            );
        }
    };

    let path = Path::new("hash_table.bin");
    let bytes = fs::read(path).map_err(|e| io_cli_error("reading input file", path, e))?;

    if bytes.len() % std::mem::size_of::<HashEntry>() != 0 {
        return Err(simple_cli_error("corrupt hash table file").into());
    }

    // SAFETY: HashEntry is Pod and the length check above ensures alignment
    let entries: &[HashEntry] = bytemuck::cast_slice(&bytes);

    let mut count = 0u64;
    for entry in entries {
        if entry.seed_len == 0 {
            continue;
        }
        let len = entry.seed_len as usize;
        if len > 4 {
            continue;
        }
        let bit_len = seed_bit_length(&entry.seed[..len]);
        if bit_len >= min_bits && bit_len <= max_bits {
            let prefix_hex = format!(
                "{:02x}{:02x}{:02x}",
                entry.hash_prefix[0], entry.hash_prefix[1], entry.hash_prefix[2]
            );
            let seed_hex: String = entry.seed[..len]
                .iter()
                .map(|b| format!("{:02x}", b))
                .collect();
            println!("{prefix_hex}  {}  {seed_hex}  {bit_len}", entry.seed_len);
            count += 1;
        }
    }

    println!("Total matching seeds: {count}");
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
