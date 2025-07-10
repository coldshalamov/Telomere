use std::time::Instant;

pub struct CompressionStats {
    start_time: Instant,
    pub total_blocks: usize,
    pub compressed_blocks: usize,
    pub greedy_matches: usize,
    pub fallback_matches: usize,
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
            "\n📊 Compression Progress:\n  • Time: {:.2}s\n  • Total Blocks Seen: {}\n  • Compressed Blocks: {} ({:.2}%)\n  • Greedy Matches: {}\n  • Fallback Matches: {}\n",
            elapsed,
            self.total_blocks,
            self.compressed_blocks,
            ratio * 100.0,
            self.greedy_matches,
            self.fallback_matches,
        );
    }
}

pub fn write_stats_csv(stats: &CompressionStats, path: &str) -> std::io::Result<()> {
    use std::fs::File;
    let elapsed = stats.start_time.elapsed().as_secs_f32();
    let ratio = stats.compressed_blocks as f32 / stats.total_blocks.max(1) as f32;
    let mut wtr = csv::Writer::from_writer(File::create(path)?);
    wtr.write_record(&["time_s", "total_blocks", "compressed_blocks", "ratio", "greedy", "fallback"])?;
    wtr.write_record(&[
        format!("{:.2}", elapsed),
        stats.total_blocks.to_string(),
        stats.compressed_blocks.to_string(),
        format!("{:.2}", ratio * 100.0),
        stats.greedy_matches.to_string(),
        stats.fallback_matches.to_string(),
    ])?;
    wtr.flush()?;
    Ok(())
}

