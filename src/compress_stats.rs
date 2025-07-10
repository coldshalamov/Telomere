use std::time::Instant;
use std::fs::File;
use csv::Writer;

pub struct CompressionStats {
    start_time: Instant,
    /// Total number of blocks seen by the compressor.
    pub total_blocks: usize,
    /// Total number of blocks output in compressed form.
    pub compressed_blocks: usize,
    /// Number of greedy matches encountered.
    pub greedy_matches: usize,
    /// Number of fallback matches encountered.
    pub fallback_matches: usize,
    /// Optional CSV logger for progress snapshots.
    csv: Option<Writer<File>>,
    /// Print progress to stdout every `interval` blocks if non-zero.
    interval: u64,
}

impl CompressionStats {
    pub fn new() -> Self {
        Self {
            start_time: Instant::now(),
            total_blocks: 0,
            compressed_blocks: 0,
            greedy_matches: 0,
            fallback_matches: 0,
            csv: None,
            interval: 0,
        }
    }

    /// Create a new stats tracker that logs progress snapshots to the given CSV file.
    pub fn with_csv(path: &str) -> std::io::Result<Self> {
        let file = File::create(path)?;
        let mut wtr = Writer::from_writer(file);
        wtr.write_record(&["seconds", "total_blocks", "compressed_blocks", "greedy", "fallback"])?;
        Ok(Self {
            start_time: Instant::now(),
            total_blocks: 0,
            compressed_blocks: 0,
            greedy_matches: 0,
            fallback_matches: 0,
            csv: Some(wtr),
            interval: 0,
        })
    }

    /// Set how often progress should be printed.
    pub fn with_interval(mut self, interval: u64) -> Self {
        self.interval = interval;
        self
    }

    pub fn log_match(&mut self, is_greedy: bool, blocks_compressed: usize) {
        self.compressed_blocks += blocks_compressed;
        if is_greedy {
            self.greedy_matches += 1;
        } else {
            self.fallback_matches += 1;
        }
    }

    /// Optionally print a short summary of the current span/seed pair.
    pub fn maybe_log(&self, span: &[u8], seed: &[u8], is_greedy: bool) {
        if self.interval > 0 && (self.total_blocks as u64) % self.interval == 0 {
            println!(
                "[{:>6}] span: {:02X?}  seed: {:02X?}  method: {}",
                self.total_blocks,
                &span[..3.min(span.len())],
                &seed[..3.min(seed.len())],
                if is_greedy { "GREEDY" } else { "FALLBACK" }
            );
        }
    }

    pub fn tick_block(&mut self) {
        self.total_blocks += 1;
        if let Some(wtr) = self.csv.as_mut() {
            let elapsed = self.start_time.elapsed().as_secs_f32();
            let _ = wtr.write_record(&[
                format!("{:.3}", elapsed),
                self.total_blocks.to_string(),
                self.compressed_blocks.to_string(),
                self.greedy_matches.to_string(),
                self.fallback_matches.to_string(),
            ]);
            let _ = wtr.flush();
        }
    }

pub fn report(&self) {
        let elapsed = self.start_time.elapsed().as_secs_f32();
        let ratio = self.compressed_blocks as f32 / self.total_blocks.max(1) as f32;
        println!(
            "\n\u{1F4CA} Compression Progress:\n  \u{2022} Time: {:.2}s\n  \u{2022} Total Blocks Seen: {}\n  \u{2022} Compressed Blocks: {} ({:.2}%)\n  \u{2022} Greedy Matches: {}\n  \u{2022} Fallback Matches: {}\n",
            elapsed,
            self.total_blocks,
            self.compressed_blocks,
            ratio * 100.0,
            self.greedy_matches,
            self.fallback_matches,
        );
        // CSV writer is flushed periodically by `tick_block`.
    }
}

/// Write a single CSV row summarizing the provided statistics.
pub fn write_stats_csv(stats: &CompressionStats, path: &str) -> std::io::Result<()> {
    let mut wtr = Writer::from_path(path)?;
    wtr.write_record(&["total_blocks", "compressed_blocks", "greedy_matches", "fallback_matches"])?;
    wtr.write_record(&[
        stats.total_blocks.to_string(),
        stats.compressed_blocks.to_string(),
        stats.greedy_matches.to_string(),
        stats.fallback_matches.to_string(),
    ])?;
    wtr.flush()?;
    Ok(())
}

