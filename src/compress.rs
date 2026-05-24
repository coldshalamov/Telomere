//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
use crate::bundler::bundle_one_layer;
use crate::compress_stats::{CompressionStats, PassStats, RunSummary};
use crate::config::Config;
use crate::header::{encode_header, encode_lotus_header, pack_bits, Header};
use crate::seed::find_seed_match;
use crate::superposition::SuperpositionManager;
use crate::tlmr::{
    encode_tlmr_header, truncated_hash_bits, TlmrHeader, LOTUS_PRESET_VERSION, TLMR_FORMAT_VERSION,
};
use crate::TelomereError;
use indicatif::{ProgressBar, ProgressStyle};
use std::collections::HashMap;
use std::time::Instant;

/// Dummy in-memory table placeholder.
#[derive(Default, serde::Serialize, serde::Deserialize)]
pub struct TruncHashTable {
    pub bits: u8,
    pub set: std::collections::HashSet<u64>,
}

/// Compress the input using literal passthrough blocks and arity-based seed compression.
///
/// Seeds are enumerated deterministically from length `1..=config.max_seed_len`.
/// The search order is consensus critical and must remain stable across
/// implementations.
pub fn compress_with_config(data: &[u8], config: &Config) -> Result<Vec<u8>, TelomereError> {
    let (out, _) = compress_multi_pass_with_config(data, config, 1, false)?;
    Ok(out)
}

