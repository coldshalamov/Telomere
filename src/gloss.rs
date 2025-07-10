use serde::{Serialize, Deserialize};
use memmap2::Mmap;
use std::fs::File;
use std::path::Path;

/// Entry describing a precomputed gloss string.
///
/// `score` tracks the Bayesian belief associated with this entry and `pass`
/// optionally records the discovery pass during table generation. These
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
        Self {
            capacity,
            map: std::collections::HashMap::new(),
        }
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

impl BeliefMap {
    /// Prune entries with belief below `min_score` and ensure the map does not
    /// exceed `max_entries`. When trimming due to size, the lowest belief
    /// entries are removed first and ties are broken by `last_used`.
    pub fn prune_low_score_entries(&mut self, min_score: f64, max_entries: usize) {
        let to_remove: Vec<[u8; 32]> = self
            .map
            .iter()
            .filter(|(_, v)| v.belief < min_score)
            .map(|(k, _)| *k)
            .collect();
        for k in to_remove {
            self.map.remove(&k);
        }

        while self.map.len() > max_entries {
            if let Some((&key, _)) = self
                .map
                .iter()
                .min_by(|a, b| {
                    let ba = a.1.belief;
                    let bb = b.1.belief;
                    ba.partial_cmp(&bb)
                        .unwrap_or(std::cmp::Ordering::Equal)
                        .then_with(|| a.1.last_used.cmp(&b.1.last_used))
                })
            {
                self.map.remove(&key);
            } else {
                break;
            }
        }
    }
}

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

    /// Drop entries whose score falls below `min_score` and ensure the table
    /// does not exceed `max_entries` items. When trimming by size the lowest
    /// scoring entries are removed first.
    pub fn prune_low_score_entries(&mut self, min_score: f64, max_entries: usize) {
        self.entries.retain(|e| e.score >= min_score);

        if self.entries.len() > max_entries {
            self.entries.sort_by(|a, b| {
                b.score
                    .partial_cmp(&a.score)
                    .unwrap_or(std::cmp::Ordering::Equal)
            });
            self.entries.truncate(max_entries);
        }
    }
}
