use crate::TelomereError;
use std::collections::HashMap;

/// Span descriptor consisting of a block count (arity) and seed index.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Span {
    pub arity: usize,
    pub seed_index: usize,
}

/// Single header encoding for compressed spans.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Header {
    /// Seeded span with a given arity.
    Standard { seed_index: usize, arity: usize },
    /// Literal passthrough for one block.
    Literal,
    /// Literal passthrough for the final tail.
    LiteralLast,
}

/// Configuration for recursive decoding.
#[derive(Debug, Clone, Default)]
pub struct Config {
    pub block_size: usize,
    /// Mapping from seed indices to generated bitstreams used during decoding.
    pub seed_expansions: HashMap<usize, Vec<u8>>,
}

/// Bit level reader used by the decoder tests.
#[derive(Debug, Clone)]
pub struct BitReader<'a> {
    data: &'a [u8],
    pos: usize,
}

impl<'a> BitReader<'a> {
    /// Create a reader from a byte slice.
    pub fn from_slice(data: &'a [u8]) -> Self {
        Self { data, pos: 0 }
    }

    /// Read a single bit returning an error on EOF.
    pub fn read_bit(&mut self) -> Result<bool, TelomereError> {
        if self.pos / 8 >= self.data.len() {
            return Err(TelomereError::Decode("unexpected EOF".into()));
        }
        let bit = ((self.data[self.pos / 8] >> (7 - (self.pos % 8))) & 1) != 0;
        self.pos += 1;
        Ok(bit)
    }

    /// Read an arbitrary number of bits.
    pub fn read_bits(&mut self, bits: usize) -> Result<u64, TelomereError> {
        let mut v = 0u64;
        for _ in 0..bits {
            v = (v << 1) | self.read_bit()? as u64;
        }
        Ok(v)
    }

    /// Read a byte slice from the underlying bits.
    pub fn read_bytes(&mut self, count: usize) -> Result<Vec<u8>, TelomereError> {
        let mut out = Vec::with_capacity(count);
        for _ in 0..count {
            out.push(self.read_bits(8)? as u8);
        }
        Ok(out)
    }

    /// Number of bits consumed so far.
    pub fn bits_read(&self) -> usize {
        self.pos
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
    if out.is_empty() { out.push(0); }
    out
}

fn encode_evql_bits(mut value: usize) -> Vec<bool> {
    let mut width = 1usize;
    let mut n = 0usize;
    while value >= (1usize << width) {
        width <<= 1;
        n += 1;
    }
    let mut bits = vec![true; n];
    bits.push(false);
    for i in (0..width).rev() {
        bits.push(((value >> i) & 1) != 0);
    }
    bits
}

fn decode_evql(reader: &mut BitReader) -> Result<usize, TelomereError> {
    let mut n = 0usize;
    loop {
        if reader.read_bit()? { n += 1; } else { break; }
    }
    let width = 1usize << n;
    let mut val = 0usize;
    for _ in 0..width {
        val = (val << 1) | reader.read_bit()? as usize;
    }
    Ok(val)
}

/// Encode a span header using the July 2025 bit layout.
pub fn encode_header(header: &Header) -> Result<Vec<u8>, TelomereError> {
    let mut bits = Vec::new();
    match header {
        Header::Standard { seed_index, arity } => {
            match *arity {
                1 => bits.push(false),
                3..=9 => {
                    bits.extend_from_slice(&[true, true]);
                    let val = arity - 3;
                    for i in (0..3).rev() {
                        bits.push(((val >> i) & 1) != 0);
                    }
                }
                10 => bits.extend_from_slice(&[true, true, true, true, true, false]),
                _ => return Err(TelomereError::Other(format!("unsupported arity {arity}"))),
            }
            bits.extend(encode_evql_bits(*seed_index));
        }
        Header::Literal => bits.extend_from_slice(&[true, false]),
        Header::LiteralLast => bits.extend_from_slice(&[true, true, true, true, true, true]),
    }
    Ok(pack_bits(&bits))
}

/// Decode a span header returning the header and bits consumed.
pub fn decode_header(data: &[u8]) -> Result<(Header, usize), TelomereError> {
    let mut r = BitReader::from_slice(data);
    let first = r.read_bit()?;
    if !first {
        let seed = decode_evql(&mut r)?;
        return Ok((Header::Standard { seed_index: seed, arity: 1 }, r.bits_read()));
    }
    let second = r.read_bit()?;
    if !second {
        return Ok((Header::Literal, r.bits_read()));
    }
    let b1 = r.read_bit()?;
    let b2 = r.read_bit()?;
    let b3 = r.read_bit()?;
    let val = (b1 as usize) << 2 | (b2 as usize) << 1 | (b3 as usize);
    if val <= 6 {
        let arity = val + 3;
        let seed = decode_evql(&mut r)?;
        return Ok((Header::Standard { seed_index: seed, arity }, r.bits_read()));
    }
    let b4 = r.read_bit()?;
    if !b4 {
        let seed = decode_evql(&mut r)?;
        return Ok((Header::Standard { seed_index: seed, arity: 10 }, r.bits_read()));
    }
    Ok((Header::LiteralLast, r.bits_read()))
}

fn generate_bits(config: &Config, seed_idx: usize) -> Result<Vec<u8>, TelomereError> {
    config
        .seed_expansions
        .get(&seed_idx)
        .cloned()
        .ok_or_else(|| TelomereError::Other(format!("missing seed expansion for {seed_idx}")))
}

fn decode_span(reader: &mut BitReader, config: &Config) -> Result<Vec<u8>, TelomereError> {
    let first = reader.read_bit()?;
    let arity = if !first {
        1
    } else if !reader.read_bit()? {
        2
    } else {
        let b1 = reader.read_bit()?;
        let b2 = reader.read_bit()?;
        let b3 = reader.read_bit()?;
        let val = (b1 as usize) << 2 | (b2 as usize) << 1 | (b3 as usize);
        if val <= 6 {
            val + 3
        } else if !reader.read_bit()? {
            10
        } else {
            return Err(TelomereError::Other("literal last not allowed".into()));
        }
    };
    if arity == 2 {
        return reader.read_bytes(config.block_size);
    }
    let seed_idx = decode_evql(reader)?;
    let child_bits = generate_bits(config, seed_idx)?;
    let mut child_reader = BitReader::from_slice(&child_bits);
    let mut out = Vec::new();
    for _ in 0..arity {
        out.extend(decode_span(&mut child_reader, config)?);
    }
    Ok(out)
}

/// Decode a stream of blocks described by nested headers.
pub fn decode(reader: &mut BitReader, config: &Config) -> Result<Vec<u8>, TelomereError> {
    let block_count = decode_evql(reader)?;
    let mut result = Vec::new();
    for _ in 0..block_count {
        result.extend(decode_span(reader, config)?);
    }
    Ok(result)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn roundtrip_header() {
        let cases = [
            Header::Standard { seed_index: 0, arity: 1 },
            Header::Standard { seed_index: 3, arity: 3 },
            Header::Literal,
            Header::LiteralLast,
        ];
        for h in cases {
            let enc = encode_header(&h).unwrap();
            let (dec, _) = decode_header(&enc).unwrap();
            assert_eq!(dec, h);
        }
    }
}

