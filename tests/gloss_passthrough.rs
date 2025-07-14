#[test]
fn mixed_gloss_and_passthrough() {
    use inchworm::{compress, decompress};

    let block_size = 3;
    let input = b"hello!!!abcxyz!".to_vec(); // "hello!!!" is glossed, rest is passthrough
    let compressed = compress(&input, block_size);
    let output = decompress(&compressed, block_size);
    assert_eq!(input, output);
}
