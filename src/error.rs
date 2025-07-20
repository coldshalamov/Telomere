use thiserror::Error;

#[derive(Error, Debug)]
pub enum TelomereError {
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),
    #[error("Decode error: {0}")]
    Decode(String),
    #[error("Hashing error: {0}")]
    Hash(String),
    #[error("Config error: {0}")]
    Config(String),
    #[error("Superposition limit exceeded for block {0}")]
    SuperpositionLimitExceeded(usize),
    #[error("Header codec error: {0}")]
    HeaderCodec(String),
    #[error("Other: {0}")]
    Other(String),
}
