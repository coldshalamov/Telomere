use sha2::{Sha256, Digest};
use std::fs::File;
use std::io::{BufWriter, Write};

fn main() -> std::io::Result<()> {
    let file = File::create("seeds_1byte.txt")?;
    let mut writer = BufWriter::new(file);

    for seed in 0u8..=255u8 {
        let mut hasher = Sha256::new();
        hasher.update(&[seed]);
        let result = hasher.finalize();
        let hex_hash = hex::encode(result);
        writeln!(writer, "{:02x}: {}", seed, hex_hash)?;
    }

    Ok(())
}
