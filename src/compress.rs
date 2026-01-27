//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
use crate::compress_stats::CompressionStats;
use crate::config::Config;
use crate::header::{encode_header, encode_lotus_header, pack_bits, Header};
use crate::seed::find_seed_match;
use crate::superposition::SuperpositionManager;
use crate::tlmr::{encode_tlmr_header, truncated_hash, TlmrHeader};
use crate::TelomereError;
use crate::bundler::bundle_one_layer;
use std::collections::HashMap;
use indicatif::{ProgressBar, ProgressStyle};

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
    let block_size = config.block_size;
    let last_block = if data.is_empty() {
        block_size
    } else {
        (data.len() - 1) % block_size + 1
    };
    let expander = config.get_expander();

    let header = encode_tlmr_header(&TlmrHeader {
        version: 0,
        block_size,
        last_block_size: last_block,
        output_hash: truncated_hash(data, expander.as_ref()),
    });
    let mut out = header.to_vec();
    let mut offset = 0usize;
    const MAX_ARITY: usize = 6;
    while offset < data.len() {
        let remaining = data.len() - offset;
        let max_bundle = (remaining / block_size).min(MAX_ARITY);
        let mut matched = false;
        for arity in (1..=max_bundle).rev() {
            if arity == 2 {
                continue; // reserved for literal marker
            }
            let span_len = arity * block_size;
            let slice = &data[offset..offset + span_len];
            if let Some(seed_idx) = find_seed_match(slice, config.max_seed_len, expander.as_ref())?
            {
                // Convert seed index to bits
                let seed_bytes = crate::index_to_seed(seed_idx, config.max_seed_len)?;
                let mut seed_bits = Vec::with_capacity(seed_bytes.len() * 8);
                for byte in seed_bytes {
                    for i in (0..8).rev() {
                        seed_bits.push(((byte >> i) & 1) != 0);
                    }
                }
                
                // Encode using Lotus header
                let total_bits_vec = encode_lotus_header(arity, &seed_bits, seed_bits.len())?;
                if (total_bits_vec.len() + 7) / 8 < span_len {
                    out.extend(pack_bits(&total_bits_vec));
                    offset += span_len;
                    matched = true;
                    break;
                }
            }
        }
        if !matched {
            let chunk = remaining.min(block_size);
            out.extend_from_slice(&encode_header(&Header::Literal)?);
            out.extend_from_slice(&data[offset..offset + chunk]);
            offset += chunk;
        }
    }
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
    let mut current = data.to_vec();
    let mut gains = Vec::new();
    let mut passes = 0usize;

    const MAX_ARITY: usize = 6;
    let block_size = config.block_size;
    
    // Get expander once (assuming it doesn't change per pass)
    let expander = config.get_expander();

    // Memory monitoring
    use sysinfo::{System, SystemExt};
    let mut sys = if config.memory_limit != usize::MAX {
        Some(System::new())
    } else {
        None
    };

    while passes < max_passes {
        if let Some(s) = &mut sys {
            s.refresh_memory();
            let used = s.used_memory() * 1024;
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
            let max_bundle = (remaining / block_size).min(MAX_ARITY);
            for arity in 1..=max_bundle {
                if arity == 2 {
                    continue; // reserved for literal marker
                }
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
            
            // Find best Arity=1
            let best_arity_1 = cands.iter()
                .filter(|c| c.arity == 1)
                .min_by_key(|c| (c.bit_len, c.seed_index))
                .ok_or_else(|| TelomereError::Superposition(format!("no arity 1 candidate at block {i}")))?;
                
            base_spans.push((i, best_arity_1.clone()));
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
        let header = encode_tlmr_header(&TlmrHeader {
            version: 0,
            block_size,
            last_block_size: last_block,
            output_hash: truncated_hash(&current, expander.as_ref()),
        });
        let mut next = header.to_vec();

        for (_idx, cand) in final_spans {
             if cand.seed_index == usize::MAX as u64 {
                // literal
                next.extend_from_slice(&encode_header(&Header::Literal)?);
                // We need to retrieve the original data for this block.
                // _idx is the block index.
                if _idx < blocks.len() {
                    next.extend_from_slice(blocks[_idx]);
                } else {
                     return Err(TelomereError::Internal("literal index out of bounds".into()));
                }
            } else {
                let arity = cand.arity as usize;
                // Reconstruct seed bits from index
                let seed_bytes = crate::index_to_seed(cand.seed_index as usize, config.max_seed_len)?;
                let mut seed_bits = Vec::with_capacity(seed_bytes.len() * 8);
                for byte in seed_bytes {
                     for i in (0..8).rev() {
                        seed_bits.push(((byte >> i) & 1) != 0);
                    }
                }
                let bits = encode_lotus_header(arity, &seed_bits, seed_bits.len())?;
                next.extend(pack_bits(&bits));
            }
        }

        let saved = current.len().saturating_sub(next.len());
        if saved == 0 && passes > 1 {
            break;
        }
        if saved > 0 {
            gains.push(saved);
        }
        current = next;
    }

    Ok((current, gains))
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
    let mut cfg = Config::default();
    cfg.block_size = block_size;
    cfg.max_seed_len = 3;
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
    let mut cfg = Config::default();
    cfg.block_size = block_size;
    cfg.max_seed_len = 3;
    compress_multi_pass_with_config(data, &cfg, max_passes, show_status)
}

/// Wrapper around [`compress_block_with_config`] with the default seed length.
pub fn compress_block(
    input: &[u8],
    block_size: usize,
    stats: Option<&mut CompressionStats>,
) -> Result<Option<(Header, usize)>, TelomereError> {
    let mut cfg = Config::default();
    cfg.block_size = block_size;
    cfg.max_seed_len = 3;
    compress_block_with_config(input, &cfg, stats)
}
