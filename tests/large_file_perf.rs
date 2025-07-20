use rand::rngs::StdRng;
use rand::{RngCore, SeedableRng};
use std::time::Instant;
use sysinfo::{ProcessExt, System, SystemExt};
use telomere::{compress_multi_pass, decompress_with_limit, Config};

fn cfg(block: usize) -> Config {
    Config { block_size: block, hash_bits: 13, ..Config::default() }
}

fn profile_case(name: &str, data: Vec<u8>) {
    let mut sys = System::new_all();
    let pid = sysinfo::get_current_pid().unwrap();
    let block_size = 4usize;
    sys.refresh_process(pid);
    let before_mem = sys.process(pid).map(|p| p.memory()).unwrap_or(0);

    let start = Instant::now();
    let (compressed, _gains) =
        compress_multi_pass(&data, block_size, 3).expect("compress");
    let comp_time = start.elapsed();
    sys.refresh_process(pid);
    let after_comp_mem = sys.process(pid).map(|p| p.memory()).unwrap_or(0);

    let start = Instant::now();
    let decompressed = decompress_with_limit(&compressed, &cfg(block_size), usize::MAX).expect("decompress");
    let decomp_time = start.elapsed();
    sys.refresh_process(pid);
    let after_decomp_mem = sys.process(pid).map(|p| p.memory()).unwrap_or(0);

    assert_eq!(data, decompressed);

    println!(
        "{name}: input={}MB compressed={}MB ratio={:.2}% comp_time={:.2?} decomp_time={:.2?} mem_before={}KB mem_after_comp={}KB mem_after_decomp={}KB",
        data.len() as f64 / 1_048_576.0,
        compressed.len() as f64 / 1_048_576.0,
        100.0 * (1.0 - compressed.len() as f64 / data.len() as f64),
        comp_time,
        decomp_time,
        before_mem,
        after_comp_mem,
        after_decomp_mem
    );
}

#[test]
#[ignore]
fn large_file_perf() {
    let size = 512 * 1024 * 1024usize;
    let mut rng = StdRng::seed_from_u64(42);

    let mut random = vec![0u8; size];
    rng.fill_bytes(&mut random);
    profile_case("random", random);

    let mut partial = vec![0u8; size];
    for chunk in partial.chunks_mut(1024) {
        let len = 512.min(chunk.len());
        rng.fill_bytes(&mut chunk[..len]);
    }
    profile_case("partial", partial);

    let zeros = vec![0u8; size];
    profile_case("zeros", zeros);
}
