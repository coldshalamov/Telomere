use crate::compress_stats::CompressionStats;
use crate::header::{encode_header, Header};
use crate::BLOCK_SIZE;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::{HashMap, HashSet};
use std::ops::RangeInclusive;

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

/// Compress the input using literal passthrough encoding.
/// Each chunk of up to 3 blocks is emitted with a header.
/// Remaining bytes are stored as a literal tail with arity 40.
pub fn compress(
    data: &[u8],
    _lens: RangeInclusive<u8>,
    _limit: Option<u64>,
    _status: u64,
    _hashes: &mut u64,
    _json: bool,
    _gloss: Option<()>, // Placeholder to match signature
    _verbosity: u8,
    _gloss_only: bool,
    _coverage: Option<&mut [bool]>,
    _partials: Option<&mut Vec<u8>>,
    _filter: Option<&mut TruncHashTable>,
) -> Vec<u8> {
    let mut out = Vec::new();
    let mut offset = 0usize;
    while offset + BLOCK_SIZE <= data.len() {
        let remaining_blocks = (data.len() - offset) / BLOCK_SIZE;
        let blocks = remaining_blocks.min(3).max(1);
        let header = encode_header(0, 36 + blocks);
        out.extend_from_slice(&header);
        let bytes = blocks * BLOCK_SIZE;
        out.extend_from_slice(&data[offset..offset + bytes]);
        offset += bytes;
    }
    let header = encode_header(0, 40);
    out.extend_from_slice(&header);
    if offset < data.len() {
        out.extend_from_slice(&data[offset..]);
    }
    out
}

/// Compress a single block and return its encoded header and bytes consumed.
/// Only passthrough matching supported in MVP.
pub fn compress_block(
    input: &[u8],
    _unused: &mut (), // Placeholder to satisfy legacy interface
    _counter: &mut u64,
    _fallback: Option<&mut ()>,
    _current_pass: u64,
    mut stats: Option<&mut CompressionStats>,
    _hash_table: Option<&HashMap<Vec<u8>, [u8; 32]>>,
) -> Option<(Header, usize)> {
    if input.len() < BLOCK_SIZE {
        return None;
    }

    if let Some(s) = stats.as_mut() {
        s.tick_block();
        let span = &input[..BLOCK_SIZE.min(input.len())];
        s.maybe_log(span, span, false);
        s.log_match(false, 1);
    }

    Some((
        Header {
            seed_index: 0,
            arity: 36 + 1,
        },
        BLOCK_SIZE,
    ))
}
