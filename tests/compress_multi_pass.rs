use sha2::{Digest, Sha256};
use telomere::{compress, compress_multi_pass};

fn expand_seed(seed: &[u8], len: usize) -> Vec<u8> {
    let mut out = Vec::with_capacity(len);
    let mut cur = seed.to_vec();
    while out.len() < len {
        let digest: [u8; 32] = Sha256::digest(&cur).into();
        out.extend_from_slice(&digest);
        cur = digest.to_vec();
    }
    out.truncate(len);
    out
}

#[test]
fn multi_pass_converges() {
    let block_size = 3usize;
    let data = expand_seed(&[0u8], block_size * 3);
    let single = compress(&data, block_size).unwrap();
    let multi = compress_multi_pass(&data, block_size, 5).unwrap();
    assert_eq!(single, multi);
}
