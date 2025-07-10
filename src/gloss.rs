use serde::{Serialize, Deserialize};
use memmap2::Mmap;
use std::fs::File;
use std::path::Path;


/// Entry describing a precomputed gloss string.
///
/// `score` tracks the Bayesian belief associated with this entry and `pass`
/// optionally records the discovery pass during table generation.  These
/// fields are currently unused by the simplified library but are preserved so
/// that future pruning or visualisation tooling can make use of them.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GlossEntry {
    pub seed: Vec<u8>,
    pub decompressed: Vec<u8>,

    /// Bayesian posterior belief `P(F | E)` for this entry.
    pub score: f64,
    /// Optional discovery pass number.
    pub pass: usize,
}

#[derive(Serialize, Deserialize, Default, Clone)]
pub struct GlossTable {
    pub entries: Vec<GlossEntry>,
}

/// Entry tracked for probabilistic fallback seeding
pub struct BeliefSeed {
    pub seed: Vec<u8>,
    pub belief: f64,
    pub last_used: u64,
    pub bundling_hits: u32,
    pub gloss_hits: u32,
}

/// Simplistic LRU cache storing at most `capacity` entries.
/// The caller is responsible for trimming when exceeding limits.
pub struct LruCache<K: std::cmp::Eq + std::hash::Hash, V> {
    capacity: usize,
    map: std::collections::HashMap<K, V>,
}

impl<K: std::cmp::Eq + std::hash::Hash, V> LruCache<K, V> {
    pub fn new(capacity: usize) -> Self {
        Self { capacity, map: std::collections::HashMap::new() }
    }

    pub fn len(&self) -> usize {
        self.map.len()
    }

    pub fn get_mut(&mut self, key: &K) -> Option<&mut V> {
        self.map.get_mut(key)
    }

    pub fn insert(&mut self, key: K, value: V) {
        if self.map.len() >= self.capacity {
            // Caller should trim externally. Oldest removal is not automatic
        }
        self.map.insert(key, value);
    }

    pub fn remove(&mut self, key: &K) -> Option<V> {
        self.map.remove(key)
    }

    pub fn iter(&self) -> std::collections::hash_map::Iter<'_, K, V> {
        self.map.iter()
    }
}

/// Map of hashed seeds to belief entries.
pub type BeliefMap = LruCache<[u8; 32], BeliefSeed>;

impl GlossTable {
    /// Placeholder generator. In this trimmed example no automatic gloss table
    /// creation is performed.
    pub fn generate() -> Self {
        Self { entries: Vec::new() }
    }

    pub fn build() -> Self {
        Self { entries: Vec::new() }
    }

    pub fn load<P: AsRef<Path>>(path: P) -> std::io::Result<Self> {
        let file = File::open(path)?;
        unsafe {
            let mmap = Mmap::map(&file)?;
            Ok(bincode::deserialize(&mmap).expect("invalid gloss table"))
        }
    }

    pub fn save<P: AsRef<Path>>(&self, path: P) -> std::io::Result<()> {
        let data = bincode::serialize(self).expect("failed to serialize gloss");
        std::fs::write(path, data)
    }

    pub fn find(&self, data: &[u8]) -> Option<&GlossEntry> {
        self.entries.iter().find(|e| e.decompressed == data)
    }

    pub fn find_with_index(&self, data: &[u8]) -> Option<(usize, &GlossEntry)> {
        self.entries.iter().enumerate().find(|(_, e)| e.decompressed == data)
    }
}
