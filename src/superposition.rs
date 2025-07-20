//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
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
    /// Total number of original blocks in the stream. Used for gap checks.
    total_blocks: usize,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum InsertResult {
    Inserted(char),
    Pruned,
}

impl SuperpositionManager {
    /// Create a new manager for a stream with the given number of blocks.
    pub fn new(total_blocks: usize) -> Self {
        SuperpositionManager {
            canonical: HashMap::new(),
            superposed: HashMap::new(),
            total_blocks,
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
                a.1.bit_len
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

    /// Ensure the canonical set of candidates covers the entire input without
    /// gaps or overlaps.
    fn verify_gap_free(&self) -> Result<(), TelomereError> {
        use TelomereError::Superposition;
        if self.total_blocks == 0 {
            return Ok(());
        }

        let mut coverage = vec![false; self.total_blocks];
        for (&(start, blocks), _) in &self.canonical {
            if start + blocks > self.total_blocks {
                return Err(Superposition("span out of bounds".into()));
            }
            for i in start..start + blocks {
                if coverage[i] {
                    return Err(Superposition("overlap detected".into()));
                }
                coverage[i] = true;
            }
        }

        if coverage.iter().any(|c| !*c) {
            return Err(Superposition("gap detected".into()));
        }
        Ok(())
    }

    pub fn insert_candidate(
        &mut self,
        key: (usize, usize),
        cand: Candidate,
    ) -> Result<(), TelomereError> {
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
        self.verify_gap_free()
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

        if block_index >= self.total_blocks {
            return Err(Superposition("block index out of range".into()));
        }

        let list = self.superposed.entry(block_index).or_default();
        list.push(('?', cand.clone()));

        list.sort_by(|a, b| {
            a.1.bit_len
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

    /// Dump the current state for debugging.
    pub fn debug_dump(&self) -> String {
        let mut out = String::new();
        out.push_str("Canonical:\n");
        let mut can: Vec<_> = self.canonical.iter().collect();
        can.sort_by_key(|(k, _)| *k);
        for ((s, b), c) in can {
            out.push_str(&format!("  ({s},{b}) -> {:?}\n", c));
        }
        out.push_str("Superposed:\n");
        let mut sup: Vec<_> = self.superposed.iter().collect();
        sup.sort_by_key(|(k, _)| *k);
        for (idx, list) in sup {
            let mut tmp = list.clone();
            tmp.sort_by_key(|x| x.0);
            for (l, c) in tmp {
                out.push_str(&format!("  {idx}{l}: {:?}\n", c));
            }
        }
        out
    }
}
