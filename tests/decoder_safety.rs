//! Decoder safety tests: malformed input must not panic or corrupt data.
use rand::Rng;
use telomere::{
    compress_multi_pass_with_config, decompress, decompress_with_limit,
    encode_v2_file_with_bit_len, Config, HasherKind, TlmrV2LayerDescriptor,
    V2_TIER_POLICY_SEED_SPAN,
};

fn fast_cfg(block_size: usize) -> Config {
    Config {
        block_size,
        max_seed_len: 1,
        hash_bits: 13,
        ..Config::default()
    }
}

#[test]
fn truncated_header_fails() {
    let block = 4usize;
    let data: Vec<u8> = (0u8..20).collect();
    let cfg = fast_cfg(block);
    let (mut compressed, _) = compress_multi_pass_with_config(&data, &cfg, 1, false).unwrap();
    compressed.truncate(compressed.len() - 1);
    assert!(decompress_with_limit(&compressed, &cfg, usize::MAX).is_err());
}

#[test]
fn orphan_bytes_fail() {
    let block = 3usize;
    let data: Vec<u8> = (0u8..10).collect();
    let cfg = fast_cfg(block);
    let (mut compressed, _) = compress_multi_pass_with_config(&data, &cfg, 1, false).unwrap();
    compressed.extend_from_slice(&[0xAA, 0xBB]);
    // Extra bytes make the stream invalid (bits_consumed check fails).
    assert!(decompress_with_limit(&compressed, &cfg, usize::MAX).is_err());
}

#[test]
fn single_bit_flip_mostly_fails() {
    let block = 4usize;
    let data: Vec<u8> = (0u8..32).collect();
    let cfg = fast_cfg(block);
    let (compressed, _) = compress_multi_pass_with_config(&data, &cfg, 1, false).unwrap();
    let total_bits = compressed.len() * 8;
    let mut rng = rand::thread_rng();
    let mut failures = 0u32;
    let trials = 50u32;
    for _ in 0..trials {
        let mut buf = compressed.clone();
        let bit = rng.gen_range(0..total_bits);
        buf[bit / 8] ^= 1u8 << (7 - (bit % 8));
        if decompress_with_limit(&buf, &cfg, usize::MAX).is_err() {
            failures += 1;
        }
    }
    // Output hash is 13 bits: ~1/8192 chance of undetected corruption.
    // With 50 trials we should catch >80% of flips.
    assert!(
        failures >= trials * 4 / 5,
        "only {}/{} flips detected",
        failures,
        trials
    );
}

#[test]
fn random_bytes_dont_panic() {
    let cfg = fast_cfg(3);
    let mut rng = rand::thread_rng();
    for _ in 0..100 {
        let len: usize = rng.gen_range(0..50);
        let garbage: Vec<u8> = (0..len).map(|_| rng.gen::<u8>()).collect();
        let _ = decompress_with_limit(&garbage, &cfg, usize::MAX);
    }
}

/// Regression test for a v2 decoder panic vector: a malicious layer descriptor
/// with `decoded_len = u64::MAX` would previously trip `Vec::with_capacity`'s
/// "capacity overflow" abort when consumers used `Config::default()` (which
/// sets `memory_limit = usize::MAX`, leaving no header-time guard). The fix
/// caps the pre-allocation using payload-derived output bounds as well as
/// Rust's `Vec::with_capacity` ceiling; the decode loop then detects the
/// inconsistency via per-record bounds checks and returns a clean `Err`.
#[test]
fn malicious_decoded_len_does_not_panic() {
    // Build a v2 file whose single layer descriptor advertises a wildly
    // oversized decoded length. The actual outer payload is irrelevant — we
    // just need the file to parse past the header/descriptor section so the
    // payload decoder runs `Vec::with_capacity(decoded_len)` on the bogus
    // value.
    let descriptor = TlmrV2LayerDescriptor {
        decoded_len: u64::MAX,
        decoded_hash: 0,
        max_seed_len: 1,
        max_span_len: 1,
        block_size: 1,
        tier_policy: V2_TIER_POLICY_SEED_SPAN,
        span_step: 1,
    };
    let outer_payload = vec![0u8; 1];
    let encoded = encode_v2_file_with_bit_len(
        HasherKind::Blake3,
        13,
        u64::MAX,
        std::slice::from_ref(&descriptor),
        &outer_payload,
        8,
    )
    .expect("encode malicious v2 file");

    // Default config sets memory_limit = usize::MAX so the layer-descriptor
    // size guard at the decompressor entry does not catch this case. With the
    // capacity clamp in place, the call must return Err — not panic.
    let cfg = Config::default();
    let result = std::panic::catch_unwind(|| decompress(&encoded, &cfg));
    assert!(
        result.is_ok(),
        "decompress panicked on malicious decoded_len = u64::MAX"
    );
    assert!(
        result.unwrap().is_err(),
        "decompress should return Err for malicious decoded_len"
    );
}
