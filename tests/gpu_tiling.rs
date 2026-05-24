//! GPU tiling and block chunk tests.
//! Note: split_into_blocks takes block_size in BITS.
use telomere::{chunk_blocks, load_chunk, split_into_blocks, BlockId, TileMap};

#[test]
fn block_chunk_mapping() {
    // 64 bytes split into 8-bit (1-byte) blocks → 64 blocks
    let input: Vec<u8> = (0u8..64).collect();
    let store = split_into_blocks(&input, 8); // 8 bits = 1 byte per block
    assert_eq!(store.blocks().len(), 64);

    let blocks: Vec<BlockId> = (0..64).map(|i| BlockId(i as u32)).collect();
    let chunks = chunk_blocks(&blocks, 10);
    assert_eq!(chunks.len(), 7); // ceil(64/10) = 7

    let map = TileMap::new(64, 10);
    assert_eq!(map.map_global(0), Some((0, 0)));
    assert_eq!(map.map_global(15), Some((1, 5)));
    assert_eq!(map.map_global(63), Some((6, 3)));

    let c3 = load_chunk(&chunks, 3).unwrap();
    assert_eq!(c3.start_index, 30);
    assert_eq!(c3.blocks.len(), 10);
}

#[test]
fn tile_map_global_mapping() {
    let map = TileMap::new(25, 10); // 25 blocks, tile size 10
    assert_eq!(map.map_global(0), Some((0, 0)));
    assert_eq!(map.map_global(9), Some((0, 9)));
    assert_eq!(map.map_global(10), Some((1, 0)));
    assert_eq!(map.map_global(24), Some((2, 4)));
    assert_eq!(map.map_global(25), None); // out of range
}
