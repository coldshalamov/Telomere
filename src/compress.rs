use crate::compress_stats::CompressionStats;
use crate::tlmr::{encode_tlmr_header, truncated_hash, TlmrHeader};
use crate::header::{encode_header, Header};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::HashSet;

/// In-memory table storing truncated SHA-256 prefixes.
#[derive(Default, Serialize, Deserialize)]
pub struct TruncHashTable {
    pub bits: u8,
    pub set: HashSet<u64>,
}

impl TruncHashTable {
    pub fn new(bits: u8) -> Self {
        assert!(bits > 0 && bits <= 64, "bits must be between 1 and 64");
        Self {
            bits,
            set: HashSet::new(),
        }
    }

    fn prefix(&self, digest: &[u8; 32]) -> u64 {
        let mut bytes = [0u8; 8];
        bytes.copy_from_slice(&digest[..8]);
        let mut val = u64::from_be_bytes(bytes);
        if self.bits < 64 {
            val >>= 64 - self.bits as u64;
        }
        val
    }

    pub fn insert_bytes(&mut self, bytes: &[u8]) {
        let digest = Sha256::digest(bytes);
        let arr: [u8; 32] = digest.into();
        let key = self.prefix(&arr);
        self.set.insert(key);
    }

    pub fn contains_bytes(&self, bytes: &[u8]) -> bool {
        let digest = Sha256::digest(bytes);
        let arr: [u8; 32] = digest.into();
        let key = self.prefix(&arr);
        self.set.contains(&key)
    }

    /// Load a serialized table from disk using bincode encoding.
    pub fn load<P: AsRef<std::path::Path>>(path: P) -> std::io::Result<Self> {
        let bytes = std::fs::read(path)?;
        bincode::deserialize(&bytes)
            .map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))
    }

    /// Persist the table to disk using bincode encoding.
    pub fn save<P: AsRef<std::path::Path>>(&self, path: P) -> std::io::Result<()> {
        let bytes = bincode::serialize(self)
            .map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))?;
        std::fs::write(path, bytes)
    }
}

/// Compress the input using literal passthrough headers.
///
/// Literal data is grouped into runs of up to three blocks. Each run is
/// emitted with a header whose arity is 29, 30 or 31. If the final region is
/// shorter than one block, a header with arity 32 precedes the remaining bytes.
pub fn compress(data: &[u8], block_size: usize) -> Vec<u8> {
    let last_block = if data.is_empty() { 0 } else { (data.len() - 1) % block_size + 1 };
    let hash = truncated_hash(data);
    let header_bytes = encode_tlmr_header(&TlmrHeader {
        version: 0,
        block_size,
        last_block_size: if last_block == 0 { block_size } else { last_block },
        output_hash: hash,
    });
    let mut out = header_bytes.to_vec();
    let mut offset = 0usize;
    if data.is_empty() {
        return out;
    }

    while offset < data.len() {
        let remaining = data.len() - offset;
        if remaining <= block_size {
            out.extend_from_slice(&encode_header(&Header::LiteralLast));
            out.extend_from_slice(&data[offset..]);
            break;
        } else {
            out.extend_from_slice(&encode_header(&Header::Literal));
            out.extend_from_slice(&data[offset..offset + block_size]);
            offset += block_size;
        }
    }

    out
}

/// Compress a single block and return its encoded header and bytes consumed.
/// Only passthrough matching supported in MVP.
pub fn compress_block(
    input: &[u8],
    block_size: usize,
    mut stats: Option<&mut CompressionStats>,
) -> Option<(Header, usize)> {
    if input.len() < block_size {
        return None;
    }

    if let Some(s) = stats.as_mut() {
        s.tick_block();
        let span = &input[..block_size.min(input.len())];
        s.maybe_log(span, span, false);
        s.log_match(false, 1);
    }

    Some((Header::Literal, block_size))
}
