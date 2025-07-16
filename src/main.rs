use std::fs;
use std::path::Path;

use clap::{Parser, Subcommand};
use inchworm::{compress, decompress};

/// Telomere command line interface.
///
/// Run with `--help` to see full usage information.
#[derive(Parser)]
#[command(
    author,
    version,
    about = "Telomere generative compression utilities",
    long_about = "Telomere compression CLI.\n\nEXAMPLES:\n  telomere compress --block-size 4 --input sample.txt --output sample.tlmr\n  telomere decompress --input sample.tlmr --output sample.txt\n"
)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Compress an input file
    Compress {
        /// Block size to use (1-32)
        #[arg(long, value_name = "N")]
        block_size: u8,
        /// Input file path
        #[arg(long, value_name = "PATH")]
        input: String,
        /// Output file path
        #[arg(long, value_name = "PATH")]
        output: String,
        /// Overwrite existing output
        #[arg(long)]
        force: bool,
    },
    /// Decompress an input file
    Decompress {
        /// Input file path
        #[arg(long, value_name = "PATH")]
        input: String,
        /// Output file path
        #[arg(long, value_name = "PATH")]
        output: String,
        /// Overwrite existing output
        #[arg(long)]
        force: bool,
    },
}

fn main() -> std::io::Result<()> {
    let cli = Cli::parse();

    match cli.command {
        Commands::Compress {
            block_size,
            input,
            output,
            force,
        } => {
            if !(1..=32).contains(&block_size) {
                eprintln!("Error: --block-size must be between 1 and 32");
                std::process::exit(1);
            }
            let input_path = Path::new(&input);
            let data = fs::read(input_path).map_err(|e| {
                eprintln!("Failed to read {}: {e}", input);
                e
            })?;
            let out_path = Path::new(&output);
            if out_path.exists() && !force {
                eprintln!(
                    "Error: output file {} already exists (use --force to overwrite)",
                    output
                );
                std::process::exit(1);
            }
            let compressed = compress(&data, block_size as usize);
            fs::write(out_path, compressed).map_err(|e| {
                eprintln!("Failed to write {}: {e}", output);
                e
            })?;
        }
        Commands::Decompress {
            input,
            output,
            force,
        } => {
            let input_path = Path::new(&input);
            let data = fs::read(input_path).map_err(|e| {
                eprintln!("Failed to read {}: {e}", input);
                e
            })?;
            let out_path = Path::new(&output);
            if out_path.exists() && !force {
                eprintln!(
                    "Error: output file {} already exists (use --force to overwrite)",
                    output
                );
                std::process::exit(1);
            }
            let decompressed = decompress(&data);
            fs::write(out_path, decompressed).map_err(|e| {
                eprintln!("Failed to write {}: {e}", output);
                e
            })?;
        }
    }

    Ok(())
}
