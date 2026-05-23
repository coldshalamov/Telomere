//! Real hasher implementations for Telomere seed expansion.
//!
//! BLAKE3 uses its native XOF (extended output function) — arbitrary-length
//! deterministic bytes from any seed, consistent across expand_into and
//! prefix_matches.
//!
//! SHA-256 uses counter mode: each 32-byte chunk is SHA256(seed || counter_le),
//! counter starting at 0.  prefix_matches only needs the first chunk so it
//! stays consistent.

use blake3::Hasher as Blake3Hasher;
use sha2::{Digest, Sha256};

pub trait SeedExpander: Send + Sync {
    /// Fill `out` with deterministic bytes derived from `seed`.
    fn expand_into(&self, seed: &[u8], out: &mut [u8]);

    /// Compute a 256-bit digest of arbitrary data (used for file integrity).
    fn digest(&self, data: &[u8]) -> [u8; 32];

    /// Return true if the first `bits` bits of H(seed) match `target`.
    /// Hot path inside `find_seed_match`.
    fn prefix_matches(&self, seed: &[u8], target: &[u8], bits: usize) -> bool;
}

// ---------------------------------------------------------------------------
// BLAKE3 — XOF path
// ---------------------------------------------------------------------------
pub struct Blake3Expander;

impl SeedExpander for Blake3Expander {
    #[inline]
    fn expand_into(&self, seed: &[u8], out: &mut [u8]) {
        let mut hasher = Blake3Hasher::new();
        hasher.update(seed);
        hasher.finalize_xof().fill(out);
    }

    #[inline]
    fn digest(&self, data: &[u8]) -> [u8; 32] {
        *blake3::hash(data).as_bytes()
    }

    #[inline]
    fn prefix_matches(&self, seed: &[u8], target: &[u8], bits: usize) -> bool {
        if bits == 0 {
            return true;
        }
        let bytes_needed = (bits + 7) / 8;
        if bytes_needed > target.len() {
            return false;
        }
        let mut expanded = vec![0u8; bytes_needed];
        self.expand_into(seed, &mut expanded);
        let full_bytes = bits / 8;
        if expanded[..full_bytes] != target[..full_bytes] {
            return false;
        }
        let rem = bits % 8;
        if rem == 0 {
            return true;
        }
        let mask = 0xFF_u8 << (8 - rem);
        (expanded[full_bytes] & mask) == (target[full_bytes] & mask)
    }
}

// ---------------------------------------------------------------------------
// SHA-256 — counter mode for outputs > 32 bytes
// ---------------------------------------------------------------------------
pub struct Sha256Expander;

impl SeedExpander for Sha256Expander {
    #[inline]
    fn expand_into(&self, seed: &[u8], out: &mut [u8]) {
        // First 32 bytes: plain SHA256(seed) — matches the "natural" SHA256 of seed.
        // Continuation beyond 32 bytes: SHA256(seed || counter_le) for counter 1, 2, …
        let first = Sha256::digest(seed);
        let n = out.len().min(32);
        out[..n].copy_from_slice(&first[..n]);
        if out.len() > 32 {
            let mut counter: u64 = 1;
            let mut pos = 32usize;
            while pos < out.len() {
                let mut h = Sha256::new();
                h.update(seed);
                h.update(counter.to_le_bytes());
                let hash = h.finalize();
                let take = (out.len() - pos).min(32);
                out[pos..pos + take].copy_from_slice(&hash[..take]);
                pos += take;
                counter += 1;
            }
        }
    }

    #[inline]
    fn digest(&self, data: &[u8]) -> [u8; 32] {
        Sha256::digest(data).into()
    }

    #[inline]
    fn prefix_matches(&self, seed: &[u8], target: &[u8], bits: usize) -> bool {
        if bits == 0 {
            return true;
        }
        let bytes_needed = (bits + 7) / 8;
        if bytes_needed > target.len() {
            return false;
        }
        let mut expanded = vec![0u8; bytes_needed];
        self.expand_into(seed, &mut expanded);
        let full_bytes = bits / 8;
        if expanded[..full_bytes] != target[..full_bytes] {
            return false;
        }
        let rem = bits % 8;
        if rem == 0 {
            return true;
        }
        let mask = 0xFF_u8 << (8 - rem);
        (expanded[full_bytes] & mask) == (target[full_bytes] & mask)
    }
}

// ---------------------------------------------------------------------------
// SHA-256 with hardware acceleration note
// The sha2 crate automatically uses x86 SHA-NI instructions when the CPU
// supports them (detected at compile time via RUSTFLAGS="-C target-feature=+sha").
// Sha256NiExpander is a named alias so callers can select it via HasherKind.
// ---------------------------------------------------------------------------
pub struct Sha256NiExpander;

impl SeedExpander for Sha256NiExpander {
    #[inline]
    fn expand_into(&self, seed: &[u8], out: &mut [u8]) {
        Sha256Expander.expand_into(seed, out)
    }
    #[inline]
    fn digest(&self, data: &[u8]) -> [u8; 32] {
        Sha256Expander.digest(data)
    }
    #[inline]
    fn prefix_matches(&self, seed: &[u8], target: &[u8], bits: usize) -> bool {
        Sha256Expander.prefix_matches(seed, target, bits)
    }
}
