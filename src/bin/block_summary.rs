use inchworm::{split_into_blocks, group_by_bit_length};
use std::{env, fs};

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() != 3 {
        eprintln!("Usage: {} <input_file> <block_size_bits>", args[0]);
        std::process::exit(1);
    }

    let path = &args[1];
    let block_size: usize = args[2].parse().expect("Invalid block size");

    let bytes = fs::read(path).expect("Failed to read input file");
    let blocks = split_into_blocks(&bytes, block_size);
    let table = group_by_bit_length(blocks);

    for (bit_length, group) in table.iter() {
        println!("{}-bit blocks: {}", bit_length, group.len());
    }
}
