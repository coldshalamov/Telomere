//! High level compression routines used by the Telomere CLI.
//!
//! The main entry point is [`compress`] which implements a minimal
//! stateless recursive compressor. Blocks are hashed and compared
//! against short seeds enumerated in canonical order. Matching spans
//! are replaced with a header referencing the seed while unmatched
//! bytes are emitted as literals. Bundles of up to `block_size` blocks
//! are tried greedily for additional savings.

use crate::compress_stats::CompressionStats;
use crate::header::{encode_header, Header};
use crate::tlmr::{encode_tlmr_header, truncated_hash, TlmrHeader};
use crate::index_to_seed;
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
        use crate::io_utils::io_error;
        let p = path.as_ref();
        let bytes = std::fs::read(p).map_err(|e| io_error("reading table file", p, e))?;
        bincode::deserialize(&bytes)
            .map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))
    }

    /// Persist the table to disk using bincode encoding.
    pub fn save<P: AsRef<std::path::Path>>(&self, path: P) -> std::io::Result<()> {
        use crate::io_utils::io_error;
        let p = path.as_ref();
        let bytes = bincode::serialize(self)
            .map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))?;
        std::fs::write(p, bytes).map_err(|e| io_error("writing table file", p, e))
    }
}

/// Generate `len` bytes by repeatedly hashing `seed` with SHA-256.
fn expand_seed(seed: &[u8], len: usize) -> Vec<u8> {
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

/// Find a seed index whose SHA-256 expansion matches the slice.
fn find_seed_match(slice: &[u8], max_seed_len: usize) -> Option<usize> {
    let mut limit = 0usize;
    for len in 1..=max_seed_len {
        limit += 1usize << (8 * len);
    }
    for idx in 0..limit {
        let seed = index_to_seed(idx, max_seed_len);
        if expand_seed(&seed, slice.len()) == slice {
            return Some(idx);
        }
    }
    None
}

/// Compress the input using brute-force seed search with optional bundling.
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
    let max_seed_len = 2;
    let max_arity = block_size;

    while offset < data.len() {
        let remaining = data.len() - offset;
        if remaining < block_size {
            out.extend_from_slice(&encode_header(&Header::LiteralLast));
            out.extend_from_slice(&data[offset..]);
            break;
        }

        let mut matched = false;
        let max_bundle = (remaining / block_size).min(max_arity);
        for arity in (1..=max_bundle).rev() {
            if arity == 2 {
                // arity 2 is reserved for literal spans in the July 2025 protocol
                continue;
            }
            let span_len = arity * block_size;
            let slice = &data[offset..offset + span_len];
            if let Some(seed_idx) = find_seed_match(slice, max_seed_len) {
                let header = Header::Standard { seed_index: seed_idx, arity };
                let hbytes = encode_header(&header);
                if hbytes.len() < span_len {
                    out.extend_from_slice(&hbytes);
                    offset += span_len;
                    matched = true;
                    break;
                }
            }
        }

        if !matched {
            let header = if remaining == block_size { Header::LiteralLast } else { Header::Literal };
            out.extend_from_slice(&encode_header(&header));
            out.extend_from_slice(&data[offset..offset + block_size]);
            offset += block_size;
        }
    }

    out
}

/// Perform multi-pass compression. After the first pass, the result is
/// repeatedly decompressed and recompressed until no further size
/// reduction is observed or `max_passes` is reached.
pub fn compress_multi_pass(
    data: &[u8],
    block_size: usize,
    max_passes: usize,
) -> Result<Vec<u8>, crate::tlmr::TlmrError> {
    let mut compressed = compress(data, block_size);
    if max_passes <= 1 {
        return Ok(compressed);
    }
    let mut prev_size = compressed.len();
    for pass in 2..=max_passes {
        let decompressed = crate::decompress_with_limit(&compressed, usize::MAX)?;
        let new_compressed = compress(&decompressed, block_size);
        if new_compressed.len() < prev_size {
            eprintln!(
                "Pass {}: size {} -> {}",
                pass,
                prev_size,
                new_compressed.len()
            );
            prev_size = new_compressed.len();
            compressed = new_compressed;
        } else {
            break;
        }
    }
    Ok(compressed)
}

/// Compress a single block and return its encoded header and bytes consumed.
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
    }

    let slice = &input[..block_size];
    if let Some(seed_idx) = find_seed_match(slice, 2) {
        let header = Header::Standard { seed_index: seed_idx, arity: 1 };
        let hbytes = encode_header(&header);
        if hbytes.len() < block_size {
            if let Some(s) = stats.as_mut() {
                s.maybe_log(slice, slice, true);
                s.log_match(true, 1);
            }
            return Some((header, block_size));
        }
    }

    if let Some(s) = stats.as_mut() {
        s.maybe_log(slice, slice, false);
        s.log_match(false, 1);
    }

    Some((Header::Literal, block_size))
}
