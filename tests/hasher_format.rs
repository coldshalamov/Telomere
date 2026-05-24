use telomere::hasher::{SeedExpander, Sha256Expander};
use telomere::{
    compress_multi_pass_with_config, decode_tlmr_header, decompress, Config, HasherKind,
};

fn cfg(hasher: HasherKind) -> Config {
    Config {
        block_size: 4,
        max_seed_len: 1,
        max_arity: 5,
        hash_bits: 13,
        hasher,
        ..Config::default()
    }
}

#[test]
fn header_hasher_metadata_selects_decompression_hasher() {
    let mut data = vec![0u8; 4];
    Sha256Expander.expand_into(&[0x00], &mut data);

    let sha_cfg = cfg(HasherKind::Sha256);
    let wrong_caller_cfg = cfg(HasherKind::Blake3);
    let (compressed, _) = compress_multi_pass_with_config(&data, &sha_cfg, 1, false).unwrap();

    let header = decode_tlmr_header(&compressed).unwrap();
    assert_eq!(header.hasher, HasherKind::Sha256);

    let decoded = decompress(&compressed, &wrong_caller_cfg).unwrap();
    assert_eq!(decoded, data, "v1 files select hasher from header metadata");
}

#[test]
fn corrupt_hasher_metadata_makes_file_not_interchangeable() {
    let mut data = vec![0u8; 4];
    Sha256Expander.expand_into(&[0x01], &mut data);

    let (mut compressed, _) =
        compress_multi_pass_with_config(&data, &cfg(HasherKind::Sha256), 1, false).unwrap();
    compressed[7] = 1; // hasher id: rewrite sha256 to blake3 without changing payload/hash.

    let err = decompress(&compressed, &cfg(HasherKind::Sha256)).unwrap_err();
    assert!(
        err.to_string().contains("output hash mismatch"),
        "unexpected error: {err}"
    );
}
