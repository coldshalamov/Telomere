use std::collections::{HashMap, VecDeque};

use crate::BLOCK_SIZE;

#[derive(Clone, Debug)]
pub struct CompressionPath {
    pub id: u64,
    pub seeds: Vec<Vec<u8>>,        // Max 16 entries
    pub span_hashes: Vec<[u8; 32]>, // One per step
    pub total_gain: u64,            // Bits saved
    pub created_at: u64,            // Global pass index
    pub replayed: u32,
}

#[derive(Clone, Debug)]
pub struct PathGloss {
    pub paths: VecDeque<CompressionPath>,
    pub index: HashMap<[u8; 32], usize>,
    pub max_paths: usize,
}

impl Default for PathGloss {
    fn default() -> Self {
        Self {
            paths: VecDeque::new(),
            index: HashMap::new(),
            max_paths: 100,
        }
    }
}

impl PathGloss {
    fn rebuild_index(&mut self) {
        self.index.clear();
        for (i, p) in self.paths.iter().enumerate() {
            if let Some(h) = p.span_hashes.first() {
                self.index.insert(*h, i);
            }
        }
    }

    fn select_evict_index(&self) -> Option<usize> {
        if self.paths.is_empty() {
            return None;
        }
        let mut candidates: Vec<(usize, &CompressionPath)> = self.paths.iter().enumerate().collect();
        if candidates.iter().any(|(_, p)| p.replayed < 2) {
            candidates.retain(|(_, p)| p.replayed < 2);
        }
        candidates
            .into_iter()
            .min_by(|a, b| {
                let g = a.1.total_gain.cmp(&b.1.total_gain);
                if g == std::cmp::Ordering::Equal {
                    a.1.created_at.cmp(&b.1.created_at)
                } else {
                    g
                }
            })
            .map(|(idx, _)| idx)
    }

    fn evict_one(&mut self) {
        if let Some(idx) = self.select_evict_index() {
            self.paths.remove(idx);
            self.rebuild_index();
        }
    }

    pub fn prune(&mut self) {
        while self.paths.len() > self.max_paths {
            self.evict_one();
        }
    }

    pub fn try_insert(&mut self, path: CompressionPath) -> bool {
        if path.seeds.len() < 2 || path.seeds.len() > 16 {
            return false;
        }
        let span_bytes = path.span_hashes.len() * BLOCK_SIZE;
        if let Some(last) = path.seeds.last() {
            if last.len() >= span_bytes {
                return false;
            }
        } else {
            return false;
        }
        if self.paths.len() >= self.max_paths {
            self.evict_one();
        }
        self.paths.push_back(path);
        self.rebuild_index();
        true
    }

    pub fn lookup(&self, hash: &[u8; 32]) -> Option<&CompressionPath> {
        self.index.get(hash).and_then(|&i| self.paths.get(i))
    }
}

