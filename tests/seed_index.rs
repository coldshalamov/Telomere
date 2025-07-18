use quickcheck::quickcheck;
use telomere::{index_to_seed, seed_to_index};

const MAX_LEN: usize = 3;

quickcheck! {
    fn index_roundtrip(idx: u64) -> bool {
        let total: u128 = (1u128 << 8) + (1u128 << 16) + (1u128 << 24);
        let idx = (idx as u128 % total) as usize;
        let seed = index_to_seed(idx, MAX_LEN);
        seed_to_index(&seed, MAX_LEN) == idx
    }
}

quickcheck! {
    fn seed_roundtrip(seed: Vec<u8>) -> bool {
        if seed.is_empty() || seed.len() > MAX_LEN {
            return true;
        }
        let idx = seed_to_index(&seed, MAX_LEN);
        index_to_seed(idx, MAX_LEN) == seed
    }
}

#[test]
fn edge_cases() {
    // first and last index for each seed length
    let edges = [
        0usize,                               // first 1-byte
        255usize,                             // last 1-byte
        256usize,                             // first 2-byte
        256 + 65535usize,                     // last 2-byte
        256 + 65536usize,                     // first 3-byte
        256 + 65536usize + 16777216usize - 1, // last 3-byte
    ];
    for &idx in &edges {
        let seed = index_to_seed(idx, MAX_LEN);
        assert_eq!(seed_to_index(&seed, MAX_LEN), idx);
    }
}

#[test]
#[should_panic]
fn empty_seed_panics() {
    let _ = seed_to_index(&[], MAX_LEN);
}

#[test]
#[should_panic]
fn index_overflow_panics() {
    let total = (1usize << 8) + (1usize << 16) + (1usize << 24);
    let _ = index_to_seed(total, MAX_LEN);
}
