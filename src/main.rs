use std::{env, fs, path::Path, time::Instant};

use inchworm::{
    compress, decompress_with_limit,
    io_utils::{extension_error, io_cli_error, simple_cli_error},
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
            "Usage: {} [c|d] <input> <output> [--block-size N] [--status] [--json] [--dry-run]",
            args[0]
        );
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
                block_size = args[i + 1]
                    .parse()
                    .map_err(|_| simple_cli_error("invalid block size"))?;
                i += 2;
            }
            "--seed-limit" => {
                i += 2; // ignored
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
            flag => {
                return Err(simple_cli_error(&format!("Unknown flag: {}", flag)).into());
            }
        }
    }

    let input_path = Path::new(&args[2]);
    let output_path = Path::new(&args[3]);
    let data =
        fs::read(input_path).map_err(|e| io_cli_error("opening input file", input_path, e))?;

    match args[1].as_str() {
        "c" => {
            let start_time = Instant::now();

            let out = compress(&data, block_size);
            if out.is_empty() {
                return Err(simple_cli_error("compress() returned no data").into());
            }

            let compressed_len = out.len();
            if !dry_run {
                fs::write(output_path, &out)
                    .map_err(|e| io_cli_error("writing output file", output_path, e))?;
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
            let decompressed = decompress_with_limit(&data, usize::MAX)
                .ok_or_else(|| simple_cli_error("truncated or corrupted input file"))?;
            fs::write(output_path, decompressed)
                .map_err(|e| io_cli_error("writing output file", output_path, e))?;
        }
        mode => {
            return Err(simple_cli_error(&format!("Unknown mode: {}", mode)).into());
        }
    }

    Ok(())
}
