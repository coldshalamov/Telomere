use crate::{BLOCK_SIZE, header::{decode_header, Header}, Region};
use crate::gloss::GlossTable;

pub fn decompress_region_with_limit(region: &Region, gloss: &GlossTable, limit: usize) -> Option<Vec<u8>> {
    match region {
        Region::Raw(data) => {
            if data.len() <= limit { Some(data.clone()) } else { None }
        }
        Region::Compressed(_seed, header) => {
            gloss.entries.get(header.seed_index).and_then(|entry| {
                if entry.decompressed.len() <= limit && header.arity == 1 {
                    Some(entry.decompressed.clone())
                } else {
                    None
                }
            })
        }
    }
}

pub fn decompress_with_limit(mut data: &[u8], gloss: &GlossTable, limit: usize) -> Option<Vec<u8>> {
    let mut out = Vec::new();
    while !data.is_empty() {
        let (seed, arity, bits) = decode_header(data).ok()?;
        let header = Header { seed_index: seed, arity };
        let header_bytes = (bits + 7) / 8;
        data = &data[header_bytes..];
        if header.is_literal() {
            let bytes = match header.arity {
                37 => BLOCK_SIZE,
                38 => 2 * BLOCK_SIZE,
                39 => 3 * BLOCK_SIZE,
                40 => data.len(),
                _ => return None,
            };
            if out.len() + bytes > limit || data.len() < bytes {
                return None;
            }
            out.extend_from_slice(&data[..bytes]);
            data = &data[bytes..];
        } else {
            let region = Region::Compressed(Vec::from(data), header);
            let part = decompress_region_with_limit(&region, gloss, limit - out.len())?;
            out.extend_from_slice(&part);
            break;
        }
    }
    Some(out)
}

pub fn decompress(data: &[u8], gloss: &GlossTable) -> Vec<u8> {
    decompress_with_limit(data, gloss, usize::MAX).unwrap_or_default()
}
