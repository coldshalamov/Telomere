//! Real-time compression progress logging utility.

#[derive(Default)]
pub struct LiveStats {
    pub total_blocks: u64,
    pub interval: u64,
}

impl LiveStats {
    pub fn new(interval: u64) -> Self {
        Self { total_blocks: 0, interval }
    }

    /// Call whenever a block has been processed.
    pub fn tick_block(&mut self) {
        self.total_blocks += 1;
    }

    /// Optionally print a short summary of the current span/seed pair.
    pub fn maybe_log(&self, span: &[u8], seed: &[u8], is_greedy: bool) {
        if self.interval > 0 && self.total_blocks % self.interval == 0 {
            println!(
                "[offset {:>6}] span: {:02X?}  seed: {:02X?}  method: {}",
                self.total_blocks,
                &span[..3.min(span.len())],
                &seed[..3.min(seed.len())],
                if is_greedy { "GREEDY" } else { "FALLBACK" }
            );
        }
    }
}

/// Lightweight stat tracker for alternate use.
#[derive(Default)]
pub struct Stats {
    pub total_blocks: u64,
}

/// Alternative logging method for cases not using `LiveStats`.
#[allow(dead_code)]
use crate::compress_stats::CompressionStats;

pub fn print_window(span: &[u8], seed: &[u8], is_greedy: bool, stats: &CompressionStats, interval: u64) {
    if interval == 0 {
        return;
    }
    let interval_usize = interval as usize;
    if stats.total_blocks % interval_usize == 0 {
        println!(
            "[{:>6}] span: {:02X?} seed: {:02X?} method: {}",
            stats.total_blocks,
            &span[..3.min(span.len())],
            &seed[..3.min(seed.len())],
            if is_greedy { "GREEDY" } else { "FALLBACK" },
        );
    }
}
