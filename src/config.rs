//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
use std::collections::HashMap;
use crate::hasher::{Blake3Expander, SeedExpander, Sha256Expander, Sha256NiExpander};

/// Enum representing the chosen hasher for seed expansion.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum HasherKind {
    Blake3,
    Sha256,
    Sha256Ni,
}

/// Runtime configuration parameters for the compressor and decompressor.
#[derive(Debug, Clone)]
pub struct Config {
    /// Fixed block size in bytes.
    pub block_size: usize,
    /// Maximum allowed seed length in bytes.
    ///
    /// The default unit tests use a value of `3` but larger seeds may be
    /// configured for real compression workloads.
    pub max_seed_len: usize,
    /// Maximum bundle arity (number of blocks per seed span).
    pub max_arity: u8,
    /// Number of bits used when truncating seed hashes.
    pub hash_bits: usize,
    /// The hasher to use for seed expansion.
    pub hasher: HasherKind,
    /// Pre-expanded seed bitstreams indexed by seed index.
    pub seed_expansions: HashMap<usize, Vec<u8>>,
    /// Whether to enable superposition (keeping multiple candidates per block).
    pub enable_superposition: bool,
    /// Maximum allowed memory usage in bytes.
    pub memory_limit: usize,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            block_size: 0,
            max_seed_len: 0,
            max_arity: 0,
            hash_bits: 0,
            hasher: HasherKind::Blake3,
            seed_expansions: HashMap::new(),
            enable_superposition: false,
            memory_limit: usize::MAX,
        }
    }
}

impl Config {
    /// Returns a boxed seed expander based on the configuration.
    pub fn get_expander(&self) -> Box<dyn SeedExpander> {
        match self.hasher {
            HasherKind::Blake3 => Box::new(Blake3Expander),
            HasherKind::Sha256 => Box::new(Sha256Expander),
            HasherKind::Sha256Ni => Box::new(Sha256NiExpander),
        }
    }
}
