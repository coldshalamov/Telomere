//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
use proptest::prelude::*;
use telomere::{decode_header, encode_header, Header};

#[test]
fn test_literal_header_encode_decode_roundtrip() {
    // Encoding then decoding a literal header should return the same variant
    let header = Header::Literal;
    let encoded = encode_header(&header).unwrap();
    let (decoded, _) = decode_header(&encoded).unwrap();
    assert_eq!(header, decoded);
}

proptest! {
    #[test]
    fn arity_header_roundtrip(arity in 0u8..=255) {
        let arity = (arity % 7) + 1;
        if arity == 2 {
            prop_assert!(encode_header(&Header::Arity(arity)).is_err());
        } else {
            let header = Header::Arity(arity);
            let encoded = encode_header(&header).unwrap();
            prop_assert!(matches!(decode_header(&encoded), Ok((decoded, _)) if decoded == header));
        }
    }
}

#[test]
fn all_header_forms_roundtrip() {
    for a in [1u8, 3, 4, 5, 6, 7, 8] {
        let h = Header::Arity(a);
        let enc = encode_header(&h).unwrap();
        let (dec, _) = decode_header(&enc).unwrap();
        assert_eq!(h, dec);
    }
    let lit = Header::Literal;
    let enc = encode_header(&lit).unwrap();
    let (dec, _) = decode_header(&enc).unwrap();
    assert_eq!(lit, dec);
}
