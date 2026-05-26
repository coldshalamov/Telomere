use lotus::{lotus_encode_into_writer, BitWriter};
use telomere::hasher::{SeedExpander, Sha256Expander};
use telomere::{
    build_seed_index_to_dir, compress_indexed_v2_with_chunked_span_step_and_telemetry,
    compress_indexed_v2_with_index, compress_indexed_v2_with_telemetry,
    compress_streaming_v2_with_telemetry, decode_tlmr_v2_header, decode_tlmr_v2_layer_descriptors,
    decode_v2_header_and_descriptors, decompress_with_limit, encode_v2_file,
    encode_v2_file_with_bit_len, estimate_target_table_chunk_upper_bound_for_tiers,
    estimate_target_table_upper_bound_for_tiers, select_weighted_candidates_for_tests,
    v2_literal_record, v2_seed_span_record, Config, HasherKind, IndexConfig, IndexedCandidate,
    MmapSeedExpansionIndex, SeedExpansionIndex, SeedLookup, TlmrV2LayerDescriptor,
    V2_RECORD_TAG_SEED_SPAN,
};

fn index_config() -> IndexConfig {
    IndexConfig {
        hasher: HasherKind::Sha256,
        max_seed_len: 1,
        max_span_len: 8,
        tier_lengths: vec![2, 4, 8],
    }
}

fn sha_expand(seed: &[u8], len: usize) -> Vec<u8> {
    let mut out = vec![0; len];
    Sha256Expander.expand_into(seed, &mut out);
    out
}

#[test]
fn seed_expansion_index_uses_exact_generated_prefixes() {
    let index = SeedExpansionIndex::build_in_memory(&index_config()).unwrap();
    let target = sha_expand(&[0x00], 8);

    let hit8 = index.lookup_exact(8, &target).unwrap().expect("8-byte hit");
    assert_eq!(hit8.seed, vec![0x00]);
    assert_eq!(hit8.seed_index, 0);

    let hit4 = index
        .lookup_exact(4, &target[..4])
        .unwrap()
        .expect("4-byte hit");
    assert_eq!(hit4.seed, vec![0x00]);

    let digest = Sha256Expander.digest(&target);
    assert!(
        index.lookup_exact(8, &digest[..8]).unwrap().is_none(),
        "index lookup must not treat hash(target) as target bytes"
    );
}

#[test]
fn disk_index_builder_supports_seed_depth_two() {
    let config = IndexConfig {
        hasher: HasherKind::Sha256,
        max_seed_len: 2,
        max_span_len: 4,
        tier_lengths: vec![4],
    };
    let dir = tempfile::tempdir().unwrap();
    let manifest = build_seed_index_to_dir(&config, dir.path()).unwrap();

    assert_eq!(manifest.max_seed_len, 2);
    assert!(manifest.tiers[0].record_count > 256);
    MmapSeedExpansionIndex::verify_dir(dir.path()).unwrap();

    let index = MmapSeedExpansionIndex::open_dir(dir.path()).unwrap();
    let target = sha_expand(&[0x01, 0x02], 4);
    let hit = index.lookup_exact(4, &target).unwrap().unwrap();
    let mut reconstructed = vec![0u8; 4];
    Sha256Expander.expand_into(&hit.seed, &mut reconstructed);
    assert_eq!(reconstructed, target);
}

#[test]
fn indexed_compression_rejects_cross_hasher_index() {
    let index = SeedExpansionIndex::build_in_memory(&index_config()).unwrap();
    let data = sha_expand(&[0x00], 8);

    let err = compress_indexed_v2_with_index(&data, &index, HasherKind::Blake3, 1, 8, 4, 1, 13)
        .unwrap_err();

    assert!(err.to_string().contains("index hasher mismatch"));
}

