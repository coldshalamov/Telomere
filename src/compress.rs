use crate::header::Header;
use crate::BLOCK_SIZE;

use sha2::{Digest, Sha256};
use std::collections::HashMap;

/// Metadata describing a previously discovered compression path.
#[derive(Clone, Debug)]
pub struct ReentryPath {
    /// Sequence of seeds that produced the original compressed span.
    pub seeds: Vec<Vec<u8>>,
    /// Total byte savings of the path when originally discovered.
    pub total_gain: usize,
    /// Number of times this path has been replayed.
    pub replayed: u8,
}

impl ReentryPath {
    /// Average gain per seed for this path.
    fn average_gain(&self) -> f32 {
        if self.seeds.is_empty() {
            0.0
        } else {
            self.total_gain as f32 / self.seeds.len() as f32
        }
    }
}

/// Simple container mapping span hashes to reentry paths.
#[derive(Default)]
pub struct PathGloss {
    pub index: HashMap<[u8; 32], ReentryPath>,
}

/// Result of attempting to compress a span. The `reentered` flag
/// signals that a stored path was reused rather than a fresh search.
pub struct CompressedSpan {
    pub header: Header,
    pub consumed: usize,
    pub reentered: bool,
}

/// Attempt to compress a block of data using previously recorded
/// reentry paths.
///
/// On success the returned [`CompressedSpan`] contains the selected
/// header, number of bytes consumed and a flag indicating a reentry
/// path was used. `None` means the caller should fall back to the
/// regular search logic.
pub fn compress_block(
    input: &[u8],
    paths: &mut PathGloss,
) -> Option<CompressedSpan> {
    // Never attempt reentry for spans smaller than a block.
    if input.len() < BLOCK_SIZE {
        return None;
    }

    // Compute the span hash used to look up previously stored paths.
    let hash: [u8; 32] = Sha256::digest(input).into();

    if let Some(path) = paths.index.get_mut(&hash) {
        // Gate weak paths based on historical gain.
        if path.average_gain() < 0.5 {
            return None;
        }

        // Limit how many times we reuse the same path.
        if path.replayed >= 3 {
            return None;
        }

        // Replay up to three seeds from the path.
        let count = path.seeds.len().min(3);
        let gain = path.total_gain.min(count * BLOCK_SIZE);

        // Only trigger if the path compresses at least one block.
        if gain < BLOCK_SIZE {
            return None;
        }

        path.replayed += 1;

        // Emit a simple header encoding the arity. Seed index is zero
        // because the full seed sequence is stored externally.
        let header = Header {
            seed_index: 0,
            arity: count,
        };
        return Some(CompressedSpan {
            header,
            consumed: count * BLOCK_SIZE,
            reentered: true,
        });
    }

    None
}

