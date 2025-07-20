use std::collections::HashMap;

use crate::types::{Candidate, TelomereError};

#[derive(Debug, Clone)]
/// Manages superposed candidates across compression passes.
///
/// Candidates are added freely during a pass. No pruning is performed
/// until [`prune_end_of_pass`] is called, ensuring that the lattice of
/// possibilities remains stable while matching logic runs.
pub struct SuperpositionManager {
    canonical: HashMap<(usize, usize), Candidate>,
    superposed: HashMap<usize, Vec<(char, Candidate)>>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum InsertResult {
    Inserted(char),
    Pruned,
}

impl SuperpositionManager {
    pub fn new() -> Self {
        SuperpositionManager {
            canonical: HashMap::new(),
            superposed: HashMap::new(),
        }
    }

    /// Deprecated wrapper maintained for compatibility. Calls
    /// [`insert_superposed`] and ignores the returned value.
    pub fn push_unpruned(&mut self, block_index: usize, cand: Candidate) {
        let _ = self.insert_superposed(block_index, cand);
    }

    /// Finalize the state after a pass.  For each block index only the best
    /// three candidates within an 8-bit delta of the shortest are retained and
    /// labeled `A`, `B` and `C` respectively.  Ordering is deterministic based
    /// on length and `seed_index` so repeated runs yield identical results.
    pub fn prune_end_of_pass(&mut self) {
        for list in self.superposed.values_mut() {
            if list.is_empty() {
                continue;
            }

            list.sort_by(|a, b| {
                a.1
                    .bit_len
                    .cmp(&b.1.bit_len)
                    .then(a.1.seed_index.cmp(&b.1.seed_index))
            });
            let best_len = list[0].1.bit_len;
            list.retain(|(_, c)| c.bit_len <= best_len + 8);
            if list.len() > 3 {
                list.truncate(3);
            }
            for (i, (label, _)) in list.iter_mut().enumerate() {
                *label = match i {
                    0 => 'A',
                    1 => 'B',
                    2 => 'C',
                    _ => unreachable!(),
                };
            }
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
    ) -> Result<InsertResult, TelomereError> {
        use TelomereError::Superposition;

        if cand.bit_len == 0 {
            return Err(Superposition("zero bit length".into()));
        }

        let list = self.superposed.entry(block_index).or_default();
        list.push(('?', cand.clone()));

        list.sort_by(|a, b| {
            a.1
                .bit_len
                .cmp(&b.1.bit_len)
                .then(a.1.seed_index.cmp(&b.1.seed_index))
        });

        let best_len = list[0].1.bit_len;
        list.retain(|(_, c)| c.bit_len <= best_len + 8);
        if list.len() > 3 {
            list.truncate(3);
        }

        let mut inserted = None;
        for (i, (label, c)) in list.iter_mut().enumerate() {
            *label = match i {
                0 => 'A',
                1 => 'B',
                2 => 'C',
                _ => unreachable!(),
            };
            if inserted.is_none()
                && c.seed_index == cand.seed_index
                && c.bit_len == cand.bit_len
                && c.arity == cand.arity
            {
                inserted = Some(*label);
            }
        }

        if inserted.is_some() {
            Ok(InsertResult::Inserted(inserted.unwrap()))
        } else {
            Ok(InsertResult::Pruned)
        }
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
                if let Some(min) = list.iter().map(|(_, c)| c.bit_len).min() {
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
