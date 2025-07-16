use inchworm::{compress, decode_header, decode_tlmr_header, decompress_with_limit, Header};

#[test]
fn compress_writes_header_then_data() {
    let block_size = 3;
    let data: Vec<u8> = (0u8..50).collect();
    let out = compress(&data, block_size);
    let decompressed = decompress_with_limit(&out, usize::MAX).unwrap();
    assert_eq!(decompressed, data);

    let header = decode_tlmr_header(&out).unwrap();
    assert_eq!(header.block_size, block_size);
    assert_eq!(header.last_block_size, if data.len() % block_size == 0 { block_size } else { data.len() % block_size });
    let mut offset = 3usize;
    let mut idx = 0usize;

    while offset < out.len() {
        let (seed, arity, bits) = decode_header(&out[offset..]).unwrap();
        let header = Header {
            seed_index: seed,
            arity,
        };
        offset += (bits + 7) / 8;
        assert_eq!(header.seed_index, 0);

        match header.arity {
            29..=31 => {
                let blocks = header.arity - 28;
                let byte_count = blocks * block_size;
                assert_eq!(
                    &out[offset..offset + byte_count],
                    &data[idx..idx + byte_count]
                );
                offset += byte_count;
                idx += byte_count;
            }
            32 => {
                assert_eq!(&out[offset..], &data[idx..]);
                idx = data.len();
                offset = out.len();
            }
            _ => panic!("unexpected arity {}", header.arity),
        }
    }

    assert_eq!(idx, data.len());
    assert_eq!(offset, out.len());
}
