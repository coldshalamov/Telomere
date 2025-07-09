use sha2::{Digest, Sha256};
use serde::{Serialize, Deserialize};
use memmap2::Mmap;
use std::fs::File;
use std::path::Path;

use crate::{
    Region,
    Header,
    BLOCK_SIZE,
};

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
        Self { entries: Vec::new() }
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

    pub fn find(&self, data: &[u8]) -> Option<&GlossEntry> {
        self.entries.iter().find(|e| e.decompressed == data)
    }

    pub fn find_with_index(&self, data: &[u8]) -> Option<(usize, &GlossEntry)> {
        self.entries.iter().enumerate().find(|(_, e)| e.decompressed == data)
    }
}

