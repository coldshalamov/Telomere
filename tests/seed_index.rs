use quickcheck::quickcheck;
use telomere::{index_to_seed, seed_to_index};

quickcheck! {
    fn seed_to_index_then_back(idx: u32) -> bool {
        // limit to 24 bits to keep seeds small
        let idx = (idx % 0x0100_0000) as u64;
        let seed = index_to_seed(idx as usize, 4);
        seed_to_index(&seed, 4) == idx as usize
    }
}

quickcheck! {
    fn index_to_seed_then_back(idx: u32) -> bool {
        let idx = (idx % 0x0100_0000) as u64;
        let seed = index_to_seed(idx as usize, 4);
        index_to_seed(seed_to_index(&seed, 4), 4) == seed
    }
}

#[test]
fn edge_cases() {
    let indices: &[u64] = &[0, 0xFF, 0xFFFF, 0xFF_FFFF];
    for &idx in indices {
        let seed = index_to_seed(idx as usize, 4);
        assert_eq!(seed_to_index(&seed, 4), idx as usize);
        assert_eq!(index_to_seed(seed_to_index(&seed, 4), 4), seed);
    }
}
