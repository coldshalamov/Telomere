//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
use crate::{compress, TelomereError};

/// Match record produced by the CPU pipeline.
#[derive(Debug, Clone)]
pub struct CpuMatchRecord {
    /// Index of the seed used to generate this match
    pub seed_index: usize,

    /// Number of blocks in the matched bundle
    pub bundle_length: usize,

    /// Vector of all global block indices that are part of this bundle
    pub block_indices: Vec<usize>,

    /// Total number of bits the original blocks occupied (before compression)
    pub original_bits: usize,
}

/// Match record produced by the GPU pipeline.
#[derive(Debug, Clone)]
pub struct GpuMatchRecord {
    /// Index of the seed used by the GPU to generate the match
    pub seed_index: usize,

    /// Number of blocks in the bundle
    pub bundle_length: usize,

    /// Global indices of each block in the bundle (start + stride)
    pub block_indices: Vec<usize>,

    /// Bit size of the original uncompressed bundle
    pub original_bits: usize,
}

/// Compress the input using the experimental hybrid CPU/GPU pipeline.
///
/// This is currently a thin wrapper around [`compress`] and mainly
/// serves as a place holder for the future GPU accelerated search.
pub fn compress_hybrid(data: &[u8], block_size: usize) -> Result<Vec<u8>, TelomereError> {
    // Placeholder for upcoming hybrid bundle coordination:
    // 1. The CPU and GPU will each produce match records in their respective formats.
    // 2. Each record will include: seed_index, bundle_length, original_bits, and all block_indices.
    // 3. We will compute compression gain per record:
    //    gain = original_bits - encoded_bits (encoded_bits = seed_index size + arity header size)
    // 4. All matches will be sorted by gain (descending).
    // 5. Non-overlapping matches will be selected greedily to maximize compression.
    // 6. Block tables will be updated in-place to apply Telomere header rewrites and block deletions.

    // All seed hashing happens on the fly with no disk-based tables. For now we
    // simply delegate to the literal compressor until the generative search is
    // implemented.
    compress(data, block_size)
}
