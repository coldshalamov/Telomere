//! Lotus header implementation used by the Telomere codec.
//!
//! The Lotus 4‑Field header uses the following MSB‑first bit layout:
//!
//! ```text
//! [mode][arity][jumpstarter(3)][len_bits][payload]
//! ```
//!
//! * **mode** – selects the width of the arity field.
//! * **arity** – encodes block arity or a literal marker.
//! * **jumpstarter** – a 3‑bit value describing the width of the following
//!   length field.
//! * **len_bits** – a single SWE-literal codeword (zero-based) of length
//!   `L = jumpstarter + 1` bits; codes are contiguous across `L`
//!   (`0..1`, `2..5`, `6..13`, …).
//! * **payload** – present only for non-literals (seed bits). Literal headers
//!   end after the arity field; raw block bits are handled by the caller.
//!
//! All functions operate in MSB‑first order and use [`TelomereError`] for error
//! reporting.

use crate::TelomereError;

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

// Utility for tests and helpers.
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

// ---------------------------------------------------------------------------
// Lotus arity helpers

/// Encode the Lotus arity field returning the mode bit and arity bits.
///
/// `arity` values of `1..=5` are valid non‑literal arities. A special value of
/// `0xFF` encodes a literal passthrough.
pub fn encode_lotus_arity_bits(arity: usize) -> Result<(bool, Vec<bool>), TelomereError> {
    let (mode, bits) = match arity {
        1 => (false, vec![false]),
        2 => (false, vec![true]),
        3 => (true, vec![false, false]),
        4 => (true, vec![false, true]),
        5 => (true, vec![true, false]),
        0xFF => (true, vec![true, true]),
        _ => {
            return Err(TelomereError::Header("invalid Lotus arity".into()));
        }
    };
    Ok((mode, bits))
}

/// Decode the Lotus arity field returning `(arity, is_literal, mode)`.
pub fn decode_lotus_arity_bits(
    reader: &mut BitReader,
) -> Result<(usize, bool, bool), TelomereError> {
    let mode = reader.read_bit()?;
    if !mode {
        let bit = reader.read_bit()?;
        let arity = if bit { 2 } else { 1 };
        Ok((arity, false, mode))
    } else {
        let b1 = reader.read_bit()?;
        let b2 = reader.read_bit()?;
        match (b1, b2) {
            (false, false) => Ok((3, false, mode)),
            (false, true) => Ok((4, false, mode)),
            (true, false) => Ok((5, false, mode)),
            (true, true) => Ok((0xFF, true, mode)),
        }
    }
}

// ---------------------------------------------------------------------------
// Lotus length helpers -------------------------------------------------------

// Encode zero-based SWE literal bits for integer `n` (n >= 0).
// Length sequence: 2 codes of length 1, 4 of length 2, 8 of length 3, ...
fn swe_lit_encode(n: usize) -> Result<Vec<bool>, TelomereError> {
    let mut level: usize = 1;
    let mut total: usize = 0;
    let x = n; // zero-based index
    loop {
        let count = 1usize << level; // 2^level
        if x < total + count {
            let offset = x - total;
            if level > 8 {
                return Err(TelomereError::Header("length header out of range".into()));
            }
            let mut bits = Vec::with_capacity(level);
            for i in (0..level).rev() {
                bits.push(((offset >> i) & 1) != 0);
            }
            return Ok(bits);
        }
        total += count;
        level += 1;
        if level > 8 {
            return Err(TelomereError::Header("length header out of range".into()));
        }
    }
}

// Decode zero-based SWE literal given its bits (we already know L = bits.len()).
fn swe_lit_decode(bits: &[bool]) -> usize {
    let l = bits.len();
    let base = (1usize << l) - 2; // total codes of shorter lengths
    // parse bits as big-endian int
    let mut v = 0usize;
    for &b in bits {
        v = (v << 1) | (b as usize);
    }
    base + v
}