#[test]
fn indexed_v2_compresses_planted_long_span_and_roundtrips() {
    let index = SeedExpansionIndex::build_in_memory(&index_config()).unwrap();
    let data = sha_expand(&[0x00], 8);

    let encoded =
        compress_indexed_v2_with_index(&data, &index, HasherKind::Sha256, 1, 8, 4, 1, 13).unwrap();

    let header = decode_tlmr_v2_header(&encoded).unwrap();
    assert_eq!(header.layer_count, 1);
    assert_eq!(header.original_len, data.len() as u64);

    let decoded = decompress_with_limit(&encoded, &Default::default(), usize::MAX).unwrap();
    assert_eq!(decoded, data);
    // Old fixed layout was 48 (header) + 32 (descriptor) = 80 bytes. The
    // Lotus-encoded layout is substantially smaller, so this generous bound
    // continues to hold while letting the format shrink further.
    assert!(encoded.len() < data.len() + 80);
}

#[test]
fn indexed_v2_records_selected_span_telemetry() {
    let index = SeedExpansionIndex::build_in_memory(&index_config()).unwrap();
    let data = sha_expand(&[0x00], 8);

    let (_encoded, telemetry) =
        compress_indexed_v2_with_telemetry(&data, &index, HasherKind::Sha256, 1, 8, 4, 1, 13)
            .unwrap();
    let span = telemetry
        .selected_spans
        .first()
        .expect("selected span telemetry");

    assert_eq!(span.pass, 1);
    assert_eq!(span.start, 0);
    assert_eq!(span.span_len, 8);
    assert_eq!(span.seed_index, 0);
    assert_eq!(span.seed_len, 1);
    assert_eq!(span.seed_hex, "00");
    // Under the new full-Lotus framing the seed-span record packs three
    // J3D2 Lotus values back-to-back (no byte tag, no u16 span_len, no
    // lotus_byte_count). For span_len=8 / seed_index=0 the encoded byte
    // length (ceil-divided from bits) shrinks from the old 5 bytes.
    assert_eq!(span.encoded_len, 3);
    assert_eq!(span.savings, span.span_len - span.encoded_len);
    assert_eq!(telemetry.layers[0].selected_spans, telemetry.selected_spans);
    let tier8 = telemetry
        .tiers
        .iter()
        .find(|tier| tier.span_len == 8)
        .expect("span-8 tier telemetry");
    assert_eq!(tier8.target_windows, 1);
    assert_eq!(tier8.lookup_count, 1);
    assert_eq!(tier8.candidate_hits_raw, 1);
    assert_eq!(tier8.candidate_hits_profitable, 1);
    assert_eq!(tier8.candidate_hits, tier8.candidate_hits_profitable);
    assert_eq!(tier8.estimated_target_table_bytes, 16);
}

#[test]
fn indexed_chunked_target_tables_match_unchunked_selected_spans() {
    let index = SeedExpansionIndex::build_in_memory(&index_config()).unwrap();
    let span = sha_expand(&[0x00], 8);
    let mut data = Vec::new();
    data.extend_from_slice(&span);
    data.extend_from_slice(&[0xAA, 0xBB, 0xCC, 0xDD]);
    data.extend_from_slice(&span);

    let (unchunked, unchunked_telemetry) =
        compress_indexed_v2_with_telemetry(&data, &index, HasherKind::Sha256, 1, 8, 4, 1, 13)
            .unwrap();
    let (chunked, chunked_telemetry) = compress_indexed_v2_with_chunked_span_step_and_telemetry(
        &data,
        &index,
        HasherKind::Sha256,
        1,
        8,
        4,
        4,
        1,
        13,
        38,
    )
    .unwrap();

    assert_eq!(
        decompress_with_limit(&chunked, &Config::default(), usize::MAX).unwrap(),
        data
    );
    assert_eq!(
        decompress_with_limit(&unchunked, &Config::default(), usize::MAX).unwrap(),
        data
    );
    assert_eq!(
        chunked_telemetry.selected_spans,
        unchunked_telemetry.selected_spans
    );
    assert!(
        chunked_telemetry.tiers.len() > unchunked_telemetry.tiers.len(),
        "chunked telemetry should report per-chunk tier rows"
    );
}

