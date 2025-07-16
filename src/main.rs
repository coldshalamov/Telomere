//! Telomere command line entry point.
//!
//! Compression and decompression are selected via the first positional
//! argument.  This binary is intentionally thin and merely forwards to the
//! library APIs found in this crate.

use std::{env, fs, path::Path, time::Instant};
use telomere::{
    compress, decompress_with_limit, io_utils::{extension_error, io_cli_error, simple_cli_error},
};

fn main() {
    if let Err(e) = run() {
        eprintln!("{e}");
        std::process::exit(1);
    }
}

fn run() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = env::args().collect();
    if args.len() < 4 {
        eprintln!(
            "Usage: {} [c|d] <input> <output> [--block-size N] [--status] [--json] [--dry-run] [--force]",
            args[0]
        );
        return Err(simple_cli_error("Insufficient arguments").into());
    }

    let mut block_size = 3_usize;
    let mut show_status = false;
    let mut json_out = false;
    let mut dry_run = false;
    let mut force = false;

    let mut i = 4;
    while i < args.len() {
        match args[i].as_str() {
            "--block-size" => {
                block_size = args.get(i + 1)
                    .ok_or_else(|| simple_cli_error("Missing value for --block-size"))?
                    .parse()
                    .map_err(|_| simple_cli_error("Invalid block size"))?;
                i += 2;
            }
            "--status" => {
                show_status = true;
                i += 1;
            }
            "--json" => {
                json_out = true;
                i += 1;
            }
            "--dry-run" => {
                dry_run = true;
                i += 1;
            }
            "--force" => {
                force = true;
                i += 1;
            }
            flag => {
                return Err(simple_cli_error(&format!("Unknown flag: {}", flag)).into());
            }
        }
    }

    let input_path = Path::new(&args[2]);
    let output_path = Path::new(&args[3]);
    let data = fs::read(input_path)
        .map_err(|e| io_cli_error("opening input file", input_path, e))?;

    match args[1].as_str() {
        "c" => {
            let start_time = Instant::now();

            let out = compress(&data, block_size);

            if out.is_empty() {
                return Err(simple_cli_error("compress() returned no data").into());
            }

            if output_path.exists() && !force && !dry_run {
                return Err(simple_cli_error(&format!(
                    "Error: output file {} already exists (use --force to overwrite)",
                    output_path.display()
                ))
                .into());
            }

            if !dry_run {
                fs::write(output_path, &out)
                    .map_err(|e| io_cli_error("writing output file", output_path, e))?;
                eprintln!("✅ Wrote compressed output to {:?}", output_path);
            } else {
                eprintln!("(dry run) skipping file write");
            }

            let raw_len = data.len();
            let compressed_len = out.len();
            let percent = 100.0 * (1.0 - (compressed_len as f64 / raw_len as f64));
            let elapsed = start_time.elapsed();

            if json_out {
                let out_json = serde_json::json!({
                    "input_bytes": raw_len,
                    "compressed_bytes": compressed_len,
                    "elapsed_ms": elapsed.as_millis(),
                });
                println!("{}", serde_json::to_string_pretty(&out_json).unwrap());
            } else if show_status {
                eprintln!("Compressed {:.2}% in {:.2?}", percent, elapsed);
            }
        }

        "d" => {
            if input_path
                .extension()
                .and_then(|s| s.to_str())
                .map_or(true, |ext| ext.to_ascii_lowercase() != "tlmr")
            {
                return Err(extension_error(input_path).into());
            }
            if output_path.exists() && !force {
                return Err(simple_cli_error(&format!(
                    "Error: output file {} already exists (use --force to overwrite)",
                    output_path.display()
                ))
                .into());
            }
            let decompressed = decompress_with_limit(&data, usize::MAX)
                .map_err(|e| simple_cli_error(&format!("decompression failed: {e}")))?;
            if !dry_run {
                fs::write(output_path, decompressed)
                    .map_err(|e| io_cli_error("writing output file", output_path, e))?;
                eprintln!("✅ Wrote decompressed output to {:?}", output_path);
            } else {
                eprintln!("(dry run) skipping file write");
            }
        }

        mode => {
            return Err(simple_cli_error(&format!("Unknown mode: {}", mode)).into());
        }
    }

    Ok(())
}
