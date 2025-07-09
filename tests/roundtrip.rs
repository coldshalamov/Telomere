#[test]
fn compression_roundtrip_identity() {
    use inchworm::{compress, decompress, GlossTable};

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
    );

    let gloss = GlossTable::default();
    let reconstructed = decompress(&output, &gloss);
    assert_eq!(input, reconstructed);
}
