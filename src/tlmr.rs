use sha2::{Digest, Sha256};
use thiserror::Error;

/// Representation of the Telomere 3-byte file header.
///
/// Bits are packed big endian starting with the most significant bit.
/// Field layout (bit indices 0..23):
/// - bits 0..=2   : protocol version
/// - bits 3..=6   : block size code (stored value + 1 = actual block size)
/// - bits 7..=10  : last block size code (stored value + 1 = bytes in final block)
/// - bits 11..=23 : lowest 13 bits of the SHA-256 of the decompressed output
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TlmrHeader {
    pub version: u8,
    pub block_size: usize,
    pub last_block_size: usize,
    pub output_hash: u16,
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

/// Encode the Telomere header with protocol version 0.
pub fn encode_tlmr_header(header: &TlmrHeader) -> [u8; 3] {
    assert!(header.version <= 7, "version out of range");
    assert!(header.block_size >= 1 && header.block_size <= 16, "block size out of range");
    assert!(header.last_block_size >= 1 && header.last_block_size <= 16, "last block size out of range");
    let mut val: u32 = 0;
    val |= (header.version as u32 & 0x7) << 21;
    val |= ((header.block_size as u32 - 1) & 0xF) << 17;
    val |= ((header.last_block_size as u32 - 1) & 0xF) << 13;
    val |= (header.output_hash as u32) & 0x1FFF;
    [
        ((val >> 16) & 0xFF) as u8,
        ((val >> 8) & 0xFF) as u8,
        (val & 0xFF) as u8,
    ]
}

/// Decode a Telomere header from the first three bytes of the input.
pub fn decode_tlmr_header(data: &[u8]) -> Result<TlmrHeader, TlmrError> {
    if data.len() < 3 {
        return Err(TlmrError::TooShort);
    }
    let val = ((data[0] as u32) << 16) | ((data[1] as u32) << 8) | data[2] as u32;
    let version = ((val >> 21) & 0x7) as u8;
    let bs_code = ((val >> 17) & 0xF) as u8;
    let lbs_code = ((val >> 13) & 0xF) as u8;
    let hash = (val & 0x1FFF) as u16;
    let block_size = bs_code as usize + 1;
    let last_block_size = lbs_code as usize + 1;
    if version > 7 || block_size == 0 || block_size > 16 || last_block_size == 0 || last_block_size > 16 {
        return Err(TlmrError::InvalidField);
    }
    Ok(TlmrHeader {
        version,
        block_size,
        last_block_size,
        output_hash: hash,
    })
}

/// Compute the 13-bit truncated SHA-256 of the provided bytes.
pub fn truncated_hash(data: &[u8]) -> u16 {
    let digest = Sha256::digest(data);
    let arr: [u8; 32] = digest.into();
    let low = ((arr[30] as u16) << 8) | arr[31] as u16;
    low & 0x1FFF
}
