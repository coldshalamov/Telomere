use std::env;
use std::fs;
use std::time::Instant;

use inchworm::{compress, decompress, LiveStats};

fn main() -> std::io::Result<()> {
    let args: Vec<String> = env::args().collect();
    if args.len() < 4 {
        eprintln!("Usage: {} [c|d] <input> <output> [--block-size N] [--status] [--json] [--dry-run]", args[0]);
        return Ok(());
    }

    let mut block_size = 3_usize;
    let mut show_status = false;
    let mut json_out = false;
    let mut dry_run = false;

    let mut i = 4;
    while i < args.len() {
        match args[i].as_str() {
            "--block-size" => {
                block_size = args[i + 1].parse().expect("invalid block size");
                i += 2;
            }
            "--status" => { show_status = true; i += 1; }
            "--json" => { json_out = true; i += 1; }
            "--dry-run" => { dry_run = true; i += 1; }
            flag => {
                eprintln!("Unknown flag: {}", flag);
                return Ok(());
            }
        }
    }

    let data = fs::read(&args[2])?;

    match args[1].as_str() {
        "c" => {
            let start_time = Instant::now();
            let mut stats = LiveStats::new(if show_status { 1 } else { 0 });

            // Compress using selected block size
            let out = compress(&data, block_size);

            eprintln!("🧪 compress() returned buffer with length: {}", out.len());
            if out.is_empty() {
                eprintln!("❌ compress() returned an empty buffer — nothing to write!");
                return Ok(());
            }

            let compressed_len = out.len();
            if !dry_run {
                let output_path = &args[3];
                eprintln!("💾 Writing {} bytes to {}", out.len(), output_path);
                match fs::write(output_path, &out) {
                    Ok(_) => eprintln!("✅ Wrote compressed output to {:?}", output_path),
                    Err(e) => eprintln!("❌ Failed to write output: {:?}", e),
                }
            } else {
                eprintln!("(dry run) skipping file write");
            }

            let raw_len = data.len();
            let percent = 100.0 * (1.0 - (compressed_len as f64 / raw_len as f64));
            let elapsed = start_time.elapsed();

            if json_out {
                let out_json = serde_json::json!({
                    "input_bytes": raw_len,
                    "compressed_bytes": compressed_len,
                    "elapsed_ms": elapsed.as_millis(),
                });
                println!("{}", serde_json::to_string_pretty(&out_json).unwrap());
            } else {
                eprintln!("Compressed {:.2}% in {:.2?}", percent, elapsed);
            }
        }

        "d" => {
            let decompressed = decompress(&data, block_size);
            fs::write(&args[3], decompressed)?;
        }

        mode => eprintln!("Unknown mode: {}", mode),
    }

    Ok(())
}
