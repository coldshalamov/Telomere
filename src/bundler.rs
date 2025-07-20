//! Greedy one-layer bundling logic.
//!
//! After each compression pass the canonical candidate for every block
//! index is known. This module merges adjacent spans if a shorter bundle
//! is available for the combined region. Only a single non-overlapping
//! layer of merges is performed per invocation which makes the operation
//! idempotent.

use std::collections::HashMap;

use crate::types::Candidate;

/// Return the number of original blocks represented by a candidate.
fn blocks_for(c: &Candidate) -> usize {
    if c.arity >= 3 { (c.arity - 1) as usize } else { 1 }
}

/// Greedily merge adjacent spans when a strictly shorter bundle exists.
///
/// * `spans` – canonical candidate for each starting block index in order
/// * `candidates` – optional bundle candidates keyed by `(start, blocks)`
///
/// The returned vector contains the new canonical spans after one bundling
/// layer. Running the function again with the same inputs will yield the same
/// output, proving idempotence.
pub fn bundle_one_layer(
    spans: &[(usize, Candidate)],
    candidates: &HashMap<(usize, usize), Candidate>,
) -> Vec<(usize, Candidate)> {
    // Pre-compute the starting block index for each span.
    let mut start_block = Vec::with_capacity(spans.len());
    let mut block = 0usize;
    for (_, c) in spans.iter() {
        start_block.push(block);
        block += blocks_for(c);
    }

    // Collect all potential merges with their source span range.
    let mut merges: Vec<(usize, usize, Candidate)> = Vec::new();
    for i in 0..spans.len() {
        let mut blocks = 0usize;
        for j in i..spans.len() {
            blocks += blocks_for(&spans[j].1);
            let key = (start_block[i], blocks);
            if let Some(cand) = candidates.get(&key) {
                let child_bits: usize = spans[i..=j].iter().map(|(_, c)| c.bit_len).sum();
                if cand.bit_len < child_bits {
                    merges.push((i, j + 1 - i, cand.clone()));
                }
            }
        }
    }

    // Prefer longer merges and resolve conflicts greedily.
    merges.sort_by(|a, b| b.1.cmp(&a.1).then(a.0.cmp(&b.0)));
    let mut used = vec![false; spans.len()];
    let mut selected: Vec<(usize, usize, Candidate)> = Vec::new();
    for (start, span, cand) in merges.into_iter() {
        if (start..start + span).any(|i| used[i]) {
            continue;
        }
        for i in start..start + span {
            used[i] = true;
        }
        selected.push((start, span, cand));
    }
    selected.sort_by_key(|(s, _, _)| *s);

    // Build the new span list from the selected merges.
    let mut result = Vec::new();
    let mut idx = 0usize;
    let mut sel_idx = 0usize;
    while idx < spans.len() {
        if sel_idx < selected.len() && selected[sel_idx].0 == idx {
            let (start, span, cand) = &selected[sel_idx];
            result.push((spans[*start].0, cand.clone()));
            idx += *span;
            sel_idx += 1;
        } else {
            result.push(spans[idx].clone());
            idx += 1;
        }
    }

    result
}

#[cfg(test)]
mod tests {
    use super::*;
    use quickcheck::quickcheck;
    use std::collections::HashMap;

    #[test]
    fn merge_single_opportunity() {
        // three literal blocks
        let spans = vec![
            (0, Candidate { seed_index: 0, arity: 1, bit_len: 16 }),
            (1, Candidate { seed_index: 1, arity: 1, bit_len: 16 }),
            (2, Candidate { seed_index: 2, arity: 1, bit_len: 16 }),
        ];
        // candidate covering first two blocks
        let mut cand_map = HashMap::new();
        cand_map.insert((0, 2), Candidate { seed_index: 10, arity: 3, bit_len: 30 });

        let out = bundle_one_layer(&spans, &cand_map);
        assert_eq!(out.len(), 2);
        assert_eq!(out[0].0, 0);
        assert_eq!(out[0].1.seed_index, 10);
        assert_eq!(out[0].1.arity, 3);
        assert_eq!(out[1].0, 2);
    }

    #[test]
    fn idempotence() {
        let spans = vec![
            (0, Candidate { seed_index: 0, arity: 1, bit_len: 16 }),
            (1, Candidate { seed_index: 1, arity: 1, bit_len: 16 }),
            (2, Candidate { seed_index: 2, arity: 1, bit_len: 16 }),
        ];
        let mut cand_map = HashMap::new();
        cand_map.insert((0, 2), Candidate { seed_index: 10, arity: 3, bit_len: 30 });

        let once = bundle_one_layer(&spans, &cand_map);
        let twice = bundle_one_layer(&once, &cand_map);
        assert_eq!(once, twice);
    }

    #[test]
    fn reject_incomplete_span() {
        let spans = vec![
            (0, Candidate { seed_index: 0, arity: 1, bit_len: 16 }),
            (1, Candidate { seed_index: 1, arity: 1, bit_len: 16 }),
        ];
        // candidate requires three blocks but only two remain from index 1
        let mut cand_map = HashMap::new();
        cand_map.insert((1, 3), Candidate { seed_index: 10, arity: 4, bit_len: 40 });

        let out = bundle_one_layer(&spans, &cand_map);
        assert_eq!(out, spans);
    }

    quickcheck! {
        fn prop_idempotent(n: u8) -> bool {
            let blocks = (n % 5) + 2;
            let mut spans = Vec::new();
            for i in 0..blocks {
                spans.push((i as usize, Candidate { seed_index: i as u64, arity: 1, bit_len: 16 }));
            }
            let mut cand_map = HashMap::new();
            if blocks >= 2 {
                cand_map.insert((0, 2), Candidate { seed_index: 99, arity: 3, bit_len: 30 });
            }
            let once = bundle_one_layer(&spans, &cand_map);
            let twice = bundle_one_layer(&once, &cand_map);
            once == twice
        }
    }
}
