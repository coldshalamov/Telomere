use thiserror::Error;

use crate::tlmr::TlmrError;

#[derive(Error, Debug)]
pub enum TelomereError {
    /// Malformed or invalid header/EVQL data.
    #[error("header error: {0}")]
    Header(String),

    /// Seed search related failure.
    #[error("seed search error: {0}")]
    SeedSearch(String),

    /// Bundling or bundle selection failure.
    #[error("bundling error: {0}")]
    Bundling(String),

    /// Superposition limit or invariant failure.
    #[error("superposition error: {0}")]
    Superposition(String),

    /// Too many superposed candidates at a block index.
    #[error("superposition limit exceeded for block {0}")]
    SuperpositionLimitExceeded(usize),

    /// Codec-specific header failure (legacy, use Header instead for new code).
    #[error("header codec error: {0}")]
    HeaderCodec(#[from] TlmrError),

    /// Hashing errors (if any).
    #[error("hashing error: {0}")]
    Hash(String),

    /// Configuration error.
    #[error("config error: {0}")]
    Config(String),

    /// Propagated I/O error.
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),

    /// Catch all for unexpected internal problems.
    #[error("internal error: {0}")]
    Internal(String),

    /// (Legacy, avoid in new code) – fallback for decoding errors.
    #[error("decode error: {0}")]
    Decode(String),

    /// (Legacy, avoid in new code) – any other error.
    #[error("other: {0}")]
    Other(String),
}
