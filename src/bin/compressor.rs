//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
use clap::Parser;
use std::fs;
use std::path::PathBuf;
use telomere::{
    compress, decompress_with_limit, Config,
    io_utils::{io_cli_error, simple_cli_error},
};

/// Compress a file using the Telomere MVP pipeline.
#[derive(Parser)]
struct Args {
    /// Input file path
    input: PathBuf,
    /// Output file path
    output: PathBuf,
    /// Block size to use during compression
    #[arg(long, default_value_t = 3)]
    block_size: usize,
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
    let data =
        fs::read(&args.input).map_err(|e| io_cli_error("reading input file", &args.input, e))?;
    let compressed = compress(&data, args.block_size)
        .map_err(|e| simple_cli_error(&format!("compression failed: {e}")))?;

    if args.test {
        let config = Config { block_size: args.block_size, hash_bits: 13, ..Config::default() };
        let decompressed = decompress_with_limit(&compressed, &config, usize::MAX)
            .map_err(|e| simple_cli_error(&format!("roundtrip failed: {e}")))?;
        if decompressed != data {
            return Err(simple_cli_error("roundtrip mismatch").into());
        }
        eprintln!("✅ roundtrip verified");
    }

    fs::write(&args.output, &compressed)
        .map_err(|e| io_cli_error("writing output file", &args.output, e))?;
    Ok(())
}
