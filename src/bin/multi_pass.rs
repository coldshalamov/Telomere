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
            .expect("Pass compression failed");
        if !status.success() {
            eprintln!("Compression pass {} failed", i);
            std::process::exit(1);
        }
    }
}
