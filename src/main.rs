#![cfg_attr(not(feature = "gpu"), deny(unsafe_code))]
//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976

use clap::{Parser, Subcommand, ValueEnum};
use std::{fs, path::PathBuf};
use telomere::{decode_tlmr_header, decompress_with_limit, Config, HasherKind};
use tracing::{error, info, warn};

#[derive(Parser)]
#[command(name = "telomere", author, version, about)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Compress a file
    #[command(alias = "c")]
    Compress(CompressArgs),
    /// Decompress a file
    #[command(alias = "d")]
    Decompress(DecompressArgs),
}

#[derive(clap::Args)]
struct CompressArgs {
    /// Input file path
    input: PathBuf,
    /// Output file path
    output: PathBuf,

    /// Max seed length in bytes (1-3 for MVP; larger values are exponentially slower)
    #[arg(long, default_value_t = 1)]
    seed_depth: usize,

    /// Max compression passes
    #[arg(long, default_value_t = 1)]
    passes: u32,

    /// Save checkpoint every N minutes
    #[arg(long, default_value_t = 10)]
    checkpoint_every: u32,

    /// Max RAM usage (e.g. "4GB", "80%")
    #[arg(long, default_value = "80%")]
    memory_limit: String,

    /// Hash function
    #[arg(long, value_enum, default_value_t = ArgHasher::Blake3)]
    hasher: ArgHasher,

    /// Resume from checkpoint file
    #[arg(long)]
    resume: Option<PathBuf>,

    /// Verify output after compression
    #[arg(long)]
    verify: bool,

    /// Overwrite existing output
    #[arg(long)]
    force: bool,

    /// Print JSON summary of per-pass statistics to stdout
    #[arg(long)]
    json: bool,

    /// Block size (legacy/tuning)
    #[arg(long, default_value_t = 4)]
    block_size: usize,
}

#[derive(clap::Args)]
struct DecompressArgs {
    /// Input file path
    input: PathBuf,
    /// Output file path
    output: PathBuf,

    /// Overwrite existing output
    #[arg(long)]
    force: bool,

    /// Hash function override for legacy files; v1 files select the hasher from the header
    #[arg(long, value_enum, default_value_t = ArgHasher::Blake3)]
    hasher: ArgHasher,
}

#[derive(ValueEnum, Clone, Debug)]
enum ArgHasher {
    Blake3,
    Sha256,
}

impl From<ArgHasher> for HasherKind {
    fn from(val: ArgHasher) -> Self {
        match val {
            ArgHasher::Blake3 => HasherKind::Blake3,
            ArgHasher::Sha256 => HasherKind::Sha256,
        }
    }
}

fn main() {
    // Initialize tracing (simple subscriber for now)
    tracing_subscriber::fmt::init();

    if let Err(e) = run() {
        error!("Fatal error: {}", e);
        eprintln!("Fatal error: {}", e);
        std::process::exit(1);
    }
}

fn run() -> Result<(), Box<dyn std::error::Error>> {
    let cli = Cli::parse();

    match cli.command {
        Commands::Compress(args) => {
            if args.resume.is_some() {
                warn!("Resume functionality not yet implemented");
            }

            if args.output.exists() && !args.force {
                return Err(format!(
                    "Output file {:?} exists (use --force to overwrite)",
                    args.output
                )
                .into());
            }

            let memory_limit_bytes = parse_memory_limit(&args.memory_limit)?;

            let config = Config {
                block_size: args.block_size,
                max_seed_len: args.seed_depth,
                max_arity: 5, // Lotus arity encoding supports 1-5
                hash_bits: 13,
                hasher: args.hasher.into(),
                seed_expansions: std::collections::HashMap::new(),
                enable_superposition: false,
                memory_limit: memory_limit_bytes,
            };
            config.validate()?;

            let input_data = fs::read(&args.input)?;

            info!(
                "Compressing {} bytes with seed_depth={} passes={}...",
                input_data.len(),
                args.seed_depth,
                args.passes
            );

            let (out, summary) =
                telomere::compress_with_run_summary(&input_data, &config, args.passes as usize)?;

            if args.json {
                println!("{}", summary.to_json());
            } else {
                summary.print_summary();
            }

            if args.verify {
                info!("Verifying...");
                let decompressed = decompress_with_limit(&out, &config, usize::MAX)?;
                if decompressed != input_data {
                    return Err("Verification failed: data mismatch".into());
                }
                info!("Verification successful");
            }

            fs::write(&args.output, &out)?;
            info!("Wrote {} bytes to {:?}", out.len(), args.output);
        }
        Commands::Decompress(args) => {
            if args.output.exists() && !args.force {
                return Err(format!(
                    "Output file {:?} exists (use --force to overwrite)",
                    args.output
                )
                .into());
            }
            let ext = args
                .input
                .extension()
                .and_then(|e| e.to_str())
                .unwrap_or("");
            if ext != "tlmr" {
                return Err(format!(
                    "Invalid file extension '.{}' — input must be a .tlmr file",
                    ext
                )
                .into());
            }

            let input_data = fs::read(&args.input)?;
            let header = decode_tlmr_header(&input_data)
                .map_err(|_| "File appears corrupt or truncated. Verify the file is intact.")?;

            let _hasher_override: HasherKind = args.hasher.into();
            let config = Config {
                block_size: header.block_size,
                max_seed_len: header.max_seed_len,
                max_arity: header.max_arity,
                hash_bits: header.hash_bits,
                hasher: header.hasher,
                seed_expansions: std::collections::HashMap::new(),
                enable_superposition: false,
                memory_limit: usize::MAX,
            };

            info!("Decompressing...");
            let out = decompress_with_limit(&input_data, &config, usize::MAX)
                .map_err(|_| "File appears corrupt or truncated. Verify the file is intact.")?;

            fs::write(&args.output, &out)?;
            info!("Wrote decompressed data to {:?}", args.output);
        }
    }

    Ok(())
}

fn parse_memory_limit(s: &str) -> Result<usize, Box<dyn std::error::Error>> {
    use sysinfo::{System, SystemExt};

    let s = s.trim().to_uppercase();
    if s.ends_with('%') {
        let pct = s.trim_end_matches('%').parse::<f64>()?;
        if !(0.0..=100.0).contains(&pct) || pct == 0.0 {
            return Err("memory percentage must be in 0..=100".into());
        }
        let mut sys = System::new();
        sys.refresh_memory();
        Ok((sys.total_memory() as f64 * pct / 100.0) as usize)
    } else {
        let mut mul = 1.0;
        let num_str;
        if s.ends_with("GB") {
            mul = 1e9;
            num_str = s.trim_end_matches("GB");
        } else if s.ends_with("MB") {
            mul = 1e6;
            num_str = s.trim_end_matches("MB");
        } else if s.ends_with("KB") {
            mul = 1e3;
            num_str = s.trim_end_matches("KB");
        } else {
            num_str = &s;
        }
        let val = num_str.parse::<f64>()?;
        if val <= 0.0 {
            return Err("memory limit must be greater than zero".into());
        }
        Ok((val * mul) as usize)
    }
}
