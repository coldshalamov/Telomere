use telomere::{log_seed, resume_seed_index};
use sha2::{Digest, Sha256};

fn main() {
    if let Err(e) = run() {
        eprintln!("{e}");
        std::process::exit(1);
    }
}

fn run() -> Result<(), Box<dyn std::error::Error>> {
    let mut index = resume_seed_index();
    for _ in 0..1000 {
        let seed = index.to_le_bytes().to_vec();
        let hash: [u8; 32] = Sha256::digest(&seed).into();
        if let Err(e) = log_seed(index, hash) {
            return Err(Box::new(e));
        }
        index += 1;
    }
    Ok(())
}
