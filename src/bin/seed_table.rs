use clap::Parser;
use inchworm::io_utils::io_cli_error;
use sha2::{Digest, Sha256};
use std::{
    collections::HashSet,
    fs::OpenOptions,
    io::{BufRead, BufReader, BufWriter, Write},
    path::Path,
};

#[derive(Parser)]
struct Args {
    /// Max bit length of seeds to generate (inclusive)
    #[clap(long)]
    bits: u32,
}

fn main() {
    if let Err(e) = run() {
        eprintln!("{e}");
        std::process::exit(1);
    }
}

fn run() -> Result<(), Box<dyn std::error::Error>> {
    let args = Args::parse();
    let max_bits = args.bits;
    let filename = "seed_table.csv";

    let mut existing = HashSet::new();

    // Read existing file if it exists
    if Path::new(filename).exists() {
        let file = std::fs::File::open(filename)
            .map_err(|e| io_cli_error("opening input file", Path::new(filename), e))?;
        let reader = BufReader::new(file);
        for line in reader.lines() {
            if let Ok(line) = line {
                let parts: Vec<_> = line.split(',').collect();
                if parts.len() >= 2 {
                    let seed_index = parts[0].parse::<u64>().unwrap_or(0);
                    let bit_length = parts[1].parse::<u32>().unwrap_or(0);
                    existing.insert((bit_length, seed_index));
                }
            }
        }
    }

    let file = OpenOptions::new()
        .append(true)
        .create(true)
        .open(filename)
        .map_err(|e| io_cli_error("opening output file", Path::new(filename), e))?;
    let mut writer = BufWriter::new(file);

    for bits in 1..=max_bits {
        let max_index = if bits >= 64 {
            u64::MAX
        } else {
            (1u64 << bits) - 1
        };
        let num_bytes = ((bits + 7) / 8) as usize;

        for i in 0..=max_index {
            if existing.contains(&(bits, i)) {
                continue;
            }

            let bytes_full = i.to_be_bytes();
            let seed_bytes = &bytes_full[8 - num_bytes..];
            let mut hasher = Sha256::new();
            hasher.update(seed_bytes);
            let result = hasher.finalize();
            let hash_hex = hex::encode(result);
            writeln!(writer, "{},{},{}", i, bits, hash_hex)
                .map_err(|e| io_cli_error("writing output file", Path::new(filename), e))?;

            if i % 100_000 == 0 {
                writer
                    .flush()
                    .map_err(|e| io_cli_error("writing output file", Path::new(filename), e))?;
                println!("Progress: bits = {}, index = {}", bits, i);
            }
        }
    }

    writer
        .flush()
        .map_err(|e| io_cli_error("writing output file", Path::new(filename), e))?;
    Ok(())
}
