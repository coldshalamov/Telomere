//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
//!
//! A [`BlockStore`] stores all block data in a contiguous arena and manages
//! metadata via compact `BlockRef` structures. This replaces the legacy
//! allocator-heavy `BlockTable`.

use hashbrown::HashMap;

/// Handle to a block stored in the `BlockStore`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct BlockId(pub u32);

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum BranchStatus {
    Active,
    Pruned,
    Collapsed,
}

#[derive(Debug, Clone)]
pub struct BlockRef {
    /// Offset into the data arena.
    pub offset: u32,
    /// Length of the block data in bytes.
    pub byte_len: u16,
    /// Bit length (can be less than byte_len * 8).
    pub bit_len: u16,
    /// Original global index in the stream.
    pub global_index: u32,
    /// Precomputed digest (BLAKE3/SHA256).
    pub digest: [u8; 32],
    /// Optional arity if compressed.
    pub arity: Option<u16>,
    /// Optional seed index.
    pub seed_index: Option<u64>,
    /// Branch label ('A', 'B', 'C'...).
    pub branch_label: char,
    /// Status.
    pub status: BranchStatus,
}

/// A cache-friendly store for block data and metadata.
pub struct BlockStore {
    /// Contiguous arena for block data.
    data_arena: Vec<u8>,
    /// Metadata for each block, indexed by `BlockId`.
    blocks: Vec<BlockRef>,
    /// Index of blocks grouped by bit length.
    groups: HashMap<usize, Vec<BlockId>>,
}

impl Default for BlockStore {
    fn default() -> Self {
        Self::new()
    }
}

impl BlockStore {
    pub fn new() -> Self {
        Self {
            data_arena: Vec::with_capacity(1024 * 1024),
            blocks: Vec::with_capacity(1024),
            groups: HashMap::new(),
        }
    }

    pub fn add_block(&mut self, data: &[u8], global_index: usize, bit_len: usize) -> BlockId {
        let offset = self.data_arena.len() as u32;
        self.data_arena.extend_from_slice(data);
        let byte_len = data.len() as u16;

        #[cfg(feature = "gpu")]
        let digest = {
            // Placeholder: Use actual hasher if needed
             [0u8; 32]
        };
        #[cfg(not(feature = "gpu"))]
        let digest = {
            // Using blake3 for speed as per mandate
            let mut hasher = blake3::Hasher::new();
            hasher.update(data);
            hasher.finalize().into()
        };

        let block = BlockRef {
            offset,
            byte_len,
            bit_len: bit_len as u16,
            global_index: global_index as u32,
            digest,
            arity: None,
            seed_index: None,
            branch_label: 'A',
            status: BranchStatus::Active,
        };

        let id = BlockId(self.blocks.len() as u32);
        self.blocks.push(block);
        self.groups.entry(bit_len).or_default().push(id);
        id
    }

    pub fn get_data(&self, id: BlockId) -> &[u8] {
        let b = &self.blocks[id.0 as usize];
        &self.data_arena[b.offset as usize..(b.offset as usize + b.byte_len as usize)]
    }

    pub fn get_block(&self, id: BlockId) -> &BlockRef {
        &self.blocks[id.0 as usize]
    }

    pub fn get_block_mut(&mut self, id: BlockId) -> &mut BlockRef {
        &mut self.blocks[id.0 as usize]
    }

    /// Access the raw blocks vector.
    pub fn blocks(&self) -> &[BlockRef] {
        &self.blocks
    }
    
    /// Iterate over groups.
    pub fn groups(&self) -> impl Iterator<Item = (&usize, &Vec<BlockId>)> {
        self.groups.iter()
    }

    /// Get blocks for a specific bit length.
    pub fn get_group(&self, len: usize) -> Option<&Vec<BlockId>> {
        self.groups.get(&len)
    }
    
    pub fn group_mut(&mut self, len: usize) -> &mut Vec<BlockId> {
         self.groups.entry(len).or_default()
    }

    pub fn group_count(&self) -> usize {
        self.groups.len()
    }
    
    pub fn iter_mut_groups(&mut self) -> impl Iterator<Item = (&usize, &mut Vec<BlockId>)> {
        self.groups.iter_mut()
    }

    pub fn clear_empty(&mut self) {
        self.groups.retain(|_, v| !v.is_empty());
    }
}

/// Split raw input into fixed-sized blocks and populate a store.
pub fn split_into_blocks(input: &[u8], block_size_bits: usize) -> BlockStore {
    let mut store = BlockStore::new();
    let block_size_bytes = (block_size_bits + 7) / 8;
    let mut offset = 0usize;
    let mut index = 0usize;

    while offset < input.len() {
        let end = (offset + block_size_bytes).min(input.len());
        let slice = &input[offset..end];
        let bits = if end - offset == block_size_bytes {
            block_size_bits
        } else {
            (end - offset) * 8
        };
        store.add_block(slice, index, bits);
        offset += block_size_bytes;
        index += 1;
    }
    store
}

/// Simulate a compression pass (legacy compat).
/// Note: This function previously mutated the table significantly.
/// We'll adapt it to work with BlockStore.
pub fn simulate_pass(store: &mut BlockStore, seed_table: &HashMap<String, usize>) -> usize {
    let mut lengths: Vec<usize> = store.groups.keys().copied().collect();
    lengths.sort_unstable_by(|a, b| b.cmp(a));

    let mut matches = 0usize;

    for len in lengths {
        // We need to iterate and potentially move blocks to a new group (len=16).
        // Since we can't easily move while iterating the HashMap, we extract indices.
        let group_ids = store.groups.get(&len).cloned().unwrap_or_default(); // Scan copy
        if group_ids.is_empty() { continue; }

        let mut next_group_indices = Vec::new();
        let mut matched_indices = Vec::new();

        for &id in &group_ids {
            // let _data = store.get_data(id).to_vec(); // Unused
            // Use digest from metadata
            let digest = store.get_block(id).digest;
            let hex = hex::encode(digest); 
            
            if let Some(&seed_idx) = seed_table.get(&hex) {
                 matched_indices.push((id, seed_idx));
                 matches += 1;
            } else {
                 next_group_indices.push(id);
            }
        }

        // Apply changes
        if !matched_indices.is_empty() {
             for (id, seed_idx) in matched_indices {
                 let block = store.get_block_mut(id);
                 block.seed_index = Some(seed_idx as u64);
                 block.arity = Some(1);
                 block.bit_len = 16;
                 
                 store.groups.entry(16).or_default().push(id);
             }
             // Update the original group to only contain unmatched
             store.groups.insert(len, next_group_indices);
        }
    }
    matches
}

/// Print summary
pub fn print_table_summary(store: &BlockStore) {
    // Iterate all blocks
    let mut all_ids: Vec<BlockId> = store.groups.values().flatten().copied().collect();
    all_ids.sort_by_key(|id| {
        let b = store.get_block(*id);
        (b.global_index, b.branch_label)
    });
    
    for id in all_ids {
        let b = store.get_block(id);
        println!("{}{}: {} bits ({:?})", b.global_index, b.branch_label, b.bit_len, b.status);
    }
}

pub fn group_by_bit_length(_blocks: Vec<BlockRef>) -> BlockStore {
    BlockStore::new() 
}
