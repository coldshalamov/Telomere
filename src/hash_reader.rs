//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
use bytemuck::{Pod, Zeroable};
use memmap2::Mmap;
use std::cmp::Ordering;

#[repr(C)]
#[derive(Clone, Copy)]
struct Entry {
    prefix: [u8; 3],
    len: u8,
    seed: [u8; 4],
}

unsafe impl Zeroable for Entry {}
unsafe impl Pod for Entry {}

/// Look up a seed by 3-byte hash prefix.
///
/// The file must be sorted by prefix. Returns `None` if no matching entry is
/// found or the mapping is malformed.
pub fn lookup_seed(mmap: &Mmap, prefix: [u8; 3]) -> Option<Vec<u8>> {
    let entry_size = std::mem::size_of::<Entry>();

    if mmap.len() % entry_size != 0 {
        return None;
    }

    // SAFETY: Entry is `Pod` and the length check above ensures the slice
    // length is a multiple of the item size.
    let entries: &[Entry] = bytemuck::cast_slice(&mmap[..]);

    let mut left = 0usize;
    let mut right = entries.len();

    while left < right {
        let mid = (left + right) / 2;
        match entries[mid].prefix.cmp(&prefix) {
            Ordering::Less => left = mid + 1,
            Ordering::Greater => right = mid,
            Ordering::Equal => {
                // Walk outward to gather all entries with the same prefix
                let mut best = entries[mid];
                let mut idx = mid;
                while idx > 0 && entries[idx - 1].prefix == prefix {
                    idx -= 1;
                    if entries[idx].len < best.len {
                        best = entries[idx];
                    }
                }
                idx = mid;
                while idx + 1 < entries.len() && entries[idx + 1].prefix == prefix {
                    idx += 1;
                    if entries[idx].len < best.len {
                        best = entries[idx];
                    }
                }

                let len = best.len as usize;
                if len > 4 {
                    return None;
                }
                return Some(best.seed[..len].to_vec());
            }
        }
    }

    None
}

#[cfg(test)]
mod tests {
    use super::*;
    use memmap2::MmapOptions;
    use tempfile::tempfile;

    #[test]
    fn basic_lookup() {
        let mut file = tempfile().unwrap();
        let entries = [
            Entry {
                prefix: [0, 0, 1],
                len: 3,
                seed: [1, 2, 3, 0],
            },
            Entry {
                prefix: [0, 1, 0],
                len: 1,
                seed: [4, 0, 0, 0],
            },
            Entry {
                prefix: [0, 1, 1],
                len: 4,
                seed: [5, 6, 7, 8],
            },
        ];
        let bytes: &[u8] = bytemuck::cast_slice(&entries);
        std::io::Write::write_all(&mut file, bytes).unwrap();
        let mmap = unsafe { MmapOptions::new().map(&file).unwrap() };

        assert_eq!(
            lookup_seed(&mmap, [0, 0, 1]).as_deref(),
            Some(&[1, 2, 3][..])
        );
        assert_eq!(lookup_seed(&mmap, [0, 1, 0]).as_deref(), Some(&[4][..]));
        assert_eq!(
            lookup_seed(&mmap, [0, 1, 1]).as_deref(),
            Some(&[5, 6, 7, 8][..])
        );
        assert!(lookup_seed(&mmap, [9, 9, 9]).is_none());
    }
}
