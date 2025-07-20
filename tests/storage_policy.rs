//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
use std::fs;
use telomere::{log_seed_to, resume_seed_index_from, HashEntry, ResourceLimits};
use tempfile::NamedTempFile;

#[test]
fn only_persist_selected_seeds() {
    let tmp = NamedTempFile::new().unwrap();
    let path = tmp.path();

    // Pretend we saw many candidate seeds but none should be persisted.
    for i in 0..100u64 {
        log_seed_to(path, i, [0u8; 32], false, None).unwrap();
    }
    // File should remain empty
    assert_eq!(fs::metadata(path).unwrap().len(), 0);

    // Persist a few final seeds
    for i in 0..3u64 {
        log_seed_to(path, i, [i as u8; 32], true, None).unwrap();
    }

    let mut file = fs::File::open(path).unwrap();
    let mut entries = Vec::new();
    loop {
        match bincode::deserialize_from::<_, HashEntry>(&mut file) {
            Ok(e) => entries.push(e),
            Err(_) => break,
        }
    }
    assert_eq!(entries.len(), 3);
    for (i, e) in entries.iter().enumerate() {
        assert_eq!(e.seed_index, i as u64);
    }
}

#[test]
fn resource_limit_abort() {
    let tmp = NamedTempFile::new().unwrap();
    let path = tmp.path();
    // Set disk limit smaller than a single entry
    let limits = ResourceLimits {
        max_disk_bytes: 1,
        max_memory_bytes: u64::MAX,
    };
    let res = log_seed_to(path, 0, [0u8; 32], true, Some(&limits));
    assert!(res.is_err());
    // Nothing should have been written
    assert!(!path.exists() || fs::metadata(path).unwrap().len() == 0);
    assert_eq!(resume_seed_index_from(path), 0);
}
