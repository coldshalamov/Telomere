use quickcheck::quickcheck;
use telomere::{index_to_seed, seed_to_index};

const MAX_LEN: usize = 3;

quickcheck! {
    fn index_roundtrip(idx: u64) -> bool {
        // Calculate the total number of valid indices for MAX_LEN
        let total: u128 = (1u128 << 8) + (1u128 << 16) + (1u128 << 24);
        let idx = (idx as u128 % total) as usize;
        let seed = index_to_seed(idx, MAX_LEN).unwrap();
        seed_to_index(&seed, MAX_LEN) == idx
    }
}

quickcheck! {
    fn seed_roundtrip(seed: Vec<u8>) -> bool {
        if seed.is_empty() || seed.len() > MAX_LEN {
            return true; // vacuously true for out-of-bounds seeds
        }
        let idx = seed_to_index(&seed, MAX_LEN);
        index_to_seed(idx, MAX_LEN).unwrap() == seed
    }
}

#[test]
fn edge_cases() {
    // First and last index for each seed length up to MAX_LEN
    let edges = [
        0usize,                               // first 1-byte
        255usize,                             // last 1-byte
        256usize,                             // first 2-byte
        256 + 65535usize,                     // last 2-byte
        256 + 65536usize,                     // first 3-byte
        256 + 65536usize + 16777216usize - 1, // last 3-byte
    ];
    for &idx in &edges {
        let seed = index_to_seed(idx, MAX_LEN).unwrap();
        assert_eq!(seed_to_index(&seed, MAX_LEN), idx);
        assert_eq!(index_to_seed(seed_to_index(&seed, MAX_LEN), MAX_LEN).unwrap(), seed);
    }
}

#[test]
#[should_panic]
fn empty_seed_panics() {
    let _ = seed_to_index(&[], MAX_LEN);
}

#[test]
fn index_overflow_errors() {
    let total = (1usize << 8) + (1usize << 16) + (1usize << 24);
    assert!(index_to_seed(total, MAX_LEN).is_err());
}
