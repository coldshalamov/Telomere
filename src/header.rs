#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Header {
    /// Flat seed with no nested length information
    Flat { seed_idx: u8 },
    /// Flat seed that represents a bundle of regions
    FlatBundle { seed_idx: u8, arity: u8 },
    /// Full seed followed by nested length
    FullNested { seed_idx: u8, nested_len: u32 },
    /// Nested length only (seed is all zeros)
    NestedOnly { seed_idx: u8, nested_len: u32 },
}

impl Header {
    fn int_to_bits(value: u32, width: usize) -> Vec<bool> {
        (0..width)
            .map(|i| ((value >> (width - 1 - i)) & 1) != 0)
            .collect()
    }

    /// Encode a u32 into big-endian 6-bit nibbles
    pub fn encode_nibbles_u32(mut n: u32) -> Vec<u8> {
        if n == 0 {
            return vec![0];
        }
        let mut out = Vec::new();
        while n > 0 {
            out.push((n & 0x3F) as u8);
            n >>= 6;
        }
        out.reverse();
        out
    }

    pub fn to_bits(&self) -> Vec<bool> {
        let mut bits = Vec::new();
        match *self {
            Header::Flat { seed_idx } => {
                bits.extend(Self::int_to_bits(0b00, 2));
                bits.extend(Self::int_to_bits(seed_idx as u32, 2));
            }
            Header::FlatBundle { seed_idx, arity } => {
                bits.extend(Self::int_to_bits(0b01, 2));
                bits.extend(Self::int_to_bits(seed_idx as u32, 2));
                bits.extend(Self::int_to_bits((arity - 2) as u32, 2));
            }
            Header::FullNested { seed_idx, nested_len } => {
                bits.extend(Self::int_to_bits(0b10, 2));
                bits.extend(Self::int_to_bits(seed_idx as u32, 2));
                for n in Self::encode_nibbles_u32(nested_len) {
                    bits.extend(Self::int_to_bits(n as u32, 6));
                }
            }
            Header::NestedOnly { seed_idx, nested_len } => {
                bits.extend(Self::int_to_bits(0b11, 2));
                bits.extend(Self::int_to_bits(seed_idx as u32, 2));
                for n in Self::encode_nibbles_u32(nested_len) {
                    bits.extend(Self::int_to_bits(n as u32, 6));
                }
            }
        }
        bits
    }

    pub fn bit_length(&self) -> usize {
        match *self {
            Header::Flat { .. } => 4,
            Header::FlatBundle { .. } => 6,
            Header::FullNested { nested_len, .. } | Header::NestedOnly { nested_len, .. } => {
                4 + 6 * Self::encode_nibbles_u32(nested_len).len()
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn roundtrip_lengths() {
        let nested_vals = [0u32, 1, 62, 63, 64, 65, 1000, 0xFFFF];
        for &val in &nested_vals {
            let full = Header::FullNested { seed_idx: 0, nested_len: val };
            assert_eq!(full.to_bits().len(), full.bit_length());
            let nested = Header::NestedOnly { seed_idx: 1, nested_len: val };
            assert_eq!(nested.to_bits().len(), nested.bit_length());
        }
        let flat = Header::Flat { seed_idx: 2 };
        assert_eq!(flat.to_bits().len(), flat.bit_length());
        let bundle = Header::FlatBundle { seed_idx: 3, arity: 4 };
        assert_eq!(bundle.to_bits().len(), bundle.bit_length());
    }
}
