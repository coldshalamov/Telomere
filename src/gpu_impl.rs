use crate::block::Block;
use crate::{GpuMatchRecord, TelomereError};
use ocl::{Buffer, ProQue};
use sha2::{Digest, Sha256};

/// GPU accelerated seed matcher backed by OpenCL.
/// If OpenCL initialization fails at runtime the matcher falls back to
/// a pure CPU implementation so existing callers do not need to handle
/// errors differently.
#[derive(Default)]
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
    /// Create a new matcher. If OpenCL context or kernel-build fails,
    /// `pro_que` will be `None` and we’ll always fall back to CPU.
    pub fn new() -> Self {
        let src = include_str!("kernels/seed_match.cl");
        let pro_que = ProQue::builder()
            .src(src)
            .build()
            .ok();
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
            let queue = pq.queue().clone();
            self.block_buf = Buffer::<u8>::builder()
                .queue(queue.clone())
                .len(self.block_bytes.len())
                .copy_host_slice(&self.block_bytes)
                .build()
                .ok();
            self.offset_buf = Buffer::<u32>::builder()
                .queue(queue.clone())
                .len(self.block_offsets.len())
                .copy_host_slice(&self.block_offsets)
                .build()
                .ok();
            self.len_buf = Buffer::<u32>::builder()
                .queue(queue.clone())
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
        let (block_buf, offset_buf, len_buf) =
            match (&self.block_buf, &self.offset_buf, &self.len_buf) {
                (Some(b), Some(o), Some(l)) => (b, o, l),
                _ => return self.cpu_seed_match(start_seed, end_seed),
            };

        let seed_count = end_seed.saturating_sub(start_seed);
        if seed_count == 0 {
            return Ok(Vec::new());
        }
        let max_matches = seed_count * self.tile.len();

        // Allocate output buffers
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

        // Build and enqueue the kernel
        let kernel = pq
            .kernel_builder("seed_match")
            .arg(block_buf)
            .arg(offset_buf)
            .arg(len_buf)
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

        // Read back how many matches we got
        let mut count = vec![0u32];
        out_count
            .read(&mut count)
            .enq()
            .map_err(|e| TelomereError::SeedSearch(format!("{e}")))?;
        let count = count[0] as usize;

        // Read back the actual match pairs
        let mut pairs = vec![[0u32; 2]; count];
        if count > 0 {
            out_records
                .read(&mut pairs)
                .enq()
                .map_err(|e| TelomereError::SeedSearch(format!("{e}")))?;
        }

        // Convert to GpuMatchRecord
        let mut out = Vec::with_capacity(count);
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

    /// Pure-CPU fallback path.
    fn cpu_seed_match(
        &self,
        start_seed: usize,
        end_seed: usize,
    ) -> Result<Vec<GpuMatchRecord>, TelomereError> {
        let mut out = Vec::new();
        for seed in start_seed..end_seed {
            let seed_byte = seed as u8;
            for block in &self.tile {
                let expanded = crate::expand_seed(&[seed_byte], block.data.len());
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

    /// Lower‐level GPU matcher that handles chunking and error mapping.
    fn seed_match_gpu(
        &self,
        pq: &ProQue,
        start_seed: usize,
        end_seed: usize,
    ) -> Result<Vec<GpuMatchRecord>, TelomereError> {
        let mut out = Vec::new();
        let queue = pq.queue().clone();
        for block in &self.tile {
            let block_len = block.data.len();
            // Upload block data
            let block_buf: Buffer<u8> = Buffer::builder()
                .queue(queue.clone())
                .flags(ocl::flags::MEM_READ_ONLY | ocl::flags::MEM_COPY_HOST_PTR)
                .len(block_len)
                .copy_host_slice(&block.data)
                .build()
                .map_err(|e| TelomereError::Internal(format!("opencl: {e}")))?;

            // Iterate seeds in chunks
            let mut seed = start_seed;
            while seed < end_seed {
                let chunk = (end_seed - seed).min(4096);
                let seeds_vec: Vec<u8> =
                    (0..chunk).map(|i| (seed + i) as u8).collect();
                let seeds_buf: Buffer<u8> = Buffer::builder()
                    .queue(queue.clone())
                    .flags(ocl::flags::MEM_READ_ONLY | ocl::flags::MEM_COPY_HOST_PTR)
                    .len(chunk)
                    .copy_host_slice(&seeds_vec)
                    .build()
                    .map_err(|e| TelomereError::Internal(format!("opencl: {e}")))?;

                let out_buf: Buffer<ocl::prm::Uint2> = Buffer::builder()
                    .queue(queue.clone())
                    .flags(ocl::flags::MEM_WRITE_ONLY)
                    .len(chunk)
                    .build()
                    .map_err(|e| TelomereError::Internal(format!("opencl: {e}")))?;

                let kernel = pq
                    .kernel_builder("match_seeds")
                    .arg(&block_buf)
                    .arg(block_len as u32)
                    .arg(&seeds_buf)
                    .arg(chunk as u32)
                    .arg(&out_buf)
                    .global_work_size(chunk)
                    .build()
                    .map_err(|e| TelomereError::Internal(format!("opencl: {e}")))?;

                unsafe {
                    kernel
                        .cmd()
                        .enq()
                        .map_err(|e| TelomereError::Internal(format!("opencl: {e}")))?;
                }

                let mut results = vec![ocl::prm::Uint2::new(0, 0); chunk];
                out_buf
                    .read(&mut results)
                    .enq()
                    .map_err(|e| TelomereError::Internal(format!("opencl: {e}")))?;

                for pair in results {
                    if pair.1 != 0 {
                        out.push(GpuMatchRecord {
                            seed_index: seed + pair.0 as usize,
                            bundle_length: pair.1 as usize,
                            block_indices: vec![block.global_index],
                            original_bits: block.bit_length,
                        });
                    }
                }

                seed += chunk;
            }
        }
        Ok(out)
    }
}
