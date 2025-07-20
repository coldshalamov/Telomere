//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
use std::fs;
use std::process::Command;

#[test]
fn invalid_extension_error() {
    let exe = env!("CARGO_BIN_EXE_telomere");
    let dir = tempfile::tempdir().unwrap();
    let input = dir.path().join("input.txt");
    fs::write(&input, b"bad").unwrap();
    let out = dir.path().join("out.bin");
    let output = Command::new(exe)
        .args(["d", input.to_str().unwrap(), out.to_str().unwrap()])
        .output()
        .expect("run failed");
    assert!(!output.status.success());
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(stderr.contains("Invalid file extension"));
}

#[test]
fn truncated_file_error() {
    let exe = env!("CARGO_BIN_EXE_telomere");
    let dir = tempfile::tempdir().unwrap();
    let input = dir.path().join("bad.tlmr");
    fs::write(&input, b"baddata").unwrap();
    let out = dir.path().join("out.bin");
    let output = Command::new(exe)
        .args(["d", input.to_str().unwrap(), out.to_str().unwrap()])
        .output()
        .expect("run failed");
    assert!(!output.status.success());
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(stderr.contains("Verify the file is intact"));
}
