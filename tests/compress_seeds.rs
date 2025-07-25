//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
use telomere::{compress, decompress_with_limit, expand_seed, Config};

#[test]
fn compress_seeds_roundtrip() {
    let block_size = 3usize;
    let seed = vec![0u8];
    let data = expand_seed(&seed, block_size * 4, false);
    let compressed = compress(&data, block_size).unwrap();
    let cfg = Config {
        block_size,
        max_seed_len: 3,
        hash_bits: 13,
        ..Config::default()
    };
    let decompressed = decompress_with_limit(&compressed, &cfg, usize::MAX).unwrap();
    assert_eq!(decompressed, data);
}
