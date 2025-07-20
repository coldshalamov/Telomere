use std::collections::HashMap;

/// Runtime configuration parameters for the compressor and decompressor.
#[derive(Debug, Clone)]
pub struct Config {
    /// Fixed block size in bytes.
    pub block_size: usize,
    /// Maximum allowed seed length in bytes.
    pub max_seed_len: usize,
    /// Maximum bundle arity (number of blocks per seed span).
    pub max_arity: u8,
    /// Number of bits used when truncating seed hashes.
    pub hash_bits: usize,
    /// Pre-expanded seed bitstreams indexed by seed index.
    pub seed_expansions: HashMap<usize, Vec<u8>>,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            block_size: 0,
            max_seed_len: 0,
            max_arity: 0,
            hash_bits: 0,
            seed_expansions: HashMap::new(),
        }
    }
}
