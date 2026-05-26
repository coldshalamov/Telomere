//! Test that higher max_seed_len produces output that is never larger than
//! lower max_seed_len (more seeds searched → only more compression possible).
//! Uses max_seed_len=1 and max_seed_len=2 for speed.
use telomere::{compress_with_config, tlmr_header_byte_len, Config};

fn cfg(block_size: usize, max_seed_len: usize) -> Config {
    Config {
        block_size,
        max_seed_len,
        hash_bits: 13,
        ..Config::default()
    }
}

#[test]
fn more_seeds_never_expands() {
    let cases: &[&[u8]] = &[&[0u8; 6], &[0xFF; 9], &[0x01, 0x02, 0x03, 0x04, 0x05, 0x06]];
    for &data in cases {
        let out1 = compress_with_config(data, &cfg(3, 1)).unwrap();
        let out2 = compress_with_config(data, &cfg(3, 2)).unwrap();
        assert!(
            out2.len() <= out1.len(),
            "max_seed_len=2 produced larger output than max_seed_len=1 for {:?}",
            data
        );
    }
}

#[test]
fn seed_len_1_roundtrip() {
    let data: Vec<u8> = (0u8..12).collect();
    let c1 = compress_with_config(&data, &cfg(3, 1)).unwrap();
    // Just verify it produces valid output (roundtrip is tested elsewhere).
    assert!(
        c1.len() >= tlmr_header_byte_len(&c1).unwrap(),
        "output must at least contain TlmrHeader"
    );
}
