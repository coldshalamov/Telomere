use telomere::{compress, decompress_with_limit};

#[test]
fn test_compression_roundtrip_stability() {
    // Compressing and then decompressing should yield the original bytes
    let input: Vec<u8> = (0u8..50).collect();
    let compressed = compress(&input, 3).unwrap();
    let decompressed = decompress_with_limit(&compressed, usize::MAX).unwrap();
    assert_eq!(decompressed, input);
}

#[test]
fn test_compression_does_not_modify_input() {
    // The compress function should not mutate the provided input slice
    let original: Vec<u8> = (0u8..30).collect();
    let input_copy = original.clone();
    let _ = compress(&input_copy, 4).unwrap();
    assert_eq!(original, input_copy);
}
