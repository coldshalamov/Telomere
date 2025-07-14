#[test]
fn compression_roundtrip_identity() {
    use inchworm::{compress, decompress};
    use inchworm::gloss::GlossTable;

    let input: Vec<u8> = (0..100u8).collect();
    let output = compress(&input);

    let gloss = GlossTable::default();
    let reconstructed = decompress(&output);
    assert_eq!(input, reconstructed);
}
