use crate::config::Config;
use crate::TelomereError;

const MAX_HEADER_BITS: usize = 500;

const MAX_RECURSION_DEPTH: usize = 30;

/// Header describing either a literal block or the arity for a seeded span.
///
/// Two canonical forms exist:
/// - [`Header::Literal`] encoded as the three bit pattern `100`.
///   The literal must be followed by `EVQL(0)` when serialized.
/// - [`Header::Arity(n)`] for `n >= 1` using the windowed VQL scheme
///   described in [`encode_arity_bits`].
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
            return Err(TelomereError::Decode("unexpected EOF".into()));
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
/// Encode `arity` using the July‑2025 windowed VQL header scheme.
///
/// * `0` encodes arity 1.
/// * `100` encodes arity 2 and indicates a literal passthrough.
/// * Larger arities encode the binary offset `arity - (2^w + 1)` using `w`
///   bits after a unary size prefix (`w-1` ones then a zero).  The special
///   case `w = 1` uses the prefix `01`.
fn encode_arity(arity: usize) -> Result<Vec<bool>, TelomereError> {
    if arity == 0 {
        return Err(TelomereError::HeaderCodec("arity must be positive".into()));
    }
    if arity == 1 {
        return Ok(vec![false]);
    }
    if arity == 2 {
        return Ok(vec![true, false, false]);
    }

    let mut bits = vec![true];
    let w = usize::BITS as usize - 1 - (arity - 1).leading_zeros() as usize;
    let prefix: Vec<bool> = if w == 1 {
        vec![false, true]
    } else {
        let mut p = vec![true; w - 1];
        p.push(false);
        p
    };
    bits.extend(prefix);
    let offset = arity - ((1usize << w) + 1);
    for i in (0..w).rev() {
        bits.push(((offset >> i) & 1) != 0);
    }
    Ok(bits)
}

// Decode an arity value according to the VQL header scheme.
//
// Returns `Ok(None)` when the literal marker (`1 0 0`) is encountered.
// The numeric value `2` is invalid and treated as a decode error.
fn decode_arity(reader: &mut BitReader) -> Result<Option<usize>, TelomereError> {
    let mut bits_read = 0usize;
    let first = reader.read_bit()?;
    bits_read += 1;
    if !first {
        return Ok(Some(1));
    }

    let second = reader.read_bit()?;
    bits_read += 1;
    if !second {
        let third = reader.read_bit()?;
        bits_read += 1;
        if !third {
            return Ok(None); // literal marker
        }
        // prefix 01 -> width 1
        let val = reader.read_bit()? as usize;
        bits_read += 1;
        return Ok(Some(3 + val));
    }

    let mut ones = 1usize;
    loop {
        if bits_read >= MAX_HEADER_BITS {
            return Err(TelomereError::HeaderCodec("arity prefix too long".into()));
        }
        let bit = reader.read_bit()?;
        bits_read += 1;
        if bit {
            ones += 1;
        } else {
            break;
        }
    }
    let width = ones + 1;
    if width >= MAX_HEADER_BITS {
        return Err(TelomereError::HeaderCodec("arity width too large".into()));
    }
    let mut value = 0usize;
    for _ in 0..width {
        if bits_read >= MAX_HEADER_BITS {
            return Err(TelomereError::HeaderCodec("arity value truncated".into()));
        }
        let b = reader.read_bit()?;
        bits_read += 1;
        value = (value << 1) | b as usize;
    }
    Ok(Some((1usize << width) + 1 + value))
}

/// Encode an arity value to raw bits without packing.
pub fn encode_arity_bits(arity: usize) -> Result<Vec<bool>, TelomereError> {
    encode_arity(arity)
}

/// Decode an arity field using the July‑2025 windowed VQL scheme.
///
/// Returns `Ok(None)` for the `100` literal marker. Errors if the bitstream
/// does not terminate within [`MAX_HEADER_BITS`].
pub fn decode_arity_bits(reader: &mut BitReader) -> Result<Option<usize>, TelomereError> {
    decode_arity(reader)
}

/// Encode a usize using EVQL and return the raw bits.
pub fn encode_evql_bits(value: usize) -> Vec<bool> {
    let mut bytes = 1usize;
    while value >= (1usize << (bytes * 8)) {
        bytes += 1;
    }
    let mut bits = Vec::new();
    for _ in 0..bytes - 1 {
        bits.push(true);
    }
    bits.push(false);
    for i in (0..bytes).rev() {
        let shift = i * 8;
        let byte = ((value >> shift) & 0xFF) as u8;
        for j in (0..8).rev() {
            bits.push(((byte >> j) & 1) != 0);
        }
    }
    bits
}

/// Decode an EVQL value from the provided bit reader.
pub fn decode_evql_bits(reader: &mut BitReader) -> Result<usize, TelomereError> {
    let mut ones = 0usize;
    while reader.read_bit()? {
        ones += 1;
        if ones > MAX_HEADER_BITS {
            return Err(TelomereError::HeaderCodec("EVQL prefix too long".into()));
        }
    }
    let bytes = ones + 1;
    if bytes * 8 > MAX_HEADER_BITS {
        return Err(TelomereError::HeaderCodec("EVQL width too large".into()));
    }
    let mut value = 0usize;
    for _ in 0..bytes {
        let mut byte = 0u8;
        for _ in 0..8 {
            let bit = reader.read_bit()?;
            byte = (byte << 1) | bit as u8;
        }
        value = (value << 8) | byte as usize;
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
        return Err(TelomereError::Decode("Too deep".into()));
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
                .ok_or_else(|| TelomereError::Other("Missing seed expansion".into()))?;
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

/// Encode a [`Header`] to a byte vector.
///
/// Literals are encoded as the arity‑2 marker followed by `EVQL(0)`.
pub fn encode_header(header: &Header) -> Result<Vec<u8>, TelomereError> {
    let mut bits = Vec::new();
    match header {
        Header::Arity(a) => bits.extend(encode_arity(*a as usize)?),
        Header::Literal => bits.extend(encode_arity(2)?),
    }
    Ok(pack_bits(&bits))
}

/// Decode a [`Header`] from the provided byte slice.
///
/// Returns the header and number of bits consumed.
pub fn decode_header(data: &[u8]) -> Result<(Header, usize), TelomereError> {
    let mut r = BitReader::from_slice(data);
    match decode_arity_bits(&mut r)? {
        None => Ok((Header::Literal, r.bits_read())),
        Some(a) => Ok((Header::Arity(a as u8), r.bits_read())),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn roundtrip_cases() {
        for arity in 1..=6u8 {
            let header = if arity == 2 {
                Header::Literal
            } else {
                Header::Arity(arity)
            };
            let enc = encode_header(&header).unwrap();
            let (dec, _) = decode_header(&enc).unwrap();
            assert_eq!(dec, header);
        }
    }
}
