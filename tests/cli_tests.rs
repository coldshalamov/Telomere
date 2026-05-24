//! CLI roundtrip test using the main telomere binary.
use std::fs;
use std::process::Command;
use telomere::{decode_tlmr_header, HasherKind};

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
            "--seed-depth",
            "1", // fast: 256 seeds per block
            "--passes",
            "1",
        ])
        .status()
        .expect("compress failed");
    assert!(status.success(), "compress subcommand failed");

    let status = Command::new(exe)
        .args([
            "decompress",
            compressed.to_str().unwrap(),
            output.to_str().unwrap(),
        ])
        .status()
        .expect("decompress failed");
    assert!(status.success(), "decompress subcommand failed");

    let orig = fs::read(&input).unwrap();
    let out = fs::read(&output).unwrap();
    assert_eq!(orig, out, "roundtrip mismatch");
}

#[test]
fn compress_json_verify_hasher_and_memory_limit_cli() {
    let exe = env!("CARGO_BIN_EXE_telomere");
    let dir = tempfile::tempdir().unwrap();
    let input = dir.path().join("input.bin");
    let compressed = dir.path().join("compressed.tlmr");

    fs::write(&input, b"metadata selected hasher").unwrap();

    let output = Command::new(exe)
        .args([
            "compress",
            input.to_str().unwrap(),
            compressed.to_str().unwrap(),
            "--block-size",
            "4",
            "--seed-depth",
            "1",
            "--passes",
            "2",
            "--hasher",
            "sha256",
            "--memory-limit",
            "100%",
            "--json",
            "--verify",
        ])
        .output()
        .expect("compress failed");

    assert!(
        output.status.success(),
        "compress failed: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("\"final_bytes\""), "stdout was {stdout}");

    let bytes = fs::read(compressed).unwrap();
    let header = decode_tlmr_header(&bytes).unwrap();
    assert_eq!(header.hasher, HasherKind::Sha256);
    assert_eq!(header.layer_count, 1);
}

#[test]
fn compress_refuses_to_overwrite_without_force() {
    let exe = env!("CARGO_BIN_EXE_telomere");
    let dir = tempfile::tempdir().unwrap();
    let input = dir.path().join("input.bin");
    let compressed = dir.path().join("compressed.tlmr");

    fs::write(&input, b"hello").unwrap();
    fs::write(&compressed, b"existing").unwrap();

    let output = Command::new(exe)
        .args([
            "compress",
            input.to_str().unwrap(),
            compressed.to_str().unwrap(),
            "--seed-depth",
            "1",
        ])
        .output()
        .expect("compress failed");

    assert!(!output.status.success());
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(stderr.contains("use --force"), "stderr was {stderr}");
}

#[test]
fn decompress_refuses_to_overwrite_without_force() {
    let exe = env!("CARGO_BIN_EXE_telomere");
    let dir = tempfile::tempdir().unwrap();
    let input = dir.path().join("input.bin");
    let compressed = dir.path().join("compressed.tlmr");
    let output_path = dir.path().join("output.bin");

    fs::write(&input, b"hello world").unwrap();
    fs::write(&output_path, b"existing").unwrap();

    let status = Command::new(exe)
        .args([
            "compress",
            input.to_str().unwrap(),
            compressed.to_str().unwrap(),
            "--seed-depth",
            "1",
        ])
        .status()
        .expect("compress failed");
    assert!(status.success());

    let output = Command::new(exe)
        .args([
            "decompress",
            compressed.to_str().unwrap(),
            output_path.to_str().unwrap(),
        ])
        .output()
        .expect("decompress failed");

    assert!(!output.status.success());
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(stderr.contains("use --force"), "stderr was {stderr}");
}

#[test]
fn corrupt_input_message_is_actionable() {
    let exe = env!("CARGO_BIN_EXE_telomere");
    let dir = tempfile::tempdir().unwrap();
    let input = dir.path().join("bad.tlmr");
    let output_path = dir.path().join("output.bin");

    fs::write(&input, b"bad").unwrap();

    let output = Command::new(exe)
        .args([
            "decompress",
            input.to_str().unwrap(),
            output_path.to_str().unwrap(),
        ])
        .output()
        .expect("decompress failed");

    assert!(!output.status.success());
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        stderr.contains("File appears corrupt or truncated"),
        "stderr was {stderr}"
    );
}
