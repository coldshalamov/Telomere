//! GPU determinism test — requires GPU feature and verified hardware.
//! Marked #[ignore] until GPU path is validated (see research plan section 4.6).
use std::fs;
use std::process::Command;

#[test]
#[ignore = "GPU path not yet verified; requires --features gpu and OpenCL hardware"]
fn compress_identical_with_and_without_gpu() {
    use rand::{Rng, SeedableRng};
    let dir = tempfile::tempdir().unwrap();
    let input = dir.path().join("input.bin");
    let cpu_out = dir.path().join("cpu.tlmr");
    let gpu_out = dir.path().join("gpu.tlmr");

    let mut rng = rand::rngs::StdRng::seed_from_u64(42);
    let data: Vec<u8> = (0..1024).map(|_| rng.gen()).collect(); // small for now
    fs::write(&input, &data).unwrap();

    let status = Command::new("cargo")
        .args(["run", "--quiet", "--release", "--bin", "compressor", "--",
               input.to_str().unwrap(), cpu_out.to_str().unwrap(),
               "--max-seed-len", "1", "--passes", "1"])
        .status()
        .expect("cpu run");
    assert!(status.success());

    let status = Command::new("cargo")
        .args(["run", "--quiet", "--release", "--features", "gpu", "--bin", "compressor", "--",
               input.to_str().unwrap(), gpu_out.to_str().unwrap(),
               "--max-seed-len", "1", "--passes", "1"])
        .status()
        .expect("gpu run");
    assert!(status.success());

    let cpu_bytes = fs::read(cpu_out).unwrap();
    let gpu_bytes = fs::read(gpu_out).unwrap();
    assert_eq!(cpu_bytes, gpu_bytes);
}
