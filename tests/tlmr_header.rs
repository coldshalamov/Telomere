//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
use telomere::hasher::Sha256Expander;
use telomere::{
    compress, decode_tlmr_header, decompress_with_limit, encode_header, encode_tlmr_header,
    truncated_hash_bits, Config, HasherKind, Header, TlmrHeader, LOTUS_PRESET_VERSION,
    TLMR_FORMAT_VERSION,
};

fn cfg(bs: usize) -> Config {
    Config {
        block_size: bs,
        hash_bits: 13,
        ..Config::default()
    }
}

#[test]
fn header_bit_roundtrip() {
    for hasher in [HasherKind::Blake3, HasherKind::Sha256] {
        for bs in 1usize..=16 {
            for last in 1usize..=bs {
                let h = TlmrHeader {
                    version: TLMR_FORMAT_VERSION,
                    lotus_preset: LOTUS_PRESET_VERSION,
                    hasher,
                    block_size: bs,
                    last_block_size: last,
                    max_seed_len: 1,
                    max_arity: 5,
                    hash_bits: 13,
                    layer_count: 1,
                    original_len: 10,
                    payload_len: 12,
                    output_hash: 0x1FFF,
                };
                let enc = encode_tlmr_header(&h);
                let decoded = decode_tlmr_header(&enc).unwrap();
                assert_eq!(decoded, h);
            }
        }
    }
}

#[test]
fn tlmr_v1_header_golden_bytes() {
    let h = TlmrHeader {
        version: TLMR_FORMAT_VERSION,
        lotus_preset: LOTUS_PRESET_VERSION,
        hasher: HasherKind::Blake3,
        block_size: 4,
        last_block_size: 2,
        max_seed_len: 1,
        max_arity: 5,
        hash_bits: 13,
        layer_count: 1,
        original_len: 10,
        payload_len: 15,
        output_hash: 0x0123,
    };
    let enc = encode_tlmr_header(&h);
    assert_eq!(
        enc,
        vec![
            0x54, 0x4C, 0x4D, 0x52, 0x01, 0x28, 0x01, 0x01, 0x00, 0x04, 0x00, 0x02, 0x01, 0x05,
            0x0D, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x0A, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x0F, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x23,
        ]
    );
    assert_eq!(decode_tlmr_header(&enc).unwrap(), h);
}

fn build_data(bytes: &[u8], bs: usize) -> Vec<u8> {
    let last = if bytes.is_empty() {
        bs
    } else {
        (bytes.len() - 1) % bs + 1
    };

    let expander = Sha256Expander;
    let mut payload = Vec::new();
    let mut offset = 0usize;
    while offset < bytes.len() {
        payload.extend_from_slice(&encode_header(&Header::Literal).unwrap());
        let len = bs.min(bytes.len() - offset);
        payload.extend_from_slice(&bytes[offset..offset + len]);
        offset += len;
    }
    let hdr = encode_tlmr_header(&TlmrHeader {
        version: TLMR_FORMAT_VERSION,
        lotus_preset: LOTUS_PRESET_VERSION,
        hasher: HasherKind::Sha256,
        block_size: bs,
        last_block_size: last,
        max_seed_len: 1,
        max_arity: 5,
        hash_bits: 13,
        layer_count: 1,
        original_len: bytes.len() as u64,
        payload_len: payload.len() as u64,
        output_hash: truncated_hash_bits(bytes, &expander, 13),
    });
    let mut out = hdr;
    out.extend(payload);
    out
}

#[test]
fn wrong_last_block_size_fails() {
    let bs = 4;
    let data: Vec<u8> = (0u8..10).collect();
    let mut buf = build_data(&data, bs);
    // corrupt last block size in header
    buf[0] ^= 0b0001_0000; // tweak block size bits to change last block size
    assert!(decompress_with_limit(&buf, &cfg(bs), usize::MAX).is_err());
}

#[test]
fn wrong_hash_fails() {
    let bs = 4;
    let data: Vec<u8> = (0u8..10).collect();
    let mut buf = build_data(&data, bs);
    // corrupt hash bits
    buf[2] ^= 0x01;
    assert!(decompress_with_limit(&buf, &cfg(bs), usize::MAX).is_err());
}

#[test]
fn random_roundtrip() {
    let bs = 5;
    let data: Vec<u8> = (0u8..37).collect();
    let out = compress(&data, bs).unwrap();
    let decoded = decompress_with_limit(&out, &cfg(bs), usize::MAX).unwrap();
    assert_eq!(data, decoded);
}
