use telomere::{compress, decode_header, decode_tlmr_header, decompress_with_limit, Header};

#[test]
fn partial_seed_block_falls_back_to_literal() {
    let block_size = 3usize;
    // 1.5 blocks of data derived from a known seed pattern
    let mut data = vec![0u8; block_size];
    data.push(0x01);

    let compressed = compress(&data, block_size).unwrap();
    let hdr = decode_tlmr_header(&compressed).unwrap();
    assert_eq!(hdr.block_size, block_size);

    // Decode body to inspect headers
    let mut offset = 3usize; // skip file header
    let mut headers = Vec::new();
    while offset < compressed.len() {
        let slice = &compressed[offset..];
        let (h, bits) = decode_header(slice).unwrap();
        headers.push(h);
        offset += (bits + 7) / 8;
        if let Header::Literal = headers.last().unwrap() {
            let remaining = compressed.len() - offset;
            let bytes = if remaining == hdr.last_block_size {
                hdr.last_block_size
            } else {
                block_size
            };
            offset += bytes;
        }
    }

    // Expect two literal blocks: the partial tail shouldn't be compressed
    assert_eq!(headers.len(), 2);
    assert!(matches!(headers[0], Header::Literal));
    assert!(matches!(headers[1], Header::Literal));

    // Ensure roundtrip works
    let decompressed = decompress_with_limit(&compressed, usize::MAX).unwrap();
    assert_eq!(decompressed, data);
}
