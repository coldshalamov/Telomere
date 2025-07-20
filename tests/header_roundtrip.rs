use quickcheck::quickcheck;
use telomere::{decode_header, encode_header, Header};

#[test]
fn test_literal_header_encode_decode_roundtrip() {
    // Encoding then decoding a literal header should return the same variant
    let header = Header::Literal;
    let encoded = encode_header(&header).unwrap();
    let (decoded, _) = decode_header(&encoded).unwrap();
    assert_eq!(header, decoded);
}

quickcheck! {
    fn arity_header_roundtrip(arity: u8) -> bool {
        let arity = (arity % 5) + 1;
        if arity == 2 {
            return encode_header(&Header::Arity(arity)).is_err();
        }
        let header = Header::Arity(arity);
        let encoded = encode_header(&header).unwrap();
        matches!(decode_header(&encoded), Ok((decoded, _)) if decoded == header)
    }
}

#[test]
fn all_header_forms_roundtrip() {
    for a in [1u8,3,4,5,6] {
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
