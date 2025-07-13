use clap::Parser;
use sha2::{Sha256, Digest};
use std::{fs::OpenOptions, io::{BufReader, BufWriter, Write, BufRead}, path::Path};

#[derive(Parser)]
struct Args {
    /// Number of bits for the seed index table
    #[clap(long)]
    bits: u32,
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = Args::parse();
    let max_index = if args.bits >= 64 {
        u64::MAX
    } else {
        (1u64 << args.bits) - 1
    };
    let filename = format!("table_{}.csv", args.bits);

    let mut start_index = 0u64;

    if Path::new(&filename).exists() {
        let file = std::fs::File::open(&filename)?;
        let reader = BufReader::new(file);
        for line in reader.lines() {
            let l = line?;
            if let Some(idx_str) = l.split(',').next() {
                if let Ok(idx) = idx_str.parse::<u64>() {
                    if idx > start_index {
                        start_index = idx;
                    }
                }
            }
        }
        start_index += 1;
    }

    println!("Starting from index: {}", start_index);

    let file = OpenOptions::new().append(true).create(true).open(&filename)?;
    let mut writer = BufWriter::new(file);

    let num_bytes = ((args.bits + 7) / 8) as usize;

    for i in start_index..=max_index {
        let bytes_full = i.to_be_bytes();
        let seed_bytes = &bytes_full[8 - num_bytes..];
        let mut hasher = Sha256::new();
        hasher.update(seed_bytes);
        let result = hasher.finalize();
        let hash_hex = hex::encode(result);
        writeln!(writer, "{},{}", i, hash_hex)?;
        if i % 100_000 == 0 {
            writer.flush()?;
            println!("Progress: {}", i);
        }
    }
    writer.flush()?;
    Ok(())
}
