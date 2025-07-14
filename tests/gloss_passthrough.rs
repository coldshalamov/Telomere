#[test]
fn mixed_gloss_and_passthrough() {
    use inchworm::{compress, decompress};
    use inchworm::gloss::{GlossEntry, GlossTable};

    let entry = GlossEntry {
        seed: vec![0xDE],
        decompressed: b"hello!!!".to_vec(),
        score: 1.0,
        pass: 0,
    };
    let gloss = GlossTable { entries: vec![entry] };

    let input = b"hello!!!abcxyz!".to_vec(); // "hello!!!" is glossed, rest is passthrough
    let compressed = compress(&input);
    let output = decompress(&compressed);
    assert_eq!(input, output);
}
