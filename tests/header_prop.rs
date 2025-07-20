use quickcheck::quickcheck;
use telomere::{decode_header, encode_header, Header};

quickcheck! {
    fn header_roundtrip(arity: u8, is_literal: bool) -> bool {
        if is_literal {
            let h = Header::Literal;
            let enc = encode_header(&h).unwrap();
            return matches!(decode_header(&enc), Ok((d, _)) if d == h);
        }
        let a = (arity % 5) + 1;
        if a == 2 {
            return encode_header(&Header::Arity(a)).is_err();
        }
        let h = Header::Arity(a);
        let enc = encode_header(&h).unwrap();
        matches!(decode_header(&enc), Ok((d, _)) if d == h)
    }
}
