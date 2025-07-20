//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
//!
//! `Stats` simply tracks block and match counts without any logging or
//! persistence.  It is mainly used by test helpers.

pub struct Stats {
    pub total_blocks: u64,
    pub greedy_matches: u64,
    pub lazy_matches: u64,
    pub matched_blocks: u64,
}

impl Stats {
    pub fn new() -> Self {
        Self {
            total_blocks: 0,
            greedy_matches: 0,
            lazy_matches: 0,
            matched_blocks: 0,
        }
    }

    pub fn tick_block(&mut self) {
        self.total_blocks += 1;
    }

    pub fn log_match(&mut self, is_greedy: bool, match_arity: usize) {
        if is_greedy {
            self.greedy_matches += 1;
        } else {
            self.lazy_matches += 1;
        }
        self.matched_blocks += match_arity as u64;
    }

    pub fn report(&self) {
        eprintln!(
            "Processed {} blocks, matches: greedy {}, lazy {}, matched blocks {}",
            self.total_blocks, self.greedy_matches, self.lazy_matches, self.matched_blocks
        );
    }
}
