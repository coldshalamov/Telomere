//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
use quickcheck::quickcheck;
use telomere::{find_seed_match, index_to_seed};
use telomere::hasher::{SeedExpander, Sha256Expander};

const MAX_LEN: usize = 3;

fn expand_seed(seed: &[u8], len: usize) -> Vec<u8> {
    let mut out = vec![0u8; len];
    let expander = Sha256Expander;
    expander.expand_into(seed, &mut out);
    out
}

quickcheck! {
    fn roundtrip_matches(seed: Vec<u8>, len: u8) -> bool {
        if seed.is_empty() || seed.len() > MAX_LEN { return true; }
        let span = (len % 16 + 1) as usize;
        let data = expand_seed(&seed, span);
        let expander = Sha256Expander;
        match find_seed_match(&data, MAX_LEN, &expander).ok().flatten() {
            Some(idx) => index_to_seed(idx, MAX_LEN).unwrap() == seed,
            None => false,
        }
    }
}

quickcheck! {
    fn unmatched_returns_none(data: Vec<u8>) -> bool {
        let expander = Sha256Expander;
        if let Ok(Some(idx)) = find_seed_match(&data, MAX_LEN, &expander) {
            let seed = index_to_seed(idx, MAX_LEN).unwrap();
            expand_seed(&seed, data.len()) == data
        } else {
            true
        }
    }
}
