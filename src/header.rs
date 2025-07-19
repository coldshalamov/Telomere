use crate::TelomereError;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Header {
    /// Normal span carrying an arity value.
    Arity(u8),
    /// Literal passthrough block.
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
    if out.is_empty() {
        out.push(0);
    }
    out
}

fn encode_vql(value: usize) -> Vec<bool> {
    assert!(value >= 2);
    let mut idx = value - 2;
    let mut sentinels = idx / 3;
    let code = idx % 3;
    let mut bits = Vec::new();
    for _ in 0..sentinels {
        bits.extend_from_slice(&[true, true]);
    }
    match code {
        0 => bits.extend_from_slice(&[false, false]),
        1 => bits.extend_from_slice(&[false, true]),
        2 => bits.extend_from_slice(&[true, false]),
        _ => unreachable!(),
    }
    bits
}

fn decode_vql(reader: &mut BitReader) -> Result<usize, TelomereError> {
    let mut sentinels = 0usize;
    loop {
        let b1 = reader.read_bit()?;
        let b2 = reader.read_bit()?;
        match (b1, b2) {
            (true, true) => sentinels += 1,
            (false, false) => return Ok(sentinels * 3 + 0 + 2),
            (false, true) => return Ok(sentinels * 3 + 1 + 2),
            (true, false) => return Ok(sentinels * 3 + 2 + 2),
        }
    }
}

pub fn encode_header(header: &Header) -> Result<Vec<u8>, TelomereError> {
    let mut bits = Vec::new();
    match header {
        Header::Literal => bits.extend_from_slice(&[true, false, false]),
        Header::Arity(n) => {
            let n = *n as usize;
            if n == 1 {
                bits.push(false);
            } else {
                bits.push(true);
                bits.extend(encode_vql(n + 1));
            }
        }
    }
    Ok(pack_bits(&bits))
}

pub fn decode_header(data: &[u8]) -> Result<(Header, usize), TelomereError> {
    let mut r = BitReader::from_slice(data);
    let toggle = r.read_bit()?;
    if !toggle {
        return Ok((Header::Arity(1), r.bits_read()));
    }
    let val = decode_vql(&mut r)?;
    if val == 2 {
        return Ok((Header::Literal, r.bits_read()));
    }
    let arity = (val - 1) as u8;
    Ok((Header::Arity(arity), r.bits_read()))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn bits_to_bytes(bits: &[bool]) -> Vec<u8> {
        pack_bits(bits)
    }

    #[test]
    fn roundtrip_cases() {
        let cases = [
            (Header::Arity(1), vec![false]),
            (Header::Arity(2), vec![true, false, true]),
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
    }
}
