//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
use std::collections::{HashMap, HashSet};

/// Record produced by either the CPU or GPU matching pipeline.
#[derive(Debug, Clone)]
pub struct BundleRecord {
    /// Seed identifier of the match.
    pub seed_index: usize,
    /// Number of blocks that make up this bundle.
    pub bundle_length: usize,
    /// All global block indices covered by this bundle.
    pub block_indices: Vec<usize>,
    /// Bit length of the original uncompressed span.
    pub original_bits: usize,
}

/// Final bundle selected for compression.
#[derive(Debug, Clone)]
pub struct AcceptedBundle {
    pub seed_index: usize,
    pub bundle_length: usize,
    pub block_indices: Vec<usize>,
    pub original_bits: usize,
    /// True if this bundle was accepted as a superposition over another.
    pub superposed: bool,
}

/// Greedily select bundles with conflict and superposition handling.
pub fn select_bundles(records: Vec<BundleRecord>) -> Vec<AcceptedBundle> {
    let mut accepted: Vec<AcceptedBundle> = Vec::new();
    let mut ownership: HashMap<usize, usize> = HashMap::new(); // block -> index in accepted

    for rec in records {
        let mut owners = HashSet::new();
        for &b in &rec.block_indices {
            if let Some(&idx) = ownership.get(&b) {
                owners.insert(idx);
            }
        }

        if owners.is_empty() {
            let idx = accepted.len();
            accepted.push(AcceptedBundle {
                seed_index: rec.seed_index,
                bundle_length: rec.bundle_length,
                block_indices: rec.block_indices.clone(),
                original_bits: rec.original_bits,
                superposed: false,
            });
            for &b in &rec.block_indices {
                ownership.insert(b, idx);
            }
            continue;
        }

        if owners.len() > 1 {
            // Ambiguous overlap.
            continue;
        }

        let owner_idx = match owners.iter().next() {
            Some(&idx) => idx,
            None => continue,
        };
        let owner = &accepted[owner_idx];
        let owner_set: HashSet<usize> = owner.block_indices.iter().copied().collect();

        if !rec.block_indices.iter().all(|b| owner_set.contains(b)) {
            // Not a subset of the owner bundle.
            continue;
        }

        if rec.original_bits > owner.original_bits + 8 {
            // Too big to superpose.
            continue;
        }

        // Accept as superposition without claiming blocks.
        println!(
            "[debug] accepting superposition: candidate seed {} over owner seed {}",
            rec.seed_index, owner.seed_index
        );
        accepted.push(AcceptedBundle {
            seed_index: rec.seed_index,
            bundle_length: rec.bundle_length,
            block_indices: rec.block_indices.clone(),
            original_bits: rec.original_bits,
            superposed: true,
        });
    }

    accepted
}
