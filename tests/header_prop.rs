use quickcheck::quickcheck;
use telomere::{decode_header, encode_header, Header};

quickcheck! {
<<<<<<< HEAD
    fn header_roundtrip(arity: u8, variant: bool) -> bool {
        if variant {
            let h = Header::Literal;
            let enc = encode_header(&h).unwrap();
            match decode_header(&enc) { Ok((d, _)) => d == h, Err(_) => false }
        } else {
            let a = (arity % 10) + 1;
            let h = Header::Arity(a);
            let enc = encode_header(&h).unwrap();
            match decode_header(&enc) { Ok((d, _)) => d == h, Err(_) => false }
=======
    fn header_roundtrip(arity: u8, is_literal: bool) -> bool {
        if is_literal {
            let h = Header::Literal;
            let enc = encode_header(&h).unwrap();
            return matches!(decode_header(&enc), Ok((d, _)) if d == h);
>>>>>>> main
        }
        let a = (arity % 6) + 1;
        let h = Header::Arity(a);
        let enc = encode_header(&h).unwrap();
        matches!(decode_header(&enc), Ok((d, _)) if d == h)
    }
}
