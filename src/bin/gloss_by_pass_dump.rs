use inchworm::GlossTable;
use std::env;

/// Dump one CSV file per discovery pass in the gloss table.
fn dump_gloss_by_pass(gloss: &GlossTable, dir: &str) -> std::io::Result<()> {
    std::fs::create_dir_all(dir)?;
    let max_pass = gloss.entries.iter().map(|e| e.pass).max().unwrap_or(0);

    for p in 0..=max_pass {
        let entries: Vec<_> = gloss.entries.iter().filter(|e| e.pass == p).collect();
        if entries.is_empty() {
            continue;
        }

        let path = format!("{}/gloss_pass_{}.csv", dir, p);
        let mut wtr = csv::Writer::from_path(path)?;
        wtr.write_record(&["ID", "Arity", "Score", "Pass", "SeedHex"])?;
        for (i, e) in entries.iter().enumerate() {
            let seed_hex = hex::encode(&e.seed);
            // Arity can be derived from decompressed length.
            let arity = e.decompressed.len() / inchworm::BLOCK_SIZE;
            wtr.write_record(&[
                i.to_string(),
                arity.to_string(),
                format!("{:.4}", e.score),
                e.pass.to_string(),
                seed_hex,
            ])?;
        }
        wtr.flush()?;
    }

    Ok(())
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() != 3 {
        eprintln!("Usage: {} <gloss.bin> <output_dir>", args[0]);
        std::process::exit(1);
    }

    let table = match GlossTable::load(&args[1]) {
        Ok(t) => t,
        Err(e) => {
            eprintln!("Failed to load gloss table: {e}");
            std::process::exit(1);
        }
    };

    if let Err(e) = dump_gloss_by_pass(&table, &args[2]) {
        eprintln!("Failed to dump gloss table: {e}");
        std::process::exit(1);
    }
}

