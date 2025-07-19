use telomere::{seed_to_index, index_to_seed};

const MAX_LEN: usize = 3;

#[test]
fn test_index_to_seed_roundtrip() {
    // Converting an index to a seed and back should yield the same index
    for i in 0..500 {
        let seed = index_to_seed(i, MAX_LEN).unwrap();
        let index = seed_to_index(&seed, MAX_LEN);
        assert_eq!(index, i);
    }
}

#[test]
fn test_monotonic_index_generation() {
    // Sequential indices should map back to increasing indices
    let mut previous_index = 0usize;
    for i in 1..1000 {
        let seed = index_to_seed(i, MAX_LEN).unwrap();
        let index = seed_to_index(&seed, MAX_LEN);
        assert!(index > previous_index);
        previous_index = index;
    }
}
