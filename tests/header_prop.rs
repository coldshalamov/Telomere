use quickcheck::quickcheck;
use telomere::{encode_header, decode_header, Header};

quickcheck! {
    fn header_roundtrip(seed: usize, arity: u8, variant: u8) -> bool {
        let seed = seed % 1_000_000; // keep indices small
        match variant % 3 {
            0 => {
                let a = (arity % 7) + 1;
                let h = Header::Standard { seed_index: seed, arity: a as usize };
                let enc = encode_header(&h);
                match decode_header(&enc) { Ok((d, _)) => d == h, Err(_) => false }
            }
            1 => {
                let h = Header::Literal;
                let enc = encode_header(&h);
                match decode_header(&enc) { Ok((d, _)) => d == h, Err(_) => false }
            }
            _ => {
                let h = Header::LiteralLast;
                let enc = encode_header(&h);
                match decode_header(&enc) { Ok((d, _)) => d == h, Err(_) => false }
            }
        }
    }
}
