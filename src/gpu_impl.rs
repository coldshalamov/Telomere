use crate::block::Block;
use crate::{GpuMatchRecord, TelomereError};
use std::sync::OnceLock;

use ocl::{flags, prm::Uint2, Buffer, ProQue};

const LAUNCH_SIZE: usize = 4096;

static PRO_QUE: OnceLock<Option<ProQue>> = OnceLock::new();

fn proque() -> Option<&'static ProQue> {
    PRO_QUE
        .get_or_init(|| {
            let src = include_str!("gpu_kernels.cl");
            match ProQue::builder().src(src).dims(1).build() {
                Ok(pq) => Some(pq),
                Err(e) => {
                    eprintln!("GPU init failed, falling back to CPU: {e}");
                    None
                }
            }
        })
        .as_ref()
}

#[derive(Default)]
pub struct GpuSeedMatcher {
    tile: Vec<Block>,
}

impl GpuSeedMatcher {
    pub fn new() -> Self {
        Self { tile: Vec::new() }
    }

    pub fn load_tile(&mut self, blocks: &[Block]) {
        self.tile = blocks.to_vec();
    }

    pub fn seed_match(
        &self,
        start_seed: usize,
        end_seed: usize,
    ) -> Result<Vec<GpuMatchRecord>, TelomereError> {
        if let Some(pq) = proque() {
            self.seed_match_gpu(pq, start_seed, end_seed)
        } else {
            self.seed_match_cpu(start_seed, end_seed)
        }
    }

    fn seed_match_cpu(
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
            let block_buf: Buffer<u8> = match Buffer::builder()
                .queue(queue.clone())
                .flags(flags::MEM_READ_ONLY | flags::MEM_COPY_HOST_PTR)
                .len(block_len)
                .copy_host_slice(&block.data)
                .build() {
                Ok(b) => b,
                Err(e) => {
                    eprintln!("GPU error {:?}, falling back to CPU", e);
                    return self.seed_match_cpu(start_seed, end_seed);
                }
            };
            let mut seed = start_seed;
            while seed < end_seed {
                let chunk = (end_seed - seed).min(LAUNCH_SIZE);
                let seeds_vec: Vec<u32> = (0..chunk).map(|i| (seed + i) as u32).collect();
                let seeds_buf: Buffer<u32> = match Buffer::<u32>::builder()
                    .queue(queue.clone())
                    .flags(flags::MEM_READ_ONLY | flags::MEM_COPY_HOST_PTR)
                    .len(chunk)
                    .copy_host_slice(&seeds_vec)
                    .build() {
                    Ok(b) => b,
                    Err(e) => {
                        eprintln!("GPU error {:?}, falling back to CPU", e);
                        return self.seed_match_cpu(start_seed, end_seed);
                    }
                };
                let out_buf: Buffer<Uint2> = match Buffer::builder()
                    .queue(queue.clone())
                    .flags(flags::MEM_WRITE_ONLY)
                    .len(chunk)
                    .build() {
                    Ok(b) => b,
                    Err(e) => {
                        eprintln!("GPU error {:?}, falling back to CPU", e);
                        return self.seed_match_cpu(start_seed, end_seed);
                    }
                };
                let kernel = match pq
                    .kernel_builder("match_seeds")
                    .arg(&block_buf)
                    .arg(block_len as u32)
                    .arg(&seeds_buf)
                    .arg(chunk as u32)
                    .arg(&out_buf)
                    .global_work_size(chunk)
                    .build() {
                    Ok(k) => k,
                    Err(e) => {
                        eprintln!("GPU error {:?}, falling back to CPU", e);
                        return self.seed_match_cpu(start_seed, end_seed);
                    }
                };
                if let Err(e) = unsafe { kernel.enq() } {
                    eprintln!("GPU error {:?}, falling back to CPU", e);
                    return self.seed_match_cpu(start_seed, end_seed);
                }
                let mut results = vec![Uint2::new(0, 0); chunk];
                if let Err(e) = out_buf.read(&mut results).enq() {
                    eprintln!("GPU error {:?}, falling back to CPU", e);
                    return self.seed_match_cpu(start_seed, end_seed);
                }
                for pair in results.iter() {
                    if pair[1] != 0 {
                        out.push(GpuMatchRecord {
                            seed_index: seed + pair[0] as usize,
                            bundle_length: pair[1] as usize,
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
