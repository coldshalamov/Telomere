//! CLI roundtrip integration test using the main telomere binary.
use std::fs;
use std::process::Command;

#[test]
fn cli_roundtrip() {
    let exe = env!("CARGO_BIN_EXE_telomere");
    let dir = std::env::temp_dir();
    let input = dir.join("telomere_input.bin");
    let compressed = dir.join("telomere_compressed.tlmr");
    let output = dir.join("telomere_output.bin");

    fs::write(&input, (0u8..14).collect::<Vec<_>>()).unwrap();

    let compress = Command::new(exe)
        .args([
            "compress",
            input.to_str().unwrap(),
            compressed.to_str().unwrap(),
            "--block-size",
            "3",
            "--seed-depth",
            "1", // fast: 256 seeds per block
            "--passes",
            "1",
        ])
        .output()
        .expect("failed to run compress");
    assert!(
        compress.status.success(),
        "compress failed: {}",
        String::from_utf8_lossy(&compress.stderr)
    );

    let decompress = Command::new(exe)
        .args([
            "decompress",
            compressed.to_str().unwrap(),
            output.to_str().unwrap(),
        ])
        .output()
        .expect("failed to run decompress");
    assert!(
        decompress.status.success(),
        "decompress failed: {}",
        String::from_utf8_lossy(&decompress.stderr)
    );

    let original = fs::read(&input).unwrap();
    let roundtrip = fs::read(&output).unwrap();
    assert_eq!(original, roundtrip);

    let _ = fs::remove_file(&input);
    let _ = fs::remove_file(&compressed);
    let _ = fs::remove_file(&output);
}
