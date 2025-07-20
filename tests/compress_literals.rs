//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
use telomere::{compress, decode_header, decode_tlmr_header, decompress_with_limit, Header, Config};

fn cfg(bs: usize) -> Config {
    Config { block_size: bs, hash_bits: 13, ..Config::default() }
}

#[test]
fn compress_writes_header_then_data() {
    let block_size = 3;
    let data: Vec<u8> = (0u8..50).collect();
    let out = compress(&data, block_size).unwrap();
    let decompressed = decompress_with_limit(&out, &cfg(block_size), usize::MAX).unwrap();
    assert_eq!(decompressed, data);

    let file_hdr = decode_tlmr_header(&out).unwrap();
    assert_eq!(file_hdr.block_size, block_size);
    assert_eq!(
        file_hdr.last_block_size,
        if data.len() % block_size == 0 {
            block_size
        } else {
            data.len() % block_size
        }
    );
    let mut offset = 3usize;
    let mut idx = 0usize;

    while offset < out.len() {
        let (hdr, bits) = decode_header(&out[offset..]).unwrap();
        offset += (bits + 7) / 8;
        match hdr {
            Header::Literal => {
                let remaining = out.len() - offset;
                let bytes = if remaining == file_hdr.last_block_size {
                    file_hdr.last_block_size
                } else {
                    block_size
                };
                assert_eq!(&out[offset..offset + bytes], &data[idx..idx + bytes]);
                offset += bytes;
                idx += bytes;
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
    let decompressed = telomere::decompress(&out, &cfg(block_size)).unwrap();
    assert!(decompressed.is_empty());
}
