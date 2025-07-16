use inchworm::io_utils::{io_cli_error, simple_cli_error};
use inchworm::{group_by_bit_length, split_into_blocks};
use std::{env, fs, path::Path};

fn main() {
    if let Err(e) = run() {
        eprintln!("{e}");
        std::process::exit(1);
    }
}

fn run() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = env::args().collect();
    if args.len() != 3 {
        return Err(simple_cli_error(&format!(
            "Usage: {} <input_file> <block_size_bits>",
            args[0]
        ))
        .into());
    }

    let path = Path::new(&args[1]);
    let block_size: usize = args[2]
        .parse()
        .map_err(|_| simple_cli_error("Invalid block size"))?;

    let bytes = fs::read(path).map_err(|e| io_cli_error("reading input file", path, e))?;
    let blocks = split_into_blocks(&bytes, block_size);
    let table = group_by_bit_length(blocks);

    for (bit_length, group) in table.iter() {
        println!("{}-bit blocks: {}", bit_length, group.len());
    }

    Ok(())
}
