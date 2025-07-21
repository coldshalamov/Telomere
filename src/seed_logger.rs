//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
//!
//! Only final or whitelisted seeds should be written to disk.  Temporary
//! candidates are discarded.  Every write checks available disk space and
//! memory usage to prevent uncontrolled resource consumption.

use serde::{Deserialize, Serialize};
use std::fs::{File, OpenOptions};
use std::io::{self, BufReader, Write};
use std::path::Path;
use sysinfo::{System, SystemExt};

#[derive(Serialize, Deserialize)]
pub struct HashEntry {
    pub seed_index: u64,
    pub hash: [u8; 32],
}

/// Resource limits checked before persisting a seed entry.
#[derive(Clone, Copy)]
pub struct ResourceLimits {
    pub max_disk_bytes: u64,
    pub max_memory_bytes: u64,
}



/// Return an error if writing an entry would exceed resource limits.
fn check_limits(limits: &ResourceLimits, path: &Path, entry_bytes: u64) -> Result<(), crate::TelomereError> {

    // first (and only) disk-limit check
let current = std::fs::metadata(path).map(|m| m.len()).unwrap_or(0);
if current + entry_bytes > limits.max_disk_bytes {
    return Err(crate::TelomereError::Io(io::Error::new(
        io::ErrorKind::Other,
        format!(
            "disk limit exceeded: {} + {} > {}",
            current, entry_bytes, limits.max_disk_bytes
        ),
    )));
}

// ---- RAM check stays as-is ----
let mut sys = System::new();

    sys.refresh_memory();
    let used = sys.used_memory() * 1024;
    if used > limits.max_memory_bytes {
        return Err(crate::TelomereError::Io(io::Error::new(
            io::ErrorKind::Other,
            format!(
                "memory limit exceeded: {} > {}",
                used, limits.max_memory_bytes
            ),
        )));
    }
    Ok(())
}

pub fn resume_seed_index() -> u64 {
    resume_seed_index_from(Path::new("hash_table.bin"))
}

/// Resume the next seed index for the given table file.
pub fn resume_seed_index_from(path: &Path) -> u64 {
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

pub fn log_seed(seed_index: u64, hash: [u8; 32]) -> Result<(), crate::TelomereError> {
    log_seed_to(Path::new("hash_table.bin"), seed_index, hash, true, None)
}

/// Optionally persist a seed entry.
///
/// If `persist` is `false`, the function is a no-op. When true, resource
/// limits are checked before the entry is appended to `path`.
pub fn log_seed_to(
    path: &Path,
    seed_index: u64,
    hash: [u8; 32],
    persist: bool,
    limits: Option<&ResourceLimits>,
) -> Result<(), crate::TelomereError> {
    if !persist {
        return Ok(());
    }

    let entry = HashEntry { seed_index, hash };
    let bytes = bincode::serialize(&entry)
        .map_err(|e| crate::TelomereError::Io(io::Error::new(io::ErrorKind::Other, e)))?;
    if let Some(l) = limits {
        check_limits(l, path, bytes.len() as u64)?;
    }
    let mut file = OpenOptions::new().create(true).append(true).open(path).map_err(crate::TelomereError::from)?;
    file.write_all(&bytes).map_err(crate::TelomereError::from)?;
    Ok(())
}
