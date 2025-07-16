use std::fs;
use std::process::Command;

#[test]
fn invalid_extension_error() {
    let exe = env!("CARGO_BIN_EXE_inchworm");
    let dir = tempfile::tempdir().unwrap();
    let input = dir.path().join("input.txt");
    fs::write(&input, b"bad").unwrap();
    let out = dir.path().join("out.bin");
    let status = Command::new(exe)
        .args(["d", input.to_str().unwrap(), out.to_str().unwrap()])
        .status()
        .expect("run failed");
    assert!(!status.success());
}

#[test]
fn truncated_file_error() {
    let exe = env!("CARGO_BIN_EXE_inchworm");
    let dir = tempfile::tempdir().unwrap();
    let input = dir.path().join("bad.tlmr");
    fs::write(&input, b"baddata").unwrap();
    let out = dir.path().join("out.bin");
    let status = Command::new(exe)
        .args(["d", input.to_str().unwrap(), out.to_str().unwrap()])
        .status()
        .expect("run failed");
    assert!(!status.success());
}
