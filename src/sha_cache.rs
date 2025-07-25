//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
//!
//! The cache keeps a configurable number of entries and evicts the least
//! recently used value when full.  It can also persist and reload a hash
//! table from disk for testing purposes.

use crate::seed::digest32;
use bincode;
use sha2::Digest;
use std::collections::HashMap;
use std::fs::File;
use std::io::{BufReader, Read};

type CacheKey = (bool, Vec<u8>);

pub struct ShaCache {
    capacity: usize,
    map: HashMap<CacheKey, [u8; 32]>,
    order: Vec<CacheKey>, // simple queue for LRU
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

    fn touch(&mut self, key: &CacheKey) {
        if let Some(pos) = self.order.iter().position(|k| k == key) {
            let key_vec = self.order.remove(pos);
            self.order.push(key_vec);
        }
    }

    fn insert(&mut self, key: CacheKey, value: [u8; 32]) {
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

    pub fn get_or_compute(&mut self, seed: &[u8], use_xxhash: bool) -> [u8; 32] {
        let key: CacheKey = (use_xxhash, seed.to_vec());
        let value = self.map.get(&key).cloned();
        if let Some(v) = value {
            self.touch(&key);
            v
        } else {
            let arr = digest32(seed, use_xxhash);
            self.insert(key, arr);
            arr
        }
    }
}

pub fn load_hash_table(path: &str) -> Result<HashMap<Vec<u8>, [u8; 32]>, crate::TelomereError> {
    let file = File::open(path).map_err(crate::TelomereError::from)?;
    let mut reader = BufReader::new(file);
    let mut buf = Vec::new();
    reader
        .read_to_end(&mut buf)
        .map_err(crate::TelomereError::from)?;
    let table: HashMap<Vec<u8>, [u8; 32]> = bincode::deserialize(&buf).map_err(|e| {
        crate::TelomereError::Io(std::io::Error::new(std::io::ErrorKind::InvalidData, e))
    })?;
    Ok(table)
}
