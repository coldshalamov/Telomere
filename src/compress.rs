use crate::compress_stats::CompressionStats;
use crate::header::{encode_header, Header};
use crate::tlmr::{encode_tlmr_header, truncated_hash, TlmrHeader};
use crate::TelomereError;

/// Dummy in-memory table placeholder.
#[derive(Default, serde::Serialize, serde::Deserialize)]
pub struct TruncHashTable {
    pub bits: u8,
    pub set: std::collections::HashSet<u64>,
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
    while offset < data.len() {
        let remaining = data.len() - offset;
        let chunk = remaining.min(block_size);
        out.extend_from_slice(&encode_header(&Header::Literal)?);
        out.extend_from_slice(&data[offset..offset + chunk]);
        offset += chunk;
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
    stats: Option<&mut CompressionStats>,
) -> Result<Option<(Header, usize)>, TelomereError> {
    if input.len() < block_size {
        return Ok(None);
    }
    if let Some(s) = stats {
        s.tick_block();
        let slice = &input[..block_size];
        s.maybe_log(slice, slice, false);
        s.log_match(false, 1);
    }
    Ok(Some((Header::Literal, block_size)))
}
