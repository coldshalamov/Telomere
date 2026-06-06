//! Lotus header implementation used by the Telomere v1 record format.
//!
//! Bit layout for a compressed (non-literal) v1 record:
//!
//! ```text
//! [canonical arity codeword][Lotus(seed_index, J3D1)]
//! ```
//!
//! For literals:
//!
//! ```text
//! [canonical literal codeword]
//! ```
//!
//! The arity discriminator is the canonical prefix-free alphabet from
//! `docs/FORMAT_CANONICAL.md`. Seed indices are routed through the real
//! `lotus` crate using the confirmed J3D1 preset:
//!
//! | arity | codeword | bits |
//! |------:|---------:|-----:|
//! |     1 |       00 |    2 |
//! |     2 |       01 |    2 |
//! |     3 |      100 |    3 |
//! |     4 |      101 |    3 |
//! |     5 |      110 |    3 |
//! |  0xFF |      111 |    3 |
//!
//! Other Lotus integers keep the shared J3D2 preset unless their format section
//! says otherwise.

use crate::TelomereError;
use lotus::{
    lotus_decode_from_reader, lotus_encode_into_writer, lotus_encoded_bit_len,
    BitReader as LotusBitReader, BitWriter as LotusBitWriter, LotusError,
};

/// Shared Lotus tiered codec preset used for v1/v2 file metadata and v2 records.
pub const LOTUS_J_BITS: usize = 3;
pub const LOTUS_TIERS: usize = 2;

/// Canonical Lotus tiered codec preset used for v1 seed indices.
pub const LOTUS_SEED_INDEX_J_BITS: usize = 3;
pub const LOTUS_SEED_INDEX_TIERS: usize = 1;

/// High level header type used by the compressor.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Header {
    Literal,
    Arity(usize),
}

/// Pack a stream of bits into bytes (MSB first).
pub fn pack_bits(bits: &[bool]) -> Vec<u8> {
    let mut out = Vec::new();
    let mut byte = 0u8;
    let mut used = 0u8;
    for &b in bits {
        byte = (byte << 1) | b as u8;
        used += 1;
        if used == 8 {
            out.push(byte);
            byte = 0;
            used = 0;
        }
    }
    if used > 0 {
        byte <<= 8 - used;
        out.push(byte);
    }
    if out.is_empty() {
        out.push(0);
    }
    out
}

#[derive(Debug, Clone)]
pub struct BitReader<'a> {
    data: &'a [u8],
    pos: usize,
}

impl<'a> BitReader<'a> {
    pub fn from_slice(data: &'a [u8]) -> Self {
        Self { data, pos: 0 }
    }

    pub fn read_bit(&mut self) -> Result<bool, TelomereError> {
        if self.pos / 8 >= self.data.len() {
            return Err(TelomereError::Header("unexpected EOF".into()));
        }
        let bit = ((self.data[self.pos / 8] >> (7 - (self.pos % 8))) & 1) != 0;
        self.pos += 1;
        Ok(bit)
    }

    pub fn bits_read(&self) -> usize {
        self.pos
    }

    pub fn read_bytes(&mut self, n: usize) -> Result<Vec<u8>, TelomereError> {
        let mut out = Vec::new();
        for _ in 0..n {
            let mut byte = 0u8;
            for _ in 0..8 {
                byte = (byte << 1) | self.read_bit()? as u8;
            }
            out.push(byte);
        }
        Ok(out)
    }
}

fn lotus_err(e: LotusError) -> TelomereError {
    TelomereError::Header(format!("lotus codec error: {e}"))
}

fn encode_arity_codeword(
    arity: usize,
    writer: &mut LotusBitWriter,
) -> Result<usize, TelomereError> {
    match arity {
        1 => writer.write_bits(0b00, 2).map_err(lotus_err)?,
        2 => writer.write_bits(0b01, 2).map_err(lotus_err)?,
        3 => writer.write_bits(0b100, 3).map_err(lotus_err)?,
        4 => writer.write_bits(0b101, 3).map_err(lotus_err)?,
        5 => writer.write_bits(0b110, 3).map_err(lotus_err)?,
        0xFF => writer.write_bits(0b111, 3).map_err(lotus_err)?,
        _ => Err(TelomereError::Header(
            "invalid v1 arity (must be 1-5 or 0xFF)".into(),
        ))?,
    }
    arity_codeword_bit_len(arity)
}

