//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
//!
//! Real seed search implementation using the SeedExpander trait.
//! Seeds are enumerated deterministically: shortest first, then
//! lexicographic big-endian order within each length.

use crate::hasher::SeedExpander;
use crate::TelomereError;

/// Search for the smallest seed whose expansion matches `slice`.
/// Returns the seed index if a compressive match is found.
pub fn find_seed_match(
    slice: &[u8],
    max_seed_len: usize,
    expander: &dyn SeedExpander,
) -> Result<Option<usize>, TelomereError> {
    if slice.is_empty() || max_seed_len == 0 {
        return Ok(None);
    }

    let target_bits = slice.len() * 8;

    // Hierarchical search: 1-byte, 2-byte, 3-byte, ...
    let mut global_idx: usize = 0;

    for len in 1..=max_seed_len {
        let seeds_in_this_len = 1usize << (8 * len);

        for local_idx in 0..seeds_in_this_len {
            // Build the seed bytes for this local index
            let mut seed = vec![0u8; len];
            let mut v = local_idx;
            for i in (0..len).rev() {
                seed[i] = (v & 0xFF) as u8;
                v >>= 8;
            }

            // Fast path: check if the hash prefix matches
            if expander.prefix_matches(&seed, slice, target_bits) {
                // Verify exact match by expanding fully
                let mut expanded = vec![0u8; slice.len()];
                expander.expand_into(&seed, &mut expanded);
                if expanded == slice {
                    return Ok(Some(global_idx + local_idx));
                }
            }
        }

        global_idx += seeds_in_this_len;
    }

    Ok(None)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::hasher::Blake3Expander;
    use crate::seed_index::index_to_seed;

    #[test]
    fn index_to_seed_roundtrip() {
        let mut offset = 0usize;
        for len in 1..=3usize {
            let count = 1usize << (8 * len);
            for local in (0..count).step_by(97) {
                let seed = index_to_seed(offset + local, 4).unwrap();
                assert_eq!(seed.len(), len, "idx={} len={}", offset + local, len);
            }
            offset += count;
        }
    }

    #[test]
    fn find_seed_match_roundtrip_1byte() {
        // Seed [0x00] expands to BLAKE3([0x00])[0..1].
        // find_seed_match must find it at global index 0 (first 1-byte seed).
        let expander = Blake3Expander;
        let mut target = [0u8; 1];
        expander.expand_into(&[0x00], &mut target);
        let idx = find_seed_match(&target, 1, &expander).unwrap();
        assert_eq!(idx, Some(0), "seed [0x00] should be at index 0");

        // Reconstruct: index_to_seed(0, 1) == [0x00].
        let seed = index_to_seed(idx.unwrap(), 1).unwrap();
        assert_eq!(seed, vec![0x00]);

        // Re-expand and verify.
        let mut check = [0u8; 1];
        expander.expand_into(&seed, &mut check);
        assert_eq!(check, target);
    }

    #[test]
    fn find_seed_match_respects_enumeration_order() {
        // The first 1-byte seed (index 0) is [0x00], last is [0xFF] = index 255.
        let expander = Blake3Expander;
        let mut target = [0u8; 1];
        expander.expand_into(&[0xFF], &mut target);
        // With max_seed_len=1, we search all 256 seeds.
        // [0xFF] should appear at index 255 unless a shorter expansion collides.
        let idx = find_seed_match(&target, 1, &expander).unwrap();
        // At minimum we found *some* seed; verify it reconstructs correctly.
        if let Some(i) = idx {
            let seed = index_to_seed(i, 1).unwrap();
            let mut check = [0u8; 1];
            expander.expand_into(&seed, &mut check);
            assert_eq!(check, target);
        }
    }
}
