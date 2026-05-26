//! Lotus header implementation used by the Telomere v1 record format.
//!
//! Bit layout for a compressed (non-literal) v1 record:
//!
//! ```text
//! [Lotus(arity_value, J1D1)][Lotus(seed_index, J3D2)]
//! ```
//!
//! For literals:
//!
//! ```text
//! [Lotus(arity_value=5, J1D1)]
//! ```
//!
//! Both the arity discriminator and the seed index payload are now routed
//! through the real `lotus` crate. Arity uses the smallest preset that admits
//! all six code points (J1D1, with values 0..=5):
//!
//! | arity | lotus value | J1D1 bits |
//! |------:|------------:|----------:|
//! |     1 |           0 |         3 |
//! |     2 |           1 |         5 |
//! |     3 |           2 |         5 |
//! |     4 |           3 |         5 |
//! |     5 |           4 |         5 |
//! |  0xFF |           5 |         6 |
//!
//! Seed indices use the unified J3D2 preset shared with v2 records.

use crate::TelomereError;
use lotus::{
    lotus_decode_from_reader, lotus_encode_into_writer, lotus_encoded_bit_len,
    BitReader as LotusBitReader, BitWriter as LotusBitWriter, LotusError,
};

/// Lotus tiered codec preset used for seed indices (shared with v2).
pub const LOTUS_J_BITS: usize = 3;
pub const LOTUS_TIERS: usize = 2;

/// Lotus tiered codec preset used for the arity field. J1D1 is the smallest
/// preset that admits the six code points (arities 1..=5 plus the literal
/// marker). It is deliberately distinct from the J3D2 preset used everywhere
/// else: arity is a 6-value enum, not a general integer, so we pay only the
/// bits the alphabet actually requires.
pub const LOTUS_ARITY_J_BITS: usize = 1;
pub const LOTUS_ARITY_TIERS: usize = 1;

/// Lotus value used to mark a literal record. Arities 1..=5 map to Lotus
/// values 0..=4 in order; the literal escape is value 5.
pub const LOTUS_ARITY_LITERAL_VALUE: u64 = 5;

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

/// Map a Telomere arity value (1..=5 or 0xFF literal) to its Lotus
/// representation.
fn arity_to_lotus_value(arity: usize) -> Result<u64, TelomereError> {
    match arity {
        1 => Ok(0),
        2 => Ok(1),
        3 => Ok(2),
        4 => Ok(3),
        5 => Ok(4),
        0xFF => Ok(LOTUS_ARITY_LITERAL_VALUE),
        _ => Err(TelomereError::Header(
            "invalid Lotus arity (must be 1-5 or 0xFF)".into(),
        )),
    }
}

/// Inverse of [`arity_to_lotus_value`].
fn lotus_value_to_arity(value: u64) -> Result<usize, TelomereError> {
    match value {
        0 => Ok(1),
        1 => Ok(2),
        2 => Ok(3),
        3 => Ok(4),
        4 => Ok(5),
        v if v == LOTUS_ARITY_LITERAL_VALUE => Ok(0xFF),
        _ => Err(TelomereError::Header(
            "invalid Lotus arity value (out of range for J1D1 arity preset)".into(),
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
/// [Lotus arity (J1D1)][Lotus seed_index (J3D2)]    // compressed
/// [Lotus arity=5 marker (J1D1)]                    // literal
/// ```
///
/// into the shared writer. Returns the number of bits written.
pub fn encode_v1_record_into_writer(
    arity: usize,
    seed_index: u64,
    writer: &mut LotusBitWriter,
) -> Result<usize, TelomereError> {
    let lotus_arity = arity_to_lotus_value(arity)?;
    let start = writer.bits_written();
    lotus_encode_into_writer(lotus_arity, LOTUS_ARITY_J_BITS, LOTUS_ARITY_TIERS, writer)
        .map_err(lotus_err)?;
    if lotus_arity != LOTUS_ARITY_LITERAL_VALUE {
        lotus_encode_into_writer(seed_index, LOTUS_J_BITS, LOTUS_TIERS, writer)
            .map_err(lotus_err)?;
    }
    Ok(writer.bits_written() - start)
}

/// Streaming decoder for a v1 record. Mirrors [`encode_v1_record_into_writer`].
pub fn decode_v1_record_from_reader(
    reader: &mut LotusBitReader<'_>,
) -> Result<(DecodedHeader, usize), TelomereError> {
    let start = reader.bits_consumed();
    let (lotus_arity, _) = lotus_decode_from_reader(reader, LOTUS_ARITY_J_BITS, LOTUS_ARITY_TIERS)
        .map_err(lotus_err)?;
    let arity = lotus_value_to_arity(lotus_arity)?;
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
        lotus_decode_from_reader(reader, LOTUS_J_BITS, LOTUS_TIERS).map_err(lotus_err)?;
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
    let lotus_arity = arity_to_lotus_value(arity)?;
    let arity_bits = lotus_encoded_bit_len(lotus_arity, LOTUS_ARITY_J_BITS, LOTUS_ARITY_TIERS)
        .map_err(lotus_err)?;
    if lotus_arity == LOTUS_ARITY_LITERAL_VALUE {
        return Ok(arity_bits);
    }
    let seed_bits =
        lotus_encoded_bit_len(seed_index, LOTUS_J_BITS, LOTUS_TIERS).map_err(lotus_err)?;
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
        // arity=1 (J1D1 value=0, 3 bits) + seed_index=0 (J3D2, 6 bits) = 9 bits.
        let bits = encode_lotus_header(1, 0).unwrap();
        assert_eq!(
            bits.len(),
            9,
            "arity=1 seed_index=0 should be J1D1 arity(3) + J3D2 seed(6)"
        );
    }

    #[test]
    fn literal_marker_bit_len() {
        // Literal escapes are the largest J1D1 value (=5), encoded in 6 bits.
        let bits = encode_lotus_header(0xFF, 0).unwrap();
        assert_eq!(bits.len(), 6, "literal marker is 6 bits in J1D1");
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
