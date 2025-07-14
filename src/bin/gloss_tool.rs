use inchworm::gloss::GlossTable;
use std::env;

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() != 3 || args[1] != "build-gloss" {
        eprintln!("Usage: {} build-gloss <output>", args[0]);
        return;
    }

    let table = GlossTable::build();
    if let Err(e) = table.save(&args[2]) {
        eprintln!("Failed to write gloss table: {e}");
    } else {
        println!("Gloss table written to {}", args[2]);
    }
}
