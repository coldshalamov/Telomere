use crate::block::Block;
use crate::TelomereError;

/// A contiguous chunk of the global block table.
///
/// `start_index` records the global index of the first block in `blocks`.
#[derive(Debug, Clone)]
pub struct BlockChunk {
    pub start_index: usize,
    pub blocks: Vec<Block>,
}

/// Map global block indices to tiled chunks.
#[derive(Debug, Clone)]
pub struct TileMap {
    total_blocks: usize,
    chunk_size: usize,
}

impl TileMap {
    /// Create a new `TileMap` covering `total_blocks` blocks.
    pub fn new(total_blocks: usize, chunk_size: usize) -> Self {
        Self { total_blocks, chunk_size }
    }

    /// Number of chunks implied by this map.
    pub fn chunk_count(&self) -> usize {
        if self.total_blocks == 0 { 0 } else { (self.total_blocks - 1) / self.chunk_size + 1 }
    }

    /// Map a global block index to `(chunk, offset)`.
    pub fn map_global(&self, index: usize) -> Option<(usize, usize)> {
        if index >= self.total_blocks { return None; }
        let chunk = index / self.chunk_size;
        let offset = index % self.chunk_size;
        Some((chunk, offset))
    }
}

/// Split a flat block list into tiled chunks.
pub fn chunk_blocks(blocks: &[Block], chunk_size: usize) -> Vec<BlockChunk> {
    let mut chunks = Vec::new();
    let mut idx = 0usize;
    while idx < blocks.len() {
        let end = (idx + chunk_size).min(blocks.len());
        let slice = blocks[idx..end].to_vec();
        chunks.push(BlockChunk { start_index: idx, blocks: slice });
        idx = end;
    }
    chunks
}

/// Load a chunk from a pre-split vector.
pub fn load_chunk(chunks: &[BlockChunk], index: usize) -> Result<BlockChunk, TelomereError> {
    chunks.get(index).cloned().ok_or_else(|| TelomereError::Other("invalid chunk".into()))
}

/// No-op flush helper for the in-memory tiling tests.
pub fn flush_chunk(_chunk: BlockChunk) -> Result<(), TelomereError> {
    Ok(())
}
