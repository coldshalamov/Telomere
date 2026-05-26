use crate::config::HasherKind;
use crate::seed_expansion_index::{SeedLookup, SEED_ORDER_VERSION};
use crate::tlmr_v2::{
    encode_v2_file, v2_fixed_seed_span_record_into_writer, v2_literal_record_into_writer,
    v2_seed_span_record_into_writer, validate_v2_search_config, validate_v2_span_step,
    TlmrV2LayerDescriptor,
};
use crate::TelomereError;
use lotus::BitWriter;
use rayon::prelude::*;
use serde::Serialize;
use std::collections::HashMap;
use std::time::Instant;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct IndexedCandidate {
    pub start: usize,
    pub span_len: usize,
    pub seed_index: usize,
    pub seed: Vec<u8>,
    /// Exact on-wire bit cost of a seed-span record encoding this candidate.
    /// Used for the bit-accurate profitability gate during selection so we do
    /// not drop candidates that save sub-byte amounts.
    pub encoded_bits: usize,
    /// Ceil-divided byte cost (`(encoded_bits + 7) / 8`). Retained for
    /// telemetry, sort orderings, and `savings()` arithmetic — never for
    /// profitability decisions.
    pub encoded_len: usize,
}

impl IndexedCandidate {
    fn end(&self) -> usize {
        self.start + self.span_len
    }

