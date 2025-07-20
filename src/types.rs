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