#[test]
fn indexed_chunked_target_table_estimate_bounds_chunk_peak() {
    let tier_lengths = [4, 8];
    let whole = estimate_target_table_upper_bound_for_tiers(16, &tier_lengths, 4);
    let chunked =
        estimate_target_table_chunk_upper_bound_for_tiers(16, &tier_lengths, 4, 28).unwrap();

    assert_eq!(whole, 96);
    assert_eq!(chunked, 28);
    assert!(chunked < whole);
}

#[test]
fn v2_recursive_two_layer_file_decodes_without_an_index() {
    let original = sha_expand(&[0x00], 4);
    let inner_payload = v2_seed_span_record(4, &[0x00], 1).unwrap().bytes;
    let outer_payload = v2_literal_record(&inner_payload).unwrap().bytes;

    let layers = vec![
        TlmrV2LayerDescriptor::for_decoded_bytes(&inner_payload, HasherKind::Sha256, 1, 4, 4, 13),
        TlmrV2LayerDescriptor::for_decoded_bytes(&original, HasherKind::Sha256, 1, 4, 4, 13),
    ];
    let encoded = encode_v2_file(
        HasherKind::Sha256,
        13,
        original.len() as u64,
        &layers,
        &outer_payload,
    )
    .unwrap();

    let decoded = decompress_with_limit(&encoded, &Default::default(), usize::MAX).unwrap();
    assert_eq!(decoded, original);

    // Corrupt the outer payload area (any non-pad bit flip should break the
    // layer hash). The first byte of the outer payload contains the Lotus tag
    // for the outer literal record, so any flip here breaks decoding before
    // the inner layer hash check. The new format places header+descriptors in
    // a single variable-length bit-stream — query the decoder for the actual
    // payload start instead of computing from removed constants.
    let (_, _, payload_start) = decode_v2_header_and_descriptors(&encoded).unwrap();
    let mut corrupt = encoded;
    corrupt[payload_start] ^= 0x80;
    assert!(decompress_with_limit(&corrupt, &Default::default(), usize::MAX).is_err());
}

#[test]
fn v2_seed_span_record_is_pure_bitstream() {
    let original = sha_expand(&[0x00], 4);
    let encoded_record = v2_seed_span_record(4, &[0x00], 1).unwrap();
    // The new wire format encodes the seed-span record as three Lotus
    // J3D2 values back-to-back with no byte tag, u16 span_len, or u8
    // lotus_byte_count. For (span_len=4, seed_index=0) in J3D2:
    //   tag=0  -> 6 bits
    //   span_len-1=3 -> small Lotus value
    //   seed_index=0 -> 6 bits
    // Total must be well under the old 5-byte framing.
    assert!(
        encoded_record.bit_len < 32,
        "expected < 32 bits, got {}",
        encoded_record.bit_len
    );
    assert_eq!(
        encoded_record.bytes.len(),
        encoded_record.bit_len.div_ceil(8)
    );

    let layer =
        TlmrV2LayerDescriptor::for_decoded_bytes(&original, HasherKind::Sha256, 1, 4, 4, 13);
    let encoded = encode_v2_file(
        HasherKind::Sha256,
        13,
        original.len() as u64,
        &[layer],
        &encoded_record.bytes,
    )
    .unwrap();
    assert_eq!(
        decompress_with_limit(&encoded, &Config::default(), usize::MAX).unwrap(),
        original
    );
    assert_ne!(
        encoded_record.bit_len % 8,
        0,
        "fixture should exercise trailing layer padding"
    );

    let mut corrupt = encoded;
    let last = corrupt.len() - 1;
    corrupt[last] |= 0x01;
    let err = decompress_with_limit(&corrupt, &Config::default(), usize::MAX).unwrap_err();
    assert!(err.to_string().contains("nonzero v2 trailing pad bit"));
}

