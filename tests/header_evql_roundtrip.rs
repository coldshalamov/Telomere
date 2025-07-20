//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
use proptest::prelude::*;
use telomere::{
    decode_arity_bits, decode_evql_bits, encode_arity_bits, encode_evql_bits, BitReader,
};

fn pack(bits: &[bool]) -> Vec<u8> {
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
        out.push(byte << (8 - used));
    }
    if out.is_empty() {
        out.push(0);
    }
    out
}

#[test]
fn arity_roundtrip_exhaustive() {
    for a in 1..=8usize {
        if a == 2 {
            assert!(encode_arity_bits(a).is_err());
            continue;
        }
        let bits = encode_arity_bits(a).unwrap();
        let packed = pack(&bits);
        let mut r = BitReader::from_slice(&packed);
        let decoded = decode_arity_bits(&mut r).unwrap();
        if a == 2 {
            assert_eq!(decoded, None);
        } else {
            assert_eq!(decoded, Some(a));
        }
    }
}

proptest! {
    #![proptest_config(ProptestConfig { cases: 600, .. ProptestConfig::default() })]
    #[test]
    fn evql_roundtrip(v in 0u32..) {
        let bits = encode_evql_bits(v as usize);
        let packed = pack(&bits);
        let mut r = BitReader::from_slice(&packed);
        let out = decode_evql_bits(&mut r).unwrap();
        prop_assert_eq!(out as u32, v);
    }

    #[test]
    fn fuzz_headers(bs in proptest::collection::vec(any::<bool>(), 0..64)) {
        let data = pack(&bs);
        let mut r = BitReader::from_slice(&data);
        let _ = decode_arity_bits(&mut r);
    }

    #[test]
    fn fuzz_safety(bs in proptest::collection::vec(any::<bool>(), 1..32)) {
        let data = pack(&bs);
        let mut r = BitReader::from_slice(&data);
        let pos_before = r.bits_read();
        let res = decode_arity_bits(&mut r);
        prop_assert!(r.bits_read() <= data.len() * 8);
        if let Ok(Some(a)) = res {
            let enc = encode_arity_bits(a).unwrap();
            if bs.len() >= enc.len() {
                prop_assert_eq!(&bs[..enc.len()], &enc[..]);
            }
        } else if let Ok(None) = res {
            let enc = vec![true, false, false];
            if bs.len() >= enc.len() {
                prop_assert_eq!(&bs[..enc.len()], &enc[..]);
            }
        }
        prop_assert!(r.bits_read() >= pos_before);
    }
}

#[test]
fn literal_marker_roundtrip() {
    let mut bits = vec![true, false, false];
    bits.extend(encode_evql_bits(0));
    let packed = pack(&bits);
    let mut r = BitReader::from_slice(&packed);
    assert_eq!(decode_arity_bits(&mut r).unwrap(), None);
    assert_eq!(decode_evql_bits(&mut r).unwrap(), 0);
}

#[test]
fn malformed_headers_error() {
    // never terminating (too many ones)
    let data = pack(&vec![true; 60]);
    let mut r = BitReader::from_slice(&data);
    assert!(decode_arity_bits(&mut r).is_err());
}
