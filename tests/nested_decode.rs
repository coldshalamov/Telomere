use telomere::{decode, BitReader, Config};
use std::collections::HashMap;

// Helper to pack bits big-endian identical to the library implementation
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
    if out.is_empty() { out.push(0); }
    out
}

fn evql_bits(value: usize) -> Vec<bool> {
    let mut width = 1usize;
    let mut n = 0usize;
    while value >= (1usize << width) {
        width <<= 1;
        n += 1;
    }
    let mut bits = vec![true; n];
    bits.push(false);
    for i in (0..width).rev() {
        bits.push(((value >> i) & 1) != 0);
    }
    bits
}

fn byte_bits(b: u8) -> Vec<bool> {
    (0..8).rev().map(|i| ((b >> i) & 1) != 0).collect()
}

#[test]
fn decode_two_level_header() {
    // Build child bitstream: three literal blocks 0x01, 0x02, 0x03
    let mut child_bits = Vec::new();
    for &b in &[0x01u8, 0x02, 0x03] {
        child_bits.extend([true, false]); // arity 2 -> literal
        child_bits.extend(byte_bits(b));
    }
    let child_bytes = pack_bits(&child_bits);

    let mut cfg = Config { block_size: 1, seed_expansions: HashMap::new() };
    cfg.seed_expansions.insert(0, child_bytes);

    // Root header
    let mut bits = Vec::new();
    bits.extend(evql_bits(1)); // block count
    bits.extend([true, true, false, false, false]); // arity 3
    bits.extend(evql_bits(0)); // seed index 0
    let input = pack_bits(&bits);

    let mut reader = BitReader::from_slice(&input);
    let out = decode(&mut reader, &cfg).unwrap();
    assert_eq!(out, vec![0x01, 0x02, 0x03]);
}
