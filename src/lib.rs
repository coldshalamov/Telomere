use std::collections::HashMap;
use std::ops::RangeInclusive;
use std::time::Instant;

mod bloom;
mod gloss;
mod header;
mod sha_cache;

pub use bloom::*;
pub use gloss::*;
pub use header::{Header, encode_header, decode_header, HeaderError};
pub use sha_cache::*;

const BLOCK_SIZE: usize = 7;

pub fn print_compression_status(original: usize, compressed: usize) {
    let ratio = 100.0 * (1.0 - compressed as f64 / original as f64);
    eprintln!("Compression: {} → {} bytes ({:.2}%)", original, compressed, ratio);
}

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
    let mut arity_counts: HashMap<usize, usize> = HashMap::new();
    let mut i = 0usize;
    let original_len = data.len();
    let mut compressed_len = 0usize;

    let mut emit_literal = |bytes: &[u8], arity: usize, chain: &mut Vec<Region>| {
        chain.push(Region::Compressed(bytes.to_vec(), Header { seed_index: 0, arity }));
        *arity_counts.entry(arity).or_insert(0) += 1;
    };

    if let Some(gloss_table) = gloss {
        while i < data.len() {
            if status_interval > 0 && *hash_counter > 0 && *hash_counter % status_interval == 0 {
                eprintln!("processed {} hashes", *hash_counter);
            }
            *hash_counter += 1;
            let mut matched = false;

            for (seed_index, entry) in gloss_table.entries.iter().enumerate() {
                if data[i..].starts_with(&entry.decompressed) {
                    let span_len = entry.decompressed.len();
                    let arity = span_len / BLOCK_SIZE;
                    let header = Header { seed_index, arity };
                    let header_bytes = encode_header(header.seed_index, header.arity);
                    if header_bytes.len() < span_len {
                        chain.push(Region::Compressed(Vec::new(), header));
                        *arity_counts.entry(arity).or_insert(0) += 1;
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
                let remaining = data.len() - i;
                if remaining >= BLOCK_SIZE {
                    let blocks = ((remaining / BLOCK_SIZE).min(3)).max(1);
                    let span_end = i + blocks * BLOCK_SIZE;
                    emit_literal(&data[i..span_end], 36 + blocks, &mut chain);
                    i = span_end;
                } else {
                    emit_literal(&data[i..], 40, &mut chain);
                    i = data.len();
                }
            }
        }
    } else {
        while i < data.len() {
            if status_interval > 0 && *hash_counter > 0 && *hash_counter % status_interval == 0 {
                eprintln!("processed {} hashes", *hash_counter);
            }
            *hash_counter += 1;
            let remaining = data.len() - i;
            if remaining >= BLOCK_SIZE {
                let blocks = ((remaining / BLOCK_SIZE).min(3)).max(1);
                let span_end = i + blocks * BLOCK_SIZE;
                emit_literal(&data[i..span_end], 36 + blocks, &mut chain);
                i = span_end;
            } else {
                emit_literal(&data[i..], 40, &mut chain);
                i = data.len();
            }
        }
    }

    // Encode headers and append literal or seed data
    let mut out = Vec::new();
    for region in chain {
        if let Region::Compressed(bytes, header) = region {
            out.extend(encode_header(header.seed_index, header.arity));
            out.extend(bytes);
            compressed_len = out.len();
            *hash_counter += 1;
            if status_interval > 0 && *hash_counter % status_interval == 0 {
                print_compression_status(original_len, compressed_len);
            }
        }
    }

    // Final compression report
    print_compression_status(original_len, out.len());

    // Arity histogram
    if !arity_counts.is_empty() {
        println!("Arity Usage:");
        let mut keys: Vec<_> = arity_counts.keys().copied().collect();
        keys.sort_unstable();
        for k in keys {
            let count = arity_counts[&k];
            let label = if k == 40 {
                "tail"
            } else if (37..=39).contains(&k) {
                "passthroughs"
            } else {
                "spans"
            };
            println!("  {} → {} {}", k, count, label);
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
            if entry.decompressed.len() > max_bytes || entry.decompressed.len() / BLOCK_SIZE != header.arity {
                return None;
            }
            Some(entry.decompressed.clone())
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
            if header.arity == 40 {
                let byte_count = data.len().saturating_sub(offset);
                let remaining = max_bytes.checked_sub(out.len())?;
                if byte_count > remaining {
                    return None;
                }
                out.extend_from_slice(&data[offset..]);
                offset = data.len();
            } else {
                let blocks = header.arity - 36;
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
            }
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
