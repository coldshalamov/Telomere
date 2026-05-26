use crate::config::HasherKind;
use crate::indexed::{
    encode_layer_records, estimate_target_table_bytes, estimate_target_table_upper_bound_for_tiers,
    select_weighted_candidates, selected_span_telemetry, IndexedCandidate, SelectedSpanTelemetry,
};
use crate::public_preset::{
    public_preset_selective_framed, PublicPresetTransformStats, PUBLIC_PRESET_CODEWORD_LEN,
    PUBLIC_PRESET_SELECTIVE_MIN_TOKEN_LEN,
};
use crate::seed_index::index_to_seed;
use crate::tlmr::MAX_ARITY;
use crate::tlmr_v2::{
    decode_v2_header_and_descriptors, encode_v2_file, validate_v2_search_config,
    validate_v2_span_step, TlmrV2LayerDescriptor, MAX_V2_SEED_LEN,
};
use crate::TelomereError;
use serde::Serialize;
use std::collections::HashMap;
use std::time::Instant;

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct StreamingTierTelemetry {
    pub span_len: usize,
    pub unique_spans: usize,
    pub target_windows: usize,
    pub lookup_count: usize,
    pub candidate_hits: usize,
    pub candidate_hits_raw: usize,
    pub candidate_hits_profitable: usize,
    pub duration_ms: u64,
    pub estimated_target_table_bytes: usize,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct StreamingLayerTelemetry {
    pub pass: usize,
    pub bytes_in: usize,
    pub payload_bytes: usize,
    pub duration_ms: u64,
    pub candidate_count: usize,
    pub selected_count: usize,
    pub literal_bytes: usize,
    pub seed_len_counts: Vec<u64>,
    pub bundle_count: usize,
    pub seeds_scanned: usize,
    pub seed_expansions: usize,
    pub selected_spans: Vec<SelectedSpanTelemetry>,
    pub tiers: Vec<StreamingTierTelemetry>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct StreamingTelemetry {
    pub candidate_count: usize,
    pub selected_count: usize,
    pub literal_bytes: usize,
    pub seed_len_counts: Vec<u64>,
    pub bundle_count: usize,
    pub seeds_scanned: usize,
    pub seed_expansions: usize,
    pub seed_limit: Option<usize>,
    pub selected_spans: Vec<SelectedSpanTelemetry>,
    pub tiers: Vec<StreamingTierTelemetry>,
    pub layers: Vec<StreamingLayerTelemetry>,
    pub final_payload_bytes: usize,
    pub container_bytes: usize,
    pub stop_reason: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct PublicPresetStreamingTelemetry {
    pub transform: PublicPresetTransformStats,
    #[serde(flatten)]
    pub streaming: StreamingTelemetry,
}

impl StreamingTelemetry {
    fn empty(max_seed_len: usize) -> Self {
        Self {
            candidate_count: 0,
            selected_count: 0,
            literal_bytes: 0,
            seed_len_counts: vec![0; max_seed_len + 1],
            bundle_count: 0,
            seeds_scanned: 0,
            seed_expansions: 0,
            seed_limit: None,
            selected_spans: Vec::new(),
            tiers: Vec::new(),
            layers: Vec::new(),
            final_payload_bytes: 0,
            container_bytes: 0,
            stop_reason: "not_started".into(),
        }
    }
}

pub fn seed_limit_from_bits(seed_bits: usize) -> Result<usize, TelomereError> {
    let max_bits = 8 * MAX_V2_SEED_LEN;
    if seed_bits == 0 || seed_bits > max_bits {
        return Err(TelomereError::Config(format!(
            "seed_bits must be in 1..={max_bits}"
        )));
    }
    1usize
        .checked_shl(seed_bits as u32)
        .ok_or_else(|| TelomereError::Config("seed_bits is too large for this platform".into()))
}

fn total_seed_count(max_seed_len: usize) -> Result<usize, TelomereError> {
    let mut total = 0usize;
    for seed_len in 1..=max_seed_len {
        let bits = 8usize
            .checked_mul(seed_len)
            .ok_or_else(|| TelomereError::Config("max_seed_len overflows seed bit width".into()))?;
        let count = 1usize.checked_shl(bits as u32).ok_or_else(|| {
            TelomereError::Config("max_seed_len is too large for this platform".into())
        })?;
        total = total
            .checked_add(count)
            .ok_or_else(|| TelomereError::Config("seed count overflows usize".into()))?;
    }
    Ok(total)
}

fn max_seed_len_for_seed_limit(seed_limit: usize) -> Result<usize, TelomereError> {
    if seed_limit == 0 {
        return Err(TelomereError::Config(
            "seed_limit must be greater than zero".into(),
        ));
    }

    let mut total = 0usize;
    for seed_len in 1..=MAX_V2_SEED_LEN {
        let count = 1usize.checked_shl((8 * seed_len) as u32).ok_or_else(|| {
            TelomereError::Config("seed bucket is too large for this platform".into())
        })?;
        total = total
            .checked_add(count)
            .ok_or_else(|| TelomereError::Config("seed count overflows usize".into()))?;
        if seed_limit <= total {
            return Ok(seed_len);
        }
    }

    Err(TelomereError::Config(format!(
        "seed_limit exceeds the v2 experimental maximum of {MAX_V2_SEED_LEN} seed bytes"
    )))
}

fn validate_seed_limit(
    max_seed_len: usize,
    seed_limit: Option<usize>,
) -> Result<(), TelomereError> {
    let Some(seed_limit) = seed_limit else {
        return Ok(());
    };
    if seed_limit == 0 {
        return Err(TelomereError::Config(
            "seed_limit must be greater than zero".into(),
        ));
    }
    let total = total_seed_count(max_seed_len)?;
    if seed_limit > total {
        return Err(TelomereError::Config(format!(
            "seed_limit {seed_limit} exceeds available canonical seeds {total} for max_seed_len={max_seed_len}"
        )));
    }
    Ok(())
}

struct SpanTier {
    span_len: usize,
    spans: HashMap<Vec<u8>, Vec<usize>>,
    target_windows: usize,
    lookup_count: usize,
    candidate_hits: usize,
    candidate_hits_raw: usize,
    candidate_hits_profitable: usize,
    duration_ms: u64,
}

#[allow(clippy::too_many_arguments)]
pub fn compress_streaming_v2(
    data: &[u8],
    hasher: HasherKind,
    max_seed_len: usize,
    max_span_len: usize,
    block_size: usize,
    max_arity: u8,
    passes: usize,
    hash_bits: usize,
) -> Result<Vec<u8>, TelomereError> {
    let (out, _) = compress_streaming_v2_with_telemetry(
        data,
        hasher,
        max_seed_len,
        max_span_len,
        block_size,
        max_arity,
        passes,
        hash_bits,
    )?;
    Ok(out)
}

#[allow(clippy::too_many_arguments)]
pub fn compress_streaming_v2_with_telemetry(
    data: &[u8],
    hasher: HasherKind,
    max_seed_len: usize,
    max_span_len: usize,
    block_size: usize,
    max_arity: u8,
    passes: usize,
    hash_bits: usize,
) -> Result<(Vec<u8>, StreamingTelemetry), TelomereError> {
    compress_streaming_v2_with_span_step_and_telemetry(
        data,
        hasher,
        max_seed_len,
        max_span_len,
        block_size,
        block_size,
        max_arity,
        passes,
        hash_bits,
    )
}

#[allow(clippy::too_many_arguments)]
pub fn compress_streaming_v2_with_span_step_and_telemetry(
    data: &[u8],
    hasher: HasherKind,
    max_seed_len: usize,
    max_span_len: usize,
    block_size: usize,
    span_step: usize,
    max_arity: u8,
    passes: usize,
    hash_bits: usize,
) -> Result<(Vec<u8>, StreamingTelemetry), TelomereError> {
    compress_streaming_v2_with_chunk_option_and_telemetry(
        data,
        hasher,
        max_seed_len,
        max_span_len,
        block_size,
        span_step,
        max_arity,
        passes,
        hash_bits,
        None,
        None,
    )
}

#[allow(clippy::too_many_arguments)]
pub fn compress_streaming_v2_with_chunked_span_step_and_telemetry(
    data: &[u8],
    hasher: HasherKind,
    max_seed_len: usize,
    max_span_len: usize,
    block_size: usize,
    span_step: usize,
    max_arity: u8,
    passes: usize,
    hash_bits: usize,
    target_chunk_bytes: usize,
) -> Result<(Vec<u8>, StreamingTelemetry), TelomereError> {
    compress_streaming_v2_with_chunk_option_and_telemetry(
        data,
        hasher,
        max_seed_len,
        max_span_len,
        block_size,
        span_step,
        max_arity,
        passes,
        hash_bits,
        Some(target_chunk_bytes),
        None,
    )
}

#[allow(clippy::too_many_arguments)]
pub fn compress_streaming_v2_with_seed_limit_and_telemetry(
    data: &[u8],
    hasher: HasherKind,
    seed_limit: usize,
    max_span_len: usize,
    block_size: usize,
    span_step: usize,
    max_arity: u8,
    passes: usize,
    hash_bits: usize,
    target_chunk_bytes: Option<usize>,
) -> Result<(Vec<u8>, StreamingTelemetry), TelomereError> {
    let max_seed_len = max_seed_len_for_seed_limit(seed_limit)?;
    compress_streaming_v2_with_chunk_option_and_telemetry(
        data,
        hasher,
        max_seed_len,
        max_span_len,
        block_size,
        span_step,
        max_arity,
        passes,
        hash_bits,
        target_chunk_bytes,
        Some(seed_limit),
    )
}

#[allow(clippy::too_many_arguments)]
fn compress_streaming_v2_with_chunk_option_and_telemetry(
    data: &[u8],
    hasher: HasherKind,
    max_seed_len: usize,
    max_span_len: usize,
    block_size: usize,
    span_step: usize,
    max_arity: u8,
    passes: usize,
    hash_bits: usize,
    target_chunk_bytes: Option<usize>,
    seed_limit: Option<usize>,
) -> Result<(Vec<u8>, StreamingTelemetry), TelomereError> {
    validate_streaming_config(
        max_seed_len,
        max_span_len,
        block_size,
        span_step,
        max_arity,
        passes,
        hash_bits,
    )?;
    validate_seed_limit(max_seed_len, seed_limit)?;

    let mut current = data.to_vec();
    let mut layers_inner_to_outer = Vec::new();
    let mut aggregate = StreamingTelemetry::empty(max_seed_len);
    aggregate.seed_limit = seed_limit;
    aggregate.stop_reason = "max_passes".into();

    for pass_idx in 0..passes {
        let started = Instant::now();
        let (payload, mut telemetry) = encode_streaming_layer(
            pass_idx + 1,
            &current,
            hasher,
            max_seed_len,
            max_span_len,
            block_size,
            span_step,
            max_arity,
            target_chunk_bytes,
            seed_limit,
        )?;
        telemetry.duration_ms = started.elapsed().as_millis() as u64;
        if pass_idx > 0 && payload.len() >= current.len() {
            aggregate.stop_reason = "non_compressive_layer".into();
            break;
        }

        merge_telemetry(&mut aggregate, &telemetry);
        aggregate.layers.push(telemetry);
        layers_inner_to_outer.push(TlmrV2LayerDescriptor::for_decoded_bytes_with_span_step(
            &current,
            hasher,
            max_seed_len,
            max_span_len,
            block_size,
            span_step,
            hash_bits,
        ));
        current = payload;
    }

    aggregate.final_payload_bytes = current.len();
    let mut layers = layers_inner_to_outer;
    layers.reverse();
    let encoded = encode_v2_file(hasher, hash_bits, data.len() as u64, &layers, &current)?;
    aggregate.container_bytes = encoded.len();
    Ok((encoded, aggregate))
}

#[allow(clippy::too_many_arguments)]
pub fn compress_streaming_v2_with_public_preset_selective_and_telemetry(
    data: &[u8],
    hasher: HasherKind,
    max_seed_len: usize,
    max_span_len: usize,
    block_size: usize,
    span_step: usize,
    max_arity: u8,
    passes: usize,
    hash_bits: usize,
    target_chunk_bytes: Option<usize>,
    seed_limit: Option<usize>,
) -> Result<(Vec<u8>, PublicPresetStreamingTelemetry), TelomereError> {
    let max_seed_len = if let Some(seed_limit) = seed_limit {
        max_seed_len_for_seed_limit(seed_limit)?
    } else {
        max_seed_len
    };
    let (transformed, transform_stats) = public_preset_selective_framed(
        data,
        hasher,
        PUBLIC_PRESET_SELECTIVE_MIN_TOKEN_LEN,
        PUBLIC_PRESET_CODEWORD_LEN,
    )?;
    let (inner_file, mut streaming) = compress_streaming_v2_with_chunk_option_and_telemetry(
        &transformed,
        hasher,
        max_seed_len,
        max_span_len,
        block_size,
        span_step,
        max_arity,
        passes,
        hash_bits,
        target_chunk_bytes,
        seed_limit,
    )?;
    let (_header, mut layers, payload_start) = decode_v2_header_and_descriptors(&inner_file)?;
    layers.push(
        TlmrV2LayerDescriptor::for_public_preset_selective_decoded_bytes(
            data,
            hasher,
            PUBLIC_PRESET_SELECTIVE_MIN_TOKEN_LEN,
            PUBLIC_PRESET_CODEWORD_LEN,
            hash_bits,
        ),
    );
    let encoded = encode_v2_file(
        hasher,
        hash_bits,
        data.len() as u64,
        &layers,
        &inner_file[payload_start..],
    )?;
    streaming.container_bytes = encoded.len();
    streaming.stop_reason = format!("{}+public_preset_selective", streaming.stop_reason);
    Ok((
        encoded,
        PublicPresetStreamingTelemetry {
            transform: transform_stats,
            streaming,
        },
    ))
}

pub fn find_streaming_candidates(
    data: &[u8],
    hasher: HasherKind,
    max_seed_len: usize,
    max_span_len: usize,
    block_size: usize,
    max_arity: u8,
) -> Result<(Vec<IndexedCandidate>, StreamingTelemetry), TelomereError> {
    find_streaming_candidates_with_span_step(
        data,
        hasher,
        max_seed_len,
        max_span_len,
        block_size,
        block_size,
        max_arity,
    )
}

pub fn find_streaming_candidates_with_span_step(
    data: &[u8],
    hasher: HasherKind,
    max_seed_len: usize,
    max_span_len: usize,
    block_size: usize,
    span_step: usize,
    max_arity: u8,
) -> Result<(Vec<IndexedCandidate>, StreamingTelemetry), TelomereError> {
    find_streaming_candidates_with_span_step_and_seed_limit(
        data,
        hasher,
        max_seed_len,
        max_span_len,
        block_size,
        span_step,
        max_arity,
        None,
    )
}

#[allow(clippy::too_many_arguments)]
pub fn find_streaming_candidates_with_span_step_and_seed_limit(
    data: &[u8],
    hasher: HasherKind,
    max_seed_len: usize,
    max_span_len: usize,
    block_size: usize,
    span_step: usize,
    max_arity: u8,
    seed_limit: Option<usize>,
) -> Result<(Vec<IndexedCandidate>, StreamingTelemetry), TelomereError> {
    validate_streaming_config(
        max_seed_len,
        max_span_len,
        block_size,
        span_step,
        max_arity,
        1,
        1,
    )?;
    validate_seed_limit(max_seed_len, seed_limit)?;
    if data.is_empty() {
        let mut telemetry = StreamingTelemetry::empty(max_seed_len);
        telemetry.seed_limit = seed_limit;
        return Ok((Vec::new(), telemetry));
    }

    let mut tiers = build_span_tiers(data, max_span_len, block_size, span_step, max_arity);
    scan_streaming_tiers(
        data.len(),
        hasher,
        max_seed_len,
        max_span_len,
        &mut tiers,
        seed_limit,
    )
}

#[allow(clippy::too_many_arguments)]
pub fn find_streaming_candidates_chunked_with_span_step(
    data: &[u8],
    hasher: HasherKind,
    max_seed_len: usize,
    max_span_len: usize,
    block_size: usize,
    span_step: usize,
    max_arity: u8,
    target_chunk_bytes: usize,
) -> Result<(Vec<IndexedCandidate>, StreamingTelemetry), TelomereError> {
    find_streaming_candidates_chunked_with_span_step_and_seed_limit(
        data,
        hasher,
        max_seed_len,
        max_span_len,
        block_size,
        span_step,
        max_arity,
        target_chunk_bytes,
        None,
    )
}

#[allow(clippy::too_many_arguments)]
pub fn find_streaming_candidates_chunked_with_span_step_and_seed_limit(
    data: &[u8],
    hasher: HasherKind,
    max_seed_len: usize,
    max_span_len: usize,
    block_size: usize,
    span_step: usize,
    max_arity: u8,
    target_chunk_bytes: usize,
    seed_limit: Option<usize>,
) -> Result<(Vec<IndexedCandidate>, StreamingTelemetry), TelomereError> {
    validate_streaming_config(
        max_seed_len,
        max_span_len,
        block_size,
        span_step,
        max_arity,
        1,
        1,
    )?;
    validate_seed_limit(max_seed_len, seed_limit)?;
    if data.is_empty() {
        let mut telemetry = StreamingTelemetry::empty(max_seed_len);
        telemetry.seed_limit = seed_limit;
        return Ok((Vec::new(), telemetry));
    }

    let tier_lengths = streaming_tier_lengths(data.len(), max_span_len, block_size, max_arity);
    let ranges = target_start_ranges(data.len(), &tier_lengths, span_step, target_chunk_bytes)?;
    let mut all_candidates = Vec::new();
    let mut aggregate = StreamingTelemetry::empty(max_seed_len);
    aggregate.seed_limit = seed_limit;
    aggregate.literal_bytes = data.len();
    aggregate.stop_reason = "scan_only_chunked".into();

    for (start, end) in ranges {
        let mut tiers = build_span_tiers_for_start_range(
            data,
            max_span_len,
            block_size,
            span_step,
            max_arity,
            start,
            end,
        );
        let (mut candidates, telemetry) = scan_streaming_tiers(
            data.len(),
            hasher,
            max_seed_len,
            max_span_len,
            &mut tiers,
            seed_limit,
        )?;
        all_candidates.append(&mut candidates);
        merge_scan_telemetry(&mut aggregate, telemetry);
    }

    aggregate.candidate_count = all_candidates.len();
    Ok((all_candidates, aggregate))
}

pub fn find_streaming_candidates_profit_window_with_span_step(
    data: &[u8],
    hasher: HasherKind,
    max_seed_len: usize,
    max_span_len: usize,
    span_step: usize,
) -> Result<(Vec<IndexedCandidate>, StreamingTelemetry), TelomereError> {
    validate_profit_window_config(max_seed_len, max_span_len, span_step)?;
    if data.is_empty() {
        return Ok((Vec::new(), StreamingTelemetry::empty(max_seed_len)));
    }

    let tier_lengths = profit_window_tier_lengths(data.len(), max_span_len);
    let mut tiers = build_span_tiers_for_lengths(data, &tier_lengths, span_step);
    scan_streaming_tiers(
        data.len(),
        hasher,
        max_seed_len,
        max_span_len,
        &mut tiers,
        None,
    )
}

fn scan_streaming_tiers(
    data_len: usize,
    hasher: HasherKind,
    max_seed_len: usize,
    max_span_len: usize,
    tiers: &mut [SpanTier],
    seed_limit: Option<usize>,
) -> Result<(Vec<IndexedCandidate>, StreamingTelemetry), TelomereError> {
    validate_seed_limit(max_seed_len, seed_limit)?;
    let tier_count = tiers.len();
    let mut candidates = Vec::new();
    let expander = hasher.get_expander();
    let mut global_offset = 0usize;
    let mut expanded = vec![0u8; max_span_len.min(data_len)];
    let mut seeds_scanned = 0usize;
    let mut seed_expansions = 0usize;

    let mut remaining_seed_budget = seed_limit.unwrap_or(total_seed_count(max_seed_len)?);
    for seed_len in 1..=max_seed_len {
        let count = 1usize << (8 * seed_len);
        let local_count = count.min(remaining_seed_budget);
        for local_idx in 0..local_count {
            let seed_index = global_offset + local_idx;
            let seed = index_to_seed(seed_index, max_seed_len)?;
            seeds_scanned += 1;
            expander.expand_into(&seed, &mut expanded);
            seed_expansions += 1;

            for tier in tiers.iter_mut() {
                tier.lookup_count += 1;
                let key = &expanded[..tier.span_len];
                let Some(starts) = tier.spans.get(key) else {
                    continue;
                };
                tier.candidate_hits_raw += starts.len();
                let encoded_bits = crate::tlmr_v2::v2_seed_span_record_bit_len(
                    tier.span_len,
                    &seed,
                    max_seed_len,
                )?;
                // Bit-accurate profit gate: compare on-wire bit cost to span
                // bit length. The `encoded_len` field below remains in bytes
                // (ceil-divided) so downstream telemetry/sort orderings stay
                // unit-consistent with `span_len`.
                if encoded_bits >= tier.span_len * 8 {
                    continue;
                }
                let encoded_len = (encoded_bits + 7) / 8;

                tier.candidate_hits += starts.len();
                tier.candidate_hits_profitable += starts.len();
                candidates.extend(starts.iter().map(|start| IndexedCandidate {
                    start: *start,
                    span_len: tier.span_len,
                    seed_index,
                    seed: seed.clone(),
                    encoded_bits,
                    encoded_len,
                }));
            }
        }
        remaining_seed_budget -= local_count;
        if remaining_seed_budget == 0 {
            break;
        }
        global_offset += count;
    }

    let telemetry = StreamingTelemetry {
        candidate_count: candidates.len(),
        selected_count: 0,
        literal_bytes: data_len,
        seed_len_counts: vec![0; max_seed_len + 1],
        bundle_count: 0,
        seeds_scanned,
        seed_expansions,
        seed_limit,
        selected_spans: Vec::new(),
        tiers: tiers
            .iter()
            .map(|tier| StreamingTierTelemetry {
                span_len: tier.span_len,
                unique_spans: tier.spans.len(),
                target_windows: tier.target_windows,
                lookup_count: tier.lookup_count,
                candidate_hits: tier.candidate_hits,
                candidate_hits_raw: tier.candidate_hits_raw,
                candidate_hits_profitable: tier.candidate_hits_profitable,
                duration_ms: tier.duration_ms,
                estimated_target_table_bytes: estimate_target_table_bytes(
                    tier.spans.len(),
                    tier.target_windows,
                    tier.span_len,
                ),
            })
            .take(tier_count)
            .collect(),
        layers: Vec::new(),
        final_payload_bytes: 0,
        container_bytes: 0,
        stop_reason: "scan_only".into(),
    };
    Ok((candidates, telemetry))
}

pub fn estimate_streaming_target_table_upper_bound(
    input_len: usize,
    max_span_len: usize,
    block_size: usize,
    span_step: usize,
    max_arity: u8,
) -> Result<usize, TelomereError> {
    validate_streaming_config(1, max_span_len, block_size, span_step, max_arity, 1, 1)?;
    let tier_lengths: Vec<usize> = (1..=max_arity)
        .map(|arity| block_size.saturating_mul(arity as usize))
        .filter(|span_len| *span_len <= max_span_len && *span_len <= input_len)
        .collect();
    Ok(estimate_target_table_upper_bound_for_tiers(
        input_len,
        &tier_lengths,
        span_step,
    ))
}

pub fn estimate_streaming_target_chunk_upper_bound(
    input_len: usize,
    max_span_len: usize,
    block_size: usize,
    span_step: usize,
    max_arity: u8,
    target_chunk_bytes: usize,
) -> Result<usize, TelomereError> {
    validate_streaming_config(1, max_span_len, block_size, span_step, max_arity, 1, 1)?;
    let tier_lengths = streaming_tier_lengths(input_len, max_span_len, block_size, max_arity);
    let ranges = target_start_ranges(input_len, &tier_lengths, span_step, target_chunk_bytes)?;
    Ok(ranges
        .iter()
        .map(|(start, end)| {
            estimate_target_table_upper_bound_for_start_range(
                input_len,
                &tier_lengths,
                span_step,
                *start,
                *end,
            )
        })
        .max()
        .unwrap_or(0))
}

#[allow(clippy::too_many_arguments)]
fn encode_streaming_layer(
    pass: usize,
    data: &[u8],
    hasher: HasherKind,
    max_seed_len: usize,
    max_span_len: usize,
    block_size: usize,
    span_step: usize,
    max_arity: u8,
    target_chunk_bytes: Option<usize>,
    seed_limit: Option<usize>,
) -> Result<(Vec<u8>, StreamingLayerTelemetry), TelomereError> {
    let (candidates, mut telemetry) = if let Some(target_chunk_bytes) = target_chunk_bytes {
        find_streaming_candidates_chunked_with_span_step_and_seed_limit(
            data,
            hasher,
            max_seed_len,
            max_span_len,
            block_size,
            span_step,
            max_arity,
            target_chunk_bytes,
            seed_limit,
        )?
    } else {
        find_streaming_candidates_with_span_step_and_seed_limit(
            data,
            hasher,
            max_seed_len,
            max_span_len,
            block_size,
            span_step,
            max_arity,
            seed_limit,
        )?
    };
    let selected = select_weighted_candidates(candidates).items;
    telemetry.selected_count = selected.len();
    telemetry.literal_bytes = data.len();
    telemetry.bundle_count = selected
        .iter()
        .filter(|candidate| candidate.span_len > block_size)
        .count();
    for candidate in &selected {
        telemetry.literal_bytes = telemetry.literal_bytes.saturating_sub(candidate.span_len);
        let len = candidate.seed.len();
        if len >= telemetry.seed_len_counts.len() {
            telemetry.seed_len_counts.resize(len + 1, 0);
        }
        telemetry.seed_len_counts[len] += 1;
    }
    let payload = encode_layer_records(data, &selected, max_seed_len)?;
    let layer = StreamingLayerTelemetry {
        pass,
        bytes_in: data.len(),
        payload_bytes: payload.len(),
        duration_ms: 0,
        candidate_count: telemetry.candidate_count,
        selected_count: telemetry.selected_count,
        literal_bytes: telemetry.literal_bytes,
        seed_len_counts: telemetry.seed_len_counts,
        bundle_count: telemetry.bundle_count,
        seeds_scanned: telemetry.seeds_scanned,
        seed_expansions: telemetry.seed_expansions,
        selected_spans: selected_span_telemetry(pass, &selected),
        tiers: telemetry.tiers,
    };
    Ok((payload, layer))
}

fn build_span_tiers(
    data: &[u8],
    max_span_len: usize,
    block_size: usize,
    span_step: usize,
    max_arity: u8,
) -> Vec<SpanTier> {
    let mut tiers = Vec::new();
    for arity in 1..=max_arity as usize {
        let tier_started = Instant::now();
        let span_len = arity * block_size;
        if span_len == 0 || span_len > max_span_len || span_len > data.len() {
            continue;
        }
        let mut spans: HashMap<Vec<u8>, Vec<usize>> = HashMap::new();
        let mut target_windows = 0usize;
        let mut start = 0usize;
        while start + span_len <= data.len() {
            target_windows += 1;
            spans
                .entry(data[start..start + span_len].to_vec())
                .or_default()
                .push(start);
            start += span_step;
        }
        tiers.push(SpanTier {
            span_len,
            spans,
            target_windows,
            lookup_count: 0,
            candidate_hits: 0,
            candidate_hits_raw: 0,
            candidate_hits_profitable: 0,
            duration_ms: tier_started.elapsed().as_millis() as u64,
        });
    }
    tiers.sort_by(|a, b| b.span_len.cmp(&a.span_len));
    tiers
}

fn build_span_tiers_for_start_range(
    data: &[u8],
    max_span_len: usize,
    block_size: usize,
    span_step: usize,
    max_arity: u8,
    range_start: usize,
    range_end: usize,
) -> Vec<SpanTier> {
    let mut tiers = Vec::new();
    for arity in 1..=max_arity as usize {
        let tier_started = Instant::now();
        let span_len = arity * block_size;
        if span_len == 0 || span_len > max_span_len || span_len > data.len() {
            continue;
        }
        let mut spans: HashMap<Vec<u8>, Vec<usize>> = HashMap::new();
        let mut target_windows = 0usize;
        let mut start = range_start;
        while start < range_end && start + span_len <= data.len() {
            target_windows += 1;
            spans
                .entry(data[start..start + span_len].to_vec())
                .or_default()
                .push(start);
            start += span_step;
        }
        if target_windows == 0 {
            continue;
        }
        tiers.push(SpanTier {
            span_len,
            spans,
            target_windows,
            lookup_count: 0,
            candidate_hits: 0,
            candidate_hits_raw: 0,
            candidate_hits_profitable: 0,
            duration_ms: tier_started.elapsed().as_millis() as u64,
        });
    }
    tiers.sort_by(|a, b| b.span_len.cmp(&a.span_len));
    tiers
}

fn build_span_tiers_for_lengths(
    data: &[u8],
    tier_lengths: &[usize],
    span_step: usize,
) -> Vec<SpanTier> {
    let mut tiers = Vec::new();
    for span_len in tier_lengths.iter().copied() {
        let tier_started = Instant::now();
        if span_len == 0 || span_len > data.len() {
            continue;
        }
        let mut spans: HashMap<Vec<u8>, Vec<usize>> = HashMap::new();
        let mut target_windows = 0usize;
        let mut start = 0usize;
        while start + span_len <= data.len() {
            target_windows += 1;
            spans
                .entry(data[start..start + span_len].to_vec())
                .or_default()
                .push(start);
            start += span_step;
        }
        tiers.push(SpanTier {
            span_len,
            spans,
            target_windows,
            lookup_count: 0,
            candidate_hits: 0,
            candidate_hits_raw: 0,
            candidate_hits_profitable: 0,
            duration_ms: tier_started.elapsed().as_millis() as u64,
        });
    }
    tiers.sort_by(|a, b| b.span_len.cmp(&a.span_len));
    tiers
}

fn streaming_tier_lengths(
    input_len: usize,
    max_span_len: usize,
    block_size: usize,
    max_arity: u8,
) -> Vec<usize> {
    (1..=max_arity)
        .map(|arity| block_size.saturating_mul(arity as usize))
        .filter(|span_len| *span_len <= max_span_len && *span_len <= input_len)
        .collect()
}

fn profit_window_tier_lengths(input_len: usize, max_span_len: usize) -> Vec<usize> {
    let upper = max_span_len.min(input_len);
    // Bit-accurate gate: a span_len is profitable only when the record bit
    // cost is strictly less than `span_len * 8`. Using the byte-rounded form
    // would discard span lengths whose record saves bits but not whole bytes.
    let shortest_profitable = (1..=upper)
        .find(|span_len| {
            crate::tlmr_v2::v2_seed_span_record_bit_len(*span_len, &[0], 1)
                .map(|encoded_bits| encoded_bits < span_len.saturating_mul(8))
                .unwrap_or(false)
        })
        .unwrap_or(upper.saturating_add(1));
    (shortest_profitable..=upper).collect()
}

fn target_start_ranges(
    input_len: usize,
    tier_lengths: &[usize],
    span_step: usize,
    target_chunk_bytes: usize,
) -> Result<Vec<(usize, usize)>, TelomereError> {
    if target_chunk_bytes == 0 {
        return Err(TelomereError::Config(
            "target_chunk_bytes must be greater than zero".into(),
        ));
    }
    if span_step == 0 || tier_lengths.is_empty() {
        return Ok(Vec::new());
    }

    let per_start_upper_bound = tier_lengths
        .iter()
        .map(|span_len| estimate_target_table_bytes(1, 1, *span_len))
        .fold(0usize, usize::saturating_add);
    if per_start_upper_bound > target_chunk_bytes {
        return Err(TelomereError::Config(format!(
            "target_chunk_bytes {target_chunk_bytes} is smaller than one chunk start estimate {per_start_upper_bound}"
        )));
    }

    let max_start_exclusive = tier_lengths
        .iter()
        .filter_map(|span_len| input_len.checked_sub(*span_len).map(|last| last + 1))
        .max()
        .unwrap_or(0);
    if max_start_exclusive == 0 {
        return Ok(Vec::new());
    }

    let starts_per_chunk = (target_chunk_bytes / per_start_upper_bound).max(1);
    let chunk_width = starts_per_chunk.saturating_mul(span_step).max(span_step);
    let mut ranges = Vec::new();
    let mut start = 0usize;
    while start < max_start_exclusive {
        let end = start.saturating_add(chunk_width).min(max_start_exclusive);
        ranges.push((start, end));
        start = end;
    }
    Ok(ranges)
}

fn estimate_target_table_upper_bound_for_start_range(
    input_len: usize,
    tier_lengths: &[usize],
    span_step: usize,
    range_start: usize,
    range_end: usize,
) -> usize {
    if span_step == 0 || range_start >= range_end {
        return 0;
    }
    tier_lengths
        .iter()
        .copied()
        .filter(|span_len| *span_len > 0 && *span_len <= input_len)
        .map(|span_len| {
            let first_invalid_start = input_len - span_len + 1;
            let effective_end = range_end.min(first_invalid_start);
            if range_start >= effective_end {
                return 0;
            }
            let target_windows = ((effective_end - 1 - range_start) / span_step) + 1;
            estimate_target_table_bytes(target_windows, target_windows, span_len)
        })
        .fold(0usize, usize::saturating_add)
}

fn merge_telemetry(target: &mut StreamingTelemetry, source: &StreamingLayerTelemetry) {
    target.candidate_count += source.candidate_count;
    target.selected_count += source.selected_count;
    target.literal_bytes += source.literal_bytes;
    target.bundle_count += source.bundle_count;
    target.seeds_scanned += source.seeds_scanned;
    target.seed_expansions += source.seed_expansions;
    target.selected_spans.extend(source.selected_spans.clone());
    if target.seed_len_counts.len() < source.seed_len_counts.len() {
        target
            .seed_len_counts
            .resize(source.seed_len_counts.len(), 0);
    }
    for (idx, count) in source.seed_len_counts.iter().enumerate() {
        target.seed_len_counts[idx] += count;
    }
    target.tiers.extend(source.tiers.clone());
}

fn merge_scan_telemetry(target: &mut StreamingTelemetry, source: StreamingTelemetry) {
    target.candidate_count += source.candidate_count;
    target.seeds_scanned += source.seeds_scanned;
    target.seed_expansions += source.seed_expansions;
    target.tiers.extend(source.tiers);
}

fn validate_streaming_config(
    max_seed_len: usize,
    max_span_len: usize,
    block_size: usize,
    span_step: usize,
    max_arity: u8,
    passes: usize,
    hash_bits: usize,
) -> Result<(), TelomereError> {
    validate_v2_search_config(max_seed_len, max_span_len, block_size, passes, hash_bits)?;
    validate_v2_span_step(span_step, block_size, max_span_len)?;
    if !(1..=MAX_ARITY).contains(&max_arity) {
        return Err(TelomereError::Config(format!(
            "max_arity must be in 1..={MAX_ARITY}"
        )));
    }
    Ok(())
}

fn validate_profit_window_config(
    max_seed_len: usize,
    max_span_len: usize,
    span_step: usize,
) -> Result<(), TelomereError> {
    validate_v2_search_config(max_seed_len, max_span_len, 1, 1, 1)?;
    if span_step == 0 || span_step > u16::MAX as usize {
        return Err(TelomereError::Config(
            "span_step must be in 1..=65535".into(),
        ));
    }
    if span_step > max_span_len {
        return Err(TelomereError::Config(
            "span_step must not exceed max_span_len".into(),
        ));
    }
    Ok(())
}
