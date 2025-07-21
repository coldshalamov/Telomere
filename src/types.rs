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

/// Telomere `.tlmr` batch file header.
///
/// Encodes file format, block size, last block tail size, number of blocks and
/// a truncated hash.  All fields are packed in the order shown below and must
/// match the encoder/decoder bit layout exactly.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct TlmrBatchHeader {
    /// 2 bits: File format version (0-3). Stored in the upper two bits of the
    /// first header byte.
    pub version: u8,
    /// 4 bits: Block size code (0-15). The actual block size is `code + 1`.
    /// Stored in bits 2..=5 of the first header byte.
    pub block_size: u8,
    /// 2 bits: Reserved for future use (always `0`). Stored in the lowest two
    /// bits of the first header byte.
    pub reserved: u8,
    /// 4 bits: Size in bytes of the tail of the final block. Encoded using the
    /// same `code + 1` scheme and stored in the upper four bits of the second
    /// header byte.
    pub last_block_size: u8,
    /// 4 bits: Reserved for future use (always `0`). Stored in the lower four
    /// bits of the second header byte.
    pub reserved2: u8,
    /// Number of blocks in the batch encoded as a little-endian `u32`.
    pub block_count: u32,
    /// 13 bits: truncated SHA-256 hash of the decompressed data. Encoded as two
    /// bytes (`u16`).
    pub hash_low13: u16,
}

