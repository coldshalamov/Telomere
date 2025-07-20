use crate::{index_to_seed, TelomereError};
use sha2::{Digest, Sha256};

/// Expand `seed` to exactly `len` bytes by repeatedly hashing with SHA-256.
///
/// The expansion starts with the seed bytes themselves. The SHA-256 digest of
/// the current buffer is appended repeatedly until at least `len` bytes have
/// been produced. The resulting vector is truncated to `len`.
pub fn expand_seed(seed: &[u8], len: usize) -> Vec<u8> {
    let mut out = Vec::with_capacity(len);
    let mut cur = seed.to_vec();
    while out.len() < len {
        let digest: [u8; 32] = Sha256::digest(&cur).into();
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
pub fn find_seed_match(slice: &[u8], max_seed_len: usize) -> Result<Option<usize>, TelomereError> {
    let mut limit: u128 = 0;
    for len in 1..=max_seed_len {
        limit += 1u128 << (8 * len);
    }
    for idx in 0..limit {
        let seed = index_to_seed(idx as usize, max_seed_len)?;
        if expand_seed(&seed, slice.len()) == slice {
            return Ok(Some(idx as usize));
        }
    }
    Ok(None)
}
