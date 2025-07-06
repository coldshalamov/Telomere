use std::collections::HashMap;
use sha2::{Digest, Sha256};

pub struct ShaCache {
    capacity: usize,
    map: HashMap<Vec<u8>, [u8; 32]>,
    order: Vec<Vec<u8>>, // simple queue for LRU
}

impl ShaCache {
    pub fn new(max_bytes: usize) -> Self {
        let entry_size = 40; // approx seed+digest
        let capacity = max_bytes / entry_size;
        ShaCache {
            capacity,
            map: HashMap::new(),
            order: Vec::new(),
        }
    }

    fn touch(&mut self, key: &[u8]) {
        if let Some(pos) = self.order.iter().position(|k| k.as_slice() == key) {
            let key_vec = self.order.remove(pos);
            self.order.push(key_vec);
        }
    }

    fn insert(&mut self, key: Vec<u8>, value: [u8; 32]) {
        if self.map.len() >= self.capacity {
            if let Some(old) = self.order.first() {
                self.map.remove(old);
            }
            if !self.order.is_empty() {
                self.order.remove(0);
            }
        }
        self.order.push(key.clone());
        self.map.insert(key, value);
    }

    pub fn get_or_compute(&mut self, seed: &[u8]) -> [u8; 32] {
        if let Some(value) = self.map.get(seed) {
            self.touch(seed);
            *value
        } else {
            let digest = Sha256::digest(seed);
            let arr: [u8; 32] = digest.into();
            self.insert(seed.to_vec(), arr);
            arr
        }
    }
}
