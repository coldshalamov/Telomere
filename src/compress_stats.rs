//! Compression statistics: per-pass deltas, JSON export, CSV logging.

use csv::Writer;
use serde::Serialize;
use std::fs::File;
use std::time::{Duration, Instant};

// ---------------------------------------------------------------------------
// Per-pass delta statistics
// ---------------------------------------------------------------------------

/// Statistics for a single compression pass.
#[derive(Debug, Clone, Serialize)]
pub struct PassStats {
    pub pass: usize,
    pub bytes_in: usize,
    pub bytes_out: usize,
    pub delta_bytes: i64,
    pub delta_pct: f64,
    pub duration_ms: u64,
}

impl PassStats {
    pub fn new(pass: usize, bytes_in: usize, bytes_out: usize, duration: Duration) -> Self {
        let delta_bytes = bytes_out as i64 - bytes_in as i64;
        let delta_pct = if bytes_in == 0 {
            0.0
        } else {
            delta_bytes as f64 / bytes_in as f64 * 100.0
        };
        Self {
            pass,
            bytes_in,
            bytes_out,
            delta_bytes,
            delta_pct,
            duration_ms: duration.as_millis() as u64,
        }
    }

    pub fn is_compressive(&self) -> bool {
        self.delta_bytes < 0
    }
}

/// Summary of a full multi-pass compression run.
#[derive(Debug, Clone, Serialize)]
pub struct RunSummary {
    pub passes: Vec<PassStats>,
    pub original_bytes: usize,
    pub final_bytes: usize,
    pub total_delta_bytes: i64,
    pub total_delta_pct: f64,
    pub total_duration_ms: u64,
}

impl RunSummary {
    pub fn new(original_bytes: usize, passes: Vec<PassStats>) -> Self {
        let final_bytes = passes.last().map(|p| p.bytes_out).unwrap_or(original_bytes);
        let total_delta = final_bytes as i64 - original_bytes as i64;
        let total_pct = if original_bytes == 0 {
            0.0
        } else {
            total_delta as f64 / original_bytes as f64 * 100.0
        };
        let total_ms = passes.iter().map(|p| p.duration_ms).sum();
        Self {
            passes,
            original_bytes,
            final_bytes,
            total_delta_bytes: total_delta,
            total_delta_pct: total_pct,
            total_duration_ms: total_ms,
        }
    }

    pub fn to_json(&self) -> String {
        serde_json::to_string_pretty(self).unwrap_or_else(|e| format!("{{\"error\":\"{}\"}}", e))
    }

    pub fn print_summary(&self) {
        eprintln!(
            "Compression: {} → {} bytes ({:+.2}%) in {}ms",
            self.original_bytes, self.final_bytes, self.total_delta_pct, self.total_duration_ms
        );
        for p in &self.passes {
            eprintln!(
                "  pass {}: {} → {} ({:+.2}%) {}ms",
                p.pass, p.bytes_in, p.bytes_out, p.delta_pct, p.duration_ms
            );
        }
    }
}

// ---------------------------------------------------------------------------
// Block-level stats (existing, kept for compatibility)
// ---------------------------------------------------------------------------

pub struct CompressionStats {
    start_time: Instant,
    pub total_blocks: usize,
    pub compressed_blocks: usize,
    pub greedy_matches: usize,
    pub fallback_matches: usize,
    csv: Option<Writer<File>>,
    interval: u64,
}

impl Default for CompressionStats {
    fn default() -> Self {
        Self::new()
    }
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

    pub fn with_csv(path: &str) -> Result<Self, crate::TelomereError> {
        let file = File::create(path).map_err(crate::TelomereError::from)?;
        let mut wtr = Writer::from_writer(file);
        wtr.write_record(&[
            "seconds",
            "total_blocks",
            "compressed_blocks",
            "greedy",
            "fallback",
        ])
        .map_err(|e| crate::TelomereError::Io(std::io::Error::new(std::io::ErrorKind::Other, e)))?;
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
            "Compression: {:.2}s | blocks={} compressed={} ({:.1}%) greedy={} fallback={}",
            elapsed,
            self.total_blocks,
            self.compressed_blocks,
            ratio * 100.0,
            self.greedy_matches,
            self.fallback_matches,
        );
    }
}

pub fn write_stats_csv(stats: &CompressionStats, path: &str) -> Result<(), crate::TelomereError> {
    let elapsed = stats.start_time.elapsed().as_secs_f32();
    let ratio = stats.compressed_blocks as f32 / stats.total_blocks.max(1) as f32;
    let mut wtr = Writer::from_writer(File::create(path).map_err(crate::TelomereError::from)?);
    wtr.write_record(&[
        "time_s",
        "total_blocks",
        "compressed_blocks",
        "ratio",
        "greedy",
        "fallback",
    ])
    .map_err(|e| crate::TelomereError::Io(std::io::Error::new(std::io::ErrorKind::Other, e)))?;
    wtr.write_record(&[
        format!("{:.2}", elapsed),
        stats.total_blocks.to_string(),
        stats.compressed_blocks.to_string(),
        format!("{:.2}", ratio * 100.0),
        stats.greedy_matches.to_string(),
        stats.fallback_matches.to_string(),
    ])
    .map_err(|e| crate::TelomereError::Io(std::io::Error::new(std::io::ErrorKind::Other, e)))?;
    wtr.flush().map_err(crate::TelomereError::from)?;
    Ok(())
}
