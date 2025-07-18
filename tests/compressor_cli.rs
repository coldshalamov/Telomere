use std::fs;
use std::process::Command;

#[test]
fn cli_roundtrip_compressor() {
    let comp = env!("CARGO_BIN_EXE_compressor");
    let decomp = env!("CARGO_BIN_EXE_decompressor");
    let dir = tempfile::tempdir().unwrap();
    let input = dir.path().join("input.bin");
    let compressed = dir.path().join("compressed.tlmr");
    let output = dir.path().join("output.bin");

    fs::write(&input, (0u8..32).collect::<Vec<_>>()).unwrap();

    let status = Command::new(comp)
        .args([
            input.to_str().unwrap(),
            compressed.to_str().unwrap(),
            "--block-size",
            "3",
            "--test",
        ])
        .status()
        .expect("compress failed");
    assert!(status.success());

    let status = Command::new(decomp)
        .args([compressed.to_str().unwrap(), output.to_str().unwrap()])
        .status()
        .expect("decompress failed");
    assert!(status.success());

    let orig = fs::read(&input).unwrap();
    let out = fs::read(&output).unwrap();
    assert_eq!(orig, out);
}

#[test]
fn decompress_errors_propagate() {
    let decomp = env!("CARGO_BIN_EXE_decompressor");
    let dir = tempfile::tempdir().unwrap();
    let input = dir.path().join("bad.txt");
    fs::write(&input, b"bad").unwrap();
    let out = dir.path().join("out.bin");
    let status = Command::new(decomp)
        .args([input.to_str().unwrap(), out.to_str().unwrap()])
        .status()
        .expect("run failed");
    assert!(!status.success());
}
