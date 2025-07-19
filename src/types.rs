#[derive(Debug, Clone, PartialEq)]
pub struct Candidate {
    pub seed_index: u64,
    pub arity: u8,
    pub bit_len: usize,
    pub pass_seen: usize,
}

pub use crate::error::TelomereError;
