//! Header encode/decode roundtrip tests for Telomere arity plus Lotus seed indices.
//!
//! As of Wave D, the arity discriminator is routed through the real `lotus`
//! crate using the J1D1 preset (six code points: arities 1..=5 plus the
//! literal escape at value 5). The legacy hand-coded `encode_lotus_arity_bits`
//! helper has been removed.
use telomere::{
    decode_header, decode_lotus_header, encode_header, encode_lotus_header, pack_bits, Header,
};

#[test]
fn literal_header_encodes_and_decodes() {
    let enc = encode_header(&Header::Literal).unwrap();
    let (dec, _bits) = decode_header(&enc).unwrap();
    assert_eq!(dec, Header::Literal);
}

#[test]
fn lotus_arity_headers_roundtrip() {
    // Each arity 1-5 with a small seed index.
    for arity in 1usize..=5 {
        let seed_index = 1;
        let bits = encode_lotus_header(arity, seed_index).unwrap();
        let packed = pack_bits(&bits);
        let (dec, used_bits) = decode_lotus_header(&packed).unwrap();
        assert_eq!(dec.arity as usize, arity, "arity={}", arity);
        assert!(!dec.is_literal);
        assert_eq!(dec.seed_index, seed_index);
        assert_eq!(
            used_bits,
            bits.len(),
            "bits consumed must equal bits emitted for arity={}",
            arity
        );
    }
}

#[test]
fn literal_marker_is_0xff() {
    // The Lotus literal marker uses arity=0xFF, encoded as J1D1 value=5
    // (6 bits with no seed payload).
    let bits = encode_lotus_header(0xFF, 0).unwrap();
    assert_eq!(bits.len(), 6, "literal marker is 6 bits in J1D1");
    let packed = pack_bits(&bits);
    let (dec, used) = decode_lotus_header(&packed).unwrap();
    assert!(dec.is_literal);
    assert_eq!(dec.arity, 0xFF);
    assert_eq!(used, 6);
}

#[test]
fn arity_2_is_valid() {
    // Arity 2 is NOT the literal marker; it is a valid compressed arity.
    let bits = encode_lotus_header(2, 255).unwrap();
    let packed = pack_bits(&bits);
    let (dec, _) = decode_lotus_header(&packed).unwrap();
    assert_eq!(dec.arity, 2);
    assert!(!dec.is_literal);
    assert_eq!(dec.seed_index, 255);
}

#[test]
fn lotus_seed_index_golden_bit_lengths() {
    // Golden bit lengths under the J1D1 arity preset + J3D2 seed preset.
    //
    // J1D1 arity widths:
    //   arity=1 -> value=0 -> 3 bits
    //   arity=2 -> value=1 -> 5 bits
    //   arity=3 -> value=2 -> 5 bits
    //   arity=4 -> value=3 -> 5 bits
    //   arity=5 -> value=4 -> 5 bits
    //   literal -> value=5 -> 6 bits
    //
    // J3D2 seed widths follow the lotus crate's encoding for the chosen
    // payload widths.
    let cases = [
        (1usize, 0u64, 3 + 6),       // arity=1 + tiny seed = 9 bits
        (1usize, 255u64, 3 + 16),    // arity=1 + 1-byte seed value
        (2usize, 255u64, 5 + 16),    // arity=2 + 1-byte seed value
        (3usize, 0u64, 5 + 6),       // arity=3 + tiny seed = 11 bits
        (5usize, 65_535u64, 5 + 25), // arity=5 + 2-byte seed value
    ];

    for (arity, seed_index, expected_bits) in cases {
        let bits = encode_lotus_header(arity, seed_index).unwrap();
        let packed = pack_bits(&bits);
        let (decoded, consumed) = decode_lotus_header(&packed).unwrap();
        assert_eq!(
            bits.len(),
            expected_bits,
            "bit count mismatch for arity={arity} seed_index={seed_index}"
        );
        assert_eq!(consumed, expected_bits);
        assert_eq!(decoded.arity as usize, arity);
        assert_eq!(decoded.seed_index, seed_index);
    }
}

#[test]
fn lotus_seed_index_tier_boundaries_roundtrip() {
    let boundaries = [63u64, 64, 4095, 4096, 65_535, 65_536];

    for seed_index in boundaries {
        let bits = encode_lotus_header(1, seed_index).unwrap();
        let packed = pack_bits(&bits);
        let (decoded, consumed) = decode_lotus_header(&packed).unwrap();
        assert_eq!(consumed, bits.len(), "bit count mismatch at {seed_index}");
        assert_eq!(decoded.arity, 1);
        assert_eq!(
            decoded.seed_index, seed_index,
            "seed index roundtrip failed at J3D2 boundary {seed_index}"
        );
    }
}

#[test]
fn encode_header_literal_only() {
    // encode_header() only supports Header::Literal; Arity must use encode_lotus_header.
    assert!(encode_header(&Header::Literal).is_ok());
}
