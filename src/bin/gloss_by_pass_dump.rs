/// Module for live compression stats logging

/// A real-time compression logger triggered at block intervals.
pub struct LiveStats {
    pub total_blocks: u64,
    pub interval: u64,
}

impl LiveStats {
    pub fn new(interval: u64) -> Self {
        Self {
            total_blocks: 0,
            interval,
        }
    }

    /// Increment the block counter.
    pub fn tick_block(&mut self) {
        self.total_blocks += 1;
    }

    /// Print span/seed summary every N blocks if interval is set.
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

/// Alternate static-printing function using shared Stats object.
#[derive(Default)]
pub struct Stats {
    pub total_blocks: u64,
}

/// Alternate interface if using external `Stats` state.
#[allow(dead_code)]
pub fn print_window(span: &[u8], seed: &[u8], is_greedy: bool, stats: &Stats, interval: u64) {
    if interval == 0 {
        return;
    }
    if stats.total_blocks % interval == 0 {
        println!(
            "[{:>6}] span: {:02X?} seed: {:02X?} method: {}",
            stats.total_blocks,
            &span[..3.min(span.len())],
            &seed[..3.min(seed.len())],
            if is_greedy { "GREEDY" } else { "FALLBACK" }
        );
    }
}

fn main() {}
