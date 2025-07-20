//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
use std::process::Command;

fn main() {
    for i in 1..=10 {
        let output = format!("kolyma_pass_{}.tlmr", i);
        let status = Command::new("cargo")
            .args([
                "run",
                "--release",
                "--bin",
                "compressor",
                "c",
                "kolyma.pdf",
                &output,
                "--status",
                "--json",
            ])
            .status()
            .unwrap_or_else(|e| {
                eprintln!("failed to launch cargo: {e}");
                std::process::exit(1);
            });
        if !status.success() {
            eprintln!("Compression pass {} failed", i);
            std::process::exit(1);
        }
    }
}
