pub struct Bloom {
    bits: Vec<u8>,
    hashes: u8,
}

impl Bloom {
    pub fn new(size_bytes: usize, hashes: u8) -> Self {
        Bloom {
            bits: vec![0; size_bytes],
            hashes,
        }
    }

    fn hash(&self, mut key: u64, i: u8) -> usize {
        key = key.wrapping_add((i as u64).wrapping_mul(0x9E3779B97F4A7C15));
        (key as usize) % (self.bits.len() * 8)
    }

    pub fn insert(&mut self, key: u64) {
        for i in 0..self.hashes {
            let bit = self.hash(key, i);
            let byte = bit / 8;
            let mask = 1u8 << (bit % 8);
            self.bits[byte] |= mask;
        }
    }

    pub fn contains(&self, key: u64) -> bool {
        for i in 0..self.hashes {
            let bit = self.hash(key, i);
            let byte = bit / 8;
            let mask = 1u8 << (bit % 8);
            if self.bits[byte] & mask == 0 {
                return false;
            }
        }
        true
    }
}
