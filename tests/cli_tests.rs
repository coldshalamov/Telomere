//! CLI roundtrip test using the main telomere binary.
use std::fs;
use std::process::Command;
use telomere::hasher::{SeedExpander, Sha256Expander};
use telomere::{
    decode_tlmr_header, decode_tlmr_v2_header, decode_tlmr_v2_layer_descriptors, HasherKind,
    V2_TIER_POLICY_PUBLIC_PRESET_SELECTIVE,
};

fn telomere_exe() -> String {
    std::env::var("CARGO_BIN_EXE_telomere").unwrap_or_else(|_| "target/debug/telomere".to_string())
}

#[test]
fn compress_roundtrip_cli() {
    let exe = telomere_exe();
    let dir = tempfile::tempdir().unwrap();
    let input = dir.path().join("input.bin");
    let compressed = dir.path().join("compressed.tlmr");
    let output = dir.path().join("output.bin");

    fs::write(&input, b"hello world").unwrap();

    let status = Command::new(&exe)
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
            "--memory-limit",
            "100%",
        ])
        .status()
        .expect("compress failed");
    assert!(status.success(), "compress subcommand failed");

    let status = Command::new(&exe)
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
    let exe = telomere_exe();
    let dir = tempfile::tempdir().unwrap();
    let input = dir.path().join("input.bin");
    let compressed = dir.path().join("compressed.tlmr");

    fs::write(&input, b"metadata selected hasher").unwrap();

    let output = Command::new(&exe)
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
fn streaming_v2_respects_memory_limit_preflight() {
    let exe = telomere_exe();
    let dir = tempfile::tempdir().unwrap();
    let input = dir.path().join("input.bin");
    let compressed = dir.path().join("compressed.tlmr");

    fs::write(&input, b"0123456789abcdef").unwrap();

    let output = Command::new(&exe)
        .args([
            "compress",
            input.to_str().unwrap(),
            compressed.to_str().unwrap(),
            "--engine",
            "streaming",
            "--format",
            "v2",
            "--hasher",
            "sha256",
            "--block-size",
            "4",
            "--max-span-len",
            "16",
            "--memory-limit",
            "1",
        ])
        .output()
        .expect("compress failed");

    assert!(!output.status.success());
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        stderr.contains("estimated streaming target table memory"),
        "stderr was {stderr}"
    );
    assert!(!compressed.exists());
}

#[test]
fn streaming_v2_chunked_target_tables_can_fit_below_whole_preflight() {
    let exe = telomere_exe();
    let dir = tempfile::tempdir().unwrap();
    let input = dir.path().join("input.bin");
    let whole_compressed = dir.path().join("whole.tlmr");
    let chunked_compressed = dir.path().join("chunked.tlmr");

    fs::write(&input, b"0123456789abcdef").unwrap();

    let whole = Command::new(&exe)
        .args([
            "compress",
            input.to_str().unwrap(),
            whole_compressed.to_str().unwrap(),
            "--engine",
            "streaming",
            "--format",
            "v2",
            "--hasher",
            "sha256",
            "--block-size",
            "4",
            "--max-span-len",
            "8",
            "--memory-limit",
            "28",
        ])
        .output()
        .expect("whole-table streaming compress failed");
    assert!(!whole.status.success());
    assert!(!whole_compressed.exists());

    let chunked = Command::new(&exe)
        .args([
            "compress",
            input.to_str().unwrap(),
            chunked_compressed.to_str().unwrap(),
            "--engine",
            "streaming",
            "--format",
            "v2",
            "--hasher",
            "sha256",
            "--block-size",
            "4",
            "--max-span-len",
            "8",
            "--memory-limit",
            "28",
            "--target-chunk-bytes",
            "28",
            "--verify",
        ])
        .output()
        .expect("chunked streaming compress failed");

    assert!(
        chunked.status.success(),
        "chunked compress failed: {}",
        String::from_utf8_lossy(&chunked.stderr)
    );
    assert!(chunked_compressed.exists());
}