#[test]
fn v2_decoder_rejects_outer_payload_bit_len_shorter_than_consumed_record() {
    let original = sha_expand(&[0x00], 4);
    let encoded_record = v2_seed_span_record(4, &[0x00], 1).unwrap();
    let layer =
        TlmrV2LayerDescriptor::for_decoded_bytes(&original, HasherKind::Sha256, 1, 4, 4, 13);
    let encoded = encode_v2_file_with_bit_len(
        HasherKind::Sha256,
        13,
        original.len() as u64,
        &[layer],
        &encoded_record.bytes,
        (encoded_record.bit_len - 1) as u64,
    )
    .unwrap();

    let err = decompress_with_limit(&encoded, &Config::default(), usize::MAX).unwrap_err();
    assert!(
        err.to_string()
            .contains("v2 payload consumed past declared bit length"),
        "{err}"
    );
}

#[test]
fn v2_decoder_rejects_extra_zero_trailing_bytes() {
    let original = sha_expand(&[0x00], 4);
    let encoded_record = v2_seed_span_record(4, &[0x00], 1).unwrap();
    assert_ne!(
        encoded_record.bit_len % 8,
        0,
        "fixture should exercise final partial-byte padding"
    );
    let mut payload = encoded_record.bytes;
    payload.push(0);
    let layer =
        TlmrV2LayerDescriptor::for_decoded_bytes(&original, HasherKind::Sha256, 1, 4, 4, 13);
    let encoded = encode_v2_file(
        HasherKind::Sha256,
        13,
        original.len() as u64,
        &[layer],
        &payload,
    )
    .unwrap();

    let err = decompress_with_limit(&encoded, &Config::default(), usize::MAX).unwrap_err();
    assert!(err.to_string().contains("excess v2 trailing pad bits"));
}

#[test]
fn v2_seed_span_record_supports_min_span_len_one() {
    let original = sha_expand(&[0x00], 1);
    let payload = v2_seed_span_record(1, &[0x00], 1).unwrap().bytes;
    let layer =
        TlmrV2LayerDescriptor::for_decoded_bytes(&original, HasherKind::Sha256, 1, 1, 1, 13);
    let encoded = encode_v2_file(
        HasherKind::Sha256,
        13,
        original.len() as u64,
        &[layer],
        &payload,
    )
    .unwrap();

    let decoded = decompress_with_limit(&encoded, &Config::default(), usize::MAX).unwrap();
    assert_eq!(decoded, original);
}

#[test]
fn v2_decoder_rejects_unknown_lotus_record_tag() {
    let mut writer = BitWriter::new();
    lotus_encode_into_writer(99, 3, 2, &mut writer).unwrap();
    let payload = writer.into_bytes();
    let layer = TlmrV2LayerDescriptor::for_decoded_bytes(&[0], HasherKind::Sha256, 1, 1, 1, 13);
    let encoded = encode_v2_file(HasherKind::Sha256, 13, 1, &[layer], &payload).unwrap();

    let err = decompress_with_limit(&encoded, &Config::default(), usize::MAX).unwrap_err();
    assert!(err.to_string().contains("unknown v2 record tag"));
}

#[test]
fn v2_decoder_rejects_nonzero_literal_alignment_padding() {
    let mut payload = v2_literal_record(b"x").unwrap().bytes;
    payload[1] |= 0x01;
    let layer = TlmrV2LayerDescriptor::for_decoded_bytes(b"x", HasherKind::Sha256, 1, 1, 1, 13);
    let encoded = encode_v2_file(HasherKind::Sha256, 13, 1, &[layer], &payload).unwrap();

    let err = decompress_with_limit(&encoded, &Config::default(), usize::MAX).unwrap_err();
    assert!(err.to_string().contains("nonzero v2 literal pad bit"));
}

