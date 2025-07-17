use telomere::index_to_seed;

#[test]
fn basic_indices() {
    assert_eq!(index_to_seed(0, 4), vec![0x00]);
    assert_eq!(index_to_seed(1, 4), vec![0x01]);
    assert_eq!(index_to_seed(255, 4), vec![0xFF]);
    assert_eq!(index_to_seed(256, 4), vec![0x00, 0x00]);
    assert_eq!(index_to_seed(257, 4), vec![0x00, 0x01]);
    assert_eq!(index_to_seed(65791, 4), vec![0xFF, 0xFF]);
    assert_eq!(index_to_seed(65792, 4), vec![0x00, 0x00, 0x00]);
}
