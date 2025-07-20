use telomere::{
    chunk_blocks, load_chunk, TileMap, GpuSeedMatcher, split_into_blocks,
};

#[test]
fn block_chunk_mapping() {
    let input: Vec<u8> = (0u8..64).collect();
    let blocks = split_into_blocks(&input, 8); // 1 byte per block
    let chunks = chunk_blocks(&blocks, 10);
    assert_eq!(chunks.len(), 7);
    let map = TileMap::new(blocks.len(), 10);
    assert_eq!(map.map_global(0), Some((0, 0)));
    assert_eq!(map.map_global(15), Some((1, 5)));
    assert_eq!(map.map_global(63), Some((6, 3)));
    let c3 = load_chunk(&chunks, 3).unwrap();
    assert_eq!(c3.start_index, 30);
    assert_eq!(c3.blocks.len(), 10);
}

#[test]
fn gpu_seed_match_stub() {
    let input: Vec<u8> = (0u8..16).collect();
    let blocks = split_into_blocks(&input, 8); // 1 byte blocks
    let mut matcher = GpuSeedMatcher::new();
    matcher.load_tile(&blocks);
    let gpu_matches = matcher.seed_match(0, 16).unwrap();
    // brute force on CPU for comparison
    let mut cpu_matches = Vec::new();
    for seed in 0usize..16 {
        let seed_byte = seed as u8;
        for block in &blocks {
            let expanded = expand_seed(&[seed_byte], block.data.len());
            if expanded == block.data {
                cpu_matches.push((seed, block.global_index));
            }
        }
    }
    let gpu_flat: Vec<(usize, usize)> = gpu_matches
        .iter()
        .map(|r| (r.seed_index, r.block_indices[0]))
        .collect();
    assert_eq!(cpu_matches, gpu_flat);
}

fn expand_seed(seed: &[u8], len: usize) -> Vec<u8> {
    use sha2::{Digest, Sha256};
    let mut out = Vec::with_capacity(len);
    let mut cur = seed.to_vec();
    while out.len() < len {
        let digest: [u8; 32] = Sha256::digest(&cur).into();
        out.extend_from_slice(&digest);
        cur = digest.to_vec();
    }
    out.truncate(len);
    out
}
