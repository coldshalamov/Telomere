use inchworm::gloss::{GlossEntry, GlossTable};

#[test]
fn prune_by_score_and_size() {
    let mut table = GlossTable { entries: Vec::new() };
    table.entries.push(GlossEntry { seed: vec![1], decompressed: vec![1], score: 0.05, pass: 0 });
    table.entries.push(GlossEntry { seed: vec![2], decompressed: vec![2], score: 0.2, pass: 0 });
    table.entries.push(GlossEntry { seed: vec![3], decompressed: vec![3], score: 0.15, pass: 0 });
    table.prune_low_score_entries(0.1, 2);
    assert_eq!(table.entries.len(), 2);
    assert!(table.entries.iter().all(|e| e.score >= 0.1));
    assert!(table.entries.iter().any(|e| e.seed == vec![2]));
}
