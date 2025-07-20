//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976

//! Representation of a candidate compression path across multiple blocks.
//!
//! A [`CompressionPath`] collects the seeds and SHA‑256 hashes used when
//! exploring more advanced compression strategies.  The structure is not
//! heavily used in the MVP but remains for future experimentation.

use std::time::Instant;

#[derive(Clone, Debug)]
pub struct CompressionPath {
    pub id: u64,
    pub seeds: Vec<Vec<u8>>,        // Max 16 entries
    pub span_hashes: Vec<[u8; 32]>, // One per step
    pub total_gain: u64,            // Bits saved
    pub created_at: Instant,        // Global pass index
    pub replayed: u32,
}
