use sha2::{Digest, Sha256};
use serde::{Serialize, Deserialize};
use memmap2::Mmap;
use std::fs::File;
use std::path::Path;

use crate::{Region, Header, BLOCK_SIZE, decompress_region_safe, decompress_safe};

#[derive(Serialize, Deserialize, Clone)]
pub struct GlossEntry {
    pub seed: Vec<u8>,
    pub header: Header,
    pub decompressed: Vec<u8>,
}

#[derive(Serialize, Deserialize, Default, Clone)]
pub struct GlossTable {
    pub entries: Vec<GlossEntry>,
}

impl GlossTable {
    pub fn generate() -> Self {
        let mut entries = Vec::new();
        for seed_len in 1..=2u8 {
            let max = 1u64 << (8 * seed_len as u64);
            for seed_val in 0..max {
                let seed_bytes = &seed_val.to_be_bytes()[8 - seed_len as usize..];
                let digest = Sha256::digest(seed_bytes);
                for len in 0..=digest.len() {
                    if let Some(bytes) = decompress_safe(&digest[..len]) {
                        let blocks = bytes.len() / BLOCK_SIZE;
                        if bytes.len() % BLOCK_SIZE != 0 || !(2..=4).contains(&blocks) {
                            continue;
                        }
                        let header = Header {
                            seed_len: seed_len - 1,
                            nest_len: len as u32,
                            arity: blocks as u8 - 1,
                        };
                        if let Some(out) = decompress_region_safe(
                            &Region::Compressed(seed_bytes.to_vec(), header),
                        ) {
                            entries.push(GlossEntry {
                                seed: seed_bytes.to_vec(),
                                header,
                                decompressed: out,
                            });
                        }
                    }
                }
            }
        }
        Self { entries }
    }

    pub fn build() -> Self {
        Self { entries: Vec::new() }
    }

    pub fn load<P: AsRef<Path>>(path: P) -> std::io::Result<Self> {
        let file = File::open(path)?;
        unsafe {
            let mmap = Mmap::map(&file)?;
            Ok(bincode::deserialize(&mmap).expect("invalid gloss table"))
        }
    }

    pub fn save<P: AsRef<Path>>(&self, path: P) -> std::io::Result<()> {
        let data = bincode::serialize(self).expect("failed to serialize gloss");
        std::fs::write(path, data)
    }
}

