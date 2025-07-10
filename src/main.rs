use std::env;
use std::fs;
use std::ops::RangeInclusive;
use std::path::Path;
use std::time::Instant;

use inchworm::{compress, decompress, GlossTable, TruncHashTable};
use serde_json;
use hex;

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() < 4 {
        eprintln!("Usage: {} [c|d] <input> <output> [--max-seed-len N] [--seed-limit N] [--status] [--json] [--verbose] [--quiet] [--gloss FILE] [--gloss-only] [--dry-run] [--gloss-coverage FILE] [--collect-partials] [--hash-filter-bits N] [--filter-known-hashes]", args[0]);
        return;
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
                show_status = true;
                i += 1;
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
            "--verbose" => {
                verbose = true;
                i += 1;
            }
            "--quiet" => {
                quiet = true;
                i += 1;
            }
            "--gloss-only" => {
                gloss_only = true;
                i += 1;
            }
            "--dry-run" => {
                dry_run = true;
                i += 1;
            }
            "--gloss-coverage" => {
                if i + 1 >= args.len() { break; }
                gloss_coverage = Some(args[i + 1].clone());
                i += 2;
            }
            "--collect-partials" => {
                collect_partials = true;
                i += 1;
            }
            "--hash-filter-bits" => {
                if i + 1 >= args.len() { break; }
                hash_filter_bits = args[i + 1].parse().expect("invalid value");
                i += 2;
            }
            "--filter-known-hashes" => {
                filter_known_hashes = true;
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

    let verbosity = if quiet { 0 } else if verbose { 2 } else { 1 };

    let mut coverage: Option<Vec<bool>> = if gloss_only && gloss_coverage.is_some() {
        gloss.as_ref().map(|g| vec![false; g.entries.len()])
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
            let mut hashes = 0u64;
            let mut partials_store = Vec::new();
            let status_interval = if show_status { 100_000 } else { 0 };

            let out = compress(
                &data,
                RangeInclusive::new(1, max_seed_len),
                seed_limit,
                status_interval,
                &mut hashes,
                json_out,
                gloss.as_ref(),
                verbosity,
                gloss_only,
                coverage.as_mut().map(|v| v.as_mut_slice()),
                if collect_partials { Some(&mut partials_store) } else { None },
                hash_filter.as_mut(),
            );

            let compressed_len = out.len();
            if !dry_run {
                fs::write(&args[3], &out).expect("failed to write output");
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

            if let (Some(path), Some(cov), Some(table)) = (gloss_coverage, coverage, gloss.as_ref()) {
                let report: Vec<_> = table
                    .entries
                    .iter()
                    .zip(cov.iter())
                    .map(|(e, m)| serde_json::json!({
                        "seed": hex::encode(&e.seed),
                        "arity": e.decompressed.len() / inchworm::BLOCK_SIZE,
                        "matched": m,
                    }))
                    .collect();
                let serialized = serde_json::to_vec_pretty(&report).expect("serialize coverage");
                if let Err(e) = fs::write(path, serialized) {
                    eprintln!("Failed to write coverage report: {e}");
                }
            }

            if collect_partials {
                eprintln!("collected {} partial matches", partials_store.len());
            }
            if let Some(filter) = hash_filter {
                let skipped_percent = 0.0;
                eprintln!("seed filter stored {} entries, skipped {:.2}% of candidates", filter.set.len(), skipped_percent);
            }
        }
        "d" => {
            let gloss = gloss.unwrap_or_default();
            let out = decompress(&data, &gloss);
            fs::write(&args[3], out).expect("failed to write output");
        }
        mode => eprintln!("Unknown mode: {}", mode),
    }
}
