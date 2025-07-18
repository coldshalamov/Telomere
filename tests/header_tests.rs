use telomere::{Header, encode_header, decode_header};

#[test]
fn header_roundtrip_across_ranges() {
    let cases = vec![
        Header::Standard { seed_index: 0, arity: 1 },
        Header::Standard { seed_index: 1, arity: 3 },
        Header::Standard { seed_index: 2, arity: 4 },
        Header::Standard { seed_index: 3, arity: 10 },
        Header::Literal,
        Header::LiteralLast,
    ];
    for h in cases {
        let enc = encode_header(&h);
        let (decoded, _) = decode_header(&enc).expect("decode failed");
        assert_eq!(h, decoded);
    }
}
