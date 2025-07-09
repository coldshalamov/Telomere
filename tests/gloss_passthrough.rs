#[test]
fn mixed_gloss_and_passthrough() {
    use inchworm::*;

    let entry = GlossEntry {
        seed: vec![0xDE],
        decompressed: b"hello!!!".to_vec(),
    };
    let gloss = GlossTable { entries: vec![entry] };

    let input = b"hello!!!abcxyz!".to_vec(); // "hello!!!" is glossed, rest is passthrough
    let mut counter = 0;
    let compressed = compress(
        &input,
        1..=2,
        None,
        1000,
        &mut counter,
        false,
        Some(&gloss),
        0,
        false,
        None,
        None,
    );
    let output = decompress(&compressed, &gloss);
    assert_eq!(input, output);
}
