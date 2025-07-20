use telomere::{compress, compress_multi_pass, expand_seed};

#[test]
fn multi_pass_converges() {
    let block_size = 3usize;
    let data = expand_seed(&[0u8], block_size * 3);
    let single = compress(&data, block_size).unwrap();
    let multi = compress_multi_pass(&data, block_size, 5).unwrap();
    assert_eq!(single, multi);
}
