use clap::Parser;
use std::fs;
use std::path::PathBuf;
use telomere::{
    decompress_with_limit, decode_tlmr_header, Config,
    io_utils::{extension_error, io_cli_error, simple_cli_error},
};

/// Decompress a Telomere file created by the compressor.
#[derive(Parser)]
struct Args {
    /// Input .tlmr file
    input: PathBuf,
    /// Output file path
    output: PathBuf,
}

fn main() {
    if let Err(e) = run() {
        eprintln!("{e}");
        std::process::exit(1);
    }
}

fn run() -> Result<(), Box<dyn std::error::Error>> {
    let args = Args::parse();
    if args
        .input
        .extension()
        .and_then(|s| s.to_str())
        .map_or(true, |ext| ext.to_ascii_lowercase() != "tlmr")
    {
        return Err(extension_error(&args.input).into());
    }
    let data =
        fs::read(&args.input).map_err(|e| io_cli_error("reading input file", &args.input, e))?;
    let header = decode_tlmr_header(&data).map_err(|e| simple_cli_error(&format!("invalid header: {e}")))?;
    let config = Config { block_size: header.block_size, hash_bits: 13, ..Config::default() };
    let decompressed = decompress_with_limit(&data, &config, usize::MAX)
        .map_err(|e| simple_cli_error(&format!("decompression failed: {e}")))?;
    fs::write(&args.output, &decompressed)
        .map_err(|e| io_cli_error("writing output file", &args.output, e))?;
    Ok(())
}
