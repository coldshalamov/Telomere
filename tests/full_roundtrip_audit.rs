use telomere::{
    compress,
    compress_multi_pass,
    decompress,
    decode_header,
    decode_tlmr_header,
    expand_seed,
    Header,
    Config,
};

fn cfg(bs: usize) -> Config {
    Config { block_size: bs, hash_bits: 13, ..Config::default() }
}

#[test]
fn full_roundtrip_audit() {
    let block_size = 3usize;
    let mut data = expand_seed(&[0u8], block_size * 2);
    data.extend_from_slice(&[1, 2, 3, 4, 5]);

    // Compress through multi-pass pipeline.
    let (compressed, _) = compress_multi_pass(&data, block_size, 3).unwrap();

    // Decompress back to original bytes.
    let decoded = decompress(&compressed, &cfg(block_size)).unwrap();
    assert_eq!(decoded, data);
}

#[test]
fn single_block_literal_roundtrip() {
    let block_size = 4usize;
    let data = vec![0xAB, 0xCD, 0xEF, 0x01];
    let compressed = compress(&data, block_size).unwrap();
    let header = decode_tlmr_header(&compressed).unwrap();
    assert_eq!(header.block_size, block_size);
    let _ = decode_header(&compressed[3..]).unwrap();
    let out = decompress(&compressed, &cfg(block_size)).unwrap();
    assert_eq!(out, data);
}

#[test]
fn multi_block_mixed_roundtrip() {
    let block_size = 3usize;
    let mut data = expand_seed(&[1u8], block_size * 3);
    data.extend_from_slice(&[0x10, 0x20, 0x30]);
    let compressed = compress(&data, block_size).unwrap();
    let hdr = decode_tlmr_header(&compressed).unwrap();
    assert_eq!(hdr.block_size, block_size);
    let mut offset = 3usize;
    while offset < compressed.len() {
        let (h, bits) = decode_header(&compressed[offset..]).unwrap();
        offset += (bits + 7) / 8;
        match h {
            Header::Literal => {
                let remaining = compressed.len() - offset;
                let bytes = if remaining == hdr.last_block_size {
                    hdr.last_block_size
                } else {
                    block_size
                };
                offset += bytes;
            }
            Header::Arity(_) => {
                // Skip EVQL bits for the seed index
                offset += 1; // at least one byte is present
            }
        }
    }
    assert_eq!(offset, compressed.len());
    let out = decompress(&compressed, &cfg(block_size)).unwrap();
    assert_eq!(out, data);
}

#[test]
fn partial_compressible_roundtrip() {
    let block_size = 3usize;
    let mut data = expand_seed(&[0u8], block_size);
    data.extend_from_slice(&[0xAA, 0xBB, 0xCC]);
    data.extend_from_slice(&expand_seed(&[0u8], block_size));
    let compressed = compress(&data, block_size).unwrap();
    let out = decompress(&compressed, &cfg(block_size)).unwrap();
    assert_eq!(out, data);
}

#[test]
fn large_file_roundtrip() {
    let block_size = 4usize;
    let data = expand_seed(&[2u8], 1_000_000);
    let compressed = compress(&data, block_size).unwrap();
    let out = decompress(&compressed, &cfg(block_size)).unwrap();
    assert_eq!(out.len(), data.len());
    assert_eq!(out[0..16], data[0..16]);
    assert_eq!(out.last(), data.last());
}

#[test]
fn single_byte_roundtrip() {
    let block_size = 1usize;
    let data = vec![0x7F];
    let compressed = compress(&data, block_size).unwrap();
    let out = decompress(&compressed, &cfg(block_size)).unwrap();
    assert_eq!(out, data);
}
