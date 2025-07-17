pub fn index_to_seed(mut idx: u64) -> Vec<u8> {
    if idx == 0 {
        return vec![0];
    }
    let mut bytes = Vec::new();
    while idx > 0 {
        bytes.push((idx & 0xFF) as u8);
        idx >>= 8;
    }
    bytes.reverse();
    bytes
}

pub fn seed_to_index(seed: &[u8]) -> u64 {
    let mut idx = 0u64;
    for &b in seed {
        idx = (idx << 8) | b as u64;
    }
    idx
}
