use crate::block::Block;
use crate::{GpuMatchRecord, TelomereError};
use ocl::{Buffer, ProQue};
use sha2::{Digest, Sha256};

/// GPU accelerated seed matcher backed by OpenCL.
///
/// If OpenCL initialization fails at runtime the matcher falls back to
/// a pure CPU implementation so existing callers do not need to handle
/// errors differently.
pub struct GpuSeedMatcher {
    pro_que: Option<ProQue>,
    tile: Vec<Block>,
    block_offsets: Vec<u32>,
    block_lens: Vec<u32>,
    block_bytes: Vec<u8>,
    block_buf: Option<Buffer<u8>>, 
    offset_buf: Option<Buffer<u32>>, 
    len_buf: Option<Buffer<u32>>, 
}

impl GpuSeedMatcher {
    /// Attempt to create a new matcher. If the OpenCL context or kernel fails
    /// to build the struct is still created but GPU acceleration will be
    /// disabled.
    pub fn new() -> Self {
        let src = include_str!("kernels/seed_match.cl");
        let pro_que = ProQue::builder().src(src).build().ok();
        Self {
            pro_que,
            tile: Vec::new(),
            block_offsets: Vec::new(),
            block_lens: Vec::new(),
            block_bytes: Vec::new(),
            block_buf: None,
            offset_buf: None,
            len_buf: None,
        }
    }

    /// Upload a tile of blocks into GPU memory (if available).
    pub fn load_tile(&mut self, blocks: &[Block]) {
        self.tile = blocks.to_vec();
        self.block_offsets.clear();
        self.block_lens.clear();
        self.block_bytes.clear();
        for b in &self.tile {
            self.block_offsets.push(self.block_bytes.len() as u32);
            self.block_lens.push(b.data.len() as u32);
            self.block_bytes.extend_from_slice(&b.data);
        }
        if let Some(pq) = &self.pro_que {
            let q = pq.queue();
            self.block_buf = Buffer::<u8>::builder()
                .queue(q.clone())
                .len(self.block_bytes.len())
                .copy_host_slice(&self.block_bytes)
                .build()
                .ok();
            self.offset_buf = Buffer::<u32>::builder()
                .queue(q.clone())
                .len(self.block_offsets.len())
                .copy_host_slice(&self.block_offsets)
                .build()
                .ok();
            self.len_buf = Buffer::<u32>::builder()
                .queue(q.clone())
                .len(self.block_lens.len())
                .copy_host_slice(&self.block_lens)
                .build()
                .ok();
        }
    }

    /// Search a range of seed indices returning any matches found.
    pub fn seed_match(
        &self,
        start_seed: usize,
        end_seed: usize,
    ) -> Result<Vec<GpuMatchRecord>, TelomereError> {
        // CPU fallback if GPU unavailable
        let pq = match &self.pro_que {
            Some(p) => p,
            None => return self.cpu_seed_match(start_seed, end_seed),
        };
        let block_buf = match (&self.block_buf, &self.offset_buf, &self.len_buf) {
            (Some(b), Some(o), Some(l)) => (b, o, l),
            _ => return self.cpu_seed_match(start_seed, end_seed),
        };

        let seed_count = end_seed.saturating_sub(start_seed);
        if seed_count == 0 {
            return Ok(Vec::new());
        }
        let max_matches = seed_count * self.tile.len();
        let out_records = Buffer::<[u32; 2]>::builder()
            .queue(pq.queue().clone())
            .len(max_matches)
            .build()
            .map_err(|e| TelomereError::SeedSearch(format!("{e}")))?;
        let out_count = Buffer::<u32>::builder()
            .queue(pq.queue().clone())
            .len(1)
            .fill_val(0u32)
            .build()
            .map_err(|e| TelomereError::SeedSearch(format!("{e}")))?;

        let kernel = pq
            .kernel_builder("seed_match")
            .arg(block_buf.0)
            .arg(block_buf.1)
            .arg(block_buf.2)
            .arg(self.tile.len() as u32)
            .arg(start_seed as u64)
            .arg(1u32) // max_seed_len fixed to 1 for now
            .arg(&out_records)
            .arg(&out_count)
            .build()
            .map_err(|e| TelomereError::SeedSearch(format!("{e}")))?;

        unsafe {
            kernel
                .cmd()
                .global_work_size(seed_count)
                .enq()
                .map_err(|e| TelomereError::SeedSearch(format!("{e}")))?;
        }

        let mut count = vec![0u32];
        out_count
            .read(&mut count)
            .enq()
            .map_err(|e| TelomereError::SeedSearch(format!("{e}")))?;
        let count = count[0] as usize;
        let mut pairs = vec![[0u32; 2]; count];
        if count > 0 {
            out_records
                .read(&mut pairs)
                .enq()
                .map_err(|e| TelomereError::SeedSearch(format!("{e}")))?;
        }

        let mut out = Vec::new();
        for p in pairs {
            let seed_idx = p[0] as usize;
            let block_idx = p[1] as usize;
            if let Some(block) = self.tile.get(block_idx) {
                out.push(GpuMatchRecord {
                    seed_index: seed_idx,
                    bundle_length: 1,
                    block_indices: vec![block.global_index],
                    original_bits: block.bit_length,
                });
            }
        }
        Ok(out)
    }

    fn cpu_seed_match(
        &self,
        start_seed: usize,
        end_seed: usize,
    ) -> Result<Vec<GpuMatchRecord>, TelomereError> {
        let mut out = Vec::new();
        for seed in start_seed..end_seed {
            let seed_byte = seed as u8;
            for block in &self.tile {
                let expanded = expand_seed(&[seed_byte], block.data.len());
                if expanded == block.data {
                    out.push(GpuMatchRecord {
                        seed_index: seed,
                        bundle_length: 1,
                        block_indices: vec![block.global_index],
                        original_bits: block.bit_length,
                    });
                }
            }
        }
        Ok(out)
    }
}

fn expand_seed(seed: &[u8], len: usize) -> Vec<u8> {
    let mut out = Vec::with_capacity(len);
    let mut cur = seed.to_vec();
    while out.len() < len {
        let digest: [u8; 32] = Sha256::digest(&cur).into();
        out.extend_from_slice(&digest);
        cur = digest.to_vec();
    }
    out.truncate(len);
    out
}
