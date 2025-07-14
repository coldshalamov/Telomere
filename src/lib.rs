mod block;
mod bloom;
mod compress;
mod compress_stats;
mod gloss;
mod gloss_prune_hook;
mod header;
mod live_window;
mod path;
mod seed_detect;
mod seed_logger;
mod sha_cache;
mod stats;
mod bundle;

pub use block::{
    apply_block_changes, detect_bundles, group_by_bit_length, split_into_blocks, Block,
    BlockChange, BlockTable,
};
pub use bloom::*;
pub use compress::{compress_block, dump_beliefmap_json, dump_gloss_to_csv, TruncHashTable};
pub use compress_stats::{write_stats_csv, CompressionStats};
pub use gloss::*;
pub use gloss_prune_hook::run as gloss_prune_hook;
pub use header::{decode_header, encode_header, Header, HeaderError};
pub use live_window::{print_window, LiveStats};
pub use path::*;
pub use seed_detect::{detect_seed_matches, BlockStatus, MatchRecord, MutableBlock};
pub use seed_logger::{log_seed, resume_seed_index, HashEntry};
pub use sha_cache::*;
pub use stats::Stats;
pub use bundle::{BlockStatus, MutableBlock, apply_bundle};

use crate::compress::FallbackSeeds;
use crate::path::PathGloss as PathGlossPrivate;
use sha2::{Digest, Sha256};
use std::collections::HashMap;
use std::ops::RangeInclusive;

pub const BLOCK_SIZE: usize = 3;

pub fn print_compression_status(original: usize, compressed: usize) {
    let ratio = 100.0 * (1.0 - compressed as f64 / original as f64);
    eprintln!(
        "Compression: {} → {} bytes ({:.2}%)",
        original, compressed, ratio
    );
}

#[derive(Debug, Clone)]
pub enum Region {
    Raw(Vec<u8>),
    Compressed(Vec<u8>, Header),
}
