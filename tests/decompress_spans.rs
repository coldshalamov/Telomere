use telomere::{
    decompress_with_limit, encode_arity_bits, encode_evql_bits, encode_header, encode_tlmr_header,
    truncated_hash, Config, Header,
};

fn cfg(block: usize) -> Config {
    Config {
        block_size: block,
        hash_bits: 13,
        ..Config::default()
    }
}

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
fn bundled_span_roundtrip() {
    let block_size = 3usize;
    let seed_block = [0xAAu8, 0xBB, 0xCC];
    let mut config = cfg(block_size);
    config.seed_expansions.insert(0, {
        let mut b = Vec::new();
        for _ in 0..3 {
            b.extend_from_slice(&encode_header(&Header::Literal).unwrap());
            b.extend_from_slice(&seed_block);
        }
        b
    });

    let mut bits = encode_arity_bits(3).unwrap();
    bits.extend(encode_evql_bits(0));
    let body = pack_bits(&bits);

    let mut data = encode_tlmr_header(&telomere::TlmrHeader {
        version: 0,
        block_size,
        last_block_size: block_size,
        output_hash: truncated_hash(&seed_block.repeat(3)),
    })
    .to_vec();
    data.extend_from_slice(&body);

    let out = decompress_with_limit(&data, &config, usize::MAX).unwrap();
    assert_eq!(out, seed_block.repeat(3));
}

#[test]
fn bundled_then_literal() {
    let block_size = 3usize;
    let seed_block = [0x10u8, 0x20, 0x30];
    let tail = [0x40u8, 0x50, 0x60];
    let mut config = cfg(block_size);
    config.seed_expansions.insert(0, {
        let mut b = Vec::new();
        for _ in 0..3 {
            b.extend_from_slice(&encode_header(&Header::Literal).unwrap());
            b.extend_from_slice(&seed_block);
        }
        b
    });

    let mut bits = encode_arity_bits(3).unwrap();
    bits.extend(encode_evql_bits(0));
    let span = pack_bits(&bits);

    let mut body = span.clone();
    body.extend_from_slice(&encode_header(&Header::Literal).unwrap());
    body.extend_from_slice(&tail);

    let mut data = encode_tlmr_header(&telomere::TlmrHeader {
        version: 0,
        block_size,
        last_block_size: block_size,
        output_hash: truncated_hash(&[seed_block.repeat(3), tail.to_vec()].concat()),
    })
    .to_vec();
    data.extend_from_slice(&body);

    let out = decompress_with_limit(&data, &config, usize::MAX).unwrap();
    let mut expected = seed_block.repeat(3);
    expected.extend_from_slice(&tail);
    assert_eq!(out, expected);
}
