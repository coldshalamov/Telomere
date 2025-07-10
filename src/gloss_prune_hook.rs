use crate::gloss::BeliefMap;

/// Invoke gloss pruning at the end of a compression pass.
pub fn run(gloss: &mut BeliefMap) {
    let max_gloss_entries = 10_000_000; // fits in 1GB
    let min_belief_score = 0.10;
    gloss.prune_low_score_entries(min_belief_score, max_gloss_entries);
}
