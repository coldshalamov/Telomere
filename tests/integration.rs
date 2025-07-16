use std::fs;
use std::path::PathBuf;
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
            "--block-size",
            "3",
            "--input",
            input.to_str().unwrap(),
            "--output",
            compressed.to_str().unwrap(),
        ])
        .output()
        .expect("failed to run compress");
    assert!(compress.status.success());

    let decompress = Command::new(exe)
        .args([
            "decompress",
            "--input",
            compressed.to_str().unwrap(),
            "--output",
            output.to_str().unwrap(),
        ])
        .output()
        .expect("failed to run decompress");
    assert!(decompress.status.success());

    let original = fs::read(&input).unwrap();
    let roundtrip = fs::read(&output).unwrap();
    assert_eq!(original, roundtrip);

    let _ = fs::remove_file(input);
    let _ = fs::remove_file(compressed);
    let _ = fs::remove_file(output);
}
