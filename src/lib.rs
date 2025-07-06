/// Attempt to decode a region without panicking.
fn decode_region_safe(data: &[u8]) -> Option<(Region, usize)> {
    for n in 1..=4 {
        if data.len() < n + HEADER_SIZE {
            continue;
        }
        let seed = &data[..n];
        let header_bytes: [u8; HEADER_SIZE] = data[n..n + HEADER_SIZE].try_into().ok()?;
        let header = Header::unpack(header_bytes);
        if header.seed_len as usize + 1 == n {
            let consumed = n + HEADER_SIZE;
            if is_fallback(seed, header_bytes) {
                if data.len() < consumed + BLOCK_SIZE {
                    return None;
                }
                let end = consumed + BLOCK_SIZE;
                let block = data[consumed..end].to_vec();
                return Some((Region::Raw(block), consumed + BLOCK_SIZE));
            } else {
                return Some((Region::Compressed(seed.to_vec(), header), consumed));
            }
        }
    }
    None
}

fn decompress_region_safe(region: &Region) -> Option<Vec<u8>> {
    match region {
        Region::Raw(bytes) => Some(bytes.clone()),
        Region::Compressed(seed, header) => {
            let digest = Sha256::digest(seed);
            if header.arity == 0 {
                Some(digest[..BLOCK_SIZE].to_vec())
            } else {
                let len = header.nest_len as usize;
                if len > digest.len() {
                    return None;
                }
                decompress_safe(&digest[..len])
            }
        }
    }
}

fn decompress_safe(mut data: &[u8]) -> Option<Vec<u8>> {
    let mut out = Vec::new();
    let mut offset = 0;
    while offset < data.len() {
        let (region, consumed) = decode_region_safe(&data[offset..])?;
        offset += consumed;
        out.extend_from_slice(&decompress_region_safe(&region)?);
    }
    Some(out)
}

/// Entry describing a digest prefix that decompresses cleanly.
pub struct GlossEntry {
    pub seed: Vec<u8>,
    pub header: Header,
    pub decompressed: Vec<u8>,
}

/// Table containing all valid seed/header pairs for 1- and 2-byte seeds.
pub struct GlossTable {
    pub entries: Vec<GlossEntry>,
}

impl GlossTable {
    /// Generate the table at runtime.
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
                        if let Some(out) = decompress_region_safe(&Region::Compressed(seed_bytes.to_vec(), header)) {
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
}
