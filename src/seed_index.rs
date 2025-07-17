/// Utilities for converting between seeds and enumeration indices.
///
/// The canonical enumeration orders seeds by byte length. All 1-byte seeds
/// come first, followed by all 2-byte seeds and so on up to
/// `max_seed_len`. Within each length range seeds are interpreted as
/// big-endian numbers. This module provides a helper to convert a padded
/// seed into its index.

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
