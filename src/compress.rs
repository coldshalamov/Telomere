use crate::header::Header;
use sha2::{Digest, Sha256};
use std::collections::HashSet;

/// In-memory table storing truncated SHA-256 prefixes.
///
/// This is used to skip seed attempts that would produce a digest
/// matching a span we have already observed. The number of bits stored
/// for each entry is configurable via `bits`.
#[derive(Default)]
pub struct TruncHashTable {
    /// Number of bits from the hash digest to store.
    pub bits: u8,
    /// Set of truncated digests.
    pub set: HashSet<u64>,
}

impl TruncHashTable {
    /// Create a new empty table for the given prefix width.
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

    /// Insert an arbitrary byte slice into the table by hashing it and
    /// storing the truncated prefix of the digest.
    pub fn insert_bytes(&mut self, bytes: &[u8]) {
        let digest = Sha256::digest(bytes);
        let arr: [u8; 32] = digest.into();
        let key = self.prefix(&arr);
        self.set.insert(key);
    }

    /// Returns true if the hashed prefix of the provided bytes already
    /// exists in the table.
    pub fn contains_bytes(&self, bytes: &[u8]) -> bool {
        let digest = Sha256::digest(bytes);
        let arr: [u8; 32] = digest.into();
        let key = self.prefix(&arr);
        self.set.contains(&key)
    }
}

/// Attempt to compress a block of data.
///
/// Returns the selected `Header` along with the number of bytes
/// consumed if a compression opportunity is found. `None` indicates
/// that the input should remain uncompressed.
pub fn compress_block(_input: &[u8]) -> Option<(Header, usize)> {
    // Compression logic to be implemented
    None
}

