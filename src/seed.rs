//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
use crate::{index_to_seed, TelomereError};
use sha2::Digest;

/// Return a 32-byte digest of `input` using either SHA-256 or a simple XXHash-like algorithm.
pub fn digest32(input: &[u8], use_xxhash: bool) -> [u8; 32] {
    if use_xxhash {
        let mut h: u64 = 0xcbf29ce484222325;
        for &b in input {
            h ^= b as u64;
            h = h.wrapping_mul(0x100000001b3);
        }
        let mut out = [0u8; 32];
        for i in 0..4 {
            out[i * 8..(i + 1) * 8].copy_from_slice(&h.to_le_bytes());
            h = h
                .rotate_left(13)
                .wrapping_add(i as u64 + 0x9e3779b97f4a7c15);
        }
        out
    } else {
        sha2::Sha256::digest(input).into()
    }
}

/// Expand `seed` to exactly `len` bytes by repeatedly hashing with SHA-256.
///
/// The expansion starts with the seed bytes themselves. The SHA-256 digest of
/// the current buffer is appended repeatedly until at least `len` bytes have
/// been produced. The resulting vector is truncated to `len`.
pub fn expand_seed(seed: &[u8], len: usize, use_xxhash: bool) -> Vec<u8> {
    let mut out = Vec::with_capacity(len);
    let mut cur = seed.to_vec();
    while out.len() < len {
        let digest = digest32(&cur, use_xxhash);
        out.extend_from_slice(&digest);
        cur = digest.to_vec();
    }
    out.truncate(len);
    out
}

/// Search for a seed index whose expansion of length `slice.len()` equals
/// `slice`.
///
/// Seeds are enumerated according to [`index_to_seed`] up to
/// `max_seed_len`. The first matching index is returned if any. Matching is
/// deterministic and greedy over enumeration order.
pub fn find_seed_match(
    slice: &[u8],
    max_seed_len: usize,
    use_xxhash: bool,
) -> Result<Option<usize>, TelomereError> {
    let mut limit: u128 = 0;
    for len in 1..=max_seed_len {
        limit += 1u128 << (8 * len);
    }
    for idx in 0..limit {
        if idx % 10000 == 0 {
             // eprintln!("Search idx: {}", idx);
        }
        let seed = index_to_seed(idx as usize, max_seed_len)?;
        if expand_seed(&seed, slice.len(), use_xxhash) == slice {
            return Ok(Some(idx as usize));
        }
    }
    Ok(None)
}
