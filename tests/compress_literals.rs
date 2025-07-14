use inchworm::{compress, decode_header, decompress_with_limit, parse_file_header, Header};

#[test]
fn compress_emits_literal_headers() {
    let block_size = 3; // Or whatever you want to test!
    let data: Vec<u8> = (0u8..50).collect();
    let out = compress(&data, block_size);
    let decompressed = decompress_with_limit(&out, usize::MAX).unwrap();
    assert_eq!(decompressed, data);

    let (mut offset, _, _, _) = parse_file_header(&out).unwrap();
    let mut idx = 0usize;
    while offset < out.len() {
        let (seed, arity, bits) = decode_header(&out[offset..]).unwrap();
        let header = Header {
            seed_index: seed,
            arity,
        };
        offset += (bits + 7) / 8;
        assert_eq!(header.seed_index, 0);
        if header.arity == 40 {
            assert_eq!(&out[offset..], &data[idx..]);
            offset = out.len();
            idx = data.len();
            break;
        } else {
            assert!(header.arity >= 37 && header.arity <= 39);
            let blocks = header.arity - 36;
            let byte_count = blocks * block_size;
            assert_eq!(
                &out[offset..offset + byte_count],
                &data[idx..idx + byte_count]
            );
            offset += byte_count;
            idx += byte_count;
        }
    }
    assert_eq!(idx, data.len());
    assert_eq!(offset, out.len());
}
