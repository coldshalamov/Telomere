use telomere::{compress, compress_multi_pass, expand_seed};

#[test]
fn multi_pass_converges_without_gain() {
    let block = 3usize;
    let data = expand_seed(&[0u8], block * 3);
    let single = compress(&data, block).unwrap();
    let (multi, gains) = compress_multi_pass(&data, block, 5).unwrap();
    assert_eq!(single, multi);
    assert!(gains.is_empty());
}

#[test]
fn random_input_never_grows() {
    let block = 3usize;
    let mut data = expand_seed(&[2u8], block * 2);
    data.extend_from_slice(&[1, 2, 3]);
    let single = compress(&data, block).unwrap();
    let (multi, gains) = compress_multi_pass(&data, block, 3).unwrap();
    assert!(multi.len() <= single.len());
    assert!(gains.iter().all(|&g| g > 0));
}

#[test]
fn repeated_seeds_gain_over_single_pass() {
    let block = 3usize;
    let mut data = expand_seed(&[1u8], block * 2);
    data.extend_from_slice(&expand_seed(&[1u8], block * 2));
    let single = compress(&data, block).unwrap();
    let (multi, gains) = compress_multi_pass(&data, block, 3).unwrap();
    assert!(multi.len() <= single.len());
    assert!(!gains.is_empty());
}