#[test]
fn indexed_v2_chunked_target_tables_can_fit_below_whole_preflight() {
    let exe = telomere_exe();
    let dir = tempfile::tempdir().unwrap();
    let index_dir = dir.path().join("sha-index");
    let input = dir.path().join("input.bin");
    let whole_compressed = dir.path().join("whole.tlmr");
    let chunked_compressed = dir.path().join("chunked.tlmr");

    fs::write(&input, b"0123456789abcdef").unwrap();
    let build = Command::new(&exe)
        .args([
            "index",
            "build",
            "--output",
            index_dir.to_str().unwrap(),
            "--hasher",
            "sha256",
            "--max-seed-len",
            "1",
            "--max-span-len",
            "8",
            "--block-size",
            "4",
        ])
        .status()
        .expect("index build failed");
    assert!(build.success());

    let whole = Command::new(&exe)
        .args([
            "compress",
            input.to_str().unwrap(),
            whole_compressed.to_str().unwrap(),
            "--engine",
            "indexed",
            "--format",
            "v2",
            "--index",
            index_dir.to_str().unwrap(),
            "--hasher",
            "sha256",
            "--block-size",
            "4",
            "--max-span-len",
            "8",
            "--memory-limit",
            "28",
        ])
        .output()
        .expect("whole indexed compress failed");
    assert!(!whole.status.success());
    assert!(!whole_compressed.exists());

    let chunked = Command::new(&exe)
        .args([
            "compress",
            input.to_str().unwrap(),
            chunked_compressed.to_str().unwrap(),
            "--engine",
            "indexed",
            "--format",
            "v2",
            "--index",
            index_dir.to_str().unwrap(),
            "--hasher",
            "sha256",
            "--block-size",
            "4",
            "--max-span-len",
            "8",
            "--memory-limit",
            "28",
            "--target-chunk-bytes",
            "28",
            "--verify",
        ])
        .output()
        .expect("chunked indexed compress failed");

    assert!(
        chunked.status.success(),
        "chunked indexed compress failed: {}",
        String::from_utf8_lossy(&chunked.stderr)
    );
    assert!(chunked_compressed.exists());
}

#[test]
fn compress_refuses_to_overwrite_without_force() {
    let exe = telomere_exe();
    let dir = tempfile::tempdir().unwrap();
    let input = dir.path().join("input.bin");
    let compressed = dir.path().join("compressed.tlmr");

    fs::write(&input, b"hello").unwrap();
    fs::write(&compressed, b"existing").unwrap();

    let output = Command::new(&exe)
        .args([
            "compress",
            input.to_str().unwrap(),
            compressed.to_str().unwrap(),
            "--seed-depth",
            "1",
            "--memory-limit",
            "100%",
        ])
        .output()
        .expect("compress failed");

    assert!(!output.status.success());
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(stderr.contains("use --force"), "stderr was {stderr}");
}

#[test]
fn decompress_refuses_to_overwrite_without_force() {
    let exe = telomere_exe();
    let dir = tempfile::tempdir().unwrap();
    let input = dir.path().join("input.bin");
    let compressed = dir.path().join("compressed.tlmr");
    let output_path = dir.path().join("output.bin");

    fs::write(&input, b"hello world").unwrap();
    fs::write(&output_path, b"existing").unwrap();

    let status = Command::new(&exe)
        .args([
            "compress",
            input.to_str().unwrap(),
            compressed.to_str().unwrap(),
            "--seed-depth",
            "1",
            "--memory-limit",
            "100%",
        ])
        .status()
        .expect("compress failed");
    assert!(status.success());

    let output = Command::new(&exe)
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
fn decompress_respects_memory_limit_cli() {
    let exe = telomere_exe();
    let dir = tempfile::tempdir().unwrap();
    let input = dir.path().join("input.bin");
    let compressed = dir.path().join("compressed.tlmr");
    let output_path = dir.path().join("output.bin");

    fs::write(&input, b"hello world").unwrap();
    let status = Command::new(&exe)
        .args([
            "compress",
            input.to_str().unwrap(),
            compressed.to_str().unwrap(),
            "--seed-depth",
            "1",
            "--memory-limit",
            "100%",
        ])
        .status()
        .expect("compress failed");
    assert!(status.success());

    let output = Command::new(&exe)
        .args([
            "decompress",
            compressed.to_str().unwrap(),
            output_path.to_str().unwrap(),
            "--memory-limit",
            "1",
        ])
        .output()
        .expect("decompress failed");

    assert!(!output.status.success());
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        stderr.contains("Decompression exceeded --memory-limit"),
        "stderr was {stderr}"
    );
    assert!(!output_path.exists());
}

