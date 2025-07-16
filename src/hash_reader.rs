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
    let mut left = 0usize;
    let mut right = mmap.len() / entry_size;

    while left < right {
        let mid = (left + right) / 2;
        let start = mid * entry_size;
        let end = start + entry_size;
        let slice = mmap.get(start..end)?;
        let entry = bytemuck::from_bytes::<Entry>(slice);
        match entry.prefix.cmp(&prefix) {
            Ordering::Less => left = mid + 1,
            Ordering::Greater => right = mid,
            Ordering::Equal => {
                let len = entry.len as usize;
                if len > 4 {
                    return None;
                }
                return Some(entry.seed[..len].to_vec());
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
