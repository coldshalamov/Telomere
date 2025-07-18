use telomere::{compress, decode_tlmr_header, decode_header, decompress_with_limit, Header};

#[test]
fn compress_writes_header_then_data() {
    let block_size = 3;
    let data: Vec<u8> = (0u8..50).collect();
    let out = compress(&data, block_size).unwrap();
    let decompressed = decompress_with_limit(&out, usize::MAX).unwrap();
    assert_eq!(decompressed, data);

    let header = decode_tlmr_header(&out).unwrap();
    assert_eq!(header.block_size, block_size);
    assert_eq!(
        header.last_block_size,
        if data.len() % block_size == 0 {
            block_size
        } else {
            data.len() % block_size
        }
    );
    let mut offset = 3usize;
    let mut idx = 0usize;

    while offset < out.len() {
        let (header, bits) = decode_header(&out[offset..]).unwrap();
        offset += (bits + 7) / 8;
        match header {
            Header::Literal => {
                assert_eq!(&out[offset..offset + block_size], &data[idx..idx + block_size]);
                offset += block_size;
                idx += block_size;
            }
            Header::LiteralLast => {
                assert_eq!(&out[offset..], &data[idx..]);
                idx = data.len();
                offset = out.len();
            }
            _ => panic!("unexpected header"),
        }
    }

    assert_eq!(idx, data.len());
    assert_eq!(offset, out.len());
}

#[test]
fn compress_empty_input() {
    let block_size = 4usize;
    let data: Vec<u8> = Vec::new();
    let out = compress(&data, block_size).unwrap();
    // output should only contain the tlmr header
    assert_eq!(out.len(), 3);
    let decompressed = telomere::decompress(&out);
    assert!(decompressed.is_empty());
}