    fn savings(&self) -> usize {
        self.span_len.saturating_sub(self.encoded_len)
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct SelectedSpanTelemetry {
    pub pass: usize,
    pub start: usize,
    pub span_len: usize,
    pub seed_index: usize,
    pub seed_len: usize,
    pub seed_hex: String,
    pub encoded_len: usize,
    pub savings: usize,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct IndexedTierTelemetry {
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
pub struct IndexedLayerTelemetry {
    pub pass: usize,
    pub bytes_in: usize,
    pub payload_bytes: usize,
    pub duration_ms: u64,
    pub candidate_count: usize,
    pub selected_count: usize,
    pub literal_bytes: usize,
    pub seed_len_counts: Vec<u64>,
    pub bundle_count: usize,
    pub selected_spans: Vec<SelectedSpanTelemetry>,
    pub tiers: Vec<IndexedTierTelemetry>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct IndexedTelemetry {
    pub candidate_count: usize,
    pub selected_count: usize,
    pub literal_bytes: usize,
    pub seed_len_counts: Vec<u64>,
    pub bundle_count: usize,
    pub selected_spans: Vec<SelectedSpanTelemetry>,
    pub tiers: Vec<IndexedTierTelemetry>,
    pub layers: Vec<IndexedLayerTelemetry>,
    pub final_payload_bytes: usize,
    pub container_bytes: usize,
    pub stop_reason: String,
}

impl IndexedTelemetry {
    fn empty(max_seed_len: usize) -> Self {
        Self {
            candidate_count: 0,
            selected_count: 0,
            literal_bytes: 0,
            seed_len_counts: vec![0; max_seed_len + 1],
            bundle_count: 0,
            selected_spans: Vec::new(),
            tiers: Vec::new(),
            layers: Vec::new(),
            final_payload_bytes: 0,
            container_bytes: 0,
            stop_reason: "not_started".into(),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct Selection {
    saved: usize,
    span_total: usize,
    seed_total: usize,
    pub(crate) items: Vec<IndexedCandidate>,
}

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
struct SelectionScore {
    saved: usize,
    span_total: usize,
    seed_total: usize,
}

impl SelectionScore {
    fn with_candidate(self, candidate: &IndexedCandidate) -> Self {
        Self {
            saved: self.saved + candidate.savings(),
            span_total: self.span_total + candidate.span_len,
            seed_total: self.seed_total + candidate.seed.len(),
        }
    }
}

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
struct SelectionDecision {
    take: bool,
    previous_count: usize,
}

#[allow(clippy::too_many_arguments)]
pub fn compress_indexed_v2_with_index<I: SeedLookup + ?Sized>(
    data: &[u8],
    index: &I,
    hasher: HasherKind,
    max_seed_len: usize,
    max_span_len: usize,
    block_size: usize,
    passes: usize,
    hash_bits: usize,
) -> Result<Vec<u8>, TelomereError> {
    let (out, _) = compress_indexed_v2_with_telemetry(
        data,
        index,
        hasher,
        max_seed_len,
        max_span_len,
        block_size,
        passes,
        hash_bits,
    )?;
    Ok(out)
}

#[allow(clippy::too_many_arguments)]
pub fn compress_indexed_v2_with_telemetry<I: SeedLookup + ?Sized>(
    data: &[u8],
    index: &I,
    hasher: HasherKind,
    max_seed_len: usize,
    max_span_len: usize,
    block_size: usize,
    passes: usize,
    hash_bits: usize,
) -> Result<(Vec<u8>, IndexedTelemetry), TelomereError> {
    compress_indexed_v2_with_span_step_and_telemetry(
        data,
        index,
        hasher,
        max_seed_len,
        max_span_len,
        block_size,
        block_size,
        passes,
        hash_bits,
    )
}

#[allow(clippy::too_many_arguments)]
pub fn compress_indexed_v2_with_span_step_and_telemetry<I: SeedLookup + ?Sized>(
    data: &[u8],
    index: &I,
    hasher: HasherKind,
    max_seed_len: usize,
    max_span_len: usize,
    block_size: usize,
    span_step: usize,
    passes: usize,
    hash_bits: usize,
) -> Result<(Vec<u8>, IndexedTelemetry), TelomereError> {
    compress_indexed_v2_with_chunk_option_and_telemetry(
        data,
        index,
        hasher,
        max_seed_len,
        max_span_len,
        block_size,
        span_step,
        passes,
        hash_bits,
        None,
    )
}

#[allow(clippy::too_many_arguments)]
pub fn compress_indexed_v2_with_chunked_span_step_and_telemetry<I: SeedLookup + ?Sized>(
    data: &[u8],
    index: &I,
    hasher: HasherKind,
    max_seed_len: usize,
    max_span_len: usize,
    block_size: usize,
    span_step: usize,
    passes: usize,
    hash_bits: usize,
    target_chunk_bytes: usize,
) -> Result<(Vec<u8>, IndexedTelemetry), TelomereError> {
    compress_indexed_v2_with_chunk_option_and_telemetry(
        data,
        index,
        hasher,
        max_seed_len,
        max_span_len,
        block_size,
        span_step,
        passes,
        hash_bits,
        Some(target_chunk_bytes),
    )
}

#[allow(clippy::too_many_arguments)]
fn compress_indexed_v2_with_chunk_option_and_telemetry<I: SeedLookup + ?Sized>(
    data: &[u8],
    index: &I,
    hasher: HasherKind,
    max_seed_len: usize,
    max_span_len: usize,
    block_size: usize,
    span_step: usize,
    passes: usize,
    hash_bits: usize,
    target_chunk_bytes: Option<usize>,
) -> Result<(Vec<u8>, IndexedTelemetry), TelomereError> {
    validate_v2_search_config(max_seed_len, max_span_len, block_size, passes, hash_bits)?;
    validate_v2_span_step(span_step, block_size, max_span_len)?;
    validate_index_for_run(index, hasher, max_seed_len, max_span_len)?;

    let mut current = data.to_vec();
    let mut layers_inner_to_outer = Vec::new();
    let mut aggregate = IndexedTelemetry::empty(max_seed_len);
    aggregate.stop_reason = "max_passes".into();

    for pass_idx in 0..passes {
        let started = Instant::now();
        let (payload, mut telemetry) = encode_indexed_layer(
            pass_idx + 1,
            &current,
            index,
            hasher,
            max_seed_len,
            max_span_len,
            block_size,
            span_step,
            target_chunk_bytes,
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

pub fn select_weighted_candidates_for_tests(
    candidates: Vec<IndexedCandidate>,
) -> Vec<IndexedCandidate> {
    select_weighted_candidates(candidates).items
}

fn validate_index_for_run<I: SeedLookup + ?Sized>(
    index: &I,
    hasher: HasherKind,
    max_seed_len: usize,
    max_span_len: usize,
) -> Result<(), TelomereError> {
    let manifest = index.manifest();
    if manifest.hasher != hasher {
        return Err(TelomereError::Config("index hasher mismatch".into()));
    }
    if manifest.seed_order_version != SEED_ORDER_VERSION {
        return Err(TelomereError::Config("index seed order mismatch".into()));
    }
    if manifest.max_seed_len != max_seed_len {
        return Err(TelomereError::Config("index max_seed_len mismatch".into()));
    }
    if manifest.max_span_len < max_span_len {
        return Err(TelomereError::Config("index max_span_len too small".into()));
    }
    Ok(())
}

#[allow(clippy::too_many_arguments)]
pub(crate) fn encode_indexed_layer<I: SeedLookup + ?Sized>(
    pass: usize,
    data: &[u8],
    index: &I,
    hasher: HasherKind,
    max_seed_len: usize,
    max_span_len: usize,
    block_size: usize,
    span_step: usize,
    target_chunk_bytes: Option<usize>,
) -> Result<(Vec<u8>, IndexedLayerTelemetry), TelomereError> {
    let (candidates, tiers) = if let Some(target_chunk_bytes) = target_chunk_bytes {
        find_indexed_candidates_chunked(
            data,
            index,
            hasher,
            max_seed_len,
            max_span_len,
            span_step,
            target_chunk_bytes,
        )?
    } else {
        find_indexed_candidates(data, index, hasher, max_seed_len, max_span_len, span_step)?
    };
    let candidate_count = candidates.len();
    let selected = select_weighted_candidates(candidates).items;
    let payload = encode_layer_records(data, &selected, max_seed_len)?;
    let mut seed_len_counts = vec![0; max_seed_len + 1];
    let mut literal_bytes = data.len();
    for candidate in &selected {
        literal_bytes = literal_bytes.saturating_sub(candidate.span_len);
        let len = candidate.seed.len();
        if len >= seed_len_counts.len() {
            seed_len_counts.resize(len + 1, 0);
        }
        seed_len_counts[len] += 1;
    }
    let layer = IndexedLayerTelemetry {
        pass,
        bytes_in: data.len(),
        payload_bytes: payload.len(),
        duration_ms: 0,
        candidate_count,
        selected_count: selected.len(),
        literal_bytes,
        seed_len_counts,
        bundle_count: selected
            .iter()
            .filter(|candidate| candidate.span_len > block_size)
            .count(),
        selected_spans: selected_span_telemetry(pass, &selected),
        tiers,
    };
    Ok((payload, layer))
}

fn find_indexed_candidates<I: SeedLookup + ?Sized>(
    data: &[u8],
    index: &I,
    hasher: HasherKind,
    max_seed_len: usize,
    max_span_len: usize,
    span_step: usize,
) -> Result<(Vec<IndexedCandidate>, Vec<IndexedTierTelemetry>), TelomereError> {
    if data.is_empty() {
        return Ok((Vec::new(), Vec::new()));
    }

    let tier_lengths = indexed_tier_lengths(index, max_span_len, data.len());
    find_indexed_candidates_for_start_range(
        data,
        index,
        IndexedStartRange {
            hasher,
            tier_lengths: &tier_lengths,
            span_step,
            range_start: 0,
            range_end: data.len(),
            max_seed_len,
        },
    )
}

fn find_indexed_candidates_chunked<I: SeedLookup + ?Sized>(
    data: &[u8],
    index: &I,
    hasher: HasherKind,
    max_seed_len: usize,
    max_span_len: usize,
    span_step: usize,
    target_chunk_bytes: usize,
) -> Result<(Vec<IndexedCandidate>, Vec<IndexedTierTelemetry>), TelomereError> {
    if data.is_empty() {
        return Ok((Vec::new(), Vec::new()));
    }

    let tier_lengths = indexed_tier_lengths(index, max_span_len, data.len());
    let ranges = target_start_ranges(data.len(), &tier_lengths, span_step, target_chunk_bytes)?;
    let mut candidates = Vec::new();
    let mut telemetry = Vec::new();
    for (range_start, range_end) in ranges {
        let (mut chunk_candidates, mut chunk_telemetry) = find_indexed_candidates_for_start_range(
            data,
            index,
            IndexedStartRange {
                hasher,
                tier_lengths: &tier_lengths,
                span_step,
                range_start,
                range_end,
                max_seed_len,
            },
        )?;
        candidates.append(&mut chunk_candidates);
        telemetry.append(&mut chunk_telemetry);
    }
    Ok((candidates, telemetry))
}

fn indexed_tier_lengths<I: SeedLookup + ?Sized>(
    index: &I,
    max_span_len: usize,
    data_len: usize,
) -> Vec<usize> {
    let mut tier_lengths: Vec<_> = index
        .manifest()
        .tiers
        .iter()
        .map(|tier| tier.span_len)
        .filter(|span_len| *span_len <= max_span_len && *span_len <= data_len)
        .collect();
    tier_lengths.sort_unstable_by(|a, b| b.cmp(a));
    tier_lengths
}

struct IndexedStartRange<'a> {
    hasher: HasherKind,
    tier_lengths: &'a [usize],
    span_step: usize,
    range_start: usize,
    range_end: usize,
    max_seed_len: usize,
}

fn find_indexed_candidates_for_start_range<I: SeedLookup + ?Sized>(
    data: &[u8],
    index: &I,
    scan: IndexedStartRange<'_>,
) -> Result<(Vec<IndexedCandidate>, Vec<IndexedTierTelemetry>), TelomereError> {
    let IndexedStartRange {
        hasher,
        tier_lengths,
        span_step,
        range_start,
        range_end,
        max_seed_len,
    } = scan;

    if tier_lengths.is_empty() || span_step == 0 || range_start >= range_end {
        return Ok((Vec::new(), Vec::new()));
    }

    let expander = hasher.get_expander();
    let mut candidates = Vec::new();
    let mut telemetry = Vec::new();

    for span_len in tier_lengths.iter().copied() {
        let tier_started = Instant::now();
        let mut grouped: HashMap<Vec<u8>, Vec<usize>> = HashMap::new();
        let mut target_windows = 0usize;
        let mut start = range_start;
        while start < range_end && start + span_len <= data.len() {
            target_windows += 1;
            grouped
                .entry(data[start..start + span_len].to_vec())
                .or_default()
                .push(start);
            start += span_step;
        }
        if target_windows == 0 {
            continue;
        }

        let grouped: Vec<_> = grouped.into_iter().collect();
        let unique_spans = grouped.len();
        let lookup_count = unique_spans;
        let tier_hits: Result<Vec<(usize, Vec<IndexedCandidate>)>, TelomereError> = grouped
            .par_iter()
            .map(|(target, starts)| {
                let Some(hit) = index.lookup_exact(span_len, target)? else {
                    return Ok((0, Vec::new()));
                };

                let mut expanded = vec![0u8; span_len];
                expander.expand_into(&hit.seed, &mut expanded);
                if expanded != *target {
                    return Ok((0, Vec::new()));
                }

                let raw_hits = starts.len();
                // Bit-accurate profit gate: a seed-span candidate is
                // profitable iff its on-wire bit cost is strictly less than
                // the span size in bits. The `encoded_len` field below
                // remains in ceil-divided bytes for downstream telemetry,
                // sort orderings, and `savings()` arithmetic.
                let encoded_bits =
                    crate::tlmr_v2::v2_seed_span_record_bit_len(span_len, &hit.seed, max_seed_len)?;
                if encoded_bits >= span_len * 8 {
                    return Ok((raw_hits, Vec::new()));
                }
                let encoded_len = (encoded_bits + 7) / 8;

                Ok((
                    raw_hits,
                    starts
                        .iter()
                        .map(|start| IndexedCandidate {
                            start: *start,
                            span_len,
                            seed_index: hit.seed_index,
                            seed: hit.seed.clone(),
                            encoded_bits,
                            encoded_len,
                        })
                        .collect(),
                ))
            })
            .collect();

        let mut candidate_hits_raw = 0usize;
        let mut tier_candidates = Vec::new();
        for (raw_hits, candidates_for_target) in tier_hits? {
            candidate_hits_raw += raw_hits;
            tier_candidates.extend(candidates_for_target);
        }
        let candidate_hits_profitable = tier_candidates.len();
        let candidate_hits = candidate_hits_profitable;
        candidates.extend(tier_candidates);
        telemetry.push(IndexedTierTelemetry {
            span_len,
            unique_spans,
            target_windows,
            lookup_count,
            candidate_hits,
            candidate_hits_raw,
            candidate_hits_profitable,
            duration_ms: tier_started.elapsed().as_millis() as u64,
            estimated_target_table_bytes: estimate_target_table_bytes(
                unique_spans,
                target_windows,
                span_len,
            ),
        });
    }

    Ok((candidates, telemetry))
}

pub(crate) fn estimate_target_table_bytes(
    unique_spans: usize,
    target_windows: usize,
    span_len: usize,
) -> usize {
    const OFFSET_BYTES: usize = 8;
    unique_spans
        .saturating_mul(span_len)
        .saturating_add(target_windows.saturating_mul(OFFSET_BYTES))
}

pub fn estimate_target_table_upper_bound_for_tiers(
    input_len: usize,
    tier_lengths: &[usize],
    span_step: usize,
) -> usize {
    if span_step == 0 {
        return usize::MAX;
    }
    tier_lengths
        .iter()
        .copied()
        .filter(|span_len| *span_len > 0 && *span_len <= input_len)
        .map(|span_len| {
            let target_windows = ((input_len - span_len) / span_step) + 1;
            estimate_target_table_bytes(target_windows, target_windows, span_len)
        })
        .fold(0usize, usize::saturating_add)
}

pub fn estimate_target_table_chunk_upper_bound_for_tiers(
    input_len: usize,
    tier_lengths: &[usize],
    span_step: usize,
    target_chunk_bytes: usize,
) -> Result<usize, TelomereError> {
    let ranges = target_start_ranges(input_len, tier_lengths, span_step, target_chunk_bytes)?;
    Ok(ranges
        .iter()
        .map(|(start, end)| {
            estimate_target_table_upper_bound_for_start_range(
                input_len,
                tier_lengths,
                span_step,
                *start,
                *end,
            )
        })
        .max()
        .unwrap_or(0))
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

fn merge_telemetry(target: &mut IndexedTelemetry, source: &IndexedLayerTelemetry) {
    target.candidate_count += source.candidate_count;
    target.selected_count += source.selected_count;
    target.literal_bytes += source.literal_bytes;
    target.bundle_count += source.bundle_count;
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

pub(crate) fn selected_span_telemetry(
    pass: usize,
    selected: &[IndexedCandidate],
) -> Vec<SelectedSpanTelemetry> {
    selected
        .iter()
        .map(|candidate| SelectedSpanTelemetry {
            pass,
            start: candidate.start,
            span_len: candidate.span_len,
            seed_index: candidate.seed_index,
            seed_len: candidate.seed.len(),
            seed_hex: hex_lower(&candidate.seed),
            encoded_len: candidate.encoded_len,
            savings: candidate.savings(),
        })
        .collect()
}

fn hex_lower(bytes: &[u8]) -> String {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    let mut out = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        out.push(HEX[(byte >> 4) as usize] as char);
        out.push(HEX[(byte & 0x0f) as usize] as char);
    }
    out
}

pub(crate) fn select_weighted_candidates(mut candidates: Vec<IndexedCandidate>) -> Selection {
    // Bit-accurate retention: a candidate is kept iff its full on-wire bit
    // cost is strictly less than the span size in bits. Comparing the
    // byte-ceil `encoded_len` against `span_len` would drop candidates that
    // save sub-byte amounts (e.g. 63 bits vs 64-bit span = 1 bit saved but
    // both ceil to 8 bytes).
    candidates.retain(|candidate| candidate.encoded_bits < candidate.span_len * 8);
    candidates.sort_by(|a, b| {
        a.end()
            .cmp(&b.end())
            .then(a.start.cmp(&b.start))
            .then(b.span_len.cmp(&a.span_len))
            .then(a.seed.len().cmp(&b.seed.len()))
            .then(a.seed_index.cmp(&b.seed_index))
    });

    let ends: Vec<usize> = candidates.iter().map(IndexedCandidate::end).collect();
    let mut scores = vec![SelectionScore::default(); candidates.len() + 1];
    let mut decisions = vec![SelectionDecision::default(); candidates.len() + 1];

    for (idx, candidate) in candidates.iter().enumerate() {
        let previous_count = ends.partition_point(|end| *end <= candidate.start);
        let include = scores[previous_count].with_candidate(candidate);
        if score_key(&include) > score_key(&scores[idx]) {
            scores[idx + 1] = include;
            decisions[idx + 1] = SelectionDecision {
                take: true,
                previous_count,
            };
        } else {
            scores[idx + 1] = scores[idx];
            decisions[idx + 1] = SelectionDecision {
                take: false,
                previous_count: idx,
            };
        }
    }

    let mut items = Vec::new();
    let mut idx = candidates.len();
    while idx > 0 {
        let decision = decisions[idx];
        if decision.take {
            items.push(candidates[idx - 1].clone());
            idx = decision.previous_count;
        } else {
            idx -= 1;
        }
    }
    items.reverse();
    items.sort_by_key(|candidate| candidate.start);

    let best = scores[candidates.len()];
    Selection {
        saved: best.saved,
        span_total: best.span_total,
        seed_total: best.seed_total,
        items,
    }
}

fn score_key(score: &SelectionScore) -> (usize, usize, std::cmp::Reverse<usize>) {
    (
        score.saved,
        score.span_total,
        std::cmp::Reverse(score.seed_total),
    )
}

pub(crate) fn encode_layer_records(
    data: &[u8],
    selected: &[IndexedCandidate],
    max_seed_len: usize,
) -> Result<Vec<u8>, TelomereError> {
    encode_layer_records_with_fixed_span(data, selected, max_seed_len, None)
}

pub(crate) fn encode_fixed_span_layer_records(
    data: &[u8],
    selected: &[IndexedCandidate],
    max_seed_len: usize,
    fixed_span_len: usize,
) -> Result<Vec<u8>, TelomereError> {
    encode_layer_records_with_fixed_span(data, selected, max_seed_len, Some(fixed_span_len))
}

fn encode_layer_records_with_fixed_span(
    data: &[u8],
    selected: &[IndexedCandidate],
    max_seed_len: usize,
    fixed_span_len: Option<usize>,
) -> Result<Vec<u8>, TelomereError> {
    let mut selected = selected.to_vec();
    selected.sort_by_key(|candidate| candidate.start);
    if let Some(fixed_span_len) = fixed_span_len {
        if fixed_span_len == 0
            || selected
                .iter()
                .any(|candidate| candidate.span_len != fixed_span_len)
        {
            return Err(TelomereError::Header(
                "fixed-span layer received non-fixed candidate".into(),
            ));
        }
    }
    let by_start: HashMap<usize, IndexedCandidate> = selected
        .into_iter()
        .map(|candidate| (candidate.start, candidate))
        .collect();

    // All records share a single BitWriter so each literal pads to byte
    // alignment relative to the layer payload, not relative to its own
    // record-internal position 0. The final partial byte is zero-padded by
    // BitWriter::into_bytes(); decoders stop on output length.
    let mut writer = BitWriter::new();
    let mut pos = 0usize;
    while pos < data.len() {
        if let Some(candidate) = by_start.get(&pos) {
            if fixed_span_len.is_some() {
                v2_fixed_seed_span_record_into_writer(&mut writer, &candidate.seed, max_seed_len)?;
            } else {
                v2_seed_span_record_into_writer(
                    &mut writer,
                    candidate.span_len,
                    &candidate.seed,
                    max_seed_len,
                )?;
            }
            pos += candidate.span_len;
            continue;
        }

        let literal_start = pos;
        while pos < data.len() && !by_start.contains_key(&pos) {
            pos += 1;
        }
        let mut literal = &data[literal_start..pos];
        while !literal.is_empty() {
            let take = literal.len().min(u16::MAX as usize);
            v2_literal_record_into_writer(&mut writer, &literal[..take])?;
            literal = &literal[take..];
        }
    }

    Ok(writer.into_bytes())
}
