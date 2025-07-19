use telomere::{encode_header, decode_header, Header};

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
    if out.is_empty() {
        out.push(0);
    }
    out
}

// Reproduce the EVQL bitstream for a seed index
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

#[test]
fn arity_bit_patterns() {
    // Expected toggle patterns for arity values using the 2025 scheme
    // 1 -> 0
    // literal -> 1 0
    // 3 -> 1 1 000
    // 4 -> 1 1 001
    // 5 -> 1 1 010
    // 6 -> 1 1 011
    // 7 -> 1 1 100
    // 8 -> 1 1 101
    // 9 -> 1 1 110
    // 10 -> 1 1 1110
    let patterns: &[(usize, &[bool])] = &[
        (1, &[false]),
        (3, &[true, true, false, false]),
        (4, &[true, true, false, true]),
        (5, &[true, true, true, false, false, false]),
        (6, &[true, true, true, false, false, true]),
        (7, &[true, true, true, false, true, false]),
        (8, &[true, true, true, false, true, true]),
        (9, &[true, true, true, true, false, false, false]),
        (10, &[true, true, true, true, false, false, true]),
    ];

    let small_seed = 3usize;
    let large_seed = 1_000_000usize;

    for &(arity, bits) in patterns {
        // Small seed index pattern
        let mut expected = bits.to_vec();
        expected.extend(evql_bits(small_seed));
        let enc = encode_header(&Header::Standard { seed_index: small_seed, arity }).unwrap();
        assert_eq!(enc, pack_bits(&expected), "arity {} small index", arity);
        let (decoded, _) = decode_header(&enc).unwrap();
        assert_eq!(decoded, Header::Standard { seed_index: small_seed, arity });

        // Large seed index pattern
        let mut expected_big = bits.to_vec();
        expected_big.extend(evql_bits(large_seed));
        let enc_big = encode_header(&Header::Standard { seed_index: large_seed, arity }).unwrap();
        assert_eq!(enc_big, pack_bits(&expected_big), "arity {} large index", arity);
        let (decoded_big, _) = decode_header(&enc_big).unwrap();
        assert_eq!(decoded_big, Header::Standard { seed_index: large_seed, arity });
    }
}

#[test]
fn literal_bit_patterns() {
    let lit = pack_bits(&[true, false]);
    let last = pack_bits(&[true, true, true, true, true, true]);

    assert_eq!(encode_header(&Header::Literal).unwrap(), lit);
    assert_eq!(encode_header(&Header::LiteralLast).unwrap(), last);

    let (dec_lit, _) = decode_header(&lit).unwrap();
    assert_eq!(dec_lit, Header::Literal);
    let (dec_last, _) = decode_header(&last).unwrap();
    assert_eq!(dec_last, Header::LiteralLast);
}

#[test]
fn seed_index_lengths() {
    // EVQL expected bit lengths for various seed indices
    // value -> total bits used by EVQL
    // 0 -> 2, 1 -> 2, 2 -> 4, 3 -> 4, 15 -> 7,
    // 16 -> 12, 255 -> 12, 256 -> 21, 1023 -> 21, 1_000_000 -> 38
    let cases = [
        (0usize, 2usize),
        (1, 2),
        (2, 4),
        (3, 4),
        (15, 7),
        (16, 12),
        (255, 12),
        (256, 21),
        (1023, 21),
        (1_000_000, 38),
    ];

    for &(seed, expected_bits) in &cases {
        let bits = evql_bits(seed);
        assert_eq!(bits.len(), expected_bits, "seed {}", seed);
        let arity_bits = [false]; // arity 1 -> single zero bit
        let mut all = arity_bits.to_vec();
        all.extend(bits.clone());
        let enc = encode_header(&Header::Standard { seed_index: seed, arity: 1 }).unwrap();
        assert_eq!(enc, pack_bits(&all));
        let (dec, used) = decode_header(&enc).unwrap();
        assert_eq!(dec, Header::Standard { seed_index: seed, arity: 1 });
        assert_eq!(used, all.len(), "bit length mismatch for seed {}", seed);
    }
}

#[test]
fn truncated_headers_fail() {
    // Truncate a valid header so not all bits are available
    let full = encode_header(&Header::Standard { seed_index: 1, arity: 3 }).unwrap();
    assert!(decode_header(&full[..0]).is_err());

    // Truncated literal marker
    let lit = encode_header(&Header::Literal).unwrap();
    assert!(decode_header(&lit[..0]).is_err());
}
