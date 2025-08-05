//! SWE seed decoding helpers
use crate::TelomereError;

fn decode_swe_literal(bits: &str) -> Result<usize, TelomereError> {
    let n = bits.len();
    let base = (1usize << n) - 1;
    let suffix = if bits.is_empty() {
        0
    } else {
        usize::from_str_radix(bits, 2)
            .map_err(|_| TelomereError::Header("invalid SWE literal".into()))?
    };
    Ok(base + suffix)
}

/// Decode a SWE seed string into a payload index and arity.
pub fn decode_seed(code: &str) -> Result<(usize, usize), TelomereError> {
    let parts: Vec<&str> = code.split(':').collect();
    if parts.is_empty() {
        return Err(TelomereError::Header("invalid seed".into()));
    }
    let arity = match parts[0] {
        "00" => 1usize,
        "01" => 2usize,
        "100" => 3usize,
        "101" => 4usize,
        "110" => 5usize,
        "111" => 0usize,
        _ => return Err(TelomereError::Header("invalid arity".into())),
    };
    if parts.len() >= 4 && parts[1] == "00" && parts[2] == "0" && parts[3] == "0" {
        return Ok((0, arity));
    }
    if parts.len() < 5 {
        return Err(TelomereError::Header("truncated seed".into()));
    }
    let payload = decode_swe_literal(parts[4])?;
    Ok((payload - 1, arity))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn decode_zero() {
        assert_eq!(decode_seed("00:00:0:0").unwrap(), (0, 1));
    }
}
