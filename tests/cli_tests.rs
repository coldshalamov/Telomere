//! See [Kolyma Spec](../kolyma.pdf) - 2025-07-20 - commit c48b123cf3a8761a15713b9bf18697061ab23976
use std::fs;
use std::process::Command;

#[test]
fn compress_roundtrip_cli() {
    let exe = env!("CARGO_BIN_EXE_telomere");
    let dir = tempfile::tempdir().unwrap();
    let input = dir.path().join("input.bin");
    let compressed = dir.path().join("compressed.tlmr");
    let output = dir.path().join("output.bin");

    fs::write(&input, b"hello world").unwrap();

    let status = Command::new(exe)
        .args([
            "compress",
            input.to_str().unwrap(),
            compressed.to_str().unwrap(),
            "--block-size",
            "4",
        ])
        .status()
        .expect("compress failed");
    assert!(status.success());

    let status = Command::new(exe)
        .args([
            "decompress",
            compressed.to_str().unwrap(),
            output.to_str().unwrap(),
        ])
        .status()
        .expect("decompress failed");
    assert!(status.success());

    let orig = fs::read(&input).unwrap();
    let out = fs::read(&output).unwrap();
    assert_eq!(orig, out);
}
