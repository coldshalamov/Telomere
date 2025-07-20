use crate::config::Config;
use crate::TelomereError;

const MAX_RECURSION_DEPTH: usize = 30;

/// Header describing either a literal block or the arity for a seeded span.
///
/// Only two forms exist:
/// - [`Header::Literal`] encoded as the fixed three bit pattern `1 0 0`.
/// - [`Header::Arity(n)`] for `n != 2` encoded with the variable length VQL
///   scheme followed by the EVQL encoded seed index.
///
/// The value `2` is reserved for the literal marker and must never be emitted
/// or accepted as a compressed span.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Header {
    /// Span with the provided arity.
    Arity(u8),
    /// Literal passthrough for one block.
    Literal,
}

/// Bit level reader used for header decoding in tests and helpers.
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

    pub fn bits_read(&self) -> usize {
        self.pos
    }

    /// Advance the reader to the next byte boundary.
    pub fn align_byte(&mut self) {
        if self.pos % 8 != 0 {
            let skip = 8 - (self.pos % 8);
            self.pos += skip;
        }
    }
}

fn pack_bits(bits: &[bool]) -> Vec<u8> {
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

// Encode an arity value using the VQL header scheme.
//
// `arity` must be positive and not equal to `2`. The value `2` is
// reserved for the literal marker and will result in an error.
fn encode_arity(arity: usize) -> Result<Vec<bool>, TelomereError> {
    if arity < 1 {
        return Err(TelomereError::Header("arity must be positive".into()));
    }
    if arity == 2 {
        return Err(TelomereError::Header(
            "arity=2 is reserved for the literal marker".into(),
        ));
    }
    let mut bits = Vec::new();
    if arity == 1 {
        bits.push(false);
        return Ok(bits);
    }
    bits.push(true);
    let mut index = arity - 1;
    let digit = index % 3;
    let reps = index / 3;
    for _ in 0..reps {
        bits.extend_from_slice(&[true, true]);
    }
    match digit {
        0 => bits.extend_from_slice(&[false, false]),
        1 => bits.extend_from_slice(&[false, true]),
        2 => bits.extend_from_slice(&[true, false]),
        _ => unreachable!(),
    }
    Ok(bits)
}

// Decode an arity value according to the VQL header scheme.
//
// Returns `Ok(None)` when the literal marker (`1 0 0`) is encountered.
// The numeric value `2` is invalid and treated as a decode error.
fn decode_arity(reader: &mut BitReader) -> Result<Option<usize>, TelomereError> {
    let first = reader.read_bit()?;
    if !first {
        return Ok(Some(1));
    }
    let mut index = 0usize;
    loop {
        let b1 = reader.read_bit()?;
        let b2 = reader.read_bit()?;
        match (b1, b2) {
            (true, true) => index += 3,
            (false, false) => {
                if index == 0 {
                    return Ok(None); // Literal marker
                } else {
                    return Ok(Some(index + 1));
                }
            }
            (false, true) => {
                if index == 0 {
                    return Err(TelomereError::Header(
                        "arity=2 is reserved for the literal marker".into(),
                    ));
                }
                return Ok(Some(index + 2));
            }
            (true, false) => return Ok(Some(index + 3)),
        }
    }
}

/// Encode an arity value to raw bits without packing.
pub fn encode_arity_bits(arity: usize) -> Result<Vec<bool>, TelomereError> {
    encode_arity(arity)
}

/// Encode a usize using EVQL and return the raw bits.
pub fn encode_evql_bits(value: usize) -> Vec<bool> {
    let mut width = 1usize;
    let mut n = 0usize;
    while width < usize::BITS as usize && value >= (1usize << width) {
        width <<= 1;
        n += 1;
    }
    let mut bits = Vec::new();
    for _ in 0..n {
        bits.push(true);
    }
    bits.push(false);
    for i in (0..width).rev() {
        bits.push(((value >> i) & 1) != 0);
    }
    bits
}

/// Decode an EVQL value from the provided bit reader.
pub fn decode_evql_bits(reader: &mut BitReader) -> Result<usize, TelomereError> {
    let mut n = 0usize;
    loop {
        let bit = reader.read_bit()?;
        if bit {
            n += 1;
        } else {
            break;
        }
    }
    let width = 1usize << n;
    let mut value = 0usize;
    for _ in 0..width {
        let b = reader.read_bit()?;
        value = (value << 1) | b as usize;
    }
    Ok(value)
}

/// Decode a span of bytes from a bitstream using seeded arity headers.
fn decode_span_rec(
    reader: &mut BitReader,
    config: &Config,
    depth: usize,
) -> Result<Vec<u8>, TelomereError> {
    if depth >= MAX_RECURSION_DEPTH {
        return Err(TelomereError::Header("Too deep".into()));
    }
    match decode_arity(reader)? {
        None => {
            // Literal block
            reader.align_byte();
            reader.read_bytes(config.block_size)
        }
        Some(arity) => {
            let seed_idx = decode_evql_bits(reader)?;
            reader.align_byte();
            let child_bits = config
                .seed_expansions
                .get(&seed_idx)
                .ok_or_else(|| TelomereError::Header("Missing seed expansion".into()))?;
            let mut child_reader = BitReader::from_slice(child_bits);
            let mut out = Vec::new();
            for _ in 0..arity {
                out.extend(decode_span_rec(&mut child_reader, config, depth + 1)?);
            }
            Ok(out)
        }
    }
}

/// Decode a span of bytes from a bitstream using seeded arity headers.
pub fn decode_span(reader: &mut BitReader, config: &Config) -> Result<Vec<u8>, TelomereError> {
    decode_span_rec(reader, config, 0)
}

pub fn encode_header(header: &Header) -> Result<Vec<u8>, TelomereError> {
    let mut bits = Vec::new();
    match header {
        Header::Arity(a) => bits.extend(encode_arity(*a as usize)?),
        Header::Literal => bits.extend_from_slice(&[true, false, false]), // "100" literal marker
    }
    Ok(pack_bits(&bits))
}

pub fn decode_header(data: &[u8]) -> Result<(Header, usize), TelomereError> {
    let mut r = BitReader::from_slice(data);
    let first = r.read_bit()?;
    if !first {
        return Ok((Header::Arity(1), r.bits_read()));
    }
    let mut index = 0usize;
    loop {
        let b1 = r.read_bit()?;
        let b2 = r.read_bit()?;
        match (b1, b2) {
            (true, true) => index += 3,
            (false, false) => {
                if index == 0 {
                    return Ok((Header::Literal, r.bits_read()));
                } else {
                    return Ok((Header::Arity((index + 1) as u8), r.bits_read()));
                }
            }
            (false, true) => {
                if index == 0 {
                    return Err(TelomereError::Header(
                        "arity=2 is reserved for the literal marker".into(),
                    ));
                }
                return Ok((Header::Arity((index + 2) as u8), r.bits_read()));
            }
            (true, false) => return Ok((Header::Arity((index + 3) as u8), r.bits_read())),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn bits_to_bytes(bits: &[bool]) -> Vec<u8> {
        super::pack_bits(bits)
    }

    #[test]
    fn roundtrip_cases() {
        let cases = [
            (Header::Arity(1), vec![false]),
            (Header::Arity(3), vec![true, true, false]),
            (Header::Arity(4), vec![true, true, true, false, false]),
            (Header::Literal, vec![true, false, false]),
        ];
        for (h, bits) in cases {
            let enc = encode_header(&h).unwrap();
            assert_eq!(enc, bits_to_bytes(&bits));
            let (dec, _) = decode_header(&enc).unwrap();
            assert_eq!(dec, h);
        }

        // Reserved arity value should fail to encode
        assert!(encode_header(&Header::Arity(2)).is_err());
        let reserved = bits_to_bytes(&[true, false, true]);
        assert!(decode_header(&reserved).is_err());
    }
}
