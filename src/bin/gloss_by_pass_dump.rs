use inchworm::GlossTable;
use std::env;

fn dump_gloss_to_csv(gloss: &GlossTable, path: &str) -> std::io::Result<()> {
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
        eprintln!("Usage: {} <gloss.bin> <output_prefix>", args[0]);
        std::process::exit(1);
    }

    let table = match GlossTable::load(&args[1]) {
        Ok(t) => t,
        Err(e) => {
            eprintln!("Failed to load gloss table: {e}");
            std::process::exit(1);
        }
    };

    let max_pass = table.entries.iter().map(|e| e.pass).max().unwrap_or(0);
    for n in 0..=max_pass {
        let file_name = format!("{}_{n}.csv", args[2]);
        let filtered: Vec<_> = table
            .entries
            .iter()
            .filter(|e| e.pass == n)
            .cloned()
            .collect();
        if filtered.is_empty() {
            continue;
        }
        let t = GlossTable { entries: filtered };
        if let Err(e) = dump_gloss_to_csv(&t, &file_name) {
            eprintln!("Failed to write {file_name}: {e}");
        } else {
            println!("Written {file_name}");
        }
    }
}

