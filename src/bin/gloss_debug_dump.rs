use inchworm::gloss::GlossTable;
use std::env;

pub fn dump_gloss_to_csv(gloss: &GlossTable, path: &str) -> std::io::Result<()> {
    let mut wtr = csv::Writer::from_path(path)?;
    wtr.write_record(&["Index", "SeedHex", "DataHex"])?;
    for (idx, entry) in gloss.entries.iter().enumerate() {
        let seed_hex = hex::encode(&entry.seed);
        let data_hex = hex::encode(&entry.decompressed);
        wtr.write_record(&[idx.to_string(), seed_hex, data_hex])?;
    }
    wtr.flush()?;
    Ok(())
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() != 3 {
        eprintln!("Usage: {} <gloss.bin> <output.csv>", args[0]);
        std::process::exit(1);
    }
    let table = match GlossTable::load(&args[1]) {
        Ok(t) => t,
        Err(e) => {
            eprintln!("Failed to load gloss table: {e}");
            std::process::exit(1);
        }
    };
    if let Err(e) = dump_gloss_to_csv(&table, &args[2]) {
        eprintln!("Failed to write CSV: {e}");
        std::process::exit(1);
    }
}