/// Apply [`compress`] repeatedly until no further gains are achieved or the
/// provided pass limit is reached.
///
/// Returns the final compressed bytes along with a vector recording the number
/// of bytes saved after each *successful* pass.  The first element corresponds
/// to the second pass since the initial invocation is considered pass `1`.
///
/// All candidate matches for a given block are inserted into the
/// [`SuperpositionManager`] during the pass without pruning. After the entire
/// input has been processed, superpositions are pruned so that only the
/// shortest candidate per block remains. The block table is therefore
/// immutable during a pass and only updated at pass boundaries.
pub fn compress_multi_pass_with_config(
    data: &[u8],
    config: &Config,
    max_passes: usize,
    show_status: bool,
) -> Result<(Vec<u8>, Vec<usize>), TelomereError> {
    config.validate()?;
    if max_passes == 0 {
        return Err(TelomereError::Config(
            "max_passes must be greater than zero".into(),
        ));
    }

    // `.tlmr` v1 is intentionally one-layer-decodable. The pass argument is
    // accepted for CLI compatibility, but recursive output is not emitted until
    // a future format version records and decodes nested layers.
    let pass_limit = max_passes.min(1);
    let mut current = data.to_vec();
    let mut gains = Vec::new();
    let mut passes = 0usize;

    // Get expander once (assuming it doesn't change per pass)
    let expander = config.get_expander();

    // Memory monitoring
    use sysinfo::{System, SystemExt};
    let mut sys = if config.memory_limit != usize::MAX {
        Some(System::new())
    } else {
        None
    };

    while passes < pass_limit {
        if let Some(s) = &mut sys {
            s.refresh_memory();
            let used = s.used_memory(); // sysinfo 0.29: used_memory() returns bytes
            if used > config.memory_limit as u64 {
                return Err(TelomereError::Internal(format!(
                    "Memory limit exceeded: {} > {}",
                    used, config.memory_limit
                )));
            }
        }

        passes += 1;
        // Split the current stream into fixed sized blocks.
        let mut blocks: Vec<&[u8]> = Vec::new();
        let mut offset = 0usize;
        let block_size = config.block_size;
        while offset < current.len() {
            let end = (offset + block_size).min(current.len());
            blocks.push(&current[offset..end]);
            offset += block_size;
        }

        let blocks_total = blocks.len();
        let maybe_pb = if show_status && blocks_total > 0 {
            let pb = ProgressBar::new(blocks_total as u64);
            pb.set_style(
                ProgressStyle::with_template(
                    "{bar:50.cyan/blue} {percent:>3}%  {pos}/{len} blocks",
                )
                .unwrap(),
            );
            Some(pb)
        } else {
            None
        };

        let mut mgr = SuperpositionManager::new(blocks.len());

        // Insert all candidates for each block index.
        for (idx, _slice) in blocks.iter().enumerate() {
            // Literal candidate always exists.
            let lit_bits = _slice.len() * 8 + 3;
            let _ = mgr.insert_superposed(
                idx,
                crate::types::Candidate {
                    seed_index: usize::MAX as u64,
                    arity: 1,
                    bit_len: lit_bits,
                },
            );

            // Seed matches for spans starting at this block.
            let remaining = current.len().saturating_sub(idx * block_size);
            let max_bundle = (remaining / block_size).min(config.max_arity as usize);
            for arity in 1..=max_bundle {
                let span_start = idx * block_size;
                let span_end = span_start + arity * block_size;
                if span_end > current.len() {
                    break;
                }
                let span = &current[span_start..span_end];
                if let Some(seed_idx) =
                    find_seed_match(span, config.max_seed_len, expander.as_ref())?
                {
                    // Convert seed index to bits
                    let seed_bytes = crate::index_to_seed(seed_idx, config.max_seed_len)?;
                    let mut seed_bits = Vec::with_capacity(seed_bytes.len() * 8);
                    for byte in seed_bytes {
                        for i in (0..8).rev() {
                            seed_bits.push(((byte >> i) & 1) != 0);
                        }
                    }

                    let total_bits_vec = encode_lotus_header(arity, &seed_bits, seed_bits.len())?;
                    let total_bits = total_bits_vec.len();

                    if (total_bits + 7) / 8 < span.len() {
                        let _ = mgr.insert_superposed(
                            idx,
                            crate::types::Candidate {
                                seed_index: seed_idx as u64,
                                arity: arity as u8,
                                bit_len: total_bits,
                            },
                        );
                    }
                }
            }

            if let Some(pb) = &maybe_pb {
                if (idx & 0xF) == 0 {
                    pb.inc(16);
                }
            }
        }

        if config.enable_superposition {
            // No pruning before bundling to maximize options
        } else {
            mgr.prune_end_of_pass();
        }

        if let Some(pb) = &maybe_pb {
            pb.finish_and_clear();
        }

        // --- Bundling Phase ---
        // 1. Construct base spans (best Arity=1 candidate for each block)
        let mut base_spans = Vec::with_capacity(blocks.len());
        let all_cands = mgr.all_superposed();
        // Sort by block index to ensure we process in order
        let mut all_cands_sorted = all_cands;
        all_cands_sorted.sort_by_key(|(idx, _)| *idx);

        let mut block_cand_map: HashMap<usize, Vec<crate::types::Candidate>> = HashMap::new();
        for (idx, list) in all_cands_sorted {
            let cands = list.into_iter().map(|(_, c)| c).collect();
            block_cand_map.insert(idx, cands);
        }

        for i in 0..blocks.len() {
            let cands = block_cand_map.get(&i).ok_or_else(|| {
                TelomereError::Superposition(format!("no candidate at block {i}"))
            })?;

            // Find best Arity=1. If pruning kept only a longer bundle candidate
            // at this start index, synthesize the literal fallback so the
            // bundler still has a gap-free base layer.
            let best_arity_1 = cands
                .iter()
                .filter(|c| c.arity == 1)
                .min_by_key(|c| (c.bit_len, c.seed_index))
                .cloned()
                .unwrap_or(crate::types::Candidate {
                    seed_index: usize::MAX as u64,
                    arity: 1,
                    bit_len: blocks[i].len() * 8 + 3,
                });

            base_spans.push((i, best_arity_1));
        }

        // 2. Construct bundle candidates (Arity > 1)
        let mut bundle_cands = HashMap::new();
        for (i, cands) in &block_cand_map {
            for c in cands {
                if c.arity > 1 {
                    bundle_cands.insert((*i, c.arity as usize), c.clone());
                }
            }
        }

        // 3. Run Bundler
        let final_spans = bundle_one_layer(&base_spans, &bundle_cands);

        // Build the next compressed stream from the bundled candidates.
        let last_block = if current.is_empty() {
            block_size
        } else {
            (current.len() - 1) % block_size + 1
        };
        let mut payload = Vec::new();

        for (_idx, cand) in final_spans {
            if cand.seed_index == usize::MAX as u64 {
                // literal
                payload.extend_from_slice(&encode_header(&Header::Literal)?);
                // We need to retrieve the original data for this block.
                // _idx is the block index.
                if _idx < blocks.len() {
                    payload.extend_from_slice(blocks[_idx]);
                } else {
                    return Err(TelomereError::Internal(
                        "literal index out of bounds".into(),
                    ));
                }
            } else {
                let arity = cand.arity as usize;
                // Reconstruct seed bits from index
                let seed_bytes =
                    crate::index_to_seed(cand.seed_index as usize, config.max_seed_len)?;
                let mut seed_bits = Vec::with_capacity(seed_bytes.len() * 8);
                for byte in seed_bytes {
                    for i in (0..8).rev() {
                        seed_bits.push(((byte >> i) & 1) != 0);
                    }
                }
                let bits = encode_lotus_header(arity, &seed_bits, seed_bits.len())?;
                payload.extend(pack_bits(&bits));
            }
        }

        let header = encode_tlmr_header(&TlmrHeader {
            version: TLMR_FORMAT_VERSION,
            lotus_preset: LOTUS_PRESET_VERSION,
            hasher: config.hasher,
            block_size,
            last_block_size: last_block,
            max_seed_len: config.max_seed_len,
            max_arity: config.max_arity,
            hash_bits: config.hash_bits,
            layer_count: 1,
            original_len: current.len() as u64,
            payload_len: payload.len() as u64,
            output_hash: truncated_hash_bits(&current, expander.as_ref(), config.hash_bits),
        });
        let mut next = header;
        next.extend(payload);

        let saved = current.len().saturating_sub(next.len());
        if saved > 0 {
            gains.push(saved);
        } else if passes > 1 {
            // Stop after first non-improving pass (convergence).
            // Higher-level callers (compress_with_run_summary) track K-pass convergence.
            break;
        }
        current = next;
    }

    Ok((current, gains))
}

