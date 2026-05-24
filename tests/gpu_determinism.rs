//! CPU/GPU matcher parity guard.
//!
//! The `gpu` feature is research-only. This test does not claim GPU output is
//! production-trusted; it requires any enabled GPU backend to agree with the
//! canonical CPU seed search for a small deterministic tile.

use telomere::hasher::{SeedExpander, Sha256Expander};
use telomere::{find_seed_match, split_into_blocks, BlockId, GpuSeedMatcher};

#[test]
fn gpu_matcher_agrees_with_cpu_seed_search_on_small_tile() {
    let expander = Sha256Expander;
    let mut data = Vec::new();
    for seed in [0x00u8, 0x01, 0x02] {
        let mut byte = [0u8; 1];
        expander.expand_into(&[seed], &mut byte);
        data.extend_from_slice(&byte);
    }

    let store = split_into_blocks(&data, 8);
    let blocks: Vec<BlockId> = (0..store.blocks().len())
        .map(|i| BlockId(i as u32))
        .collect();

    let mut matcher = GpuSeedMatcher::new();
    matcher.load_tile(&store, &blocks);
    let gpu_matches = matcher.seed_match(0, 256, &expander).unwrap();

    for block in blocks {
        let bytes = store.get_data(block);
        let expected = find_seed_match(bytes, 1, &expander).unwrap();
        if let Some(seed_index) = expected {
            assert!(
                gpu_matches.iter().any(|record| {
                    record.seed_index == seed_index
                        && record.block_indices == vec![block.0 as usize]
                }),
                "GPU matcher missed CPU seed {seed_index} for block {}",
                block.0
            );
        }
    }
}
