use std::collections::{BTreeMap, BTreeSet, HashMap};

/// Unique key for a candidate span within a block stream.
///
/// `offset` represents the starting byte offset and `span_len` is the number of
/// bytes spanned.
pub type SpanKey = (usize, usize);

/// Representation of a single candidate encoding for a span.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Candidate {
    /// Seed table index referencing the expansion used.
    pub seed_index: u64,
    /// Arity of the encoded form.
    pub arity: u8,
    /// Total encoded length in bits.
    pub bit_len: usize,
    /// Compression pass when this candidate was discovered.
    pub pass_seen: usize,
}

/// Holds the best known candidate followed by alternative variants.
#[derive(Debug, Clone)]
pub struct CandidateList {
    best: Candidate,
    others: Vec<Candidate>,
}

impl CandidateList {
    const MAX_OTHERS: usize = 4;

    /// Create a list with a single candidate.
    pub fn new(c: Candidate) -> Self {
        Self {
            best: c,
            others: Vec::new(),
        }
    }

    /// Insert a new candidate and prune the list.
    pub fn insert(&mut self, c: Candidate) {
        if c.bit_len < self.best.bit_len {
            let old = std::mem::replace(&mut self.best, c);
            self.others.push(old);
        } else {
            self.others.push(c);
        }
        self.prune();
    }

    fn prune(&mut self) {
        self.others.sort_by_key(|c| c.bit_len);
        let keep_len = self.best.bit_len + 8;
        self.others.retain(|c| c.bit_len <= keep_len);
        if self.others.len() > Self::MAX_OTHERS {
            self.others.truncate(Self::MAX_OTHERS);
        }
    }

    /// Iterate over all candidates starting with the best.
    pub fn iter(&self) -> impl Iterator<Item = &Candidate> {
        std::iter::once(&self.best).chain(self.others.iter())
    }
}

/// Global manager tracking the best candidates per span.
#[derive(Debug, Default)]
pub struct SuperpositionManager {
    map: HashMap<SpanKey, CandidateList>,
    buckets: BTreeMap<usize, BTreeSet<SpanKey>>, // keyed by span_len
}

impl SuperpositionManager {
    /// Create an empty manager.
    pub fn new() -> Self {
        Self {
            map: HashMap::new(),
            buckets: BTreeMap::new(),
        }
    }

    /// Insert a new candidate for the given span.
    pub fn insert_candidate(&mut self, key: SpanKey, cand: Candidate) {
        match self.map.entry(key) {
            std::collections::hash_map::Entry::Vacant(e) => {
                self.buckets.entry(key.1).or_default().insert(key);
                e.insert(CandidateList::new(cand));
            }
            std::collections::hash_map::Entry::Occupied(mut e) => {
                e.get_mut().insert(cand);
            }
        }
    }

    /// Retrieve all candidates for a span ordered by quality.
    pub fn get_candidates(&self, key: &SpanKey) -> Vec<&Candidate> {
        self.map
            .get(key)
            .map(|l| l.iter().collect())
            .unwrap_or_default()
    }

    /// Remove a span and its candidates from tracking.
    pub fn remove_span(&mut self, key: &SpanKey) {
        if self.map.remove(key).is_some() {
            if let Some(set) = self.buckets.get_mut(&key.1) {
                set.remove(key);
                if set.is_empty() {
                    self.buckets.remove(&key.1);
                }
            }
        }
    }

    /// Iterate over all span keys in ascending length order.
    pub fn all_keys(&self) -> impl Iterator<Item = &SpanKey> {
        self.buckets.values().flat_map(|set| set.iter())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_candidate(bit_len: usize) -> Candidate {
        Candidate {
            seed_index: 0,
            arity: 1,
            bit_len,
            pass_seen: 0,
        }
    }

    #[test]
    fn candidate_best_and_others() {
        let mut list = CandidateList::new(sample_candidate(10));
        assert_eq!(list.iter().count(), 1);

        list.insert(sample_candidate(12));
        let bits: Vec<usize> = list.iter().map(|c| c.bit_len).collect();
        assert_eq!(bits, vec![10, 12]);

        list.insert(sample_candidate(8));
        let bits: Vec<usize> = list.iter().map(|c| c.bit_len).collect();
        assert_eq!(bits, vec![8, 10, 12]);
    }

    #[test]
    fn prune_by_delta() {
        let mut list = CandidateList::new(sample_candidate(10));
        list.insert(sample_candidate(20));
        // 20 is more than 8 bits longer than 10 and should be pruned
        let bits: Vec<usize> = list.iter().map(|c| c.bit_len).collect();
        assert_eq!(bits, vec![10]);
    }

    #[test]
    fn bucket_management() {
        let mut mgr = SuperpositionManager::new();
        let key_a = (0, 3);
        let key_b = (5, 2);
        mgr.insert_candidate(key_a, sample_candidate(5));
        mgr.insert_candidate(key_b, sample_candidate(6));

        let keys: Vec<SpanKey> = mgr.all_keys().cloned().collect();
        assert_eq!(keys, vec![key_b, key_a]); // ordered by span_len = 2 then 3

        mgr.remove_span(&key_b);
        let keys: Vec<SpanKey> = mgr.all_keys().cloned().collect();
        assert_eq!(keys, vec![key_a]);
    }
}
