//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
use telomere::{decode_span, encode_header, BitReader, Config, Header};

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

fn encode_arity_bits(arity: usize) -> Vec<bool> {
    assert!(arity >= 1);
    let mut bits = Vec::new();
    if arity == 1 {
        bits.push(false);
        return bits;
    }
    bits.push(true);
    let index = arity - 1;
    let digit = index % 3;
    let reps = index / 3;
    for _ in 0..reps {
        bits.extend_from_slice(&[true, true]);
    }
    match digit {
        0 => bits.extend_from_slice(&[false, false]),
        1 => bits.extend_from_slice(&[false, true]),
        2 => bits.extend_from_slice(&[true, false]),
        _ => unreachable!(),
    }
    bits
}

fn encode_evql_bits(value: usize) -> Vec<bool> {
    let mut width = 1usize;
    let mut n = 0usize;
    while width < usize::BITS as usize && value >= (1usize << width) {
        width <<= 1;
        n += 1;
    }
    let mut bits = Vec::new();
    for _ in 0..n {
        bits.push(true);
    }
    bits.push(false);
    for i in (0..width).rev() {
        bits.push(((value >> i) & 1) != 0);
    }
    bits
}

#[test]
fn nested_seed_decode() {
    let mut config = Config::default();
    config.block_size = 3;
    config.max_seed_len = 1;

    let stream = {
        let mut bits = encode_arity_bits(1);
        bits.extend(encode_evql_bits(0));
        pack_bits(&bits)
    };

    let expected = telomere::expand_seed(&[0u8], config.block_size, false);
    let mut reader = BitReader::from_slice(&stream);
    let out = decode_span(&mut reader, &config).unwrap();
    assert_eq!(out, expected);
}
