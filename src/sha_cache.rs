//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
//!
//! The cache keeps a configurable number of entries and evicts the least
//! recently used value when full.  It can also persist and reload a hash
//! table from disk for testing purposes.

use bincode;
use sha2::{Digest, Sha256};
use std::collections::HashMap;
use std::fs::File;
use std::io::{BufReader, Read};

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
        let value = self.map.get(seed).cloned();
        if let Some(v) = value {
            self.touch(seed);
            v
        } else {
            let digest = Sha256::digest(seed);
            let arr: [u8; 32] = digest.into();
            self.insert(seed.to_vec(), arr);
            arr
        }
    }
}

pub fn load_hash_table(path: &str) -> std::io::Result<HashMap<Vec<u8>, [u8; 32]>> {
    let file = File::open(path)?;
    let mut reader = BufReader::new(file);
    let mut buf = Vec::new();
    reader.read_to_end(&mut buf)?;
    let table: HashMap<Vec<u8>, [u8; 32]> = bincode::deserialize(&buf)
        .map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))?;
    Ok(table)
}
