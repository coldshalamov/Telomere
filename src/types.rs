//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
#[derive(Debug, Clone, PartialEq)]
pub struct Candidate {
    /// Seed enumeration index used for this candidate.
    pub seed_index: u64,
    /// Number of blocks represented by this candidate.
    pub arity: u8,
    /// Total encoded length in bits for this candidate.
    pub bit_len: usize,
}

pub use crate::error::TelomereError;

/// Batch-level Telomere header used for streaming compression outputs.
///
/// Fields are stored big endian per the Telomere specification.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct TlmrBatchHeader {
    /// Protocol version encoded as a three bit value.
    pub version: u8,
    /// Encoded block size where the stored value is the size minus one (1..=16).
    pub block_size: u8,
    /// Encoded size in bytes of the final block using the same scheme as
    /// `block_size`.
    pub last_block_size: u8,
    /// Number of blocks included in the batch.
    pub block_count: u32,
    /// Lower 13 bits of the SHA-256 hash of the decompressed data.
    pub hash_low13: u16,
}

