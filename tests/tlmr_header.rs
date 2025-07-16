use inchworm::{
    decode_tlmr_header, encode_header, encode_tlmr_header, decompress_with_limit,
    truncated_hash, TlmrHeader, compress,
};

#[test]
fn header_bit_roundtrip() {
    for version in 0u8..=7 {
        for bs in 1usize..=16 {
            for last in 1usize..=16 {
                let h = TlmrHeader {
                    version,
                    block_size: bs,
                    last_block_size: last,
                    output_hash: 0x1FFF,
                };
                let enc = encode_tlmr_header(&h);
                let decoded = decode_tlmr_header(&enc).unwrap();
                assert_eq!(decoded, h);
            }
        }
    }
}

fn build_data(bytes: &[u8], bs: usize) -> Vec<u8> {
    let last = if bytes.is_empty() { bs } else { (bytes.len() - 1) % bs + 1 };
    let hdr = encode_tlmr_header(&TlmrHeader { version: 0, block_size: bs, last_block_size: last, output_hash: truncated_hash(bytes) });
    let mut out = hdr.to_vec();
    let mut offset = 0usize;
    while offset + bs <= bytes.len() {
        let blocks = 1usize;
        out.extend_from_slice(&encode_header(0, 28 + blocks));
        out.extend_from_slice(&bytes[offset..offset + bs]);
        offset += bs;
    }
    if offset < bytes.len() {
        out.extend_from_slice(&encode_header(0, 32));
        out.extend_from_slice(&bytes[offset..]);
    }
    out
}

#[test]
fn wrong_last_block_size_fails() {
    let bs = 4;
    let data: Vec<u8> = (0u8..10).collect();
    let mut buf = build_data(&data, bs);
    // corrupt last block size in header
    buf[0] ^= 0b0001_0000; // tweak block size bits to change last block size
    assert!(decompress_with_limit(&buf, usize::MAX).is_err());
}

#[test]
fn wrong_hash_fails() {
    let bs = 4;
    let data: Vec<u8> = (0u8..10).collect();
    let mut buf = build_data(&data, bs);
    // corrupt hash bits
    buf[2] ^= 0x01;
    assert!(decompress_with_limit(&buf, usize::MAX).is_err());
}

#[test]
fn random_roundtrip() {
    let bs = 5;
    let data: Vec<u8> = (0u8..37).collect();
    let out = compress(&data, bs);
    let decoded = decompress_with_limit(&out, usize::MAX).unwrap();
    assert_eq!(data, decoded);
}
