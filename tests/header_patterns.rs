//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
use telomere::{decode_header, encode_header, Header};

fn pack_bits(bits: &[bool]) -> Vec<u8> {
    let mut out = Vec::new();
    let mut byte = 0u8;
    let mut used = 0u8;
    for &b in bits {
        byte = (byte << 1) | b as u8;
        used += 1;
        if used == 8 {
            out.push(byte);
            byte = 0;
            used = 0;
        }
    }
    if used > 0 {
        byte <<= 8 - used;
        out.push(byte);
    }
    if out.is_empty() {
        out.push(0);
    }
    out
}

#[test]
fn known_patterns_roundtrip() {
    let cases: &[(Header, &[bool])] = &[
        (Header::Arity(1), &[false]),
        (Header::Arity(3), &[true, true, false]),
        (Header::Arity(4), &[true, true, true, false, false]),
        (Header::Literal, &[true, false, false]),
    ];
    for (h, bits) in cases {
        let enc = encode_header(h).unwrap();
        assert_eq!(enc, pack_bits(bits));
        let (dec, _) = decode_header(&enc).unwrap();
        assert_eq!(&dec, h);
    }

    assert!(encode_header(&Header::Arity(2)).is_err());
    let reserved = pack_bits(&[true, false, true]);
    assert!(decode_header(&reserved).is_err());
}

#[test]
fn truncated_headers_fail() {
    let full = encode_header(&Header::Arity(3)).unwrap();
    assert!(decode_header(&full[..0]).is_err());
    let lit = encode_header(&Header::Literal).unwrap();
    assert!(decode_header(&lit[..0]).is_err());
}
