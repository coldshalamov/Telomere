use bloomfilter::Bloom as RawBloom;

/// Simple wrapper around the `bloomfilter` crate using `u64` items.
pub struct Bloom {
    filter: RawBloom<u64>,
}

impl Bloom {
    /// Create a new bloom filter for `items` expected entries with the given
    /// false positive rate.
    pub fn new(items: usize, fp_rate: f64) -> Self {
        let filter = RawBloom::new_for_fp_rate(items, fp_rate);
        Self { filter }
    }

    /// Insert a value into the filter.
    pub fn insert(&mut self, value: &u64) {
        self.filter.set(value);
    }

    /// Check whether a value is possibly in the set.
    pub fn contains(&self, value: &u64) -> bool {
        self.filter.check(value)
    }

    /// Check if a value is in the set and insert it if not.
    /// Returns true if the value was already present.
    pub fn check_and_insert(&mut self, value: &u64) -> bool {
        let present = self.filter.check(value);
        if !present {
            self.filter.set(value);
        }
        present
    }
}

#[cfg(test)]
mod tests {
    use super::Bloom;

    #[test]
    fn basic_usage() {
        let mut bloom = Bloom::new(100, 0.01);
        assert!(!bloom.contains(&42));
        bloom.insert(&42);
        assert!(bloom.contains(&42));
    }
}
