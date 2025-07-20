use std::collections::HashMap;

pub struct Config {
    pub block_size: usize,
    pub max_seed_len: usize,
    pub max_arity: u8,
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
