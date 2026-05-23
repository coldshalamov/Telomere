//! Random roundtrip tests using rand for reproducibility.
use rand::Rng;
use telomere::{compress_multi_pass_with_config, decompress_with_limit, Config};

fn fast_cfg(block_size: usize) -> Config {
    Config {
        block_size,
        max_seed_len: 1,
        hash_bits: 13,
        ..Config::default()
    }
}

#[test]
fn random_roundtrip() {
    let mut rng = rand::thread_rng();
    for _ in 0..20 {
        let len = rng.gen_range(0..100);
        let block = rng.gen_range(1..8);
        let data: Vec<u8> = (0..len).map(|_| rng.gen::<u8>()).collect();
        let cfg = fast_cfg(block);
        let (out, _) = compress_multi_pass_with_config(&data, &cfg, 1, false).unwrap();
        let decompressed = decompress_with_limit(&out, &cfg, usize::MAX).unwrap();
        assert_eq!(data, decompressed, "len={} block={}", len, block);
    }
}

#[test]
fn known_pattern_roundtrip() {
    // A known byte sequence that is very likely to be all-literal (no seed matches).
    let pattern: [u8; 8] = [0xDE, 0xAD, 0xBE, 0xEF, 0x01, 0x02, 0x03, 0x04];
    let cfg = fast_cfg(4);
    let (out, _) = compress_multi_pass_with_config(&pattern, &cfg, 1, false).unwrap();
    let decoded = decompress_with_limit(&out, &cfg, usize::MAX).unwrap();
    assert_eq!(decoded, pattern);
}
