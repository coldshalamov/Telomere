#![cfg_attr(not(feature = "gpu"), deny(unsafe_code))]
//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
//!
//! Compression and decompression are exposed as subcommands. This binary
//! intentionally performs minimal argument handling before delegating to the
//! library APIs found in this crate.

use clap::{ArgGroup, Args, Parser, Subcommand};
use std::{error::Error, fs, path::PathBuf, time::Instant};
use telomere::{
    compress_multi_pass, decode_tlmr_header, decompress_with_limit,
    io_utils::{extension_error, io_cli_error, simple_cli_error, telomere_cli_error, CliError},
    truncated_hash, Config,
};

fn print_cli_error(err: &CliError) {
    eprintln!("{}", err.msg);
    let mut src = err.source();
    while let Some(s) = src {
        eprintln!("Caused by: {}", s);
        src = s.source();
    }
}

fn main() {
    if let Err(e) = run() {
        print_cli_error(&e);
        std::process::exit(1);
    }
}

fn run() -> Result<(), CliError> {
    let cli = Cli::parse();
    match cli.command {
        Command::Compress(mut args) => {
            let input_path = args
                .input
                .take()
                .or(args.input_pos)
                .ok_or_else(|| simple_cli_error("missing input path"))?;
            let output_path = args
                .output
                .take()
                .or(args.output_pos)
                .ok_or_else(|| simple_cli_error("missing output path"))?;
            let config = Config {
                block_size: args.block_size,
                max_seed_len: args.max_seed_len,
                max_arity: args.max_arity,
                hash_bits: args.hash_bits,
                seed_expansions: std::collections::HashMap::new(),
            };
            let data = fs::read(&input_path)
                .map_err(|e| io_cli_error("opening input file", &input_path, e))?;

            let start_time = Instant::now();
            let (out, gains) = compress_multi_pass(&data, config.block_size, args.passes)
                .map_err(|e| telomere_cli_error("compression failed", e))?;

            if out.is_empty() {
                return Err(simple_cli_error("compression returned no data"));
            }

            if output_path.exists() && !args.force && !args.dry_run {
                return Err(simple_cli_error(&format!(
                    "Error: output file {} already exists (use --force to overwrite)",
                    output_path.display()
                )));
            }

            if !args.dry_run {
                fs::write(&output_path, &out)
                    .map_err(|e| io_cli_error("writing output file", &output_path, e))?;
                eprintln!("✅ Wrote compressed output to {:?}", output_path);
            } else {
                eprintln!("(dry run) skipping file write");
            }

            let raw_len = data.len();
            let compressed_len = out.len();
            let percent = 100.0 * (1.0 - (compressed_len as f64 / raw_len as f64));
            let elapsed = start_time.elapsed();

            if args.json {
                let cfg = Config {
                    block_size: args.block_size,
                    hash_bits: args.hash_bits,
                    ..Config::default()
                };
                let (hash, err) = match decompress_with_limit(&out, &cfg, usize::MAX) {
                    Ok(bytes) => (truncated_hash(&bytes), None::<String>),
                    Err(e) => (0, Some(e.to_string())),
                };
                let out_json = serde_json::json!({
                    "raw_bytes": raw_len,
                    "compressed_bytes": compressed_len,
                    "compression_ratio": compressed_len as f64 / raw_len as f64,
                    "round_trip_hash": hash,
                    "error": err,
                });
                match serde_json::to_string_pretty(&out_json) {
                    Ok(s) => println!("{}", s),
                    Err(e) => eprintln!("json serialization error: {e}"),
                }
            } else if args.status {
                for (idx, gain) in gains.iter().enumerate() {
                    eprintln!("pass {} gained {} bytes", idx + 2, gain);
                }
                eprintln!("Compressed {:.2}% in {:.2?}", percent, elapsed);
            }
        }
        Command::Decompress(mut args) => {
            let input_path = args
                .input
                .take()
                .or(args.input_pos)
                .ok_or_else(|| simple_cli_error("missing input path"))?;
            let output_path = args
                .output
                .take()
                .or(args.output_pos)
                .ok_or_else(|| simple_cli_error("missing output path"))?;
            let config = Config {
                block_size: args.block_size,
                max_seed_len: args.max_seed_len,
                max_arity: args.max_arity,
                hash_bits: args.hash_bits,
                seed_expansions: std::collections::HashMap::new(),
            };
            if input_path
                .extension()
                .and_then(|s| s.to_str())
                .map_or(true, |ext| ext.to_ascii_lowercase() != "tlmr")
            {
                return Err(extension_error(&input_path));
            }
            if output_path.exists() && !args.force {
                return Err(simple_cli_error(&format!(
                    "Error: output file {} already exists (use --force to overwrite)",
                    output_path.display()
                )));
            }
            let data = fs::read(&input_path)
                .map_err(|e| io_cli_error("opening input file", &input_path, e))?;
            // Always decode header and use correct config to ensure strictness
            let header = decode_tlmr_header(&data)
                .map_err(|e| simple_cli_error(&format!("invalid header: {e}")))?;
            let cfg = Config {
                block_size: header.block_size,
                hash_bits: args.hash_bits,
                ..Config::default()
            };
            let decompressed = decompress_with_limit(&data, &cfg, usize::MAX)
                .map_err(|e| simple_cli_error(&format!("decompression failed: {e}")))?;
            if !args.dry_run {
                fs::write(&output_path, decompressed)
                    .map_err(|e| io_cli_error("writing output file", &output_path, e))?;
                eprintln!("✅ Wrote decompressed output to {:?}", output_path);
            } else {
                eprintln!("(dry run) skipping file write");
            }
        }
    }

    Ok(())
}