#[test]
fn v2_decoder_rejects_out_of_range_lotus_seed_index() {
    let mut writer = BitWriter::new();
    lotus_encode_into_writer(V2_RECORD_TAG_SEED_SPAN, 3, 2, &mut writer).unwrap();
    lotus_encode_into_writer(3, 3, 2, &mut writer).unwrap();
    lotus_encode_into_writer(256, 3, 2, &mut writer).unwrap();
    let payload = writer.into_bytes();
    let layer = TlmrV2LayerDescriptor::for_decoded_bytes(&[0; 4], HasherKind::Sha256, 1, 4, 4, 13);
    let encoded = encode_v2_file(HasherKind::Sha256, 13, 4, &[layer], &payload).unwrap();

    let err = decompress_with_limit(&encoded, &Config::default(), usize::MAX).unwrap_err();
    assert!(err.to_string().contains("invalid v2 seed index"));
}

#[test]
fn v2_layer_hash_mismatch_after_valid_record_decode_is_rejected() {
    let expected = sha_expand(&[0x00], 4);
    let payload = v2_seed_span_record(4, &[0x01], 1).unwrap().bytes;
    let layer =
        TlmrV2LayerDescriptor::for_decoded_bytes(&expected, HasherKind::Sha256, 1, 4, 4, 13);
    let encoded = encode_v2_file(
        HasherKind::Sha256,
        13,
        expected.len() as u64,
        &[layer],
        &payload,
    )
    .unwrap();

    let err = decompress_with_limit(&encoded, &Config::default(), usize::MAX).unwrap_err();
    assert!(err.to_string().contains("layer hash mismatch"));
}

#[test]
fn weighted_selection_beats_greedy_overlap() {
    let selected = select_weighted_candidates_for_tests(vec![
        IndexedCandidate {
            start: 0,
            span_len: 4,
            seed_index: 1,
            seed: vec![0x01],
            encoded_bits: 3 * 8,
            encoded_len: 3,
        },
        IndexedCandidate {
            start: 0,
            span_len: 2,
            seed_index: 2,
            seed: vec![0x02],
            encoded_bits: 8,
            encoded_len: 1,
        },
        IndexedCandidate {
            start: 2,
            span_len: 4,
            seed_index: 3,
            seed: vec![0x03],
            encoded_bits: 8,
            encoded_len: 1,
        },
    ]);

    assert_eq!(selected.len(), 2);
    assert_eq!(selected[0].start, 0);
    assert_eq!(selected[0].span_len, 2);
    assert_eq!(selected[1].start, 2);
    assert_eq!(selected[1].span_len, 4);
}

#[test]
fn weighted_selection_handles_many_non_overlapping_spans() {
    let candidates: Vec<_> = (0..1024)
        .map(|idx| IndexedCandidate {
            start: idx * 4,
            span_len: 4,
            seed_index: idx,
            seed: vec![(idx % 256) as u8],
            encoded_bits: 8,
            encoded_len: 1,
        })
        .collect();

    let selected = select_weighted_candidates_for_tests(candidates);

    assert_eq!(selected.len(), 1024);
    assert_eq!(selected.first().unwrap().start, 0);
    assert_eq!(selected.last().unwrap().start, 4092);
}

#[test]
fn v2_decoder_rejects_huge_intermediate_layer_before_allocation() {
    let layer = TlmrV2LayerDescriptor {
        decoded_len: 2048,
        decoded_hash: 0,
        max_seed_len: 1,
        max_span_len: 4,
        block_size: 4,
        tier_policy: 1,
        span_step: 4,
    };
    let encoded = encode_v2_file(HasherKind::Sha256, 13, 0, &[layer], &[]).unwrap();
    let cfg = Config {
        memory_limit: 1024,
        ..Config::default()
    };

    let err = decompress_with_limit(&encoded, &cfg, 1024).unwrap_err();
    assert!(err.to_string().contains("layer output limit exceeded"));
}

