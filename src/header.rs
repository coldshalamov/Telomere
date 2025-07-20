use crate::config::Config;
use crate::TelomereError;

// July‑2025 header prefix table (MSB first)
// 0      -> arity 1
// 100    -> literal passthrough
// 1010   -> arity 3
// 1011   -> arity 4
// 11000  -> arity 5
// 11001  -> arity 6
// 11010  -> arity 7
// 11011  -> arity 8

const MAX_HEADER_BITS: usize = 500;
const MAX_RECURSION_DEPTH: usize = 30;

const LITERAL_BITS: [bool; 3] = [true, false, false];

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
            return Err(TelomereError::HeaderCodec("unexpected EOF".into()));
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

/// Return true if the provided bits start with the literal header marker.
pub fn is_literal_bits(bits: &[bool]) -> bool {
    bits.len() >= 3 && bits[0] && !bits[1] && !bits[2]
}

// Encode an arity value using the VQL header scheme.
fn encode_arity(arity: usize) -> Result<Vec<bool>, TelomereError> {
    if arity < 1 {
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
///
/// # Examples
/// ```
/// use telomere::encode_arity_bits;
/// assert_eq!(encode_arity_bits(1).unwrap(), vec![false]);
/// assert_eq!(encode_arity_bits(3).unwrap(), vec![true, false, true, false]);
/// assert_eq!(encode_arity_bits(4).unwrap(), vec![true, false, true, true]);
/// ```
pub fn encode_arity_bits(arity: usize) -> Result<Vec<bool>, TelomereError> {
    if arity == 2 {
        return Err(TelomereError::HeaderCodec("arity 2 reserved".into()));
    }
    encode_arity(arity)
}

/// Decode an arity field using the July‑2025 windowed VQL scheme.
///
/// Returns `Ok(None)` for the literal marker. Unknown prefixes are reported as
/// `TelomereError::HeaderCodec`.
pub fn decode_arity_bits(reader: &mut BitReader) -> Result<Option<usize>, TelomereError> {
    decode_arity(reader)
}

/// Encode an integer using the EVQL format.
///
/// The value is written as unary length `k` (`k` one bits followed by zero)
/// then exactly `k+1` bytes most significant byte first.
///
/// # Examples
/// ```
/// use telomere::encode_evql_bits;
/// assert_eq!(encode_evql_bits(0), vec![false, false, false, false, false, false, false, false, false]);
/// ```
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
    if bytes > 1 {
        let max = 1usize << ((bytes - 1) * 8);
        if value < max {
            return Err(TelomereError::HeaderCodec("overlong EVQL".into()));
        }
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
        return Err(TelomereError::HeaderCodec("Too deep".into()));
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
                .ok_or_else(|| TelomereError::HeaderCodec("Missing seed expansion".into()))?;
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
/// Literals are encoded as the reserved `100` marker followed by `EVQL(0)`.
pub fn encode_header(header: &Header) -> Result<Vec<u8>, TelomereError> {
    let mut bits = Vec::new();
    match header {
        Header::Arity(a) => bits.extend(encode_arity_bits(*a as usize)?),
        Header::Literal => bits.extend_from_slice(&LITERAL_BITS),
    }
    Ok(pack_bits(&bits))
}

/// Decode a [`Header`] from the provided byte slice.
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
        for arity in 1..=8u8 {
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
