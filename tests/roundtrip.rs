use quickcheck::quickcheck;
use telomere::{compress, decompress};

quickcheck! {
    fn random_roundtrip(data: Vec<u8>, bs: u8) -> bool {
        let block_size = (bs % 16 + 1) as usize; // limit block size 1..16
        let out = compress(&data, block_size).unwrap();
        let decoded = decompress(&out);
        decoded == data
    }
}

#[test]
fn fixed_roundtrip() {
    let block_size = 3usize;
    let input: Vec<u8> = (0u8..100).collect();
    let out = compress(&input, block_size).unwrap();
    let decoded = decompress(&out);
    assert_eq!(input, decoded);
}
