#[derive(Default)]
pub struct Stats {
    pub total_blocks: u64,
}

#[allow(dead_code)]
pub fn print_window(span: &[u8], seed: &[u8], is_greedy: bool, stats: &Stats, interval: u64) {
    if interval == 0 {
        return;
    }
    if stats.total_blocks % interval == 0 {
        println!(
            "[{:\>6}] span: {:02X?} seed: {:02X?} method: {}",
            stats.total_blocks,
            &span[..3.min(span.len())],
            &seed[..3.min(seed.len())],
            if is_greedy { "GREEDY" } else { "FALLBACK" },
        );
    }
}
