/// Utilities for deterministic enumeration of variable-length seeds.
///
/// Seeds are enumerated in big-endian order by length. All 1-byte
/// sequences come first, followed by all 2-byte sequences, then 3-byte
/// sequences, and so on. `index_to_seed` reconstructs the canonical seed
/// bytes for a given index.

/// Returns the canonical variable-length seed bytes for the given index.
/// - All 1-byte seeds come first (indices 0..=255)
/// - All 2-byte seeds next (indices 256..=65535+255)
/// - All 3-byte seeds after that, etc.
/// Supports up to `max_seed_len` bytes.
pub fn index_to_seed(idx: usize, max_seed_len: usize) -> Vec<u8> {
    let mut total: u128 = 0;
    let target = idx as u128;
    for len in 1..=max_seed_len {
        let count: u128 = 1u128 << (8 * len);
        if target < total + count {
            let offset = target - total;
            let mut out = vec![0u8; len];
            for i in 0..len {
                out[len - 1 - i] = ((offset >> (8 * i)) & 0xFF) as u8;
            }
            return out;
        }
        total += count;
    }
    panic!("index out of range");
}
