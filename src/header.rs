pub fn encode_nibbles_u32(mut value: u32) -> Vec<u8> {
    if value == 0 {
        return vec![0];
    }
    let mut out = Vec::new();
    while value > 0 {
        out.push((value & 0x3F) as u8);
        value >>= 6;
    }
    out
}

pub fn decode_nibbles(nibbles: &[u8]) -> u32 {
    let mut value = 0u32;
    for (i, &n) in nibbles.iter().enumerate() {
        value |= ((n & 0x3F) as u32) << (6 * i);
    }
    value
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn roundtrip_various_values() {
        let values = [0u32, 1, 63, 64, 12345, u32::MAX];
        for &v in &values {
            let encoded = encode_nibbles_u32(v);
            assert!(encoded.iter().all(|&b| b <= 63));
            let decoded = decode_nibbles(&encoded);
            assert_eq!(decoded, v);
        }
    }

    #[test]
    fn decode_empty_slice() {
        assert_eq!(decode_nibbles(&[]), 0);
    }
}
