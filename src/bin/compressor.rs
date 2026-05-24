//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
use clap::Parser;
use std::fs;
use std::path::PathBuf;
use telomere::{
    compress_multi_pass_with_config, decode_tlmr_header, decompress_with_limit,
    io_utils::{io_cli_error, simple_cli_error},
    Config,
};

/// Compress a file using the Telomere MVP pipeline.
#[derive(Parser)]
struct Args {
    /// Input file path
    input: PathBuf,
    /// Output file path
    output: PathBuf,
    /// Block size in bytes
    #[arg(long, default_value_t = 4)]
    block_size: usize,
    /// Maximum seed length in bytes (1=fast, 2=slow-ish, 3=expensive)
    #[arg(long, default_value_t = 1)]
    max_seed_len: usize,
    /// Number of compression passes
    #[arg(long, default_value_t = 1)]
    passes: usize,
    /// Verify decompression after compressing
    #[arg(long)]
    test: bool,
}

fn main() {
    if let Err(e) = run() {
        eprintln!("{e}");
        std::process::exit(1);
    }
}

fn run() -> Result<(), Box<dyn std::error::Error>> {
    let args = Args::parse();
    let config = Config {
        block_size: args.block_size,
        max_seed_len: args.max_seed_len,
        hash_bits: 13,
        ..Config::default()
    };
    config.validate()?;
    let data =
        fs::read(&args.input).map_err(|e| io_cli_error("reading input file", &args.input, e))?;
    let (compressed, gains) = compress_multi_pass_with_config(&data, &config, args.passes, false)
        .map_err(|e| simple_cli_error(&format!("compression failed: {e}")))?;

    if !gains.is_empty() {
        for (i, saved) in gains.iter().enumerate() {
            eprintln!("pass {}: saved {} bytes", i + 2, saved);
        }
    }

    if args.test {
        let header = decode_tlmr_header(&compressed)
            .map_err(|e| simple_cli_error(&format!("invalid header: {e}")))?;
        let verify_cfg = Config {
            block_size: header.block_size,
            max_seed_len: header.max_seed_len,
            max_arity: header.max_arity,
            hash_bits: header.hash_bits,
            hasher: header.hasher,
            ..Config::default()
        };
        let decompressed = decompress_with_limit(&compressed, &verify_cfg, usize::MAX)
            .map_err(|e| simple_cli_error(&format!("roundtrip failed: {e}")))?;
        if decompressed != data {
            return Err(simple_cli_error("roundtrip mismatch").into());
        }
        eprintln!("✓ roundtrip verified");
    }

    fs::write(&args.output, &compressed)
        .map_err(|e| io_cli_error("writing output file", &args.output, e))?;
    Ok(())
}
