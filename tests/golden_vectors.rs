//! Golden byte vectors for the Lotus-encoded `.tlmr` wire format.
//!
//! These tests pin the EXACT bytes emitted for known (deterministic) inputs.
//! They exist so that any future change which re-orders fields, swaps Lotus
//! presets, alters the bit layout, or shifts header parameters fails loudly
//! at the wire boundary rather than silently breaking forward compatibility
//! with already-written `.tlmr` files.
//!
//! Updating a vector is an intentional act:
//!   1. Re-run the test under `--nocapture` (the helper macro `pin!` keeps
//!      enough scaffolding for a maintainer to read the actual bytes).
//!   2. Confirm that the change is a deliberate wire-format change, not an
//!      accidental ripple from an unrelated edit.
//!   3. Update the pinned hex AND add a note in the docs/RELEASE_CHECKLIST
//!      describing what changed.
//!
//! Vectors covered:
//!   - V1 record (Lotus arity + Lotus seed_index) for arity=1, seed=0.
//!   - V1 record (literal marker).
//!   - V2 seed-span record for span_len=8, seed=[0], max_seed_len=1.
//!   - V2 literal record for the four bytes `[1, 2, 3, 4]`.
//!   - V1 file header (TlmrHeader) with a canonical fast configuration.
//!   - V2 file header (TlmrV2Header) with a canonical fast configuration.

use telomere::{
    encode_lotus_header, encode_tlmr_header, encode_tlmr_v2_header, pack_bits, v2_literal_record,
    v2_seed_span_record, HasherKind, TlmrHeader, TlmrV2Header, LOTUS_PRESET_VERSION,
    TLMR_FORMAT_VERSION,
};

/// Format a byte slice as `0xNN, 0xNN, …` for inclusion in the pinned table
/// when a maintainer updates a vector.
fn hex_table(bytes: &[u8]) -> String {
    bytes
        .iter()
        .map(|b| format!("0x{:02x}", b))
        .collect::<Vec<_>>()
        .join(", ")
}

// ---------------------------------------------------------------------------
// V1 record (arity + seed_index) goldens.

#[test]
fn v1_record_arity1_seed0_golden() {
    // Smallest possible compressed v1 record: arity=1 (J1D1 value=0, 3 bits)
    // + seed_index=0 (J3D2 value=0, 6 bits) = 9 bits. Packed MSB-first to
    // a byte boundary by `pack_bits`, the trailing 7 bits are zero pad.
    let bits = encode_lotus_header(1, 0).unwrap();
    let bytes = pack_bits(&bits);
    println!(
        "v1_record_arity1_seed0: bit_len={} bytes={}",
        bits.len(),
        hex_table(&bytes)
    );
    assert_eq!(bits.len(), 9, "arity=1 seed_index=0 should be 9 bits total");
    assert_eq!(bytes.len(), 2, "9 bits pack into 2 bytes");
    assert_eq!(
        bytes,
        vec![0x63, 0x80],
        "pinned wire bytes for arity=1 seed_index=0"
    );
}

#[test]
fn v1_record_literal_marker_golden() {
    // Literal escape: arity=0xFF maps to Lotus value=5 (J1D1's largest code
    // point, 6 bits). The packed byte has two trailing zero pad bits.
    let bits = encode_lotus_header(0xFF, 0).unwrap();
    let bytes = pack_bits(&bits);
    println!(
        "v1_record_literal_marker: bit_len={} bytes={}",
        bits.len(),
        hex_table(&bytes)
    );
    assert_eq!(bits.len(), 6, "literal marker is 6 bits in J1D1");
    assert_eq!(bytes.len(), 1);
    assert_eq!(bytes, vec![0xa0], "pinned wire bytes for literal marker");
}

// ---------------------------------------------------------------------------
// V2 record goldens.

