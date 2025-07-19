use quickcheck::quickcheck;
use telomere::{encode_header, decode_header, Header};

quickcheck! {
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
        }
    }
}
