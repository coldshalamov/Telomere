use crate::compress_stats::CompressionStats;
use crate::header::{encode_arity_bits, encode_evql_bits, encode_header, Header};
use crate::seed_index::index_to_seed;
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

fn expand_seed(seed: &[u8], len: usize) -> Vec<u8> {
    use sha2::{Digest, Sha256};
    let mut out = Vec::with_capacity(len);
    let mut cur = seed.to_vec();
    while out.len() < len {
        let digest: [u8; 32] = Sha256::digest(&cur).into();
        out.extend_from_slice(&digest);
        cur = digest.to_vec();
    }
    out.truncate(len);
    out
}

fn find_seed_match(slice: &[u8], _max_seed_len: usize) -> Result<Option<usize>, TelomereError> {
    let seed = [0u8];
    if expand_seed(&seed, slice.len()) == slice {
        return Ok(Some(0));
    }
    Ok(None)
}

/// Compress the input using literal passthrough blocks.
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
                continue;
            }
            let span_len = arity * block_size;
            let slice = &data[offset..offset + span_len];
            if let Some(seed_idx) = find_seed_match(slice, MAX_SEED_LEN)? {
                let header_bits = encode_arity_bits(arity)?;
                let evql_bits = encode_evql_bits(seed_idx);
                let total_bits = header_bits.len() + evql_bits.len();
                if total_bits / 8 < span_len {
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

pub fn compress_multi_pass(
    data: &[u8],
    block_size: usize,
    _max_passes: usize,
) -> Result<Vec<u8>, TelomereError> {
    compress(data, block_size)
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
        if total_bits / 8 < block_size {
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
