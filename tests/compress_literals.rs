use inchworm::{compress, decompress_with_limit, decode_header, Header, BLOCK_SIZE};
use inchworm::gloss::GlossTable;

#[test]
fn compress_emits_literal_headers() {
    let data: Vec<u8> = (0u8..50).collect();
    let mut hashes = 0u64;
    let out = compress(
        &data,
        1..=1,
        None,
        0,
        &mut hashes,
        false,
        0,
        false,
        None,
        None,
        None,
    );
    let table = GlossTable::default();
    let decompressed = decompress_with_limit(&out, &table, usize::MAX).unwrap();
    assert_eq!(decompressed, data);

    let mut offset = 0usize;
    let mut idx = 0usize;
    while offset < out.len() {
        let (seed, arity, bits) = decode_header(&out[offset..]).unwrap();
        let header = Header { seed_index: seed, arity };
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
            let byte_count = blocks * BLOCK_SIZE;
            assert_eq!(&out[offset..offset + byte_count], &data[idx..idx + byte_count]);
            offset += byte_count;
            idx += byte_count;
        }
    }
    assert_eq!(idx, data.len());
    assert_eq!(offset, out.len());
}
