//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
use telomere::{compress, decode_header, decode_tlmr_header, expand_seed, index_to_seed, Header};

fn decode_evql_bits(reader: &mut telomere::BitReader) -> usize {
    let mut n = 0usize;
    loop {
        let bit = reader.read_bit().unwrap();
        if bit {
            n += 1;
        } else {
            break;
        }
    }
    let width = 1usize << n;
    let mut value = 0usize;
    for _ in 0..width {
        let b = reader.read_bit().unwrap();
        value = (value << 1) | b as usize;
    }
    value
}

fn decode(data: &[u8], block_size: usize, last_block_size: usize, max_seed_len: usize) -> Vec<u8> {
    let mut offset = 0usize;
    let mut out = Vec::new();
    while offset < data.len() {
        let slice = &data[offset..];
        let (header, bits) = decode_header(slice).unwrap();
        let mut reader = telomere::BitReader::from_slice(slice);
        for _ in 0..bits {
            reader.read_bit().unwrap();
        }
        match header {
            Header::Literal => {
                offset += (bits + 7) / 8;
                let remaining = data.len() - offset;
                let chunk = if remaining == last_block_size {
                    last_block_size
                } else {
                    block_size
                };
                out.extend_from_slice(&data[offset..offset + chunk]);
                offset += chunk;
            }
            Header::Arity(a) => {
                let seed_idx = decode_evql_bits(&mut reader);
                let total_bits = reader.bits_read();
                offset += (total_bits + 7) / 8;
                let seed = index_to_seed(seed_idx, max_seed_len).unwrap();
                out.extend_from_slice(&expand_seed(&seed, a as usize * block_size));
            }
        }
    }
    out
}

#[test]
fn compress_seeds_roundtrip() {
    let block_size = 3usize;
    let seed = vec![0u8];
    let data = expand_seed(&seed, block_size * 4);
    let compressed = compress(&data, block_size).unwrap();
    let hdr = decode_tlmr_header(&compressed).unwrap();
    let body = &compressed[3..];
    let decompressed = decode(body, hdr.block_size, hdr.last_block_size, 3);
    assert_eq!(decompressed, data);
}
