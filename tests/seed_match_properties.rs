use quickcheck::quickcheck;
use telomere::{expand_seed, find_seed_match, index_to_seed};

const MAX_LEN: usize = 3;

quickcheck! {
    fn roundtrip_matches(seed: Vec<u8>, len: u8) -> bool {
        if seed.is_empty() || seed.len() > MAX_LEN { return true; }
        let span = (len % 16 + 1) as usize;
        let data = expand_seed(&seed, span);
        match find_seed_match(&data, MAX_LEN).ok().flatten() {
            Some(idx) => index_to_seed(idx, MAX_LEN).unwrap() == seed,
            None => false,
        }
    }
}

quickcheck! {
    fn unmatched_returns_none(data: Vec<u8>) -> bool {
        if let Ok(Some(idx)) = find_seed_match(&data, MAX_LEN) {
            let seed = index_to_seed(idx, MAX_LEN).unwrap();
            expand_seed(&seed, data.len()) == data
        } else {
            true
        }
    }
}
