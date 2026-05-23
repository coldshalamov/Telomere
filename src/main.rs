#![cfg_attr(not(feature = "gpu"), deny(unsafe_code))]
//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976

use clap::{Parser, Subcommand, ValueEnum};
use std::{fs, path::PathBuf, time::Instant};
use telomere::{
    compress_multi_pass_with_config, decode_tlmr_header, decompress_with_limit,
    truncated_hash, Config, HasherKind,
};
use tracing::{info, error, warn};

#[derive(Parser)]
#[command(name = "telomere", author, version, about)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Compress a file
    Compress(CompressArgs),
    /// Decompress a file
    Decompress(DecompressArgs),
}

#[derive(clap::Args)]
struct CompressArgs {
    /// Input file path
    input: PathBuf,
    /// Output file path
    output: PathBuf,

    /// Max seed length in bytes (1-3 for MVP; larger values are exponentially slower)
    #[arg(long, default_value_t = 3)]
    seed_depth: usize,

    /// Max compression passes
    #[arg(long, default_value_t = 149)]
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
    
    /// Block size (legacy/tuning)
    #[arg(long, default_value_t = 3)]
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
    
    /// Hash function (override header/default)
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

            let memory_limit_bytes = parse_memory_limit(&args.memory_limit);

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

            let input_data = fs::read(&args.input)?;
            
            info!("Compressing {} bytes...", input_data.len());
            let start = Instant::now();

            let (out, gains) = compress_multi_pass_with_config(
                &input_data, 
                &config, 
                args.passes as usize, 
                true 
            )?;

            info!("Compressed in {:.2?}", start.elapsed());
            for (i, gain) in gains.iter().enumerate() {
                info!("Pass {}: saved {} bytes", i + 2, gain);
            }

            if args.verify {
                info!("Verifying...");
                let expander = config.get_expander();
                let hash = truncated_hash(&out, expander.as_ref());
                
                let decompressed = decompress_with_limit(&out, &config, usize::MAX)?;
                if decompressed != input_data {
                    return Err("Verification failed: data mismatch".into());
                }
                info!("Verification successful. Hash: {}", hash);
            }

            fs::write(&args.output, &out)?;
            info!("Wrote {} bytes to {:?}", out.len(), args.output);
        }
        Commands::Decompress(args) => {
             if args.output.exists() && !args.force {
                return Err(format!("Output file {:?} exists (use --force to overwrite)", args.output).into());
            }

            let input_data = fs::read(&args.input)?;
            let header = decode_tlmr_header(&input_data)?;
            
            let config = Config {
                block_size: header.block_size,
                max_seed_len: 0, 
                max_arity: 0,
                hash_bits: 13, 
                hasher: args.hasher.into(), 
                seed_expansions: std::collections::HashMap::new(),
                enable_superposition: false,
                memory_limit: usize::MAX,
            };

            info!("Decompressing...");
            let out = decompress_with_limit(&input_data, &config, usize::MAX)?;
            
            fs::write(&args.output, &out)?;
            info!("Wrote decompressed data to {:?}", args.output);
        }
    }

    Ok(())
}

fn parse_memory_limit(s: &str) -> usize {
    use sysinfo::{System, SystemExt};
    
    let s = s.trim().to_uppercase();
    if s.ends_with('%') {
        let pct = s.trim_end_matches('%').parse::<f64>().unwrap_or(80.0);
        let mut sys = System::new();
        sys.refresh_memory();
        (sys.total_memory() as f64 * pct / 100.0) as usize
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
        let val = num_str.parse::<f64>().unwrap_or(1024.0 * 1024.0 * 1024.0); // Default 1GB? Or fallback.
        (val * mul) as usize
    }
}
