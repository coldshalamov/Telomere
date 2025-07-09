use std::ops::RangeInclusive;

mod bloom;
mod gloss;
mod header;
mod sha_cache;

pub use bloom::*;
pub use gloss::*;
pub use header::{Header, encode_header, decode_header, HeaderError};
pub use sha_cache::*;

const BLOCK_SIZE: usize = 7;

#[derive(Debug, Clone)]
pub enum Region {
    Raw(Vec<u8>),
    Compressed(Vec<u8>, Header),
}

pub fn compress(
    data: &[u8],
    seed_len_range: RangeInclusive<u8>,
    seed_limit: Option<u64>,
    status_interval: u64,
    hash_counter: &mut u64,
    json_out: bool,
    gloss: Option<&GlossTable>,
    verbosity: u8,
    gloss_only: bool,
    mut coverage: Option<&mut [bool]>,
    mut partials: Option<&mut Vec<(Vec<u8>, Header)>>,
) -> Vec<u8> {
    // Only the parameters relevant to this simplified example are used.
    // All others are ignored to keep the demo implementation concise.

    // Build the chain of compressed or raw regions.
    let mut chain = Vec::new();
    let mut i = 0usize;

    if let Some(gloss_table) = gloss {
        while i < data.len() {
            let mut matched = false;

            for (seed_index, entry) in gloss_table.entries.iter().enumerate() {
                if data[i..].starts_with(&entry.decompressed) {
                    let span_len = entry.decompressed.len();
                    let arity = span_len / BLOCK_SIZE;

                    let header = Header { seed_index, arity };
                    let header_bytes = encode_header(header.seed_index, header.arity);

                    if header_bytes.len() < span_len {
                        chain.push(Region::Compressed(Vec::new(), header));
                        if let Some(cov) = coverage.as_mut() {
                            if seed_index < cov.len() {
                                cov[seed_index] = true;
                            }
                        }
                        i += span_len;
                        matched = true;
                        break;
                    }
                }
            }

            if !matched {
                let end = (i + BLOCK_SIZE).min(data.len());
                chain.push(Region::Raw(data[i..end].to_vec()));
                i = end;
            }
        }
    } else {
        chain = data
            .chunks(BLOCK_SIZE)
            .map(|b| Region::Raw(b.to_vec()))
            .collect();
    }

    // Serialize regions into a flat byte vector using VQL headers.
    let mut out = Vec::new();
    for region in chain {
        match region {
            Region::Raw(bytes) => out.extend(bytes),
            Region::Compressed(_, h) => out.extend(encode_header(h.seed_index, h.arity)),
        }
    }

    out
}

pub fn decompress_region_with_limit(
    region: &Region,
    gloss: &GlossTable,
    max_bytes: usize,
) -> Option<Vec<u8>> {
    match region {
        Region::Raw(bytes) => {
            if bytes.len() > max_bytes {
                None
            } else {
                Some(bytes.clone())
            }
        }
        Region::Compressed(_, header) => {
            let entry = gloss.entries.get(header.seed_index)?;
            if entry.header.arity != header.arity {
                return None;
            }
            if entry.decompressed.len() > max_bytes {
                None
            } else {
                Some(entry.decompressed.clone())
            }
        }
    }
}

pub fn decompress_with_limit(
    mut data: &[u8],
    gloss: &GlossTable,
    max_bytes: usize,
) -> Option<Vec<u8>> {
    let mut out = Vec::new();
    let mut offset = 0usize;
    while offset < data.len() {
        let (seed_idx, arity, bits) = decode_header(&data[offset..]).ok()?;
        let header = Header { seed_index: seed_idx, arity };
        offset += (bits + 7) / 8;
        let region = Region::Compressed(Vec::new(), header);
        let remaining = max_bytes.checked_sub(out.len())?;
        let bytes = decompress_region_with_limit(&region, gloss, remaining)?;
        out.extend_from_slice(&bytes);
    }
    Some(out)
}

pub fn decompress(data: &[u8], gloss: &GlossTable) -> Vec<u8> {
    decompress_with_limit(data, gloss, usize::MAX).expect("decompression failed")
}
