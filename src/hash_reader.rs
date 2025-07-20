//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
use bytemuck::{Pod, Zeroable};
use std::cmp::Ordering;

#[repr(C)]
#[derive(Clone, Copy, Zeroable, Pod)]
struct Entry {
    prefix: [u8; 3],
    len: u8,
    seed: [u8; 4],
}

/// Look up a seed by 3-byte hash prefix.
///
/// The file must be sorted by prefix. Returns `None` if no matching entry is
/// found or the mapping is malformed.
pub fn lookup_seed(bytes: &[u8], prefix: [u8; 3]) -> Option<Vec<u8>> {
    let entry_size = std::mem::size_of::<Entry>();

    if bytes.len() % entry_size != 0 {
        return None;
    }

    // SAFETY: Entry is `Pod` and the length check above ensures the slice
    // length is a multiple of the item size.
    let entries: &[Entry] = bytemuck::cast_slice(bytes);

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
                if len == 0 || len > 4 {
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

    #[test]
    fn basic_lookup() {
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

        assert_eq!(
            lookup_seed(bytes, [0, 0, 1]).as_deref(),
            Some(&[1, 2, 3][..])
        );
        assert_eq!(lookup_seed(bytes, [0, 1, 0]).as_deref(), Some(&[4][..]));
        assert_eq!(
            lookup_seed(bytes, [0, 1, 1]).as_deref(),
            Some(&[5, 6, 7, 8][..])
        );
        assert!(lookup_seed(bytes, [9, 9, 9]).is_none());
    }

    #[test]
    fn rejects_malformed_length() {
        // length not a multiple of entry size
        let bytes = [0u8; 7];
        assert!(lookup_seed(&bytes, [0, 0, 0]).is_none());
    }

    #[test]
    fn handles_zero_len_seed() {
        // zero length should be ignored and return None
        let entries = [Entry { prefix: [1, 2, 3], len: 0, seed: [0; 4] }];
        let bytes: &[u8] = bytemuck::cast_slice(&entries);
        assert!(lookup_seed(bytes, [1, 2, 3]).is_none());
    }
}
