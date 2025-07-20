use thiserror::Error;

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
    /// Propagated I/O error.
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
    /// Catch all for unexpected internal problems.
    #[error("internal error: {0}")]
    Internal(String),
}
