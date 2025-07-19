use std::collections::HashMap;

use crate::types::{Candidate, TelomereError};

#[derive(Debug, Clone)]
pub struct SuperpositionManager {
    canonical: HashMap<(usize, usize), Candidate>,
    superposed: HashMap<usize, Vec<(char, Candidate)>>,
}

impl SuperpositionManager {
    pub fn new() -> Self {
        SuperpositionManager {
            canonical: HashMap::new(),
            superposed: HashMap::new(),
        }
    }

    pub fn insert_candidate(&mut self, key: (usize, usize), cand: Candidate) {
        match self.canonical.entry(key) {
            std::collections::hash_map::Entry::Occupied(mut e) => {
                if cand.bit_len < e.get().bit_len {
                    e.insert(cand);
                }
            }
            std::collections::hash_map::Entry::Vacant(v) => {
                v.insert(cand);
            }
        }
    }

    pub fn insert_superposed(
        &mut self,
        block_index: usize,
        cand: Candidate,
    ) -> Result<(), TelomereError> {
        use TelomereError::SuperpositionLimitExceeded;
        let list = self.superposed.entry(block_index).or_insert_with(Vec::new);
        if list.len() >= 3 {
            return Err(SuperpositionLimitExceeded(block_index));
        }
        let label = match list.len() {
            0 => 'A',
            1 => 'B',
            2 => 'C',
            _ => unreachable!(),
        };
        list.push((label, cand));
        Ok(())
    }

    pub fn remove_superposed(&mut self, block_index: usize) {
        self.superposed.remove(&block_index);
    }

    pub fn collapse_superpositions(&mut self) {
        let keys: Vec<usize> = self.superposed.keys().copied().collect();
        for k in keys {
            if let Some(list) = self.superposed.get_mut(&k) {
                if list.len() < 2 {
                    continue;
                }
                let mut sorted = list.clone();
                sorted.sort_by_key(|(_, c)| c.bit_len);
                let min = sorted[0].1.bit_len;
                let max = sorted.last().unwrap().1.bit_len;
                if max > min + 8 {
                    list.retain(|(_, c)| c.bit_len <= min + 8);
                }
            }
        }
    }

    pub fn promote_superposed(&mut self, block_index: usize, label: char) -> Option<Candidate> {
        let list = self.superposed.remove(&block_index)?;
        let winner = list.into_iter().find(|(l, _)| *l == label);
        winner.map(|(_, c)| c)
    }

    pub fn best_superposed(&self, block_index: usize) -> Option<&Candidate> {
        self.superposed
            .get(&block_index)
            .and_then(|v| v.iter().min_by_key(|(_, c)| c.bit_len).map(|(_, c)| c))
    }

    pub fn all_canonical(&self) -> Vec<((usize, usize), &Candidate)> {
        self.canonical.iter().map(|(k, v)| (*k, v)).collect()
    }

    pub fn all_superposed(&self) -> Vec<(usize, Vec<(char, Candidate)>)> {
        self.superposed
            .iter()
            .map(|(k, v)| (*k, v.clone()))
            .collect()
    }
}
