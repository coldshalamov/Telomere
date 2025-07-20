//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
use proptest::prelude::*;
use telomere::{decode_header, encode_header, Header};

proptest! {
    #[test]
    fn header_roundtrip(arity in 0u8..=255, is_literal in proptest::bool::ANY) {
        if is_literal {
            let h = Header::Literal;
            let enc = encode_header(&h).unwrap();
            prop_assert!(matches!(decode_header(&enc), Ok((d, _)) if d == h));
        } else {
            let a = (arity % 5) + 1;
            if a == 2 {
                prop_assert!(encode_header(&Header::Arity(a)).is_err());
            } else {
                let h = Header::Arity(a);
                let enc = encode_header(&h).unwrap();
                prop_assert!(matches!(decode_header(&enc), Ok((d, _)) if d == h));
            }
        }
    }
}
