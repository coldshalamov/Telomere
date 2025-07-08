use std::fmt;

/// Header describing how a compressed region should be interpreted.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Header {
    /// Fully literal bytes with no nesting.
    Flat { seed_index: u8 },
    /// Literal bytes bundled into a flat region of specified arity.
    FlatBundle { seed_index: u8, arity: u8 },
    /// Both flat and nested data included.
    FullNested { seed_index: u8, nested_len: Vec<u8> },
    /// Only nested data present.
    NestedOnly { seed_index: u8, nested_len: Vec<u8> },
}

impl Header {
    /// Decode a `Header` from raw bits.
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
                if bits.len() < 4 || (bits.len() - 4) % 6 != 0 {
                    return Err("invalid nested length bits".to_string());
                }
                let mut nested = Vec::new();
                let mut idx = 4;
                while idx < bits.len() {
                    let end = idx + 6;
                    nested.push(Self::bits_to_val(&bits[idx..end]));
                    idx = end;
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

    fn bits_to_val(slice: &[bool]) -> u8 {
        slice.iter().fold(0u8, |acc, &b| (acc << 1) | b as u8)
    }
}

impl fmt::Display for Header {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Header::Flat { seed_index } => write!(f, "Flat(seed_index={})", seed_index),
            Header::FlatBundle { seed_index, arity } => write!(f, "FlatBundle(seed_index={}, arity={})", seed_index, arity),
            Header::FullNested { seed_index, nested_len } => write!(f, "FullNested(seed_index={}, len_nibbles={})", seed_index, nested_len.len()),
            Header::NestedOnly { seed_index, nested_len } => write!(f, "NestedOnly(seed_index={}, len_nibbles={})", seed_index, nested_len.len()),
        }
    }
}
