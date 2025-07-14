
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

