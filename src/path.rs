use std::collections::{HashMap, VecDeque};

#[derive(Clone)]
pub struct CompressionPath {
    pub path_id: u64,
    pub seeds: Vec<Vec<u8>>, // Max 16
    pub span_hashes: Vec<[u8; 32]>,
    pub total_gain: u32,
    pub replayed: u32,
}

pub struct PathGloss {
    pub paths: VecDeque<CompressionPath>,
    pub index: HashMap<[u8; 32], usize>,
}

impl PathGloss {
    pub fn new() -> Self {
        Self {
            paths: VecDeque::new(),
            index: HashMap::new(),
        }
    }

    pub fn add_path(&mut self, mut path: CompressionPath) {
        if path.seeds.len() > 16 {
            path.seeds.truncate(16);
        }
        if 2 * path.total_gain < path.seeds.len() as u32 {
            return; // skip low gain paths
        }
        self.paths.push_back(path);
        self.rebuild_index();
        if self.paths.len() > 100 {
            let (idx, _) = self
                .paths
                .iter()
                .enumerate()
                .min_by_key(|(_, p)| p.total_gain)
                .unwrap();
            self.remove_at(idx);
        }
    }

    pub fn match_span(&self, hash: &[u8; 32]) -> Option<(usize, &CompressionPath)> {
        self.index
            .get(hash)
            .and_then(|&idx| self.paths.get(idx).map(|p| (idx, p)))
    }

    pub fn increment_replayed(&mut self, idx: usize) {
        if let Some(p) = self.paths.get_mut(idx) {
            p.replayed += 1;
        }
    }

    fn rebuild_index(&mut self) {
        self.index.clear();
        for (i, p) in self.paths.iter().enumerate() {
            for h in &p.span_hashes {
                self.index.insert(*h, i);
            }
        }
    }

    fn remove_at(&mut self, idx: usize) {
        if idx >= self.paths.len() {
            return;
        }
        let mut vec: Vec<_> = self.paths.drain(..).collect();
        let removed = vec.remove(idx);
        self.paths = vec.into();
        for h in &removed.span_hashes {
            self.index.remove(h);
        }
        self.rebuild_index();
    }
}
