use std::collections::HashMap;
use std::ops::RangeInclusive;
use std::time::Instant;

mod bloom;
mod compress;
mod gloss;
mod header;
mod sha_cache;
mod path;
mod seed_logger;

pub use bloom::*;
pub use compress::TruncHashTable;
pub use gloss::*;
pub use header::{Header, encode_header, decode_header, HeaderError};
pub use sha_cache::*;
pub use path::*;
pub use seed_logger::{resume_seed_index, log_seed, HashEntry};

const BLOCK_SIZE: usize = 7;

pub fn print_compression_status(original: usize, compressed: usize) {
    let ratio = 100.0 * (1.0 - compressed as f64 / original as f64);
    eprintln!("Compression: {} → {} bytes ({:.2}%)", original, compressed, ratio);
}

#[derive(Debug, Clone)]
pub enum Region {
    Raw(Vec<u8>),
    Compressed(Vec<u8>, Header),
}

// … FULL compress(), decompress(), decompress_with_limit(), etc.
