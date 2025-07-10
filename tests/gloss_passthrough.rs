#[test]
fn mixed_gloss_and_passthrough() {
    use inchworm::*;
    use std::collections::HashMap;

    let entry = GlossEntry {
        seed: vec![0xDE],
        decompressed: b"hello!!!".to_vec(),
        score: 1.0,
        pass: 0,
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
        None,
        &HashMap::new(),
    );
    let output = decompress(&compressed, &gloss);
    assert_eq!(input, output);
}
