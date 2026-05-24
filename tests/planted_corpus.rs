use telomere::{compress_multi_pass_with_config, decompress, Config, HasherKind};

#[test]
fn planted_sha256_arity2_corpus_has_negative_delta() {
    let hex_data: String = include_str!("fixtures/planted_sha256_arity2.hex")
        .split_whitespace()
        .collect();
    let data = hex::decode(hex_data).unwrap();
    let cfg = Config {
        block_size: 2,
        max_seed_len: 1,
        max_arity: 2,
        hash_bits: 13,
        hasher: HasherKind::Sha256,
        ..Config::default()
    };

    let (compressed, _) = compress_multi_pass_with_config(&data, &cfg, 1, false).unwrap();
    assert!(
        compressed.len() < data.len(),
        "planted corpus should demonstrate negative delta: {} !< {}",
        compressed.len(),
        data.len()
    );
    let decoded = decompress(&compressed, &cfg).unwrap();
    assert_eq!(decoded, data);
}
