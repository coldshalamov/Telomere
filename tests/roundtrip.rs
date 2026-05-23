//! Roundtrip tests — verify compress/decompress identity.
//! Uses max_seed_len=1 for speed (256 seeds per block, < 1 ms).
//! Full max_seed_len=3 is exercised in large_file_perf.rs (slow suite).
use quickcheck::quickcheck;
use telomere::{compress_multi_pass_with_config, decompress, Config};

fn fast_cfg(block_size: usize) -> Config {
    Config {
        block_size,
        max_seed_len: 1, // only 256 seeds per block — roundtrip speed
        hash_bits: 13,
        ..Config::default()
    }
}

quickcheck! {
    fn random_roundtrip(data: Vec<u8>, bs: u8) -> bool {
        let block_size = ((bs % 8) as usize) + 1; // 1..=8
        let cfg = fast_cfg(block_size);
        let (out, _) = compress_multi_pass_with_config(&data, &cfg, 1, false).unwrap();
        match decompress(&out, &cfg) {
            Ok(decoded) => decoded == data,
            Err(_) => false,
        }
    }
}

#[test]
fn fixed_roundtrip_small() {
    let block_size = 3usize;
    let input: Vec<u8> = (0u8..30).collect();
    let cfg = fast_cfg(block_size);
    let (out, _gains) = compress_multi_pass_with_config(&input, &cfg, 1, false).unwrap();
    let decoded = decompress(&out, &cfg).expect("decompress failed");
    assert_eq!(input, decoded);
}

#[test]
fn fixed_roundtrip_empty() {
    let cfg = fast_cfg(4);
    let (out, _) = compress_multi_pass_with_config(&[], &cfg, 1, false).unwrap();
    let decoded = decompress(&out, &cfg).unwrap_or_default();
    assert_eq!(decoded, Vec::<u8>::new());
}

#[test]
fn fixed_roundtrip_repetitive() {
    // Repetitive data is the best case for the generative approach.
    let block_size = 2usize;
    let input: Vec<u8> = std::iter::repeat(0xAAu8).take(20).collect();
    let cfg = fast_cfg(block_size);
    let (out, _) = compress_multi_pass_with_config(&input, &cfg, 3, false).unwrap();
    let decoded = decompress(&out, &cfg).expect("decompress failed on repetitive input");
    assert_eq!(input, decoded);
}