fn decode_arity_codeword(reader: &mut LotusBitReader<'_>) -> Result<usize, TelomereError> {
    let selector = reader.read_bits(1).map_err(lotus_err)?;
    if selector == 0 {
        let field = reader.read_bits(1).map_err(lotus_err)?;
        return Ok((field as usize) + 1);
    }

    match reader.read_bits(2).map_err(lotus_err)? {
        0b00 => Ok(3),
        0b01 => Ok(4),
        0b10 => Ok(5),
        0b11 => Ok(0xFF),
        _ => unreachable!("read_bits(2) returns 0..=3"),
    }
}

fn arity_codeword_bit_len(arity: usize) -> Result<usize, TelomereError> {
    match arity {
        1 | 2 => Ok(2),
        3..=5 | 0xFF => Ok(3),
        _ => Err(TelomereError::Header(
            "invalid v1 arity (must be 1-5 or 0xFF)".into(),
        )),
    }
}

// ---------------------------------------------------------------------------
// Header encode/decode

/// Decoded Lotus header structure.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DecodedHeader {
    pub arity: u8,
    pub is_literal: bool,
    pub seed_index: u64,
}

/// Streaming encoder for a v1 record. Writes
///
/// ```text
/// [canonical arity codeword][Lotus seed_index (J3D1)]    // compressed
/// [canonical literal codeword]                            // literal
/// ```
///
/// into the shared writer. Returns the number of bits written.
pub fn encode_v1_record_into_writer(
    arity: usize,
    seed_index: u64,
    writer: &mut LotusBitWriter,
) -> Result<usize, TelomereError> {
    let start = writer.bits_written();
    encode_arity_codeword(arity, writer)?;
    if arity != 0xFF {
        lotus_encode_into_writer(
            seed_index,
            LOTUS_SEED_INDEX_J_BITS,
            LOTUS_SEED_INDEX_TIERS,
            writer,
        )
        .map_err(lotus_err)?;
    }
    Ok(writer.bits_written() - start)
}

/// Streaming decoder for a v1 record. Mirrors [`encode_v1_record_into_writer`].
pub fn decode_v1_record_from_reader(
    reader: &mut LotusBitReader<'_>,
) -> Result<(DecodedHeader, usize), TelomereError> {
    let start = reader.bits_consumed();
    let arity = decode_arity_codeword(reader)?;
    if arity == 0xFF {
        return Ok((
            DecodedHeader {
                arity: 0xFF,
                is_literal: true,
                seed_index: 0,
            },
            reader.bits_consumed() - start,
        ));
    }
    let (seed_index, _) =
        lotus_decode_from_reader(reader, LOTUS_SEED_INDEX_J_BITS, LOTUS_SEED_INDEX_TIERS)
            .map_err(lotus_err)?;
    Ok((
        DecodedHeader {
            arity: arity as u8,
            is_literal: false,
            seed_index,
        },
        reader.bits_consumed() - start,
    ))
}

/// Returns the exact number of bits a v1 record will consume on the wire,
/// without performing the encoding.
pub fn v1_record_bit_len(arity: usize, seed_index: u64) -> Result<usize, TelomereError> {
    let arity_bits = arity_codeword_bit_len(arity)?;
    if arity == 0xFF {
        return Ok(arity_bits);
    }
    let seed_bits =
        lotus_encoded_bit_len(seed_index, LOTUS_SEED_INDEX_J_BITS, LOTUS_SEED_INDEX_TIERS)
            .map_err(lotus_err)?;
    Ok(arity_bits + seed_bits)
}

/// Encode a complete Lotus header including the tiered seed index. Returns the
/// bits in MSB order. This is a wrapper around the streaming form for callers
/// that haven't migrated to `BitWriter` yet.
pub fn encode_lotus_header(arity: usize, seed_index: u64) -> Result<Vec<bool>, TelomereError> {
    let mut writer = LotusBitWriter::new();
    let bit_len = encode_v1_record_into_writer(arity, seed_index, &mut writer)?;
    let bytes = writer.into_bytes();
    let mut out = Vec::with_capacity(bit_len);
    for i in 0..bit_len {
        let byte = bytes[i / 8];
        let bit = (byte >> (7 - (i % 8))) & 1 != 0;
        out.push(bit);
    }
    Ok(out)
}