#[derive(Parser)]
#[command(author, version, about)]
struct Cli {
    #[command(subcommand)]
    command: Command,
}

#[derive(Subcommand)]
enum Command {
    /// Compress a file
    #[command(alias = "c")]
    Compress(ActionArgs),
    /// Decompress a file
    #[command(alias = "d")]
    Decompress(ActionArgs),
}

#[derive(Args)]
#[command(
    group(
        ArgGroup::new("input_src")
            .required(true)
            .args(["input", "input_pos"]),
    ),
    group(
        ArgGroup::new("output_dst")
            .required(true)
            .args(["output", "output_pos"]),
    )
)]
struct ActionArgs {
    /// Input file path
    #[arg(short, long, value_name = "FILE")]
    input: Option<PathBuf>,
    /// Output file path
    #[arg(short, long, value_name = "FILE")]
    output: Option<PathBuf>,
    /// Input file path (positional)
    #[arg(index = 1, value_name = "INPUT", conflicts_with = "input")]
    input_pos: Option<PathBuf>,
    /// Output file path (positional)
    #[arg(index = 2, value_name = "OUTPUT", conflicts_with = "output")]
    output_pos: Option<PathBuf>,
    /// Compression block size
    #[arg(long, default_value_t = 3)]
    block_size: usize,
    /// Maximum seed length
    #[arg(long, default_value_t = 2)]
    max_seed_len: usize,
    /// Maximum arity
    #[arg(long, default_value_t = 8)]
    max_arity: u8,
    /// Number of hash bits
    #[arg(long, default_value_t = 13)]
    hash_bits: usize,
    /// Maximum compression passes
    #[arg(long, default_value_t = 10)]
    passes: usize,
    /// Print a short progress line for every block
    #[arg(long)]
    status: bool,
    /// Emit a JSON summary after completion
    #[arg(long)]
    json: bool,
    /// Perform the operation but skip writing the output file
    #[arg(long)]
    dry_run: bool,
    /// Overwrite the output file if it already exists
    #[arg(long)]
    force: bool,
}