/// Field4 encoder: returns `(jumpstarter, len_bits)`
//
// With `L ∈ [1..=8]`, the zero-based SWE-literal can represent
// `payload_bit_len ∈ [0..=509]`. `510+` is out of range and must error.
pub fn encode_lotus_len_bits(payload_bit_len: usize) -> Result<(u8, Vec<bool>), TelomereError> {
    // Encode as a single zero-based SWE-literal codeword
    let len_bits = swe_lit_encode(payload_bit_len)?;
    let L = len_bits.len(); // 1..=8
    if !(1..=8).contains(&L) {
        return Err(TelomereError::Header("length header out of range".into()));
    }
    let j = (L - 1) as u8; // 3-bit jumpstarter value
    Ok((j, len_bits))
}

pub fn decode_lotus_len_bits(
    reader: &mut BitReader,
) -> Result<(usize, u8, Vec<bool>), TelomereError> {
    // Jumpstarter is exactly 3 bits; L = j + 1 must be in [1..=8].
    // We then read exactly L bits and decode a single zero-based
    // SWE-literal codeword.
    // Read exactly 3 bits of jumpstarter
    let mut j = 0u8;
    for _ in 0..3 {
        j = (j << 1)
            | reader
                .read_bit()
                .map_err(|_| TelomereError::Header("truncated header".into()))? as u8;
    }
    let L = (j as usize) + 1;
    if !(1..=8).contains(&L) {
        return Err(TelomereError::Header("length header out of range".into()));
    }

    // Read exactly L bits → one SWE-literal codeword for payload_bit_len
    let mut bits = Vec::with_capacity(L);
    for _ in 0..L {
        bits.push(
            reader
                .read_bit()
                .map_err(|_| TelomereError::Header("truncated header".into()))?,
        );
    }
    let payload_bit_len = swe_lit_decode(&bits);
    Ok((payload_bit_len, j, bits))
}

// ---------------------------------------------------------------------------
// Header encode/decode

/// Decoded Lotus header structure.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DecodedHeader {
    pub arity: u8,
    pub is_literal: bool,
    pub mode: bool,
    pub jumpstarter: u8,
    pub len_bits: Vec<bool>,
    pub payload_bits: Vec<bool>,
}

/// Encode a complete Lotus header including payload bits.
pub fn encode_lotus_header(
    arity: usize,
    payload_bits: &[bool],
    payload_bit_len: usize,
) -> Result<Vec<bool>, TelomereError> {
    let (mode, arity_bits) = encode_lotus_arity_bits(arity)?;
    let mut out = Vec::new();
    out.push(mode);
    out.extend_from_slice(&arity_bits);
    if arity == 0xFF {
        if payload_bit_len != 0 || !payload_bits.is_empty() {
            return Err(TelomereError::Header(
                "literal must not carry payload".into(),
            ));
        }
        return Ok(out); // header-only literal (3 bits total)
    }
    if payload_bits.len() != payload_bit_len {
        return Err(TelomereError::Header("payload length mismatch".into()));
    }
    let (jumpstarter, len_bits) = encode_lotus_len_bits(payload_bit_len)?;
    for i in (0..3).rev() {
        out.push(((jumpstarter >> i) & 1) != 0);
    }
    out.extend_from_slice(&len_bits);
    out.extend_from_slice(payload_bits);
    Ok(out)
}

/// Decode a Lotus header from the provided byte slice.
pub fn decode_lotus_header(data: &[u8]) -> Result<(DecodedHeader, usize), TelomereError> {
    let mut reader = BitReader::from_slice(data);
    let (arity, is_literal, mode) = decode_lotus_arity_bits(&mut reader)?;
    if is_literal {
        let consumed = reader.bits_read();
        return Ok((
            DecodedHeader {
                arity: 0xFF,
                is_literal: true,
                mode,
                jumpstarter: 0,
                len_bits: Vec::new(),
                payload_bits: Vec::new(),
            },
            consumed,
        ));
    }
    let (len, jumpstarter, len_bits) = decode_lotus_len_bits(&mut reader)?;
    let mut payload_bits = Vec::new();
    for _ in 0..len {
        payload_bits.push(
            reader
                .read_bit()
                .map_err(|_| TelomereError::Header("truncated header".into()))?,
        );
    }
    let consumed = reader.bits_read();
    Ok((
        DecodedHeader {
            arity: arity as u8,
            is_literal: false,
            mode,
            jumpstarter,
            len_bits,
            payload_bits,
        },
        consumed,
    ))
}

// ---------------------------------------------------------------------------
// Tests

#[cfg(test)]
mod tests {
    use super::*;

