//! Runtime configuration and validation for supported Telomere engines.
use crate::hasher::{Blake3Expander, SeedExpander, Sha256Expander, Sha256NiExpander};
use crate::tlmr::{MAX_ARITY, MAX_BLOCK_SIZE, MAX_HASH_BITS, MAX_SEED_LEN};
use crate::TelomereError;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Enum representing the chosen hasher for seed expansion.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum HasherKind {
    Blake3,
    Sha256,
    Sha256Ni,
}

impl HasherKind {
    pub fn as_str(self) -> &'static str {
        match self {
            HasherKind::Blake3 => "blake3",
            HasherKind::Sha256 | HasherKind::Sha256Ni => "sha256",
        }
    }

    pub fn get_expander(self) -> Box<dyn SeedExpander> {
        match self {
            HasherKind::Blake3 => Box::new(Blake3Expander),
            HasherKind::Sha256 => Box::new(Sha256Expander),
            HasherKind::Sha256Ni => Box::new(Sha256NiExpander),
        }
    }
}

/// Runtime configuration parameters for the compressor and decompressor.
#[derive(Debug, Clone)]
pub struct Config {
    /// Fixed block size in bytes.
    pub block_size: usize,
    /// Maximum allowed seed length in bytes.
    ///
    /// Seed depth 1 is fast, 2 is slow-ish, and 3 is expensive.
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
            block_size: 4,
            max_seed_len: 1,
            max_arity: 5, // Lotus arity encoding supports 1-5; 6+ requires format extension
            hash_bits: 13,
            hasher: HasherKind::Blake3,
            seed_expansions: HashMap::new(),
            enable_superposition: false,
            memory_limit: usize::MAX,
        }
    }
}

impl Config {
    /// Validate runtime settings against the active `.tlmr` v1 format limits.
    pub fn validate(&self) -> Result<(), TelomereError> {
        if !(1..=MAX_BLOCK_SIZE).contains(&self.block_size) {
            return Err(TelomereError::Config(format!(
                "block_size must be in 1..={MAX_BLOCK_SIZE}"
            )));
        }
        if !(1..=MAX_SEED_LEN).contains(&self.max_seed_len) {
            return Err(TelomereError::Config(format!(
                "max_seed_len must be in 1..={MAX_SEED_LEN}"
            )));
        }
        if !(1..=MAX_ARITY).contains(&self.max_arity) {
            return Err(TelomereError::Config(format!(
                "max_arity must be in 1..={MAX_ARITY}"
            )));
        }
        if !(1..=MAX_HASH_BITS).contains(&self.hash_bits) {
            return Err(TelomereError::Config(format!(
                "hash_bits must be in 1..={MAX_HASH_BITS}"
            )));
        }
        if self.memory_limit == 0 {
            return Err(TelomereError::Config(
                "memory_limit must be greater than zero".into(),
            ));
        }
        Ok(())
    }

    /// Returns a boxed seed expander based on the configuration.
    pub fn get_expander(&self) -> Box<dyn SeedExpander> {
        self.hasher.get_expander()
    }
}
