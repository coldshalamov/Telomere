use std::collections::HashMap;
use std::time::Instant;
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

    // Convert leftover Raw regions into passthrough headers (arity 38–40)
    let mut final_chain = Vec::new();
    let mut j = 0;
    while j < chain.len() {
        match &chain[j] {
            Region::Raw(bytes) => {
                let mut collected = bytes.clone();
                let mut blocks = 1usize;
                while blocks < 3 && j + blocks < chain.len() {
                    if let Region::Raw(next) = &chain[j + blocks] {
                        collected.extend_from_slice(next);
                        blocks += 1;
                    } else {
                        break;
                    }
                }
                let arity = match blocks {
                    1 => 38,
                    2 => 39,
                    _ => 40,
                };
                final_chain.push(Region::Compressed(collected, Header { seed_index: 0, arity }));
                j += blocks;
            }
            other => {
                final_chain.push(other.clone());
                j += 1;
            }
        }
    }

    // Emit headers for all compressed regions
    let mut out = Vec::new();
    for region in final_chain {
        if let Region::Compressed(_, header) = region {
            out.extend(encode_header(header.seed_index, header.arity));
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
        if header.is_literal() {
            let blocks = header.arity - 37;
            let byte_count = blocks * BLOCK_SIZE;
            if offset + byte_count > data.len() {
                return None;
            }
            let remaining = max_bytes.checked_sub(out.len())?;
            if byte_count > remaining {
                return None;
            }
            out.extend_from_slice(&data[offset..offset + byte_count]);
            offset += byte_count;
        } else {
            let region = Region::Compressed(Vec::new(), header);
            let remaining = max_bytes.checked_sub(out.len())?;
            let bytes = decompress_region_with_limit(&region, gloss, remaining)?;
            out.extend_from_slice(&bytes);
        }
    }
    Some(out)
}

pub fn decompress(data: &[u8], gloss: &GlossTable) -> Vec<u8> {
    decompress_with_limit(data, gloss, usize::MAX).expect("decompression failed")
}
