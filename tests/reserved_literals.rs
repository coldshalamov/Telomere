use inchworm::{decompress_with_limit, encode_file_header};

fn encode_reserved(data: &[u8], block_size: usize) -> Vec<u8> {
    let mut out = encode_file_header(data, block_size);
    let mut offset = 0usize;
    while offset + block_size <= data.len() {
        let remaining_blocks = (data.len() - offset) / block_size;
        let blocks = remaining_blocks.min(3).max(1);
        let code = match blocks {
            1 => 29u8,
            2 => 30u8,
            _ => 31u8,
        };
        out.push(code);
        let bytes = blocks * block_size;
        out.extend_from_slice(&data[offset..offset + bytes]);
        offset += bytes;
    }
    out.push(32u8);
    out.extend_from_slice(&data[offset..]);
    out
}

#[test]
fn reserved_roundtrip_various_lengths() {
    let block_size = 4;
    for len in 1usize..20 {
        let data: Vec<u8> = (0..len as u8).collect();
        let encoded = encode_reserved(&data, block_size);
        let out = decompress_with_limit(&encoded, usize::MAX).unwrap();
        assert_eq!(out, data);
    }
}