#[test]
fn v2_decoder_rejects_unknown_descriptor_fields() {
    // The v3 wire format encodes the header and layer descriptors as a
    // continuous Lotus bit-stream, so the old "reserved byte" check is gone
    // (there ARE no reserved bytes — variable-length encodings can't reserve
    // future-proof slots). Tier policy and span_step constraints still hold,
    // and we exercise them by constructing v2 files via the public API with
    // deliberately invalid descriptor values.
    let original = sha_expand(&[0x00], 4);
    let payload = v2_seed_span_record(4, &[0x00], 1).unwrap().bytes;

    // Unknown tier policy: rejected at decode time.
    let bad_policy_layer = TlmrV2LayerDescriptor {
        decoded_len: original.len() as u64,
        decoded_hash: 0,
        max_seed_len: 1,
        max_span_len: 4,
        block_size: 4,
        tier_policy: 99,
        span_step: 4,
    };
    let bad_policy = encode_v2_file(
        HasherKind::Sha256,
        13,
        original.len() as u64,
        &[bad_policy_layer],
        &payload,
    )
    .unwrap();
    assert!(decompress_with_limit(&bad_policy, &Config::default(), usize::MAX).is_err());

    // span_step out of range (zero is rejected at encode time, so use a value
    // larger than block_size which the validator rejects at decode time).
    let bad_span_step_layer = TlmrV2LayerDescriptor {
        decoded_len: original.len() as u64,
        decoded_hash: 0,
        max_seed_len: 1,
        max_span_len: 4,
        block_size: 4,
        tier_policy: 1,
        span_step: 8, // > block_size
    };
    let bad_span_step = encode_v2_file(
        HasherKind::Sha256,
        13,
        original.len() as u64,
        &[bad_span_step_layer],
        &payload,
    )
    .unwrap();
    assert!(decompress_with_limit(&bad_span_step, &Config::default(), usize::MAX).is_err());

    // Sanity: a well-formed file with the same parameters roundtrips. Without
    // this we'd be testing nothing.
    let good_layer =
        TlmrV2LayerDescriptor::for_decoded_bytes(&original, HasherKind::Sha256, 1, 4, 4, 13);
    let good = encode_v2_file(
        HasherKind::Sha256,
        13,
        original.len() as u64,
        &[good_layer],
        &payload,
    )
    .unwrap();
    assert_eq!(
        decompress_with_limit(&good, &Config::default(), usize::MAX).unwrap(),
        original
    );
}

#[test]
fn v2_decoder_accepts_sub_block_span_step_metadata() {
    let original = sha_expand(&[0x00], 4);
    let payload = v2_seed_span_record(4, &[0x00], 1).unwrap().bytes;
    let layer = TlmrV2LayerDescriptor::for_decoded_bytes_with_span_step(
        &original,
        HasherKind::Sha256,
        1,
        4,
        4,
        1,
        13,
    );
    let encoded = encode_v2_file(
        HasherKind::Sha256,
        13,
        original.len() as u64,
        &[layer],
        &payload,
    )
    .unwrap();

    let decoded = decompress_with_limit(&encoded, &Config::default(), usize::MAX).unwrap();
    assert_eq!(decoded, original);
    let descriptor = decode_tlmr_v2_layer_descriptors(&encoded)
        .unwrap()
        .remove(0);
    assert_eq!(descriptor.span_step, 1);
}

#[test]
fn v2_public_compressors_reject_invalid_hash_bits_without_panicking() {
    let index = SeedExpansionIndex::build_in_memory(&index_config()).unwrap();
    let data = sha_expand(&[0x00], 8);

    let indexed_err =
        compress_indexed_v2_with_index(&data, &index, HasherKind::Sha256, 1, 8, 4, 1, 0)
            .unwrap_err();
    assert!(indexed_err.to_string().contains("hash_bits"));

    let streaming_err =
        compress_streaming_v2_with_telemetry(&data, HasherKind::Sha256, 1, 8, 4, 2, 1, 0)
            .unwrap_err();
    assert!(streaming_err.to_string().contains("hash_bits"));
}
