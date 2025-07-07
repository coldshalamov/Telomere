use serde::{Deserialize, Serialize};

/// Size of the default bloom filter in bytes (1MB).
const DEFAULT_BYTES: usize = 1_048_576;
/// Size of the optional smaller bloom filter in bytes (256KB).
const SMALL_BYTES: usize = 262_144;

/// Simple bloom filter tuned for SHA-256 digest prefix matching.
#[derive(Clone, Serialize, Deserialize)]
pub struct Bloom {
    bits: Vec<u8>,
}

impl Bloom {
    /// Create a new bloom filter. Pass `true` to use a smaller ~256KB table
    /// instead of the default 1MB one.
    pub fn new(use_small: bool) -> Self {
        let size = if use_small { SMALL_BYTES } else { DEFAULT_BYTES };
        Self { bits: vec![0; size] }
    }

    /// Reconstruct a bloom filter from raw bytes.
    pub fn from_bytes(bytes: Vec<u8>) -> Self {
        Self { bits: bytes }
    }

    /// Export the bloom filter as raw bytes for persistence.
    pub fn to_bytes(&self) -> Vec<u8> {
        self.bits.clone()
    }

    fn set_bit(&mut self, idx: usize) {
        let byte = idx / 8;
        let bit = idx % 8;
        self.bits[byte] |= 1 << bit;
    }

    fn get_bit(&self, idx: usize) -> bool {
        let byte = idx / 8;
        let bit = idx % 8;
        (self.bits[byte] >> bit) & 1 == 1
    }

    fn hashes(prefix: &[u8; 3], len_bits: usize) -> [usize; 4] {
        let x = u32::from_be_bytes([0, prefix[0], prefix[1], prefix[2]]);
        let h1 = x.wrapping_mul(0x5bd1_e995) ^ (x >> 16);
        let h2 = x.rotate_left(13).wrapping_mul(0xc2b2_ae35);
        let h3 = x.wrapping_mul(0x27d4_eb2d);
        let h4 = x.reverse_bits().wrapping_mul(0x1656_67b1);

        [
            (h1 as usize) % len_bits,
            (h2 as usize) % len_bits,
            (h3 as usize) % len_bits,
            (h4 as usize) % len_bits,
        ]
    }

    /// Insert a three byte digest prefix into the filter.
    pub fn insert_prefix(&mut self, prefix: &[u8; 3]) {
        let len_bits = self.bits.len() * 8;
        for idx in Self::hashes(prefix, len_bits) {
            self.set_bit(idx);
        }
    }

    /// Check whether a digest prefix may be contained in the filter.
    pub fn may_contain_prefix(&self, prefix: &[u8; 3]) -> bool {
        let len_bits = self.bits.len() * 8;
        Self::hashes(prefix, len_bits)
            .iter()
            .all(|&idx| self.get_bit(idx))
    }
}

#[cfg(test)]
mod tests {
    use super::Bloom;

    #[test]
    fn prefix_roundtrip() {
        let mut bloom = Bloom::new(false);
        let p = [1, 2, 3];
        assert!(!bloom.may_contain_prefix(&p));
        bloom.insert_prefix(&p);
        assert!(bloom.may_contain_prefix(&p));
    }

    #[test]
    fn serialization_roundtrip() {
        let mut bloom = Bloom::new(true);
        let p = [9, 9, 9];
        bloom.insert_prefix(&p);
        let bytes = bloom.to_bytes();
        let bloom2 = Bloom::from_bytes(bytes);
        assert!(bloom2.may_contain_prefix(&p));
    }
}
