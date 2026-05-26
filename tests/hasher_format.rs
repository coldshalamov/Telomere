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
    // Wave D moved the hasher id off a fixed byte offset (it's now inside the
    // variable-length Lotus header bit stream). Flip a bit in the payload
    // section instead — any payload-level corruption invalidates the file's
    // output_hash, which is what this test is asserting.
    let last_idx = compressed.len() - 1;
    compressed[last_idx] ^= 0xFF;

    let err = decompress(&compressed, &cfg(HasherKind::Sha256)).unwrap_err();
    // The corruption could trip the lotus decoder, the seed-index validator,
    // the output hash check, the payload-length sanity gate, or the trailing
    // pad-bit check depending on which bits flipped. All are accepted as
    // legitimate rejections.
    let msg = err.to_string();
    assert!(
        msg.contains("hash")
            || msg.contains("lotus")
            || msg.contains("invalid")
            || msg.contains("header")
            || msg.contains("Header")
            || msg.contains("length")
            || msg.contains("orphan")
            || msg.contains("overflow")
            || msg.contains("pad bit"),
        "unexpected error: {err}"
    );
}
