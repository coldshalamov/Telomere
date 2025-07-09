use serde::{Serialize, Deserialize};
use std::fs::{File, OpenOptions};
use std::io::{self, BufReader};
use std::path::Path;

#[derive(Serialize, Deserialize)]
pub struct HashEntry {
    pub seed_index: u64,
    pub seed: Vec<u8>,
    pub hash: [u8; 32],
}

pub fn resume_seed_index() -> u64 {
    let path = Path::new("hash_table.bin");
    let file = match File::open(path) {
        Ok(f) => f,
        Err(_) => return 0,
    };
    let mut reader = BufReader::new(file);
    let mut last = None;
    loop {
        match bincode::deserialize_from::<_, HashEntry>(&mut reader) {
            Ok(entry) => last = Some(entry.seed_index),
            Err(_) => break,
        }
    }
    match last {
        Some(idx) => idx + 1,
        None => 0,
    }
}

pub fn log_seed(seed_index: u64, seed: Vec<u8>, hash: [u8; 32]) -> io::Result<()> {
    let entry = HashEntry { seed_index, seed, hash };
    let mut file = OpenOptions::new()
        .create(true)
        .append(true)
        .open("hash_table.bin")?;
    bincode::serialize_into(&mut file, &entry)
        .map_err(|e| io::Error::new(io::ErrorKind::Other, e))
}
