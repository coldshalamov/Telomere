use telomere::{compress, decode_file_header, decode_header, decompress_with_limit, Header};

#[test]
fn compress_writes_header_then_data() {
    let block_size = 3;
    let data: Vec<u8> = (0u8..50).collect();
    let out = compress(&data, block_size);
    let decompressed = decompress_with_limit(&out, usize::MAX).unwrap();
    assert_eq!(decompressed, data);

    let (mut offset, len, bs) = decode_file_header(&out).unwrap();
    assert_eq!(len, data.len());
    assert_eq!(bs, block_size);
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
