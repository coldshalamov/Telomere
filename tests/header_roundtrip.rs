use telomere::{Header, encode_header, decode_header};
use quickcheck::quickcheck;

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
        // Arity is limited to 1-5 according to the spec
        let arity = (arity % 5) + 1;
        let header = Header::Arity(arity);
        let encoded = encode_header(&header).unwrap();
        matches!(decode_header(&encoded), Ok((decoded, _)) if decoded == header)
    }
}