#[test]
fn v2_seed_span_record_8_seed0_golden() {
    // (span_len=8, seed=[0], max_seed_len=1): tag=0 (J3D2, 6 bits) +
    // (span_len-1)=7 (J3D2, ? bits) + seed_index=0 (J3D2, 6 bits) = 22 bits
    // packed into 3 bytes per the existing `v2_seed_span_record_short_is_under_three_bytes`
    // test. This vector pins the exact byte values that come out.
    let r = v2_seed_span_record(8, &[0u8], 1).unwrap();
    println!(
        "v2_seed_span(8, [0], 1): bit_len={} bytes={}",
        r.bit_len,
        hex_table(&r.bytes)
    );
    assert_eq!(r.bit_len, 22, "expected 22 bits per Wave B headline");
    assert_eq!(r.bytes.len(), 3);
    assert_eq!(
        r.bytes,
        vec![0x1c, 0x8a, 0x1c],
        "pinned wire bytes for v2_seed_span(8, [0], 1)"
    );
}

#[test]
fn v2_literal_record_4_bytes_golden() {
    // V2 literal record for the four bytes [1, 2, 3, 4]:
    //   tag=1 (J3D2)
    //   (len-1)=3 (J3D2)
    //   0..7 zero pad to byte boundary
    //   four raw payload bytes
    let r = v2_literal_record(&[1, 2, 3, 4]).unwrap();
    println!(
        "v2_literal([1,2,3,4]): bit_len={} bytes={}",
        r.bit_len,
        hex_table(&r.bytes)
    );
    assert_eq!(r.bytes.len(), 7);
    assert_eq!(r.bit_len, 56);
    assert_eq!(
        r.bytes,
        vec![0x20, 0x10, 0x80, 0x01, 0x02, 0x03, 0x04],
        "pinned wire bytes for v2_literal([1,2,3,4])"
    );
}

// ---------------------------------------------------------------------------
// File header goldens.

/// Canonical "small" v1 header used for the golden vector. Chosen to be the
/// smallest legal configuration: 1-byte blocks, 1-byte max seed length, arity
/// 1, BLAKE3 hasher, 13-bit hash, one layer, zero payload bits, hash=0.
fn canonical_v1_header() -> TlmrHeader {
    TlmrHeader {
        version: TLMR_FORMAT_VERSION,
        lotus_preset: LOTUS_PRESET_VERSION,
        hasher: HasherKind::Blake3,
        block_size: 1,
        last_block_size: 1,
        max_seed_len: 1,
        max_arity: 1,
        hash_bits: 13,
        layer_count: 1,
        original_len: 0,
        payload_bit_len: 0,
        output_hash: 0,
    }
}

#[test]
fn v1_header_typical_golden() {
    let header = canonical_v1_header();
    let encoded = encode_tlmr_header(&header);
    println!(
        "v1_header_typical: len={} bytes={}",
        encoded.len(),
        hex_table(&encoded)
    );
    assert_eq!(
        encoded,
        vec![
            0x54, 0x4c, 0x4d, 0x52, 0x02, 0x20, 0x90, 0x08, 0x04, 0x02, 0x01, 0x00, 0x90, 0x10,
            0x07, 0x1c, 0x00, 0x00,
        ],
        "pinned wire bytes for canonical v1 header"
    );
}

/// Canonical "small" v2 header used for the golden vector. Sha256 hasher,
/// seed order version = 1 (current), one layer descriptor, 13-bit hash,
/// original_len = 0, outer_payload_bit_len = 0, hash = 0.
fn canonical_v2_header() -> TlmrV2Header {
    TlmrV2Header {
        version: telomere::TLMR_V2_FORMAT_VERSION,
        lotus_preset: telomere::LOTUS_PRESET_V2,
        hasher: HasherKind::Sha256,
        seed_order_version: telomere::V2_SEED_ORDER_VERSION,
        layer_count: 1,
        hash_bits: 13,
        original_len: 0,
        outer_payload_bit_len: 0,
        output_hash: 0,
    }
}

#[test]
fn v2_header_typical_golden() {
    let header = canonical_v2_header();
    let encoded = encode_tlmr_v2_header(&header).unwrap();
    println!(
        "v2_header_typical: len={} bytes={}",
        encoded.len(),
        hex_table(&encoded)
    );
    assert_eq!(
        encoded,
        vec![0x54, 0x4c, 0x4d, 0x52, 0x03, 0x20, 0x90, 0x48, 0x04, 0x02, 0x40, 0x38, 0xe0, 0x00,],
        "pinned wire bytes for canonical v2 header"
    );
}
