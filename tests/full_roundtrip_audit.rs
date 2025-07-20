use telomere::{compress_multi_pass, decompress, expand_seed};

#[test]
fn full_roundtrip_audit() {
    let block_size = 3usize;
    let mut data = expand_seed(&[0u8], block_size * 2);
    data.extend_from_slice(&[1, 2, 3, 4, 5]);

    // Compress through multi-pass pipeline.
    let compressed = compress_multi_pass(&data, block_size, 3).unwrap();

    // Decompress back to original bytes.
    let decoded = decompress(&compressed).unwrap();
    assert_eq!(decoded, data);
}
