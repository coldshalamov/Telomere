use clap::Parser;
use memmap2::Mmap;
use sha2::{Digest, Sha256};
use std::fs::{self, File};
use std::io::Write;
use std::path::{Path, PathBuf};
use telomere::io_utils::{io_cli_error, simple_cli_error};
use bytemuck::{Pod, Zeroable};
use serde::Serialize;
use std::cmp::Ordering;

#[repr(C)]
#[derive(Clone, Copy)]
struct Entry {
    prefix: [u8; 3],
    len: u8,
    seed: [u8; 4],
}

unsafe impl Zeroable for Entry {}
unsafe impl Pod for Entry {}

#[derive(Parser)]
struct Args {
    /// Input file to analyze
    input: PathBuf,
    /// Block size in bytes
    #[arg(long, default_value_t = 3)]
    block_size: usize,
    /// Minimum seed bit length to count as match
    #[arg(long, default_value_t = 1)]
    min_bits: u32,
    /// Maximum seed bit length to count as match
    #[arg(long, default_value_t = 256)]
    max_bits: u32,
    /// Only print summary totals
    #[arg(long)]
    summary: bool,
    /// Optional CSV output path for per-block results
    #[arg(long)]
    csv: Option<PathBuf>,
    /// Optional JSON output path for per-block results
    #[arg(long)]
    json: Option<PathBuf>,
}

#[derive(Serialize)]
struct Record {
    index: usize,
    category: String,
}

fn main() {
    if let Err(e) = run() {
        eprintln!("{e}");
        std::process::exit(1);
    }
}

fn run() -> Result<(), Box<dyn std::error::Error>> {
    let args = Args::parse();

    if args.min_bits > args.max_bits {
        return Err(simple_cli_error("min_bits greater than max_bits").into());
    }

    let input = fs::read(&args.input)
        .map_err(|e| io_cli_error("reading input file", &args.input, e))?;

    let table_path = Path::new("hash_table.bin");
    let file = File::open(table_path)
        .map_err(|e| io_cli_error("opening hash table", table_path, e))?;
    let mmap = unsafe { Mmap::map(&file).map_err(|e| io_cli_error("mapping hash table", table_path, e))? };

    let mut counts = [0u64; 4]; // 1,2,3,literal
    let mut json_records = Vec::new();
    let mut csv_writer = match &args.csv {
        Some(p) => {
            let f = File::create(p).map_err(|e| io_cli_error("creating csv", p, e))?;
            let mut wtr = csv::Writer::from_writer(f);
            wtr.write_record(&["index", "category"])?;
            Some(wtr)
        }
        None => None,
    };

    for (idx, chunk) in input.chunks(args.block_size).enumerate() {
        let digest = Sha256::digest(chunk);
        let prefix = [digest[0], digest[1], digest[2]];
        let result = lookup_seed(&mmap, prefix, args.min_bits, args.max_bits);
        let category = match result {
            Some(seed) => match seed.len() {
                1 => {
                    counts[0] += 1;
                    "seed-1"
                }
                2 => {
                    counts[1] += 1;
                    "seed-2"
                }
                3 => {
                    counts[2] += 1;
                    "seed-3"
                }
                _ => {
                    counts[3] += 1;
                    "literal"
                }
            },
            None => {
                counts[3] += 1;
                "literal"
            }
        };

        if let Some(wtr) = csv_writer.as_mut() {
            wtr.write_record(&[idx.to_string(), category.to_string()])?;
        }
        if args.json.is_some() {
            json_records.push(Record {
                index: idx,
                category: category.to_string(),
            });
        }
        if !args.summary {
            println!("block {idx}: {category}");
        }
    }

    if let Some(wtr) = csv_writer.as_mut() {
        wtr.flush()?;
    }
    if let Some(path) = &args.json {
        let mut f = File::create(path)
            .map_err(|e| io_cli_error("creating json", path, e))?;
        serde_json::to_writer_pretty(&mut f, &json_records)?;
        f.write_all(b"\n")?;
    }

    let total = counts.iter().sum::<u64>().max(1);
    println!("#blocks: {}", total);
    println!(
        "#1-byte seed: {} ({:.1}%)",
        counts[0],
        100.0 * counts[0] as f64 / total as f64
    );
    println!(
        "#2-byte seed: {} ({:.1}%)",
        counts[1],
        100.0 * counts[1] as f64 / total as f64
    );
    println!(
        "#3-byte seed: {} ({:.1}%)",
        counts[2],
        100.0 * counts[2] as f64 / total as f64
    );
    println!(
        "#literal: {} ({:.1}%)",
        counts[3],
        100.0 * counts[3] as f64 / total as f64
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

fn lookup_seed(
    mmap: &Mmap,
    prefix: [u8; 3],
    min_bits: u32,
    max_bits: u32,
) -> Option<Vec<u8>> {
    let entry_size = std::mem::size_of::<Entry>();
    if mmap.len() % entry_size != 0 {
        return None;
    }
    let entries: &[Entry] = bytemuck::cast_slice(&mmap[..]);

    let mut left = 0usize;
    let mut right = entries.len();
    while left < right {
        let mid = (left + right) / 2;
        match entries[mid].prefix.cmp(&prefix) {
            Ordering::Less => left = mid + 1,
            Ordering::Greater => right = mid,
            Ordering::Equal => {
                let mut idx = mid;
                while idx > 0 && entries[idx - 1].prefix == prefix {
                    idx -= 1;
                }
                let mut best: Option<Vec<u8>> = None;
                while idx < entries.len() && entries[idx].prefix == prefix {
                    let e = entries[idx];
                    let len = e.len as usize;
                    if len == 0 || len > 4 {
                        idx += 1;
                        continue;
                    }
                    let seed = &e.seed[..len];
                    let bits = seed_bit_length(seed);
                    if bits >= min_bits && bits <= max_bits {
                        if let Some(ref b) = best {
                            if len < b.len() {
                                best = Some(seed.to_vec());
                            }
                        } else {
                            best = Some(seed.to_vec());
                        }
                    }
                    idx += 1;
                }
                return best;
            }
        }
    }
    None
}

