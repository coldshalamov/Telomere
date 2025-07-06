use std::env;
use std::fs;
use std::ops::RangeInclusive;
use std::path::Path;

use inchworm::{compress, decompress, GlossTable};

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() < 4 {
        eprintln!("Usage: {} [c|d] <input> <output> [--max-seed-len N] [--seed-limit N] [--status N] [--json] [--gloss FILE]", args[0]);
        return;
    }

    let mut max_seed_len = 4u8;
    let mut seed_limit: Option<u64> = None;
    let mut status = 1_000_000u64;
    let mut json_out = false;
    let mut gloss_path: Option<String> = None;

    let mut i = 4;
    while i < args.len() {
        match args[i].as_str() {
            "--max-seed-len" => {
                if i + 1 >= args.len() { break; }
                max_seed_len = args[i + 1].parse().expect("invalid value");
                i += 2;
            }
            "--seed-limit" => {
                if i + 1 >= args.len() { break; }
                seed_limit = Some(args[i + 1].parse().expect("invalid value"));
                i += 2;
            }
            "--status" => {
                if i + 1 >= args.len() { break; }
                status = args[i + 1].parse().expect("invalid value");
                i += 2;
            }
            "--gloss" => {
                if i + 1 >= args.len() { break; }
                gloss_path = Some(args[i + 1].clone());
                i += 2;
            }
            "--json" => {
                json_out = true;
                i += 1;
            }
            flag => {
                eprintln!("Unknown flag: {}", flag);
                return;
            }
        }
    }

    let data = fs::read(&args[2]).expect("failed to read input");

    let gloss = if let Some(path) = gloss_path {
        match GlossTable::load(Path::new(&path)) {
            Ok(t) => {
                eprintln!("Loaded gloss table from {} ({} entries)", path, t.entries.len());
                Some(t)
            }
            Err(e) => {
                eprintln!("Failed to load gloss table: {e}");
                None
            }
        }
    } else {
        None
    };

    match args[1].as_str() {
        "c" => {
            let mut hashes = 0u64;
            let out = compress(
                &data,
                RangeInclusive::new(1, max_seed_len),
                seed_limit,
                status,
                &mut hashes,
                json_out,
            );
            fs::write(&args[3], out).expect("failed to write output");
        }
        "d" => {
            let out = decompress(&data);
            fs::write(&args[3], out).expect("failed to write output");
        }
        mode => eprintln!("Unknown mode: {}", mode),
    }
}