/// Multi-pass compression with per-pass delta stats returned as a [`RunSummary`].
///
/// Each pass is timed independently. Returns the smallest output seen across all
/// passes — if no pass was compressive, returns the first-pass output.
pub fn compress_with_run_summary(
    data: &[u8],
    config: &Config,
    max_passes: usize,
) -> Result<(Vec<u8>, RunSummary), TelomereError> {
    if max_passes == 0 {
        return Err(TelomereError::Config(
            "max_passes must be greater than zero".into(),
        ));
    }
    let original_bytes = data.len();
    let t0 = Instant::now();
    let (out, _) = compress_multi_pass_with_config(data, config, max_passes, false)?;
    let pass_stats = vec![PassStats::new(1, original_bytes, out.len(), t0.elapsed())];
    let summary = RunSummary::new(original_bytes, pass_stats);
    Ok((out, summary))
}

pub fn compress_block_with_config(
    input: &[u8],
    config: &Config,
    mut stats: Option<&mut CompressionStats>,
) -> Result<Option<(Header, usize)>, TelomereError> {
    let block_size = config.block_size;
    if input.len() < block_size {
        return Ok(None);
    }
    if let Some(s) = stats.as_deref_mut() {
        s.tick_block();
    }

    let expander = config.get_expander();

    let slice = &input[..block_size];
    if let Some(seed_idx) = find_seed_match(slice, config.max_seed_len, expander.as_ref())? {
        let seed_bytes = crate::index_to_seed(seed_idx, config.max_seed_len)?;
        let mut seed_bits = Vec::with_capacity(seed_bytes.len() * 8);
        for byte in seed_bytes {
            for i in (0..8).rev() {
                seed_bits.push(((byte >> i) & 1) != 0);
            }
        }
        let total_bits_vec = encode_lotus_header(1, &seed_bits, seed_bits.len())?;

        if (total_bits_vec.len() + 7) / 8 < block_size {
            if let Some(s) = stats.as_deref_mut() {
                s.maybe_log(slice, slice, false);
                s.log_match(false, 1);
            }
            return Ok(Some((Header::Arity(1), block_size)));
        }
    }

    if let Some(s) = stats.as_deref_mut() {
        s.maybe_log(slice, slice, false);
        s.log_match(false, 1);
    }
    Ok(Some((Header::Literal, block_size)))
}

/// Wrapper using the CI default seed length of 3 bytes.
pub fn compress(data: &[u8], block_size: usize) -> Result<Vec<u8>, TelomereError> {
    let cfg = Config {
        block_size,
        max_seed_len: 1,
        ..Config::default()
    };
    const MAX_PASSES: usize = 10;
    let (out, gains) = compress_multi_pass_with_config(data, &cfg, MAX_PASSES, false)?;

    let mut in_len = data.len();
    if gains.is_empty() {
        println!("Compression pass 1: {} bytes → {} bytes", in_len, out.len());
    }
    for (idx, saved) in gains.iter().enumerate() {
        let out_len = in_len.saturating_sub(*saved);
        println!(
            "Compression pass {}: {} bytes → {} bytes",
            idx + 1,
            in_len,
            out_len
        );
        in_len = out_len;
    }

    Ok(out)
}

/// Wrapper around [`compress_multi_pass_with_config`] using a 3 byte seed limit.
pub fn compress_multi_pass(
    data: &[u8],
    block_size: usize,
    max_passes: usize,
    show_status: bool,
) -> Result<(Vec<u8>, Vec<usize>), TelomereError> {
    let cfg = Config {
        block_size,
        max_seed_len: 1,
        ..Config::default()
    };
    compress_multi_pass_with_config(data, &cfg, max_passes, show_status)
}

/// Wrapper around [`compress_block_with_config`] with the default seed length.
pub fn compress_block(
    input: &[u8],
    block_size: usize,
    stats: Option<&mut CompressionStats>,
) -> Result<Option<(Header, usize)>, TelomereError> {
    let cfg = Config {
        block_size,
        max_seed_len: 1,
        ..Config::default()
    };
    compress_block_with_config(input, &cfg, stats)
}
