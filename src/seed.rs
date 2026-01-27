//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
use crate::{index_to_seed, TelomereError};
use crate::hasher::SeedExpander;

/// Search for a seed index whose expansion of length `slice.len()` equals
/// `slice`.
///
/// Seeds are enumerated according to [`index_to_seed`] up to
/// `max_seed_len`. The first matching index is returned if any. Matching is
/// deterministic and greedy over enumeration order.
pub fn find_seed_match(
    slice: &[u8],
    max_seed_len: usize,
    expander: &dyn SeedExpander,
) -> Result<Option<usize>, TelomereError> {
    let mut limit: u128 = 0;
    for len in 1..=max_seed_len {
        limit += 1u128 << (8 * len);
    }
    
    // Safety check for huge limits
    if limit > usize::MAX as u128 {
        // Just cap at usize max for iteration
        limit = usize::MAX as u128;
    }

    // Optimization: avoid allocating "expanded" buffer for every check if prefix_matches is sufficient.
    // prefix_matches checks if expansion *starts with* slice.
    // Since we are looking for exact match of length `slice.len()`, `prefix_matches` checks exactly that.
    
    for idx in 0..limit {
        let seed = index_to_seed(idx as usize, max_seed_len)?;
        
        // We only care if the expansion matches 'slice' exactly.
        // The slice length is the target length.
        // prefix_matches(seed, slice, slice.len() * 8) checks if expansion prefix matches slice.
        if expander.prefix_matches(&seed, slice, slice.len() * 8) {
            return Ok(Some(idx as usize));
        }
    }
    Ok(None)
}
