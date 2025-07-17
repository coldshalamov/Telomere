//! Candidate representations for a single block and pruning utilities.

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Candidate {
    /// Total encoded length in bits for this representation.
    pub bits_length: usize,
    /// Seed index used for deterministic tie breaking.
    pub seed: usize,
    /// Whether this candidate originates from a bundle spanning multiple blocks.
    pub from_bundle: bool,
}

#[derive(Debug, Clone)]
pub struct Block {
    /// All candidate encodings for this block.
    pub candidates: Vec<Candidate>,
}

/// Prune the candidates for each block after a compression pass.
///
/// - Candidates are sorted by `bits_length` (shortest first; tie broken by
///   `seed` for determinism).
/// - All candidates whose length is more than 8 bits longer than the best are
///   removed.
/// - If any candidate comes from a successful bundle, all non-bundled
///   candidates are discarded, leaving only the bundle representation(s).
pub fn prune_candidates(blocks: &mut [Block]) {
    for block in blocks.iter_mut() {
        if block.candidates.is_empty() {
            continue;
        }

        // Deterministic ordering.
        block.candidates.sort_by(|a, b| {
            a.bits_length
                .cmp(&b.bits_length)
                .then_with(|| a.seed.cmp(&b.seed))
        });

        // Length delta prune.
        let best = block.candidates[0].bits_length;
        block.candidates.retain(|c| c.bits_length <= best + 8);

        // Bundling prune.
        let has_bundle = block.candidates.iter().any(|c| c.from_bundle);
        if has_bundle {
            block.candidates.retain(|c| c.from_bundle);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn prunes_candidates_by_bits_length() {
        let mut blocks = [Block {
            candidates: vec![
                Candidate {
                    bits_length: 24,
                    seed: 1,
                    from_bundle: false,
                },
                Candidate {
                    bits_length: 27,
                    seed: 2,
                    from_bundle: false,
                },
                Candidate {
                    bits_length: 35,
                    seed: 3,
                    from_bundle: false,
                },
            ],
        }];
        prune_candidates(&mut blocks);
        let cands = &blocks[0].candidates;
        assert_eq!(cands.len(), 2);
        assert_eq!(cands[0].bits_length, 24);
        assert_eq!(cands[1].bits_length, 27);
    }

    #[test]
    fn multiple_candidates_within_delta_survive() {
        let mut blocks = [Block {
            candidates: vec![
                Candidate {
                    bits_length: 20,
                    seed: 2,
                    from_bundle: false,
                },
                Candidate {
                    bits_length: 21,
                    seed: 1,
                    from_bundle: false,
                },
            ],
        }];
        prune_candidates(&mut blocks);
        let cands = &blocks[0].candidates;
        assert_eq!(cands.len(), 2);
        assert_eq!(cands[0].bits_length, 20);
        assert_eq!(cands[1].bits_length, 21);
    }

    #[test]
    fn bundle_wipes_out_nonbundles() {
        let mut blocks = [Block {
            candidates: vec![
                Candidate {
                    bits_length: 24,
                    seed: 1,
                    from_bundle: false,
                },
                Candidate {
                    bits_length: 25,
                    seed: 2,
                    from_bundle: true,
                },
                Candidate {
                    bits_length: 30,
                    seed: 3,
                    from_bundle: false,
                },
            ],
        }];
        prune_candidates(&mut blocks);
        let cands = &blocks[0].candidates;
        assert_eq!(cands.len(), 1);
        assert!(cands[0].from_bundle);
    }

    #[test]
    fn pruning_is_deterministic() {
        let template = Block {
            candidates: vec![
                Candidate {
                    bits_length: 20,
                    seed: 2,
                    from_bundle: false,
                },
                Candidate {
                    bits_length: 20,
                    seed: 1,
                    from_bundle: false,
                },
                Candidate {
                    bits_length: 21,
                    seed: 3,
                    from_bundle: false,
                },
            ],
        };
        let mut blocks1 = [template.clone()];
        let mut blocks2 = [template];
        prune_candidates(&mut blocks1);
        prune_candidates(&mut blocks2);
        assert_eq!(blocks1[0].candidates, blocks2[0].candidates);
    }
}
