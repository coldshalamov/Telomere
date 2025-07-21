use telomere::{compress, decompress_with_limit, index_to_seed, expand_seed, Config};

fn cfg(bs: usize, max_seed_len: usize) -> Config {
    Config { block_size: bs, max_seed_len, hash_bits: 13, ..Config::default() }
}

#[test]
fn seed_indices_roundtrip() {
    let block = 3usize;
    let cfg = cfg(block, 3);
    for idx in 0..10usize {
        let seed = index_to_seed(idx, cfg.max_seed_len).unwrap();
        let data = expand_seed(&seed, block);
        let compressed = compress(&data, block).unwrap();
        let out = decompress_with_limit(&compressed, &cfg, usize::MAX).unwrap();
        assert_eq!(out, data);
    }
}
