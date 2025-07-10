use std::time::Instant;

pub struct CompressionStats {
    start_time: Instant,
    total_blocks: usize,
    compressed_blocks: usize,
    greedy_matches: usize,
    fallback_matches: usize,
}

impl CompressionStats {
    pub fn new() -> Self {
        Self {
            start_time: Instant::now(),
            total_blocks: 0,
            compressed_blocks: 0,
            greedy_matches: 0,
            fallback_matches: 0,
        }
    }

    pub fn log_match(&mut self, is_greedy: bool, blocks_compressed: usize) {
        self.compressed_blocks += blocks_compressed;
        if is_greedy {
            self.greedy_matches += 1;
        } else {
            self.fallback_matches += 1;
        }
    }

    pub fn tick_block(&mut self) {
        self.total_blocks += 1;
    }

    pub fn report(&self) {
        let elapsed = self.start_time.elapsed().as_secs_f32();
        let ratio = self.compressed_blocks as f32 / self.total_blocks.max(1) as f32;
        println!(
            "\n\xF0\x9F\x93\x8A Compression Progress:\n  \xE2\x80\xA2 Time: {:.2}s\n  \xE2\x80\xA2 Total Blocks Seen: {}\n  \xE2\x80\xA2 Compressed Blocks: {} ({:.2}%)\n  \xE2\x80\xA2 Greedy Matches: {}\n  \xE2\x80\xA2 Fallback Matches: {}\n",
            elapsed,
            self.total_blocks,
            self.compressed_blocks,
            ratio * 100.0,
            self.greedy_matches,
            self.fallback_matches,
        );
    }
}

