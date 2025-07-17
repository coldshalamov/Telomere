use quickcheck::quickcheck;
use telomere::{index_to_seed, seed_to_index};

quickcheck! {
    fn seed_to_index_then_back(idx: u32) -> bool {
        // limit to 24 bits to keep seeds small
        let idx = (idx % 0x0100_0000) as u64;
        let seed = index_to_seed(idx);
        seed_to_index(&seed) == idx
    }
}

quickcheck! {
    fn index_to_seed_then_back(idx: u32) -> bool {
        let idx = (idx % 0x0100_0000) as u64;
        let seed = index_to_seed(idx);
        index_to_seed(seed_to_index(&seed)) == seed
    }
}

#[test]
fn edge_cases() {
    let indices: &[u64] = &[0, 0xFF, 0xFFFF, 0xFF_FFFF];
    for &idx in indices {
        let seed = index_to_seed(idx);
        assert_eq!(seed_to_index(&seed), idx);
        assert_eq!(index_to_seed(seed_to_index(&seed)), seed);
    }
}
