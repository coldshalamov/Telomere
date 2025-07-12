use std::env;
use std::fs;
use std::ops::RangeInclusive;
use std::path::Path;
use std::time::Instant;

use inchworm::{compress, GlossTable, TruncHashTable, BLOCK_SIZE, LiveStats};

use inchworm::{encode_header, unpack_region};


use serde_json;
use hex;

fn main() -> std::io::Result<()> {
    println!("✅ Running updated binary build");

    let args: Vec<String> = env::args().collect();
    if args.len() < 4 {
        eprintln!("Usage: {} [c|d] <input> <output> [--max-seed-len N] [--seed-limit N] [--status] [--json] [--verbose] [--quiet] [--gloss FILE] [--gloss-only] [--dry-run] [--gloss-coverage FILE] [--collect-partials] [--hash-filter-bits N] [--filter-known-hashes]", args[0]);
        return Ok(());
    }

    let mut max_seed_len = 4u8;
    let mut seed_limit: Option<u64> = None;
    let mut show_status = false;
    let mut json_out = false;
    let mut gloss_path: Option<String> = None;
    let mut verbose = false;
    let mut quiet = false;
    let mut gloss_only = false;
    let mut dry_run = false;
    let mut gloss_coverage: Option<String> = None;
    let mut collect_partials = false;
    let mut hash_filter_bits: u8 = 24;
    let mut filter_known_hashes = false;

    let mut i = 4;
    while i < args.len() {
        match args[i].as_str() {
            "--max-seed-len" => { max_seed_len = args[i + 1].parse().expect("invalid value"); i += 2; }
            "--seed-limit" => { seed_limit = Some(args[i + 1].parse().expect("invalid value")); i += 2; }
            "--status" => { show_status = true; i += 1; }
            "--gloss" => { gloss_path = Some(args[i + 1].clone()); i += 2; }
            "--json" => { json_out = true; i += 1; }
            "--verbose" => { verbose = true; i += 1; }
            "--quiet" => { quiet = true; i += 1; }
            "--gloss-only" => { gloss_only = true; i += 1; }
            "--dry-run" => { dry_run = true; i += 1; }
            "--gloss-coverage" => { gloss_coverage = Some(args[i + 1].clone()); i += 2; }
            "--collect-partials" => { collect_partials = true; i += 1; }
            "--hash-filter-bits" => { hash_filter_bits = args[i + 1].parse().expect("invalid value"); i += 2; }
            "--filter-known-hashes" => { filter_known_hashes = true; i += 1; }
            flag => {
                eprintln!("Unknown flag: {}", flag);
                return Ok(());
            }
        }
    }

    let data = fs::read(&args[2])?;
    let gloss = GlossTable::load("gloss.bin").unwrap_or_else(|_| GlossTable::default());

    let mut coverage: Option<Vec<bool>> = if gloss_only && gloss_coverage.is_some() {
        Some(vec![false; gloss.entries.len()])
    } else {
        None
    };

        let mut hash_filter = if filter_known_hashes {
        Some(TruncHashTable::new(hash_filter_bits))
    } else {
        None
    };

    match args[1].as_str() {
        "c" => {
            let start_time = Instant::now();
            let mut stats = LiveStats::new(if show_status { 1 } else { 0 });
            let mut hashes = 0u64;

            // Load precomputed hash table (full up to 3 bytes)
            let mut table = TruncHashTable::load("hash_table.bin")
                .expect("failed to load hash_table.bin");

            // Compress using hash table only, skipping gloss and greedy
            let out = compress(
                &data,
                1..=max_seed_len,
                seed_limit,
                stats,
                &mut hashes,
                json_out,
                None, // No gloss
                if verbose { 2 } else if quiet { 0 } else { 1 },
                false, // gloss_only = false
                None,  // No coverage
                None,  // No partials
                Some(&mut table),
            );

            println!("🧪 compress() returned buffer with length: {}", out.len());
            if out.is_empty() {
                eprintln!("❌ compress() returned an empty buffer — nothing to write!");
                return Ok(());
            }

            let compressed_len = out.len();
            if !dry_run {
                let output_path = &args[3];
                println!("💾 Writing {} bytes to {}", out.len(), output_path);
                match fs::write(output_path, &out) {
                    Ok(_) => eprintln!("✅ Wrote compressed output to {:?}", output_path),
                    Err(e) => eprintln!("❌ Failed to write output: {:?}", e),
                }
            } else {
                println!("(dry run) skipping file write");
            }

            let raw_len = data.len();
            let percent = 100.0 * (1.0 - (compressed_len as f64 / raw_len as f64));
            let elapsed = start_time.elapsed();

            if json_out {
                let out_json = serde_json::json!({
                    "input_bytes": raw_len,
                    "compressed_bytes": compressed_len,
                    "total_hashes": hashes,
                    "elapsed_ms": elapsed.as_millis(),
                });
                println!("{}", serde_json::to_string_pretty(&out_json).unwrap());
            } else {
                println!("Compressed {:.2}% in {:.2?}", percent, elapsed);
            }
        }

        "d" => {
            println!("🔎 Running unpack_region() test...");

            let seed = b"abc"; // 3-byte seed
            let header = encode_header(0, 0); // seed_index = 0, arity = 0

            match unpack_region(&header, seed) {
                Ok(span) => {
                    println!("✅ Unpacked span: {:?}", span);
                }
                Err(e) => {
                    eprintln!("❌ Unpacking failed: {}", e);
                }
            }
        }

                mode => eprintln!("Unknown mode: {}", mode),
    }

    Ok(())
}