#[test]
fn v2_decompress_respects_memory_limit_cli() {
    let exe = telomere_exe();
    let dir = tempfile::tempdir().unwrap();
    let input = dir.path().join("input.bin");
    let compressed = dir.path().join("compressed.tlmr");
    let output_path = dir.path().join("output.bin");

    let mut planted = vec![0; 8];
    Sha256Expander.expand_into(&[0x00], &mut planted);
    fs::write(&input, &planted).unwrap();

    let status = Command::new(&exe)
        .args([
            "compress",
            input.to_str().unwrap(),
            compressed.to_str().unwrap(),
            "--engine",
            "streaming",
            "--format",
            "v2",
            "--hasher",
            "sha256",
            "--seed-depth",
            "1",
            "--max-span-len",
            "16",
            "--block-size",
            "4",
            "--memory-limit",
            "100%",
        ])
        .status()
        .expect("v2 compress failed");
    assert!(status.success(), "v2 compress subcommand failed");

    let output = Command::new(&exe)
        .args([
            "decompress",
            compressed.to_str().unwrap(),
            output_path.to_str().unwrap(),
            "--memory-limit",
            "1",
        ])
        .output()
        .expect("v2 decompress failed");

    assert!(!output.status.success());
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        stderr.contains("Decompression exceeded --memory-limit"),
        "stderr was {stderr}"
    );
    assert!(!output_path.exists());
}

