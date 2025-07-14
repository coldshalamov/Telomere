#[test]
fn mixed_gloss_and_passthrough() {
    use inchworm::{compress, decompress};

    let input = b"hello!!!abcxyz!".to_vec(); // "hello!!!" is glossed, rest is passthrough
    let compressed = compress(&input);
    let output = decompress(&compressed);
    assert_eq!(input, output);
}
