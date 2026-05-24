//! Header encode/decode roundtrip tests for the current Lotus 4-field format.
use telomere::{
    decode_header, decode_lotus_header, encode_header, encode_lotus_arity_bits,
    encode_lotus_header, pack_bits, Header,
};

#[test]
fn literal_header_encodes_and_decodes() {
    let enc = encode_header(&Header::Literal).unwrap();
    let (dec, _bits) = decode_header(&enc).unwrap();
    assert_eq!(dec, Header::Literal);
}

#[test]
fn lotus_arity_field_golden_vectors() {
    let cases = [
        (1usize, false, vec![false]),
        (2usize, false, vec![true]),
        (3usize, true, vec![false, false]),
        (4usize, true, vec![false, true]),
        (5usize, true, vec![true, false]),
        (0xFFusize, true, vec![true, true]),
    ];

    for (arity, expected_mode, expected_bits) in cases {
        let (mode, bits) = encode_lotus_arity_bits(arity).unwrap();
        assert_eq!(mode, expected_mode, "mode for arity {arity}");
        assert_eq!(bits, expected_bits, "bits for arity {arity}");
    }
}

#[test]
fn lotus_arity_headers_roundtrip() {
    // Each arity 1-5 with a trivial 8-bit payload.
    for arity in 1usize..=5 {
        let payload = vec![false, false, false, false, false, false, false, true]; // 8 bits = value 1
        let bits = encode_lotus_header(arity, &payload, payload.len()).unwrap();
        let packed = pack_bits(&bits);
        let (dec, used_bits) = decode_lotus_header(&packed).unwrap();
        assert_eq!(dec.arity as usize, arity, "arity={}", arity);
        assert!(!dec.is_literal);
        assert_eq!(dec.payload_bits, payload);
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
    // The Lotus literal marker uses arity=0xFF (mode=true, bits=[true,true]).
    let bits = encode_lotus_header(0xFF, &[], 0).unwrap();
    assert_eq!(bits.len(), 3, "literal marker is exactly 3 bits");
    let packed = pack_bits(&bits);
    let (dec, used) = decode_lotus_header(&packed).unwrap();
    assert!(dec.is_literal);
    assert_eq!(dec.arity, 0xFF);
    assert_eq!(used, 3);
}

#[test]
fn arity_2_is_valid() {
    // Arity 2 is NOT the literal marker; it is a valid compressed arity.
    let payload = vec![true; 16]; // 16-bit payload
    let bits = encode_lotus_header(2, &payload, payload.len()).unwrap();
    let packed = pack_bits(&bits);
    let (dec, _) = decode_lotus_header(&packed).unwrap();
    assert_eq!(dec.arity, 2);
    assert!(!dec.is_literal);
}

#[test]
fn encode_header_literal_only() {
    // encode_header() only supports Header::Literal; Arity must use encode_lotus_header.
    assert!(encode_header(&Header::Literal).is_ok());
    // No test for Arity since encode_header doesn't support it — use encode_lotus_header.
}
