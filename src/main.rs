use std::env;
use std::fs;

use inchworm::{compress, decompress};
use std::ops::RangeInclusive;

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() < 4 {
        eprintln!("Usage: {} [c|d] <input> <output> [--max-seed-len N] [--seed-limit N] [--status N]", args[0]);
        return;
    }

    let mut max_seed_len = 4u8;
    let mut seed_limit: Option<u64> = None;
    let mut status = 1_000_000u64;

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
            flag => {
                eprintln!("Unknown flag: {}", flag);
                return;
            }
        }
    }

    let data = fs::read(&args[2]).expect("failed to read input");

    match args[1].as_str() {
        "c" => {
            let mut hashes = 0u64;
            let out = compress(&data, RangeInclusive::new(1, max_seed_len), seed_limit, status, &mut hashes);
            fs::write(&args[3], out).expect("failed to write output");
        }
        "d" => {
            let out = decompress(&data);
            fs::write(&args[3], out).expect("failed to write output");
        }
        mode => eprintln!("Unknown mode: {}", mode),
    }
}
