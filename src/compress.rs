use crate::compress_stats::CompressionStats;
use crate::header::{encode_arity_bits, encode_evql_bits, encode_header, Header};
use crate::seed::find_seed_match;
use crate::superposition::SuperpositionManager;
use crate::tlmr::{encode_tlmr_header, truncated_hash, TlmrHeader};
use crate::TelomereError;

/// Dummy in-memory table placeholder.
#[derive(Default, serde::Serialize, serde::Deserialize)]
pub struct TruncHashTable {
    pub bits: u8,
    pub set: std::collections::HashSet<u64>,
}

fn pack_bits(bits: &[bool]) -> Vec<u8> {
    let mut out = Vec::new();
    let mut byte = 0u8;
    let mut used = 0u8;
    for &b in bits {
        byte = (byte << 1) | b as u8;
        used += 1;
        if used == 8 {
            out.push(byte);
            byte = 0;
            used = 0;
        }
    }
    if used > 0 {
        byte <<= 8 - used;
        out.push(byte);
    }
    if out.is_empty() {
        out.push(0);
    }
    out
}

/// Compress the input using literal passthrough blocks and arity-based seed compression.
pub fn compress(data: &[u8], block_size: usize) -> Result<Vec<u8>, TelomereError> {
    let last_block = if data.is_empty() {
        block_size
    } else {
        (data.len() - 1) % block_size + 1
    };
    let header = encode_tlmr_header(&TlmrHeader {
        version: 0,
        block_size,
        last_block_size: last_block,
        output_hash: truncated_hash(data),
    });
    let mut out = header.to_vec();
    let mut offset = 0usize;
    const MAX_ARITY: usize = 6;
    const MAX_SEED_LEN: usize = 3;
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
            if let Some(seed_idx) = find_seed_match(slice, MAX_SEED_LEN)? {
                let header_bits = encode_arity_bits(arity)?;
                let evql_bits = encode_evql_bits(seed_idx);
                let total_bits = header_bits.len() + evql_bits.len();
                if (total_bits + 7) / 8 < span_len {
                    let mut bits = header_bits;
                    bits.extend(evql_bits);
                    out.extend(pack_bits(&bits));
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
pub fn compress_multi_pass(
    data: &[u8],
    block_size: usize,
    max_passes: usize,
) -> Result<(Vec<u8>, Vec<usize>), TelomereError> {
    let mut current = data.to_vec();
    let mut gains = Vec::new();
    let mut passes = 0usize;

    const MAX_ARITY: usize = 6;
    const MAX_SEED_LEN: usize = 3;

    while passes < max_passes {
        passes += 1;
        let mut mgr = SuperpositionManager::new();

        // Split the current stream into fixed sized blocks.
        let mut blocks: Vec<&[u8]> = Vec::new();
        let mut offset = 0usize;
        while offset < current.len() {
            let end = (offset + block_size).min(current.len());
            blocks.push(&current[offset..end]);
            offset += block_size;
        }

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
                if let Some(seed_idx) = find_seed_match(span, MAX_SEED_LEN)? {
                    let header_bits = encode_arity_bits(arity)?;
                    let evql_bits = encode_evql_bits(seed_idx);
                    let total_bits = header_bits.len() + evql_bits.len();
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
        }

        mgr.prune_end_of_pass();

        // Build the next compressed stream from the pruned candidates.
        let last_block = if current.is_empty() {
            block_size
        } else {
            (current.len() - 1) % block_size + 1
        };
        let header = encode_tlmr_header(&TlmrHeader {
            version: 0,
            block_size,
            last_block_size: last_block,
            output_hash: truncated_hash(&current),
        });
        let mut next = header.to_vec();

        let mut i = 0usize;
        while i < blocks.len() {
            let cand = mgr.best_superposed(i).unwrap();
            if cand.seed_index == usize::MAX as u64 {
                // literal
                next.extend_from_slice(&encode_header(&Header::Literal)?);
                next.extend_from_slice(blocks[i]);
                i += 1;
            } else {
                let arity = cand.arity as usize;
                let span_start = i * block_size;
                let _span_end = span_start + arity * block_size;
                let header_bits = encode_arity_bits(arity)?;
                let mut bits = header_bits;
                bits.extend(encode_evql_bits(cand.seed_index as usize));
                next.extend(pack_bits(&bits));
                i += arity;
                // bytes themselves are reconstructed from seed, so nothing appended
            }
        }

        let saved = current.len().saturating_sub(next.len());
        if saved == 0 {
            break;
        }
        gains.push(saved);
        current = next;
    }

    Ok((current, gains))
}

pub fn compress_block(
    input: &[u8],
    block_size: usize,
    mut stats: Option<&mut CompressionStats>,
) -> Result<Option<(Header, usize)>, TelomereError> {
    if input.len() < block_size {
        return Ok(None);
    }
    if let Some(s) = stats.as_deref_mut() {
        s.tick_block();
    }

    let slice = &input[..block_size];
    if let Some(seed_idx) = find_seed_match(slice, 3)? {
        let header_bits = encode_arity_bits(1)?;
        let evql_bits = encode_evql_bits(seed_idx);
        let total_bits = header_bits.len() + evql_bits.len();
        if (total_bits + 7) / 8 < block_size {
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
