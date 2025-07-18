/// Utilities for converting between seeds and enumeration indices.
///
/// The July 2025 Telomere protocol enumerates seeds by byte length in
/// big-endian order. All 1-byte seeds come first, followed by all 2-byte
/// seeds and so on up to `max_seed_len`. Within each length range the seed
/// bytes are interpreted as a big-endian integer. Both directions of the
/// mapping are implemented here.

/// Returns the index of a given seed in the canonical enumeration.
///
/// Seeds are interpreted using their slice length. Multi-byte seeds must
/// therefore be left padded so the slice length matches the intended
/// canonical length. For example, with `max_seed_len = 2` the seed
/// `\x01` (one byte) maps to index `1`, while the two byte seed
/// `\x00\x01` maps to index `257`.
pub fn seed_to_index(seed: &[u8], max_seed_len: usize) -> usize {
    assert!(!seed.is_empty(), "seed cannot be empty");
    assert!(seed.len() <= max_seed_len, "seed longer than max_seed_len");

    let mut index = 0usize;
    for len in 1..seed.len() {
        index += 1usize << (len * 8);
    }

    let mut value = 0usize;
    for &byte in seed {
        value = (value << 8) | byte as usize;
    }

    index + value
}

use crate::TelomereError;

/// Returns the canonical seed for the given enumeration index.
///
/// The enumeration follows the July 2025 Telomere protocol. Indices are
/// assigned in big-endian order, grouped first by seed length. Passing an
/// index outside the valid range for `max_seed_len` returns an error.
pub fn index_to_seed(index: usize, max_seed_len: usize) -> Result<Vec<u8>, TelomereError> {
    let mut remaining = index as u128;
    for len in 1..=max_seed_len {
        let count = 1u128 << (len * 8);
        if remaining < count {
            let mut seed = vec![0u8; len];
            for i in 0..len {
                seed[len - 1 - i] = ((remaining >> (8 * i)) & 0xFF) as u8;
            }
            return Ok(seed);
        }
        remaining -= count;
    }
    Err(TelomereError::Decode("index out of range".into()))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn basic_indices() {
        assert_eq!(seed_to_index(&[0x00], 2), 0);
        assert_eq!(seed_to_index(&[0x01], 2), 1);
        assert_eq!(seed_to_index(&[0x00, 0x01], 2), 256 + 1);
        assert_eq!(seed_to_index(&[0x01, 0x00], 2), 256 + 256);
    }
}
