// === Add compress() and decompress() from main branch ===

pub fn compress(
    data: &[u8],
    seed_len_range: RangeInclusive<u8>,
    seed_limit: Option<u64>,
    status_interval: u64,
    hash_counter: &mut u64,
    json_out: bool,
    gloss: Option<&GlossTable>,
    verbosity: u8,
) -> Vec<u8> {
    // ... [unchanged compress logic here] ...
}

pub fn decompress(mut data: &[u8]) -> Vec<u8> {
    // ... [unchanged decompress logic here] ...
}

// === Now add the test module ===

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use std::path::PathBuf;

    fn simple_compress(data: &[u8]) -> Vec<u8> {
        let mut out = Vec::new();
        for chunk in data.chunks(BLOCK_SIZE) {
            out.extend_from_slice(&encode_region(&Region::Raw(chunk.to_vec())));
        }
        out
    }

    #[test]
    fn generate_gloss() {
        let table = GlossTable::generate();
        assert!(!table.entries.is_empty());
    }

    #[test]
    fn gloss_save_load_roundtrip() {
        let table = GlossTable::generate();
        let path = std::env::temp_dir().join("gloss_test.bin");
        table.save(&path).unwrap();
        let loaded = GlossTable::load(&path).unwrap();
        assert_eq!(table.entries.len(), loaded.entries.len());
        let _ = fs::remove_file(path);
    }

    #[test]
    fn roundtrip_small_buffer() {
        let data: Vec<u8> = (0u8..14).collect();
        let encoded = simple_compress(&data);
        let decoded = decompress_safe(&encoded).unwrap();
        assert_eq!(decoded, data);
    }

    #[test]
    fn malformed_region() {
        assert!(decode_region_safe(&[0x01]).is_none());
        let good = encode_region(&Region::Raw(vec![0; BLOCK_SIZE]));
        let truncated = &good[..good.len() - 1];
        assert!(decode_region_safe(truncated).is_none());
    }

    #[test]
    fn json_stats_output() {
        let chain = vec![Region::Raw(vec![0; BLOCK_SIZE])];
        let result = std::panic::catch_unwind(|| {
            print_stats(&chain, BLOCK_SIZE, 1, 0, 0, 0, true, 1, Instant::now(), true);
        });
        assert!(result.is_ok());
    }
}
