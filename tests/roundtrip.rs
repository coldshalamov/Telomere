#[test]
fn compression_roundtrip_identity() {
    use inchworm::{compress, decompress};

    let block_size = 3; // or any size you want to test
    let input: Vec<u8> = (0..100u8).collect();

    let output = compress(&input, block_size);
    let reconstructed = decompress(&output);
    assert_eq!(input, reconstructed);
}