#[test]
fn corrupt_input_message_is_actionable() {
    let exe = telomere_exe();
    let dir = tempfile::tempdir().unwrap();
    let input = dir.path().join("bad.tlmr");
    let output_path = dir.path().join("output.bin");

    fs::write(&input, b"bad").unwrap();

    let output = Command::new(&exe)
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

#[test]
fn index_build_info_verify_and_indexed_v2_cli_roundtrip() {
    let exe = telomere_exe();
    let dir = tempfile::tempdir().unwrap();
    let index_dir = dir.path().join("sha-index");
    let input = dir.path().join("input.bin");
    let compressed = dir.path().join("compressed.tlmr");
    let output_path = dir.path().join("output.bin");

    let mut planted = vec![0; 8];
    Sha256Expander.expand_into(&[0x00], &mut planted);
    fs::write(&input, &planted).unwrap();

    let build = Command::new(&exe)
        .args([
            "index",
            "build",
            "--output",
            index_dir.to_str().unwrap(),
            "--hasher",
            "sha256",
            "--max-seed-len",
            "1",
            "--max-span-len",
            "8",
            "--block-size",
            "4",
        ])
        .output()
        .expect("index build failed");
    assert!(
        build.status.success(),
        "index build failed: {}",
        String::from_utf8_lossy(&build.stderr)
    );

    let info = Command::new(&exe)
        .args(["index", "info", index_dir.to_str().unwrap()])
        .output()
        .expect("index info failed");
    assert!(info.status.success());
    assert!(String::from_utf8_lossy(&info.stdout).contains("\"max_span_len\": 8"));

    let verify = Command::new(&exe)
        .args(["index", "verify", index_dir.to_str().unwrap()])
        .status()
        .expect("index verify failed");
    assert!(verify.success());

    let compress = Command::new(&exe)
        .args([
            "compress",
            input.to_str().unwrap(),
            compressed.to_str().unwrap(),
            "--engine",
            "indexed",
            "--index",
            index_dir.to_str().unwrap(),
            "--format",
            "v2",
            "--hasher",
            "sha256",
            "--seed-depth",
            "1",
            "--max-span-len",
            "8",
            "--block-size",
            "4",
            "--passes",
            "2",
            "--json",
        ])
        .output()
        .expect("indexed compress failed");
    assert!(
        compress.status.success(),
        "indexed compress failed: {}",
        String::from_utf8_lossy(&compress.stderr)
    );
    let json: serde_json::Value = serde_json::from_slice(&compress.stdout).unwrap();
    assert_eq!(
        json["engine_telemetry"]["container_bytes"],
        json["final_bytes"]
    );
    assert!(
        json["engine_telemetry"]["candidate_count"]
            .as_u64()
            .unwrap()
            > 0
    );
    assert!(json["engine_telemetry"]["selected_count"].as_u64().unwrap() > 0);
    assert_eq!(
        json["engine_telemetry"]["selected_spans"][0]["seed_hex"],
        "00"
    );
    assert_eq!(
        json["engine_telemetry"]["layers"][0]["selected_spans"][0]["span_len"],
        8
    );

    let bytes = fs::read(&compressed).unwrap();
    let header = decode_tlmr_v2_header(&bytes).unwrap();
    assert_eq!(header.hasher, HasherKind::Sha256);
    assert_eq!(header.layer_count, 1);

    let decompress = Command::new(&exe)
        .args([
            "decompress",
            compressed.to_str().unwrap(),
            output_path.to_str().unwrap(),
        ])
        .status()
        .expect("v2 decompress failed");
    assert!(decompress.success());
    assert_eq!(fs::read(output_path).unwrap(), planted);
}

#[test]
fn streaming_v2_json_reports_engine_telemetry() {
    let exe = telomere_exe();
    let dir = tempfile::tempdir().unwrap();
    let input = dir.path().join("input.bin");
    let compressed = dir.path().join("compressed.tlmr");

    let mut planted = vec![0; 8];
    Sha256Expander.expand_into(&[0x00], &mut planted);
    fs::write(&input, &planted).unwrap();

    let output = Command::new(&exe)
        .args([
            "compress",
            input.to_str().unwrap(),
            compressed.to_str().unwrap(),
            "--engine",
            "streaming",
            "--format",
            "v2",
            "--hasher",
            "sha256",
            "--seed-depth",
            "1",
            "--max-span-len",
            "8",
            "--block-size",
            "4",
            "--json",
            "--verify",
        ])
        .output()
        .expect("streaming compress failed");
    assert!(
        output.status.success(),
        "streaming compress failed: {}",
        String::from_utf8_lossy(&output.stderr)
    );

    let json: serde_json::Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(
        json["final_bytes"].as_u64().unwrap(),
        fs::metadata(&compressed).unwrap().len()
    );
    assert_eq!(
        json["engine_telemetry"]["container_bytes"],
        json["final_bytes"]
    );
    assert_eq!(json["engine_telemetry"]["layers"][0]["pass"], 1);
    assert_eq!(json["engine_telemetry"]["seeds_scanned"], 256);
    assert_eq!(json["engine_telemetry"]["seed_expansions"], 256);
    assert_eq!(json["engine_telemetry"]["layers"][0]["seeds_scanned"], 256);
    assert!(
        json["engine_telemetry"]["candidate_count"]
            .as_u64()
            .unwrap()
            > 0
    );
    assert!(json["engine_telemetry"]["selected_count"].as_u64().unwrap() > 0);
    assert_eq!(
        json["engine_telemetry"]["selected_spans"][0]["seed_hex"],
        "00"
    );
    assert_eq!(
        json["engine_telemetry"]["layers"][0]["selected_spans"][0]["span_len"],
        8
    );
    assert_eq!(
        json["engine_telemetry"]["tiers"][0]["lookup_count"],
        json["engine_telemetry"]["seeds_scanned"]
    );
    assert_eq!(
        json["engine_telemetry"]["tiers"][0]["candidate_hits"],
        json["engine_telemetry"]["tiers"][0]["candidate_hits_profitable"]
    );
    assert_eq!(
        json["engine_telemetry"]["tiers"][0]["candidate_hits_raw"],
        1
    );
    assert_eq!(json["engine_telemetry"]["tiers"][0]["target_windows"], 1);
    assert!(
        json["engine_telemetry"]["layers"][0]["payload_bytes"]
            .as_u64()
            .unwrap()
            < planted.len() as u64
    );

    let bytes = fs::read(&compressed).unwrap();
    let header = decode_tlmr_v2_header(&bytes).unwrap();
    assert_eq!(header.hasher, HasherKind::Sha256);
}

#[test]
fn streaming_v2_public_preset_transform_cli_roundtrips_native() {
    let exe = telomere_exe();
    let dir = tempfile::tempdir().unwrap();
    let input = dir.path().join("input.jsonl");
    let compressed = dir.path().join("compressed.tlmr");
    let output_path = dir.path().join("output.jsonl");

    let row = br#"{"event":"order_update","amount_cents":12345,"status":"fulfilled"}"#;
    let mut data = Vec::new();
    for _ in 0..80 {
        data.extend_from_slice(row);
        data.push(b'\n');
    }
    fs::write(&input, &data).unwrap();

    let output = Command::new(&exe)
        .args([
            "compress",
            input.to_str().unwrap(),
            compressed.to_str().unwrap(),
            "--engine",
            "streaming",
            "--format",
            "v2",
            "--hasher",
            "sha256",
            "--seed-depth",
            "1",
            "--max-span-len",
            "8",
            "--block-size",
            "4",
            "--span-step",
            "1",
            "--transform",
            "public-preset-selective",
            "--public-preset-min-token-len",
            "7",
            "--json",
            "--verify",
        ])
        .output()
        .expect("streaming transform compress failed");
    assert!(
        output.status.success(),
        "streaming transform compress failed: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    let json: serde_json::Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(json["engine_telemetry"]["transform"]["min_token_len"], 7);
    assert!(
        json["engine_telemetry"]["transform"]["token_replacements"]
            .as_u64()
            .unwrap()
            > 0
    );

    let bytes = fs::read(&compressed).unwrap();
    let header = decode_tlmr_v2_header(&bytes).unwrap();
    assert_eq!(header.layer_count, 2);
    let descriptors = decode_tlmr_v2_layer_descriptors(&bytes).unwrap();
    assert_eq!(
        descriptors[1].tier_policy,
        V2_TIER_POLICY_PUBLIC_PRESET_SELECTIVE
    );

    let decompress = Command::new(&exe)
        .args([
            "decompress",
            compressed.to_str().unwrap(),
            output_path.to_str().unwrap(),
        ])
        .status()
        .expect("transform v2 decompress failed");
    assert!(decompress.success());
    assert_eq!(fs::read(output_path).unwrap(), data);
}

#[test]
fn streaming_v2_seed_bits_controls_search_budget() {
    let exe = telomere_exe();
    let dir = tempfile::tempdir().unwrap();
    let input = dir.path().join("input.bin");
    let compressed = dir.path().join("compressed.tlmr");

    let mut planted = vec![0; 8];
    Sha256Expander.expand_into(&[0x00, 0x00], &mut planted);
    fs::write(&input, planted).unwrap();

    let output = Command::new(&exe)
        .args([
            "compress",
            input.to_str().unwrap(),
            compressed.to_str().unwrap(),
            "--engine",
            "streaming",
            "--format",
            "v2",
            "--hasher",
            "sha256",
            "--seed-bits",
            "9",
            "--max-span-len",
            "8",
            "--block-size",
            "4",
            "--json",
            "--verify",
        ])
        .output()
        .expect("streaming seed-bits compress failed");
    assert!(
        output.status.success(),
        "streaming seed-bits compress failed: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    let json: serde_json::Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(json["engine_telemetry"]["seed_limit"], 512);
    assert_eq!(json["engine_telemetry"]["layers"][0]["seeds_scanned"], 512);
    assert!(
        json["engine_telemetry"]["layers"][0]["selected_count"]
            .as_u64()
            .unwrap()
            > 0
    );
    assert_eq!(
        json["engine_telemetry"]["layers"][0]["seed_len_counts"][2],
        1
    );
}

#[test]
fn streaming_v2_json_telemetry_limit_bounds_selected_spans() {
    let exe = telomere_exe();
    let dir = tempfile::tempdir().unwrap();
    let input = dir.path().join("input.bin");
    let compressed = dir.path().join("compressed.tlmr");

    let mut planted = vec![0; 8];
    Sha256Expander.expand_into(&[0x00], &mut planted);
    fs::write(&input, planted.repeat(4)).unwrap();

    let output = Command::new(&exe)
        .args([
            "compress",
            input.to_str().unwrap(),
            compressed.to_str().unwrap(),
            "--engine",
            "streaming",
            "--format",
            "v2",
            "--hasher",
            "sha256",
            "--seed-depth",
            "1",
            "--max-span-len",
            "8",
            "--block-size",
            "4",
            "--json",
            "--telemetry-limit",
            "1",
            "--verify",
        ])
        .output()
        .expect("streaming compress failed");
    assert!(
        output.status.success(),
        "streaming compress failed: {}",
        String::from_utf8_lossy(&output.stderr)
    );

    let json: serde_json::Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(
        json["engine_telemetry"]["selected_spans"]
            .as_array()
            .unwrap()
            .len(),
        1
    );
    assert_eq!(json["engine_telemetry"]["selected_spans_total"], 4);
    assert_eq!(json["engine_telemetry"]["selected_spans_omitted"], 3);
    assert_eq!(
        json["engine_telemetry"]["layers"][0]["selected_spans"]
            .as_array()
            .unwrap()
            .len(),
        1
    );
    assert_eq!(
        json["engine_telemetry"]["layers"][0]["selected_spans_total"],
        4
    );
}

#[test]
fn streaming_v2_cli_span_step_one_finds_offset_span() {
    let exe = telomere_exe();
    let dir = tempfile::tempdir().unwrap();
    let input = dir.path().join("input.bin");
    let compressed = dir.path().join("compressed.tlmr");

    let mut planted = vec![0xAA];
    let mut span = vec![0; 8];
    Sha256Expander.expand_into(&[0x00], &mut span);
    planted.extend_from_slice(&span);
    fs::write(&input, planted).unwrap();

    let output = Command::new(&exe)
        .args([
            "compress",
            input.to_str().unwrap(),
            compressed.to_str().unwrap(),
            "--engine",
            "streaming",
            "--format",
            "v2",
            "--hasher",
            "sha256",
            "--seed-depth",
            "1",
            "--max-span-len",
            "8",
            "--block-size",
            "4",
            "--span-step",
            "1",
            "--passes",
            "1",
            "--memory-limit",
            "100%",
            "--json",
            "--verify",
            "--force",
        ])
        .output()
        .expect("compress failed");

    assert!(
        output.status.success(),
        "compress failed: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    let stdout = String::from_utf8_lossy(&output.stdout);
    let summary: serde_json::Value = serde_json::from_str(&stdout).unwrap();
    assert!(
        summary["engine_telemetry"]["selected_count"]
            .as_u64()
            .unwrap()
            >= 1,
        "summary was {summary:#}"
    );

    let descriptors = decode_tlmr_v2_layer_descriptors(&fs::read(compressed).unwrap()).unwrap();
    assert_eq!(descriptors[0].span_step, 1);
}

#[test]
fn compress_rejects_span_step_outside_v2_engines() {
    let exe = telomere_exe();
    let dir = tempfile::tempdir().unwrap();
    let input = dir.path().join("input.bin");
    let compressed = dir.path().join("compressed.tlmr");

    fs::write(&input, b"span step should not be ignored").unwrap();

    let output = Command::new(&exe)
        .args([
            "compress",
            input.to_str().unwrap(),
            compressed.to_str().unwrap(),
            "--span-step",
            "1",
            "--memory-limit",
            "100%",
        ])
        .output()
        .expect("compress failed");

    assert!(!output.status.success());
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        stderr.contains("indexed/streaming v2"),
        "stderr was {stderr}"
    );
}

#[test]
fn indexed_cli_rejects_stale_cross_hasher_index() {
    let exe = telomere_exe();
    let dir = tempfile::tempdir().unwrap();
    let index_dir = dir.path().join("sha-index");
    let input = dir.path().join("input.bin");
    let compressed = dir.path().join("compressed.tlmr");

    fs::write(&input, b"stale index guard").unwrap();

    let build = Command::new(&exe)
        .args([
            "index",
            "build",
            "--output",
            index_dir.to_str().unwrap(),
            "--hasher",
            "sha256",
            "--max-seed-len",
            "1",
            "--max-span-len",
            "8",
            "--block-size",
            "4",
        ])
        .status()
        .expect("index build failed");
    assert!(build.success());

    let output = Command::new(&exe)
        .args([
            "compress",
            input.to_str().unwrap(),
            compressed.to_str().unwrap(),
            "--engine",
            "indexed",
            "--index",
            index_dir.to_str().unwrap(),
            "--format",
            "v2",
            "--hasher",
            "blake3",
            "--seed-depth",
            "1",
            "--max-span-len",
            "8",
        ])
        .output()
        .expect("indexed compress failed");

    assert!(!output.status.success());
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        stderr.contains("index hasher mismatch"),
        "stderr was {stderr}"
    );
}
