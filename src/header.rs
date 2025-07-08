use std::fmt;

/// Header describing how a compressed region should be interpreted.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Header {
    /// Flat seed with no nested length information
    Flat { seed_index: u8 },
    /// Flat seed that represents a bundle of regions
    FlatBundle { seed_index: u8, arity: u8 },
    /// Full seed followed by nested length
    FullNested { seed_index: u8, nested_len: Vec<u8> },
    /// Nested length only (seed is all zeros)
    NestedOnly { seed_index: u8, nested_len: Vec<u8> },
}

impl Header {
    pub fn from_bits(bits: &[bool]) -> Result<Self, String> {
        if bits.len() < 4 {
            return Err("header too short".to_string());
        }
        let kind = Self::bits_to_val(&bits[0..2]);
        let seed_index = Self::bits_to_val(&bits[2..4]);

        match kind {
            0 => {
                if bits.len() != 4 {
                    return Err("flat header length mismatch".to_string());
                }
                Ok(Header::Flat { seed_index })
            }
            1 => {
                if bits.len() != 6 {
                    return Err("flat bundle header length mismatch".to_string());
                }
                let arity_code = Self::bits_to_val(&bits[4..6]);
                if arity_code > 2 {
                    return Err("invalid arity".to_string());
                }
                Ok(Header::FlatBundle { seed_index, arity: arity_code + 2 })
            }
            2 | 3 => {
                if (bits.len() - 4) % 6 != 0 {
                    return Err("invalid nested length bits".to_string());
                }
                let mut nested = Vec::new();
                let mut idx = 4;
                while idx + 6 <= bits.len() {
                    nested.push(Self::bits_to_val(&bits[idx..idx + 6]));
                    idx += 6;
                }
                if kind == 2 {
                    Ok(Header::FullNested { seed_index, nested_len: nested })
                } else {
                    Ok(Header::NestedOnly { seed_index, nested_len: nested })
                }
            }
            _ => Err("invalid header type".to_string()),
        }
    }

    pub fn to_bits(&self) -> Vec<bool> {
        let mut bits = Vec::new();
        match self {
            Header::Flat { seed_index } => {
                bits.extend(Self::int_to_bits(0b00, 2));
                bits.extend(Self::int_to_bits(*seed_index as u32, 2));
            }
            Header::FlatBundle { seed_index, arity } => {
                bits.extend(Self::int_to_bits(0b01, 2));
                bits.extend(Self::int_to_bits(*seed_index as u32, 2));
                bits.extend(Self::int_to_bits((*arity - 2) as u32, 2));
            }
            Header::FullNested { seed_index, nested_len } |
            Header::NestedOnly { seed_index, nested_len } => {
                let toggle = if matches!(self, Header::FullNested { .. }) { 0b10 } else { 0b11 };
                bits.extend(Self::int_to_bits(toggle, 2));
                bits.extend(Self::int_to_bits(*seed_index as u32, 2));
                for &n in nested_len {
                    bits.extend(Self::int_to_bits(n as u32, 6));
                }
            }
        }
        bits
    }

    pub fn bit_length(&self) -> usize {
        match self {
            Header::Flat { .. } => 4,
            Header::FlatBundle { .. } => 6,
            Header::FullNested { nested_len, .. } |
            Header::NestedOnly { nested_len, .. } => 4 + 6 * nested_len.len(),
        }
    }

    pub fn encode_nibbles_u32(mut value: u32) -> Vec<u8> {
        if value == 0 {
            return vec![0];
        }
        let mut out = Vec::new();
        while value > 0 {
            out.push((value & 0x3F) as u8);
            value >>= 6;
        }
        out.reverse();
        out
    }

    pub fn decode_nibbles(nibbles: &[u8]) -> u32 {
        let mut value = 0u32;
        for (i, &n) in nibbles.iter().rev().enumerate() {
            value |= (n as u32) << (6 * (nibbles.len() - 1 - i));
        }
        value
    }

    fn int_to_bits(value: u32, width: usize) -> Vec<bool> {
        (0..width)
            .map(|i| ((value >> (width - 1 - i)) & 1) != 0)
            .collect()
    }

    fn bits_to_val(slice: &[bool]) -> u8 {
        slice.iter().fold(0u8, |acc, &b| (acc << 1) | b as u8)
    }
}

impl fmt::Display for Header {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Header::Flat { seed_index } => write!(f, "Flat(seed_index={})", seed_index),
            Header::FlatBundle { seed_index, arity } => {
                write!(f, "FlatBundle(seed_index={}, arity={})", seed_index, arity)
            }
            Header::FullNested { seed_index, nested_len } => {
                write!(f, "FullNested(seed_index={}, len_nibbles={})", seed_index, nested_len.len())
            }
            Header::NestedOnly { seed_index, nested_len } => {
                write!(f, "NestedOnly(seed_index={}, len_nibbles={})", seed_index, nested_len.len())
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn roundtrip_various_lengths() {
        let values = [0u32, 1, 62, 63, 64, 1000, 16383, 0xFFFFF];
        for &val in &values {
            let encoded = Header::encode_nibbles_u32(val);
            let decoded = Header::decode_nibbles(&encoded);
            assert_eq!(decoded, val);
        }
    }

    #[test]
    fn bit_roundtrip_matches_length() {
        let headers = [
            Header::Flat { seed_index: 2 },
            Header::FlatBundle { seed_index: 1, arity: 3 },
            Header::FullNested { seed_index: 0, nested_len: vec![1, 2, 3] },
            Header::NestedOnly { seed_index: 3, nested_len: vec![63, 0, 1] },
        ];
        for h in &headers {
            let bits = h.to_bits();
            assert_eq!(bits.len(), h.bit_length());
        }
    }
}