    fn lcg(state: &mut u32) -> u32 {
        *state = state.wrapping_mul(1664525).wrapping_add(1013904223);
        *state
    }

    #[test]
    fn roundtrip_arities_random_lengths() {
        let mut seed = 0x12345678u32;
        for arity in 1..=5usize {
            for _ in 0..10 {
                let len = (lcg(&mut seed) % 256 + 1) as usize;
                let mut payload = Vec::with_capacity(len);
                for _ in 0..len {
                    payload.push((lcg(&mut seed) & 1) != 0);
                }
                let bits = encode_lotus_header(arity, &payload, len).unwrap();
                let packed = pack_bits(&bits);
                let (dec, used) = decode_lotus_header(&packed).unwrap();
                assert_eq!(dec.arity as usize, arity);
                assert!(!dec.is_literal);
                assert_eq!(dec.payload_bits, payload);
                assert_eq!(dec.len_bits.len(), dec.jumpstarter as usize + 1);
                assert_eq!(used, bits.len());
            }
        }
    }

    #[test]
    fn roundtrip_literal_header_only() {
        let bits = encode_lotus_header(0xFF, &[], 0).unwrap();
        assert_eq!(bits.len(), 3);
        let packed = pack_bits(&bits);
        let (dec, used) = decode_lotus_header(&packed).unwrap();
        assert!(dec.is_literal);
        assert_eq!(dec.arity, 0xFF);
        assert!(dec.payload_bits.is_empty());
        assert_eq!(used, 3);
    }

    #[test]
    fn len_bits_bounds() {
        let (_j0, b0) = encode_lotus_len_bits(0).unwrap();
        assert_eq!(b0.len(), 1);
        let (_j1, b1) = encode_lotus_len_bits(1).unwrap();
        assert_eq!(b1.len(), 1);
        let (_j7a, b127) = encode_lotus_len_bits(127).unwrap();
        assert_eq!(b127.len(), 7);
        let (_j7b, b128) = encode_lotus_len_bits(128).unwrap();
        assert_eq!(b128.len(), 7);
        let (_j7c, b253) = encode_lotus_len_bits(253).unwrap();
        assert_eq!(b253.len(), 7);
        let (_j8a, b254) = encode_lotus_len_bits(254).unwrap();
        assert_eq!(b254.len(), 8);
        let (_j8b, b509) = encode_lotus_len_bits(509).unwrap();
        assert_eq!(b509.len(), 8);
        assert!(encode_lotus_len_bits(510).is_err());
    }

    #[test]
    fn zero_based_len_is_dense() {
        // (length, expected_L)
        let cases = [
            (0, 1),
            (1, 1),
            (2, 2),
            (5, 2),
            (6, 3),
            (13, 3),
            (14, 4),
            (126, 7),
            (127, 7),
            (128, 7),
            (253, 7),
            (254, 8),
            (509, 8),
        ];
        for (len, L) in cases {
            let payload: Vec<bool> = std::iter::repeat(false).take(len).collect();
            let bits = encode_lotus_header(1, &payload, len).unwrap();
            let packed = pack_bits(&bits);
            let (dec, used) = decode_lotus_header(&packed).unwrap();
            assert_eq!(used, bits.len());
            assert!(!dec.is_literal);
            assert_eq!(dec.payload_bits.len(), len);
            assert_eq!(dec.len_bits.len(), L);
            assert_eq!(dec.len_bits.len(), dec.jumpstarter as usize + 1);
        }
        assert!(encode_lotus_len_bits(510).is_err());
    }

    #[test]
    fn literal_rejects_payload() {
        let payload = vec![true, false, true];
        assert!(encode_lotus_header(0xFF, &payload, payload.len()).is_err());
        assert!(encode_lotus_header(0xFF, &[], 1).is_err());
    }

    #[test]
    fn invalid_arity_encoding() {
        assert!(encode_lotus_arity_bits(6).is_err());
    }

    #[test]
    fn decode_short_payload_fails() {
        let payload = vec![true, false, true, false];
        let bits = encode_lotus_header(1, &payload, payload.len()).unwrap();
        let mut packed = pack_bits(&bits);
        packed.pop();
        assert!(decode_lotus_header(&packed).is_err());
    }
}
