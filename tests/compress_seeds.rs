//! Test that compression finds real seed matches and roundtrips correctly.
//! Uses Blake3Expander to generate target data so the compressor can find seeds.
use telomere::hasher::{Blake3Expander, SeedExpander};
use telomere::{
    compress_multi_pass_with_config, decode_lotus_header, decompress, Config, TLMR_HEADER_LEN,
};

fn blake3_cfg(block_size: usize) -> Config {
    Config {
        block_size,
        max_seed_len: 1, // 256 seeds per block — fast
        hash_bits: 13,
        ..Config::default()
    }
}

fn expand(seed: &[u8], len: usize) -> Vec<u8> {
    let mut out = vec![0u8; len];
    Blake3Expander.expand_into(seed, &mut out);
    out
}

#[test]
fn compress_seeds_literal_roundtrip() {
    // Random-ish bytes: compressor uses literal path, roundtrip still works.
    let cfg = blake3_cfg(3);
    let data: Vec<u8> = (0u8..30).collect();
    let (compressed, _) = compress_multi_pass_with_config(&data, &cfg, 1, false).unwrap();
    let decoded = decompress(&compressed, &cfg).expect("decompress failed");
    assert_eq!(decoded, data);
}

#[test]
fn compress_seeds_known_seed_roundtrip() {
    // Block of 1 byte = BLAKE3([0x00])[0]. The compressor must find seed [0x00] at index 0.
    let cfg = blake3_cfg(1);
    let data = expand(&[0x00], 4); // 4 blocks of 1 byte each
    let (compressed, _) = compress_multi_pass_with_config(&data, &cfg, 1, false).unwrap();
    let decoded = decompress(&compressed, &cfg).expect("decompress failed");
    assert_eq!(decoded, data);
}

#[test]
fn compress_seeds_multi_block_roundtrip() {
    // Mix of blocks that match a known seed and blocks that don't.
    let cfg = blake3_cfg(2);
    let mut data = expand(&[0x00], 2); // 1 block: guaranteed 2-byte match from seed [0x00]
    data.extend_from_slice(&[0xDE, 0xAD]); // 1 block: literal (almost certainly)
    data.extend_from_slice(&expand(&[0x00], 2)); // repeat
    let (compressed, _) = compress_multi_pass_with_config(&data, &cfg, 1, false).unwrap();
    let decoded = decompress(&compressed, &cfg).expect("decompress failed");
    assert_eq!(decoded, data);
}

#[test]
fn compressor_emits_arity_2_when_it_is_the_first_compressive_span() {
    let cfg = Config {
        block_size: 2,
        max_seed_len: 1,
        max_arity: 2,
        hash_bits: 13,
        ..Config::default()
    };
    let data = expand(&[0x42], 4);

    let (compressed, _) = compress_multi_pass_with_config(&data, &cfg, 1, false).unwrap();
    let (first, _) = decode_lotus_header(&compressed[TLMR_HEADER_LEN..]).unwrap();

    assert!(!first.is_literal);
    assert_eq!(first.arity, 2, "arity 2 is a valid compressed span");
    let decoded = decompress(&compressed, &cfg).expect("decompress failed");
    assert_eq!(decoded, data);
}
