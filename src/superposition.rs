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
    Pruned(Vec<char>),
}

impl SuperpositionManager {
    pub fn new() -> Self {
        SuperpositionManager {
            canonical: HashMap::new(),
            superposed: HashMap::new(),
        }
    }

    /// Insert a candidate without any pruning. Labels are assigned
    /// deterministically in insertion order. Pruning must be invoked
    /// separately after the pass completes.
    pub fn push_unpruned(&mut self, block_index: usize, cand: Candidate) {
        let list = self.superposed.entry(block_index).or_default();
        let label = ((list.len() as u8) + b'A') as char;
        list.push((label, cand));
    }

    /// Prune all stored candidates keeping only the shortest per block index.
    /// Ties are broken deterministically by label so results remain
    /// reproducible between runs.
    /// Collapse each superposition down to a single candidate.
    ///
    /// This should be called exactly once at the end of a compression pass.
    pub fn prune_end_of_pass(&mut self) {
        for (_idx, list) in self.superposed.iter_mut() {
            if list.is_empty() {
                continue;
            }
            list.sort_by(|a, b| a.1.bit_len.cmp(&b.1.bit_len).then(a.0.cmp(&b.0)));
            let best_len = list[0].1.bit_len;
            list.retain(|(_, c)| c.bit_len == best_len);
            if list.len() > 1 {
                let keep = list[0].0;
                list.retain(|(l, _)| *l == keep);
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

        let list = self.superposed.entry(block_index).or_insert_with(Vec::new);
        let mut pruned = Vec::new();

        // Determine the minimum length if this candidate were inserted.
        let mut min_len = cand.bit_len;
        for (_, c) in list.iter() {
            if c.bit_len < min_len {
                min_len = c.bit_len;
            }
        }

        // Remove existing candidates that exceed the allowed delta.
        let mut to_remove = Vec::new();
        for (idx, (l, c)) in list.iter().enumerate() {
            if c.bit_len > min_len + 8 {
                to_remove.push(idx);
                pruned.push(*l);
            }
        }
        for idx in to_remove.into_iter().rev() {
            list.remove(idx);
        }

        // If the new candidate itself is outside the delta it is pruned.
        if cand.bit_len > min_len + 8 {
            pruned.sort();
            return Ok(InsertResult::Pruned(pruned));
        }

        if list.len() < 3 {
            // Assign the first available label.
            let label = ['A', 'B', 'C']
                .into_iter()
                .find(|l| !list.iter().any(|(el, _)| el == l))
                .ok_or_else(|| Superposition("no label available".into()))?;
            list.push((label, cand));
            pruned.sort();
            if pruned.is_empty() {
                Ok(InsertResult::Inserted(label))
            } else {
                Ok(InsertResult::Pruned(pruned))
            }
        } else {
            // Replace the worst candidate if the new one is shorter.
            let (worst_idx, worst_len) = list
                .iter()
                .enumerate()
                .max_by_key(|(_, (_, c))| c.bit_len)
                .map(|(i, (_, c))| (i, c.bit_len))
                .ok_or_else(|| Superposition("no candidates".into()))?;
            if cand.bit_len < worst_len {
                let (label, _) = list.remove(worst_idx);
                pruned.push(label);
                list.push((label, cand));
                pruned.sort();
                Ok(InsertResult::Pruned(pruned))
            } else {
                pruned.sort();
                if pruned.is_empty() {
                    Err(Superposition(format!("limit exceeded at block {}", block_index)))
                } else {
                    Ok(InsertResult::Pruned(pruned))
                }
            }
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
