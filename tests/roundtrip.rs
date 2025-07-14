#[test]
fn compression_roundtrip_identity() {
    use inchworm::{compress, decompress};

    let input: Vec<u8> = (0..100u8).collect();

    let output = compress(&input);

    let reconstructed = decompress(&output);
    assert_eq!(input, reconstructed);
}
