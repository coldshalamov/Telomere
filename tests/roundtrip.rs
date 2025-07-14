#[test]
fn compression_roundtrip_identity() {
    use inchworm::{compress, decompress};

    let input: Vec<u8> = (0..100u8).collect();
    let mut counter = 0u64;

    let output = compress(
        &input,
        1..=2,
        None,
        1000,
        &mut counter,
        false,
        None,
        0,
        false,
        None,
        None,
        None,
    );

    let reconstructed = decompress(&output);
    assert_eq!(input, reconstructed);
}
