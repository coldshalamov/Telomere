use thiserror::Error;

/// Simple header representation used by higher level APIs.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Header {
    pub seed_index: usize,
    pub arity: usize,
}

impl Header {
    /// Returns true if this header represents a literal passthrough region.
    pub fn is_literal(&self) -> bool {
        matches!(self.arity, 37 | 38 | 39 | 40)
    }
}

/// Errors that can occur while decoding a header
#[derive(Debug, Error, PartialEq, Eq)]
pub enum HeaderError {
    #[error("unexpected end of input")]
    UnexpectedEof,
    #[error("invalid arity code")]
    InvalidArity,
}

/// Encode a compressed header using Inchworm's VQL scheme.
/// Returns a big-endian bit packed byte vector.
pub fn encode_header(seed_index: usize, arity: usize) -> Vec<u8> {
    assert!(arity >= 1, "arity must be at least 1");
    let mut bits = Vec::new();
    encode_vql(seed_index, &mut bits);
    bits.extend(encode_arity_bits(arity));
    pack_bits(&bits)
}

/// Decode a compressed header from a bitstream.
/// Returns the seed index, arity and the number of bits consumed.
pub fn decode_header(input: &[u8]) -> Result<(usize, usize, usize), HeaderError> {
    let mut pos = 0usize;
    let seed = decode_vql(input, &mut pos)?;
    let arity = decode_arity_stream(input, &mut pos)?;
    Ok((seed, arity, pos))
}

// ---- Internal utilities ----

fn encode_vql(value: usize, out: &mut Vec<bool>) {
    let mut width = 1usize;
    let mut n = 0usize;
    while value >= (1usize << width) {
        width <<= 1;
        n += 1;
    }
    for _ in 0..n {
        out.push(true);
    }
    out.push(false);
    for i in (0..width).rev() {
        out.push(((value >> i) & 1) != 0);
    }
}

fn decode_vql(input: &[u8], pos: &mut usize) -> Result<usize, HeaderError> {
    let mut n = 0usize;
    loop {
        match get_bit(input, *pos) {
            Some(true) => {
                n += 1;
                *pos += 1;
            }
            Some(false) => {
                *pos += 1;
                break;
            }
            None => return Err(HeaderError::UnexpectedEof),
        }
    }
    let width = 1usize << n;
    let mut value = 0usize;
    for _ in 0..width {
        match get_bit(input, *pos) {
            Some(bit) => {
                value = (value << 1) | (bit as usize);
                *pos += 1;
            }
            None => return Err(HeaderError::UnexpectedEof),
        }
    }
    Ok(value)
}

fn get_bit(input: &[u8], pos: usize) -> Option<bool> {
    if pos / 8 >= input.len() {
        None
    } else {
        Some(((input[pos / 8] >> (7 - (pos % 8))) & 1) != 0)
    }
}

fn pack_bits(bits: &[bool]) -> Vec<u8> {
    let mut out = Vec::new();
    let mut byte = 0u8;
    let mut used = 0u8;
    for &b in bits {
        byte = (byte << 1) | (b as u8);
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

/// Encode an arity into dynamic toggle bits (unpacked).
pub fn encode_arity(arity: usize) -> Vec<u8> {
    pack_bits(&encode_arity_bits(arity))
}

/// Decode an arity from a packed bitstream starting at bit 0.
/// Returns the decoded arity and number of bits consumed.
pub fn decode_arity(bits: &[u8]) -> Result<(usize, usize), HeaderError> {
    let mut pos = 0usize;
    let val = decode_arity_stream(bits, &mut pos)?;
    Ok((val, pos))
}

// ---- arity helpers ----

fn encode_arity_bits(arity: usize) -> Vec<bool> {
    assert!(arity >= 1, "arity must be at least 1");
    let mut level = 1usize;
    let mut start = 1usize;
    loop {
        let window = 3usize.pow((level - 1) as u32);
        if arity < start + window {
            break;
        }
        start += window;
        level += 1;
    }
    let index = arity - start;
    let width = if level == 1 { 0 } else { 1usize << (level - 1) };
    let mut out = Vec::new();
    for _ in 0..(level - 1) {
        out.push(true);
    }
    out.push(false);
    for i in (0..width).rev() {
        out.push(((index >> i) & 1) != 0);
    }
    out
}

fn decode_arity_stream(input: &[u8], pos: &mut usize) -> Result<usize, HeaderError> {
    let mut ones = 0usize;
    loop {
        match get_bit(input, *pos) {
            Some(true) => {
                ones += 1;
                *pos += 1;
            }
            Some(false) => {
                *pos += 1;
                break;
            }
            None => return Err(HeaderError::UnexpectedEof),
        }
    }
    let level = ones + 1;
    let width = if level == 1 { 0 } else { 1usize << (level - 1) };
    let mut index = 0usize;
    for _ in 0..width {
        match get_bit(input, *pos) {
            Some(bit) => {
                index = (index << 1) | (bit as usize);
                *pos += 1;
            }
            None => return Err(HeaderError::UnexpectedEof),
        }
    }
    let mut start = 1usize;
    for i in 1..level {
        start += 3usize.pow((i - 1) as u32);
    }
    let window = 3usize.pow((level - 1) as u32);
    if index >= window {
        return Err(HeaderError::InvalidArity);
    }
    Ok(start + index)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn vql_small() {
        let enc = encode_header(0, 2);
        let (seed, arity, bits) = decode_header(&enc).unwrap();
        assert_eq!(seed, 0);
        assert_eq!(arity, 2);
        assert_eq!(bits, 6);
        assert_eq!(enc.len(), 1);
    }

    #[test]
    fn vql_mid() {
        let enc = encode_header(3, 6);
        let (seed, arity, bits) = decode_header(&enc).unwrap();
        assert_eq!(seed, 3);
        assert_eq!(arity, 6);
        assert_eq!(bits, 11);
        assert_eq!(enc.len(), (bits + 7) / 8);
    }

    #[test]
    fn vql_large() {
        let enc = encode_header(300, 200);
        let (seed, arity, bits) = decode_header(&enc).unwrap();
        assert_eq!(seed, 300);
        assert_eq!(arity, 200);
        assert_eq!(bits, 59);
        assert_eq!(enc.len(), (bits + 7) / 8);
    }

    #[test]
    fn arity_roundtrip() {
        for &a in &[1usize, 4, 13, 40, 100] {
            let enc = encode_arity(a);
            assert_eq!(decode_arity(&enc).unwrap().0, a);
        }
    }
}
