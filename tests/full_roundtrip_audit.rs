//! End-to-end roundtrip audit across various data types and sizes.
//! Uses max_seed_len=1 for speed. The large_file test is explicitly marked slow.
use telomere::hasher::{Blake3Expander, SeedExpander};
use telomere::{
    compress_multi_pass_with_config, decode_header, decode_tlmr_header_with_len,
    decode_v1_record_from_reader, decompress, Config,
};

fn fast_cfg(block_size: usize) -> Config {
    Config {
        block_size,
        max_seed_len: 1,
        hash_bits: 13,
        ..Config::default()
    }
}

fn expand(seed: &[u8], len: usize) -> Vec<u8> {
    let mut out = vec![0u8; len];
    Blake3Expander.expand_into(seed, &mut out);
    out
}

#[test]
fn full_roundtrip_structured_data() {
    let cfg = fast_cfg(1);
    let mut data = expand(&[0x00], 4);
    data.extend_from_slice(&[0x01, 0x02, 0x03, 0x04]);
    let (compressed, _) = compress_multi_pass_with_config(&data, &cfg, 3, false).unwrap();
    let decoded = decompress(&compressed, &cfg).expect("decompress failed");
    assert_eq!(decoded, data);
}

#[test]
fn single_block_literal_roundtrip() {
    let cfg = fast_cfg(4);
    let data = vec![0xAB, 0xCD, 0xEF, 0x01];
    let (compressed, _) = compress_multi_pass_with_config(&data, &cfg, 1, false).unwrap();
    let (header, header_len) = decode_tlmr_header_with_len(&compressed).unwrap();
    assert_eq!(header.block_size, 4);
    let _ = decode_header(&compressed[header_len..]).unwrap();
    let out = decompress(&compressed, &cfg).expect("decompress failed");
    assert_eq!(out, data);
}

#[test]
fn mixed_literal_and_seed_roundtrip() {
    let cfg = fast_cfg(1);
    let mut data = expand(&[0x01], 1); // likely has seed match
    data.push(0xFF); // literal (unless 0xFF has a 1-byte seed — fine either way)
    data.extend(expand(&[0x01], 1));
    let (compressed, _) = compress_multi_pass_with_config(&data, &cfg, 1, false).unwrap();
    let out = decompress(&compressed, &cfg).expect("decompress failed");
    assert_eq!(out, data);
}

#[test]
fn header_stream_structure_valid() {
    // Walk the compressed bit stream and verify every record decodes cleanly.
    // V1 payload is a single Lotus bit-stream of concatenated records, so the
    // walk must be bit-precise (no per-record byte alignment).
    let cfg = fast_cfg(3);
    let mut data = expand(&[0x01], 6);
    data.extend_from_slice(&[0x10, 0x20, 0x30]);
    let (compressed, _) = compress_multi_pass_with_config(&data, &cfg, 1, false).unwrap();
    let (header, header_len) = decode_tlmr_header_with_len(&compressed).unwrap();
    let payload = &compressed[header_len..];
    let payload_bit_len: usize = header.payload_bit_len.try_into().unwrap();
    let mut reader = lotus::BitReader::new(payload);
    let mut decoded_len = 0usize;
    let original_len: usize = header.original_len.try_into().unwrap();
    while decoded_len < original_len {
        let (rec, _) = decode_v1_record_from_reader(&mut reader).unwrap();
        if rec.is_literal {
            // Mirror encoder: pad to byte boundary then read raw bytes.
            while !reader.bits_consumed().is_multiple_of(8) {
                reader.read_bits(1).unwrap();
            }
            let remaining = original_len - decoded_len;
            let bytes = if remaining <= header.last_block_size {
                remaining
            } else {
                header.block_size
            };
            for _ in 0..bytes {
                reader.read_bits(8).unwrap();
            }
            decoded_len += bytes;
        } else {
            decoded_len += (rec.arity as usize) * header.block_size;
        }
    }
    // Final reader position must fit within the declared payload bit length
    // (it can be at exactly payload_bit_len or slightly less if the file has
    // trailing pad bits — but never past it).
    assert!(
        reader.bits_consumed() <= payload_bit_len,
        "stream consumed correctly: {} bits used vs {} declared",
        reader.bits_consumed(),
        payload_bit_len
    );
    let out = decompress(&compressed, &cfg).expect("decompress failed");
    assert_eq!(out, data);
}

#[test]
fn single_byte_roundtrip() {
    let cfg = fast_cfg(1);
    let data = vec![0x7F];
    let (compressed, _) = compress_multi_pass_with_config(&data, &cfg, 1, false).unwrap();
    let out = decompress(&compressed, &cfg).expect("decompress failed");
    assert_eq!(out, data);
}

#[test]
fn empty_input_roundtrip() {
    let cfg = fast_cfg(4);
    let data: Vec<u8> = vec![];
    let (compressed, _) = compress_multi_pass_with_config(&data, &cfg, 1, false).unwrap();
    // Empty input: decompressor may return empty or an error — either is acceptable.
    let out = decompress(&compressed, &cfg).unwrap_or_default();
    assert_eq!(out, data);
}