/// Decode a Lotus header from the provided byte slice. Returns the decoded
/// fields and the number of bits consumed.
pub fn decode_lotus_header(data: &[u8]) -> Result<(DecodedHeader, usize), TelomereError> {
    let mut reader = LotusBitReader::new(data);
    decode_v1_record_from_reader(&mut reader)
}

pub fn decode_header(data: &[u8]) -> Result<(Header, usize), TelomereError> {
    let (decoded, consumed) = decode_lotus_header(data)?;
    let header = if decoded.is_literal {
        Header::Literal
    } else {
        Header::Arity(decoded.arity as usize)
    };
    Ok((header, consumed))
}

pub fn encode_header(header: &Header) -> Result<Vec<u8>, TelomereError> {
    match header {
        Header::Literal => {
            let bits = encode_lotus_header(0xFF, 0)?;
            Ok(pack_bits(&bits))
        }
        _ => Err(TelomereError::Header(
            "encode_header only supports Literal, use encode_lotus_header for Arity".into(),
        )),
    }
}

// ---------------------------------------------------------------------------
// Tests

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn roundtrip_seed_indices() {
        for arity in 1..=5usize {
            for seed_index in [
                0u64, 1, 2, 5, 6, 13, 14, 100, 255, 256, 1000, 65535, 65791, 1_000_000,
            ] {
                let bits = encode_lotus_header(arity, seed_index).unwrap();
                let bytes = pack_bits(&bits);
                let (decoded, consumed_bits) = decode_lotus_header(&bytes).unwrap();
                assert_eq!(
                    decoded.arity as usize, arity,
                    "arity mismatch for seed_index={seed_index}"
                );
                assert!(!decoded.is_literal);
                assert_eq!(
                    decoded.seed_index, seed_index,
                    "seed_index roundtrip failed for arity={arity}"
                );
                assert_eq!(consumed_bits, bits.len(), "bit count mismatch");
            }
        }
    }

    #[test]
    fn roundtrip_literal_header_only() {
        let bits = encode_lotus_header(0xFF, 0).unwrap();
        let bytes = pack_bits(&bits);
        let (decoded, _) = decode_lotus_header(&bytes).unwrap();
        assert!(decoded.is_literal);
        assert_eq!(decoded.arity, 0xFF);
    }

    #[test]
    fn small_indices_are_compact() {
        // arity=1 ("00", 2 bits) + seed_index=0 (J3D1, 5 bits) = 7 bits.
        let bits = encode_lotus_header(1, 0).unwrap();
        assert_eq!(
            bits.len(),
            7,
            "arity=1 seed_index=0 should be canonical arity(2) + J3D1 seed(5)"
        );
    }

    #[test]
    fn literal_marker_bit_len() {
        // Literal escapes are the canonical 111 codeword.
        let bits = encode_lotus_header(0xFF, 0).unwrap();
        assert_eq!(bits.len(), 3, "literal marker is 3 bits");
    }

    #[test]
    fn invalid_arity_encoding() {
        assert!(encode_lotus_header(0, 0).is_err());
        assert!(encode_lotus_header(6, 0).is_err());
        assert!(encode_lotus_header(7, 0).is_err());
    }

    #[test]
    fn decode_short_input_fails() {
        let result = decode_lotus_header(&[]);
        assert!(result.is_err());
    }

    #[test]
    fn v1_record_bit_len_matches_encoder() {
        for arity in [1usize, 2, 3, 4, 5, 0xFF] {
            let seeds: &[u64] = if arity == 0xFF {
                &[0]
            } else {
                &[0, 1, 255, 4096, 65535]
            };
            for &seed_index in seeds {
                let bits = encode_lotus_header(arity, seed_index).unwrap();
                let predicted = v1_record_bit_len(arity, seed_index).unwrap();
                assert_eq!(predicted, bits.len(), "arity={arity} seed={seed_index}");
            }
        }
    }
}
