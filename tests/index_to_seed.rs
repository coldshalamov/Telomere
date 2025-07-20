//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
use telomere::index_to_seed;

#[test]
fn basic_indices() {
    assert_eq!(index_to_seed(0, 4).unwrap(), vec![0x00]);
    assert_eq!(index_to_seed(1, 4).unwrap(), vec![0x01]);
    assert_eq!(index_to_seed(255, 4).unwrap(), vec![0xFF]);
    assert_eq!(index_to_seed(256, 4).unwrap(), vec![0x00, 0x00]);
    assert_eq!(index_to_seed(257, 4).unwrap(), vec![0x00, 0x01]);
    assert_eq!(index_to_seed(65791, 4).unwrap(), vec![0xFF, 0xFF]);
    assert_eq!(index_to_seed(65792, 4).unwrap(), vec![0x00, 0x00, 0x00]);
}
