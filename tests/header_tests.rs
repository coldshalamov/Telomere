use telomere::{Header, encode_header, decode_header};

#[test]
fn header_roundtrip_across_ranges() {
    let cases = vec![
        Header::Arity(1),
        Header::Arity(2),
        Header::Arity(3),
        Header::Arity(4),
        Header::Literal,
    ];
    for h in cases {
        let enc = encode_header(&h).unwrap();
        let (decoded, _) = decode_header(&enc).expect("decode failed");
        assert_eq!(h, decoded);
    }
}
