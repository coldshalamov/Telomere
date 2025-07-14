
/// Status of a mutable block during bundling operations.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum BlockStatus {
    Active,
    Removed,
}

/// Mutable representation of a block within a compression table.
#[derive(Debug, Clone)]
pub struct MutableBlock {
    /// Original global index before any transformations.
    pub origin_index: usize,
    /// Current position within the table.
    pub position: usize,
    /// Current length in bits of this block.
    pub bit_length: usize,
    /// Raw byte data for this block.
    pub data: Vec<u8>,
    /// Optional arity if this block is compressed.
    pub arity: Option<usize>,
    /// Optional seed index associated with the compressed form.
    pub seed_index: Option<usize>,
    /// Current status of the block.
    pub status: BlockStatus,
}

/// Apply a bundling operation: insert compressed block and mark bundled ones.
pub fn apply_bundle(
    table: &mut Vec<MutableBlock>,
    bundle_indices: &[usize],
    seed_index: usize,
    arity: usize,
    new_bit_length: usize,
) {
    if bundle_indices.is_empty() {
        return;
    }

    let pos = bundle_indices[0];
    for b in table.iter_mut() {
        if bundle_indices.contains(&b.position) {
            b.status = BlockStatus::Removed;
        }
    }

    table.push(MutableBlock {
        origin_index: table[pos].origin_index,
        position: pos,
        bit_length: new_bit_length,
        data: vec![], // will be generated from header
        arity: Some(arity),
        seed_index: Some(seed_index),
        status: BlockStatus::Active,
    });
}

