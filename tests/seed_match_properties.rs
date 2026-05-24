//! Property tests for find_seed_match: the search must find any seed whose
//! expansion matches the target.  Uses Blake3Expander consistently.
use telomere::hasher::{Blake3Expander, SeedExpander};
use telomere::{find_seed_match, index_to_seed};

fn expand(seed: &[u8], len: usize) -> Vec<u8> {
    let mut out = vec![0u8; len];
    Blake3Expander.expand_into(seed, &mut out);
    out
}

#[test]
fn known_seed_found_1byte() {
    // 1-byte seeds (256 total): for each, expand to 1 byte and verify find_seed_match
    // returns the correct index.
    let expander = Blake3Expander;
    for seed_byte in 0u8..=255 {
        let seed = vec![seed_byte];
        let data = expand(&seed, 1);
        let result = find_seed_match(&data, 1, &expander).unwrap();
        if let Some(idx) = result {
            let found_seed = index_to_seed(idx, 1).unwrap();
            let check = expand(&found_seed, 1);
            assert_eq!(check, data, "seed {:?} → found {:?}", seed, found_seed);
        } else {
            panic!("find_seed_match returned None for seed {:?}", seed);
        }
    }
}

#[test]
fn found_seed_always_reconstructs_correctly() {
    // For any data, if find_seed_match returns Some(idx), the reconstructed seed
    // must expand to the original data.
    let expander = Blake3Expander;
    let test_cases: &[&[u8]] = &[&[0x00], &[0xFF], &[0x42], &[0x00, 0x00], &[0x01, 0x02]];
    for &data in test_cases {
        if let Ok(Some(idx)) = find_seed_match(data, 1, &expander) {
            let seed = index_to_seed(idx, 1).unwrap();
            let check = expand(&seed, data.len());
            assert_eq!(check, data);
        }
    }
}

#[test]
fn empty_input_returns_none() {
    assert_eq!(find_seed_match(&[], 1, &Blake3Expander).unwrap(), None);
}

#[test]
fn zero_max_seed_len_returns_none() {
    assert_eq!(find_seed_match(&[0x42], 0, &Blake3Expander).unwrap(), None);
}
