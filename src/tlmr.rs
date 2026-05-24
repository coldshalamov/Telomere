//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
use crate::config::HasherKind;
use crate::hasher::SeedExpander;
use thiserror::Error;

pub const TLMR_MAGIC: [u8; 4] = *b"TLMR";
pub const TLMR_FORMAT_VERSION: u8 = 1;
pub const TLMR_HEADER_LEN: usize = 40;
pub const LOTUS_PRESET_VERSION: u8 = 1;
pub const MAX_BLOCK_SIZE: usize = 16;
pub const MAX_SEED_LEN: usize = 3;
pub const MAX_ARITY: u8 = 5;
pub const MAX_HASH_BITS: usize = 64;

/// Rich Telomere file header used by the active `.tlmr` format.
///
/// Version 1 deliberately replaces the old 3-byte experimental header. The
/// active header records the hasher, Lotus preset, search limits, layer count,
/// original length, payload length, and truncated output hash so a decoder can
/// reconstruct the file without out-of-band CLI flags.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TlmrHeader {
    pub version: u8,
    pub lotus_preset: u8,
    pub hasher: HasherKind,
    pub block_size: usize,
    pub last_block_size: usize,
    pub max_seed_len: usize,
    pub max_arity: u8,
    pub hash_bits: usize,
    pub layer_count: u8,
    pub original_len: u64,
    pub payload_len: u64,
    pub output_hash: u64,
}

/// Errors that can occur while decoding or validating the header.
#[derive(Debug, Error, PartialEq, Eq)]
pub enum TlmrError {
    #[error("header too short")]
    TooShort,
    #[error("invalid header field")]
    InvalidField,
    #[error("output hash mismatch")]
    OutputHashMismatch,
}

impl From<&str> for TlmrError {
    fn from(_: &str) -> Self {
        TlmrError::InvalidField
    }
}

impl From<String> for TlmrError {
    fn from(_: String) -> Self {
        TlmrError::InvalidField
    }
}

fn hasher_to_id(hasher: HasherKind) -> u8 {
    match hasher {
        HasherKind::Blake3 => 1,
        HasherKind::Sha256 | HasherKind::Sha256Ni => 2,
    }
}

fn id_to_hasher(id: u8) -> Result<HasherKind, TlmrError> {
    match id {
        1 => Ok(HasherKind::Blake3),
        2 => Ok(HasherKind::Sha256),
        _ => Err(TlmrError::InvalidField),
    }
}

fn hash_mask(bits: usize) -> u64 {
    if bits >= 64 {
        u64::MAX
    } else {
        (1u64 << bits) - 1
    }
}

fn validate_header(header: &TlmrHeader) {
    assert_eq!(
        header.version, TLMR_FORMAT_VERSION,
        "unsupported format version"
    );
    assert_eq!(
        header.lotus_preset, LOTUS_PRESET_VERSION,
        "unsupported Lotus preset"
    );
    assert!(
        (1..=MAX_BLOCK_SIZE).contains(&header.block_size),
        "block size out of range"
    );
    assert!(
        (1..=header.block_size).contains(&header.last_block_size),
        "last block size out of range"
    );
    assert!(
        (1..=MAX_SEED_LEN).contains(&header.max_seed_len),
        "max seed length out of range"
    );
    assert!(
        (1..=MAX_ARITY).contains(&header.max_arity),
        "max arity out of range"
    );
    assert!(
        (1..=MAX_HASH_BITS).contains(&header.hash_bits),
        "hash bits out of range"
    );
    assert_eq!(
        header.layer_count, 1,
        "only one-layer files are supported in v1"
    );
    assert!(
        header.output_hash & !hash_mask(header.hash_bits) == 0,
        "output hash exceeds hash_bits"
    );
}

/// Encode the active `.tlmr` v1 header.
pub fn encode_tlmr_header(header: &TlmrHeader) -> Vec<u8> {
    validate_header(header);

    let mut out = Vec::with_capacity(TLMR_HEADER_LEN);
    out.extend_from_slice(&TLMR_MAGIC);
    out.push(header.version);
    out.push(TLMR_HEADER_LEN as u8);
    out.push(header.lotus_preset);
    out.push(hasher_to_id(header.hasher));
    out.extend_from_slice(&(header.block_size as u16).to_be_bytes());
    out.extend_from_slice(&(header.last_block_size as u16).to_be_bytes());
    out.push(header.max_seed_len as u8);
    out.push(header.max_arity);
    out.push(header.hash_bits as u8);
    out.push(header.layer_count);
    out.extend_from_slice(&header.original_len.to_be_bytes());
    out.extend_from_slice(&header.payload_len.to_be_bytes());
    out.extend_from_slice(&header.output_hash.to_be_bytes());
    debug_assert_eq!(out.len(), TLMR_HEADER_LEN);
    out
}

/// Decode the active `.tlmr` v1 header from the start of `data`.
pub fn decode_tlmr_header(data: &[u8]) -> Result<TlmrHeader, TlmrError> {
    if data.len() < TLMR_HEADER_LEN {
        return Err(TlmrError::TooShort);
    }

    if data[0..4] != TLMR_MAGIC {
        return Err(TlmrError::InvalidField);
    }

    let version = data[4];
    let header_len = data[5] as usize;
    let lotus_preset = data[6];
    let hasher = id_to_hasher(data[7])?;
    let block_size = u16::from_be_bytes([data[8], data[9]]) as usize;
    let last_block_size = u16::from_be_bytes([data[10], data[11]]) as usize;
    let max_seed_len = data[12] as usize;
    let max_arity = data[13];
    let hash_bits = data[14] as usize;
    let layer_count = data[15];
    let original_len = u64::from_be_bytes(data[16..24].try_into().unwrap());
    let payload_len = u64::from_be_bytes(data[24..32].try_into().unwrap());
    let output_hash = u64::from_be_bytes(data[32..40].try_into().unwrap());

    let header = TlmrHeader {
        version,
        lotus_preset,
        hasher,
        block_size,
        last_block_size,
        max_seed_len,
        max_arity,
        hash_bits,
        layer_count,
        original_len,
        payload_len,
        output_hash,
    };

    if header_len != TLMR_HEADER_LEN
        || version != TLMR_FORMAT_VERSION
        || lotus_preset != LOTUS_PRESET_VERSION
        || !(1..=MAX_BLOCK_SIZE).contains(&block_size)
        || !(1..=block_size).contains(&last_block_size)
        || !(1..=MAX_SEED_LEN).contains(&max_seed_len)
        || !(1..=MAX_ARITY).contains(&max_arity)
        || !(1..=MAX_HASH_BITS).contains(&hash_bits)
        || layer_count != 1
        || output_hash & !hash_mask(hash_bits) != 0
    {
        return Err(TlmrError::InvalidField);
    }

    Ok(header)
}

/// Compute a low-bit truncated digest of the provided bytes using the given expander.
pub fn truncated_hash_bits(data: &[u8], expander: &dyn SeedExpander, bits: usize) -> u64 {
    assert!(
        (1..=MAX_HASH_BITS).contains(&bits),
        "hash bits out of range"
    );
    let digest = expander.digest(data);
    let low = u64::from_be_bytes(digest[24..32].try_into().unwrap());
    low & hash_mask(bits)
}

/// Compute the legacy/default 13-bit truncated digest.
pub fn truncated_hash(data: &[u8], expander: &dyn SeedExpander) -> u16 {
    truncated_hash_bits(data, expander, 13) as u16
}
