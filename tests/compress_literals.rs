use inchworm::{compress, decode_file_header, decode_header, decompress_with_limit, Header};

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
        let (seed, arity, bits) = decode_header(&out[offset..]).unwrap();
        let header = Header {
            seed_index: seed,
            arity,
        };
        offset += (bits + 7) / 8;
        assert_eq!(header.seed_index, 0);
        if header.arity == 32 {
            assert_eq!(&out[offset..], &data[idx..]);
            idx = data.len();
            offset = out.len();
            break;
        } else {
            assert!(header.arity >= 29 && header.arity <= 31);
            let blocks = header.arity - 28;
            let bytes = blocks * block_size;
            assert_eq!(&out[offset..offset + bytes], &data[idx..idx + bytes]);
            offset += bytes;
            idx += bytes;
        }
    }
    assert_eq!(idx, data.len());
    assert_eq!(offset, out.len());
}
