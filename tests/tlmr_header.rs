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
                    payload_bit_len: 96,
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
fn tlmr_v1_header_starts_with_magic_and_version() {
    // The Lotus-encoded variable-length v1 header replaces the legacy 40-byte
    // fixed layout. The only stable byte-level claim is the 5-byte raw prefix
    // (magic + version); everything after is a Lotus bit stream whose layout
    // changes when the underlying preset changes. We assert the prefix here
    // and rely on roundtrip tests above for full-fidelity field coverage.
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
        payload_bit_len: 120,
        output_hash: 0x0123,
    };
    let enc = encode_tlmr_header(&h);
    assert_eq!(&enc[0..4], b"TLMR");
    assert_eq!(enc[4], TLMR_FORMAT_VERSION);
    // The new header for this typical config must be substantially smaller
    // than the legacy 40-byte fixed layout.
    assert!(
        enc.len() < 20,
        "expected v1 header < 20 bytes, got {}",
        enc.len()
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
        payload_bit_len: (payload.len() as u64) * 8,
        output_hash: truncated_hash_bits(bytes, &expander, 13),
    });
    let mut out = hdr;
    out.extend(payload);
    out
}

#[test]
fn wrong_hash_fails() {
    let bs = 4;
    let data: Vec<u8> = (0u8..10).collect();
    let mut buf = build_data(&data, bs);
    // Flip a bit deep inside the encoded header (well past the magic+version
    // prefix). Some byte index in the middle of the Lotus stream — by this
    // point we're guaranteed to be inside either a field value or the raw
    // hash bits, both of which will fail validation or hash check.
    let flip_idx = buf.len() / 2;
    buf[flip_idx] ^= 0x01;
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
