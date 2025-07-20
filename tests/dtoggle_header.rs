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
fn basic_patterns() {
    let cases: &[(Header, &[bool])] = &[
        (Header::Arity(1), &[false]),
        (Header::Arity(3), &[true, false, true, false]),
        (Header::Arity(4), &[true, false, true, true]),
        (Header::Arity(5), &[true, true, false, false, false]),
        (Header::Arity(6), &[true, true, false, false, true]),
        (Header::Arity(7), &[true, true, false, true, false]),
        (Header::Arity(8), &[true, true, false, true, true]),
        (Header::Literal, &[true, false, false]),
    ];
    for (h, bits) in cases {
        let enc = encode_header(h).unwrap();
        assert_eq!(enc, pack_bits(bits));
        let (dec, _) = decode_header(&enc).unwrap();
        assert_eq!(&dec, h);
    }

    // reserved arity value should be rejected
    assert!(encode_header(&Header::Arity(2)).is_err());
    let pattern = pack_bits(&[true, true, true, true, true]);
    assert!(decode_header(&pattern).is_err());
}
