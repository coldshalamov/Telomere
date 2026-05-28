#!/usr/bin/env python3
"""Layered math-first Telomere power model.

This script performs no raw corpus seed search. It models what exact
seed-span search should do before anyone spends compute on it. The point is to
separate powered claims from expected nulls, and to make scaling direction
visible across record costs, match tables, hardware profiles, and recursive
passes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
POWER_MODEL_MD = ROOT / "docs" / "POWER_MODEL.md"

LOTUS_J_BITS = 3
LOTUS_TIERS = 2
V2_RECORD_TAG_SEED_SPAN = 0
DEFAULT_INPUT_BYTES = 1_000_000
DEFAULT_SPAN_LENS = (6, 7, 8, 9, 10, 12, 16, 24, 32)
DEFAULT_SEED_DEPTHS = (1, 2, 3, 4, 5, 6)


@dataclass(frozen=True)
class ModelConfig:
    input_bytes: int
    span_lens: tuple[int, ...]
    seed_depths: tuple[int, ...]
    seed_limit: int | None
    span_step: int
    passes: int
    profile: str
    preset_hit_multiplier: float
    bundle_multiplier: float
    superposition_retention: float
    pass_multiplier_growth: float
    duplicate_factor: float


@dataclass(frozen=True)
class HardwareProfile:
    name: str
    seed_expansions_per_sec: float
    target_table_build_bytes_per_sec: float
    lookup_key_bytes_per_sec: float
    io_bytes_per_sec: float
    target_table_memory_budget_bytes: int
    note: str


@dataclass(frozen=True)
class SpanTierRow:
    span_len: int
    windows: int
    unique_spans_estimate: int
    target_table_bytes: int
    record_bits_variable: int
    record_bits_fixed: int
    profitable_variable: bool
    profitable_fixed: bool
    expected_raw_hits: float
    expected_distinct_raw_hits: float
    expected_profitable_hits_variable: float
    expected_profitable_hits_fixed: float
    p_zero_raw: float
    p_at_least_one_raw: float
    p_zero_distinct: float
    p_at_least_one_distinct: float
    selected_hits_variable: float
    selected_hits_fixed: float
    expected_saved_bytes_variable: float
    expected_saved_bytes_fixed: float


@dataclass(frozen=True)
class FrontierRow:
    max_seed_len: int
    seed_count: int
    log2_seed_count: float
    min_profitable_span_variable: int
    min_profitable_span_fixed: int
    record_bits_at_variable_frontier: int
    fixed_record_bits: int
    raw_gap_bits_variable: float
    raw_gap_bits_fixed: float
    target_spans_for_one_variable: float
    target_spans_for_one_fixed: float
    expected_variable_hits_per_gib: float
    expected_fixed_hits_per_gib: float


@dataclass(frozen=True)
class HardwareRow:
    max_seed_len: int
    seed_count: int
    tier_count: int
    table_bytes: int
    chunks: int
    seed_expansions: int
    lookup_count: int
    expansion_seconds: float
    lookup_seconds: float
    table_build_seconds: float
    io_seconds: float
    total_seconds: float


@dataclass(frozen=True)
class PassRow:
    pass_index: int
    input_bytes: int
    expected_raw_hits: float
    expected_profitable_hits: float
    selected_hits: float
    selected_bytes: float
    saved_bytes: float
    literal_runs_estimate: int
    literal_overhead_bytes: float
    payload_bytes: int
    rate_of_change: float
    active_multiplier: float
    stop_reason: str


@dataclass(frozen=True)
class Scenario:
    name: str
    seed_count: int
    target_span_count: int
    span_len_bytes: int
    expected_hits: float
    p_zero: float
    p_at_least_one: float
    evidence_class: str
    allowed_conclusion: str


HARDWARE_PROFILES = {
    # These are explicit assumptions, not measured claims. They are deliberately
    # easy to override in the model instead of being hidden in prose.
    "laptop-cpu": HardwareProfile(
        name="laptop-cpu",
        seed_expansions_per_sec=25_000_000,
        target_table_build_bytes_per_sec=1_500_000_000,
        lookup_key_bytes_per_sec=2_000_000_000,
        io_bytes_per_sec=500_000_000,
        target_table_memory_budget_bytes=2 * 1024**3,
        note="Assumed desktop/laptop CPU profile; use as scale intuition only.",
    ),
    "high-cpu": HardwareProfile(
        name="high-cpu",
        seed_expansions_per_sec=250_000_000,
        target_table_build_bytes_per_sec=8_000_000_000,
        lookup_key_bytes_per_sec=12_000_000_000,
        io_bytes_per_sec=3_000_000_000,
        target_table_memory_budget_bytes=64 * 1024**3,
        note="Assumed high-core CPU server profile.",
    ),
    "gpu-io-bound": HardwareProfile(
        name="gpu-io-bound",
        seed_expansions_per_sec=5_000_000_000,
        target_table_build_bytes_per_sec=20_000_000_000,
        lookup_key_bytes_per_sec=24_000_000_000,
        io_bytes_per_sec=12_000_000_000,
        target_table_memory_budget_bytes=80 * 1024**3,
        note="Assumed accelerator profile; modeled as I/O and table-bandwidth sensitive.",
    ),
    "datacenter": HardwareProfile(
        name="datacenter",
        seed_expansions_per_sec=1_000_000_000_000,
        target_table_build_bytes_per_sec=200_000_000_000,
        lookup_key_bytes_per_sec=500_000_000_000,
        io_bytes_per_sec=100_000_000_000,
        target_table_memory_budget_bytes=10 * 1024**4,
        note="Assumed aggregate fleet profile for scale direction, not a lab measurement.",
    ),
}


def ceil_div(numerator: int, denominator: int) -> int:
    return (numerator + denominator - 1) // denominator


def fmt_int(value: int) -> str:
    return f"{value:,}"


def fmt_float(value: float, digits: int = 3) -> str:
    if value == 0:
        return "0"
    if abs(value) >= 10_000 or abs(value) < 0.001:
        return f"{value:.{digits}e}"
    return f"{value:.{digits}f}"


def fmt_seconds(seconds: float) -> str:
    if seconds < 1e-6:
        return f"{seconds:.3e}s"
    if seconds < 1:
        return f"{seconds * 1000:.2f}ms"
    if seconds < 120:
        return f"{seconds:.2f}s"
    if seconds < 172_800:
        return f"{seconds / 3600:.2f}h"
    return f"{seconds / 86_400:.2f}d"


def parse_int_list(raw: str) -> tuple[int, ...]:
    values = tuple(int(item.strip()) for item in raw.split(",") if item.strip())
    if not values or any(value <= 0 for value in values):
        raise argparse.ArgumentTypeError("expected comma-separated positive integers")
    return values


def lotus_width_for_value(value: int) -> int:
    if value < 0:
        raise ValueError("Lotus value must be non-negative")
    width = 1
    while True:
        start = (1 << width) - 2
        end = (1 << (width + 1)) - 3
        if start <= value <= end:
            return width
        width += 1


def max_width_for_config(j_bits: int = LOTUS_J_BITS, tiers: int = LOTUS_TIERS) -> int:
    max_width = 1 << j_bits
    for _ in range(tiers):
        shift = max_width + 1
        if shift >= 128:
            return (1 << 127) - 1
        max_width = (1 << shift) - 4
    return max_width


def lotus_encoded_bit_len(value: int, j_bits: int = LOTUS_J_BITS, tiers: int = LOTUS_TIERS) -> int:
    if not 1 <= j_bits <= 8 or tiers <= 0:
        raise ValueError("invalid Lotus config")
    if value < 0:
        raise ValueError("Lotus value must be non-negative")

    payload_value = value + 1
    payload_width = lotus_width_for_value(payload_value)
    if payload_width > max_width_for_config(j_bits, tiers):
        raise ValueError("Lotus value exceeds config range")

    total_tier_width = 0
    current_width = payload_width
    for _ in range(tiers):
        tier_width = lotus_width_for_value(current_width)
        total_tier_width += tier_width
        current_width = tier_width
    if current_width == 0 or current_width > (1 << j_bits):
        raise ValueError("Lotus jumpstarter overflow")
    return j_bits + total_tier_width + payload_width


def seed_count(max_seed_len: int, seed_limit: int | None = None) -> int:
    total = sum(256**length for length in range(1, max_seed_len + 1))
    return min(total, seed_limit) if seed_limit is not None else total


def seed_index_for_depth(max_seed_len: int, seed_limit: int | None = None) -> int:
    return seed_count(max_seed_len, seed_limit) - 1


def target_span_count(input_bytes: int, span_len_bytes: int, span_step: int = 1) -> int:
    if input_bytes < span_len_bytes:
        return 0
    return 1 + (input_bytes - span_len_bytes) // span_step


def expected_hits(seed_count_value: int, target_span_count_value: int, span_len_bytes: int) -> float:
    return seed_count_value * target_span_count_value / float(2 ** (8 * span_len_bytes))


def probability_zero(expected_hit_count: float) -> float:
    if expected_hit_count > 745:
        return 0.0
    return math.exp(-expected_hit_count)


def probability_at_least_one(expected_hit_count: float) -> float:
    return 1.0 - probability_zero(expected_hit_count)


def seed_count_for_success_probability(
    success_probability: float,
    target_span_count_value: int,
    span_len_bytes: int,
) -> int:
    if not 0 < success_probability < 1:
        raise ValueError("success_probability must be in (0, 1)")
    if target_span_count_value <= 0:
        raise ValueError("target_span_count must be positive")
    universe = 2 ** (8 * span_len_bytes)
    return math.ceil(-math.log(1 - success_probability) * universe / target_span_count_value)


def v2_seed_span_record_bits(span_len: int, max_seed_len: int, seed_limit: int | None = None) -> int:
    return v2_seed_span_record_bits_for_seed_index(
        span_len,
        seed_index_for_depth(max_seed_len, seed_limit),
    )


def v2_seed_span_record_bits_for_seed_index(span_len: int, seed_index: int) -> int:
    return (
        lotus_encoded_bit_len(V2_RECORD_TAG_SEED_SPAN)
        + lotus_encoded_bit_len(span_len - 1)
        + lotus_encoded_bit_len(seed_index)
    )


def v2_fixed_seed_span_record_bits(max_seed_len: int, seed_limit: int | None = None) -> int:
    return v2_fixed_seed_span_record_bits_for_seed_index(seed_index_for_depth(max_seed_len, seed_limit))


def v2_fixed_seed_span_record_bits_for_seed_index(seed_index: int) -> int:
    return lotus_encoded_bit_len(V2_RECORD_TAG_SEED_SPAN) + lotus_encoded_bit_len(
        seed_index
    )


def v2_literal_overhead_bits(literal_len: int) -> int:
    if literal_len <= 0:
        return 0
    bits_before_raw = lotus_encoded_bit_len(1) + lotus_encoded_bit_len(literal_len - 1)
    pad = (8 - (bits_before_raw % 8)) % 8
    return bits_before_raw + pad


def minimum_profitable_span(max_seed_len: int, fixed_span: bool) -> int:
    for span_len in range(1, 4097):
        record_bits = (
            v2_fixed_seed_span_record_bits(max_seed_len)
            if fixed_span
            else v2_seed_span_record_bits(span_len, max_seed_len)
        )
        if record_bits < span_len * 8:
            return span_len
    raise ValueError("no profitable span found in search range")


def classify(expected_hit_count: float) -> tuple[str, str]:
    if expected_hit_count < 0.1:
        return (
            "underpowered/null-expected",
            "A zero-hit result is expected and is not evidence against the thesis.",
        )
    if expected_hit_count < 3.0:
        return (
            "weakly powered",
            "A zero-hit result is unsurprising enough to require caution, not a broad claim.",
        )
    return (
        "powered for exact-hit detection",
        "A zero-hit result is surprising enough to investigate the model or implementation.",
    )


def scenario(
    name: str,
    seed_count_value: int,
    target_span_count_value: int,
    span_len_bytes: int,
) -> Scenario:
    hits = expected_hits(seed_count_value, target_span_count_value, span_len_bytes)
    p0 = probability_zero(hits)
    evidence_class, allowed = classify(hits)
    return Scenario(
        name=name,
        seed_count=seed_count_value,
        target_span_count=target_span_count_value,
        span_len_bytes=span_len_bytes,
        expected_hits=hits,
        p_zero=p0,
        p_at_least_one=1 - p0,
        evidence_class=evidence_class,
        allowed_conclusion=allowed,
    )


def target_table_bytes(windows: int, span_len: int, duplicate_factor: float) -> tuple[int, int]:
    if windows <= 0:
        return 0, 0
    unique = max(1, math.ceil(windows / max(duplicate_factor, 1.0)))
    # Mirrors the current telemetry estimate: key bytes for unique spans plus
    # one usize-like start position for every candidate window. Hash-map node
    # overhead is deliberately not hidden in this number.
    bytes_estimate = unique * span_len + windows * 8
    return unique, bytes_estimate


def selected_hit_estimate(
    expected_profitable_hits: float,
    span_len: int,
    input_bytes: int,
    retention: float,
) -> float:
    if expected_profitable_hits <= 0 or input_bytes <= 0:
        return 0.0
    coverage_density = expected_profitable_hits * span_len / input_bytes
    non_overlap = expected_profitable_hits / (1.0 + coverage_density)
    capacity = input_bytes / span_len
    return min(non_overlap * retention, capacity)


def span_tier_rows(
    config: ModelConfig,
    max_seed_len: int,
    input_bytes: int | None = None,
    multiplier: float | None = None,
) -> list[SpanTierRow]:
    actual_input = config.input_bytes if input_bytes is None else input_bytes
    active_multiplier = (
        config.preset_hit_multiplier * config.bundle_multiplier
        if multiplier is None
        else multiplier
    )
    rows: list[SpanTierRow] = []
    seeds = seed_count(max_seed_len, config.seed_limit)
    for span_len in config.span_lens:
        windows = target_span_count(actual_input, span_len, config.span_step)
        unique, table_bytes = target_table_bytes(windows, span_len, config.duplicate_factor)
        raw = expected_hits(seeds, windows, span_len) * active_multiplier
        distinct_raw = expected_hits(seeds, unique, span_len) * active_multiplier
        record_bits_variable = v2_seed_span_record_bits(span_len, max_seed_len, config.seed_limit)
        record_bits_fixed = v2_fixed_seed_span_record_bits(max_seed_len, config.seed_limit)
        profitable_variable = record_bits_variable < span_len * 8
        profitable_fixed = record_bits_fixed < span_len * 8
        profitable_hits_variable = raw if profitable_variable else 0.0
        profitable_hits_fixed = raw if profitable_fixed else 0.0
        selected_variable = selected_hit_estimate(
            profitable_hits_variable,
            span_len,
            actual_input,
            config.superposition_retention,
        )
        selected_fixed = selected_hit_estimate(
            profitable_hits_fixed,
            span_len,
            actual_input,
            config.superposition_retention,
        )
        saved_variable = selected_variable * max((span_len * 8 - record_bits_variable) / 8.0, 0.0)
        saved_fixed = selected_fixed * max((span_len * 8 - record_bits_fixed) / 8.0, 0.0)
        rows.append(
            SpanTierRow(
                span_len=span_len,
                windows=windows,
                unique_spans_estimate=unique,
                target_table_bytes=table_bytes,
                record_bits_variable=record_bits_variable,
                record_bits_fixed=record_bits_fixed,
                profitable_variable=profitable_variable,
                profitable_fixed=profitable_fixed,
                expected_raw_hits=raw,
                expected_distinct_raw_hits=distinct_raw,
                expected_profitable_hits_variable=profitable_hits_variable,
                expected_profitable_hits_fixed=profitable_hits_fixed,
                p_zero_raw=probability_zero(raw),
                p_at_least_one_raw=probability_at_least_one(raw),
                p_zero_distinct=probability_zero(distinct_raw),
                p_at_least_one_distinct=probability_at_least_one(distinct_raw),
                selected_hits_variable=selected_variable,
                selected_hits_fixed=selected_fixed,
                expected_saved_bytes_variable=saved_variable,
                expected_saved_bytes_fixed=saved_fixed,
            )
        )
    return rows


def minimum_profitable_frontier() -> list[FrontierRow]:
    rows: list[FrontierRow] = []
    for depth in range(1, 9):
        seeds = seed_count(depth)
        variable_span = minimum_profitable_span(depth, fixed_span=False)
        fixed_span = minimum_profitable_span(depth, fixed_span=True)
        variable_bits = v2_seed_span_record_bits(variable_span, depth)
        fixed_bits = v2_fixed_seed_span_record_bits(depth)
        log2_seeds = math.log2(seeds)
        variable_gap = 8 * variable_span - log2_seeds
        fixed_gap = 8 * fixed_span - log2_seeds
        rows.append(
            FrontierRow(
                max_seed_len=depth,
                seed_count=seeds,
                log2_seed_count=log2_seeds,
                min_profitable_span_variable=variable_span,
                min_profitable_span_fixed=fixed_span,
                record_bits_at_variable_frontier=variable_bits,
                fixed_record_bits=fixed_bits,
                raw_gap_bits_variable=variable_gap,
                raw_gap_bits_fixed=fixed_gap,
                target_spans_for_one_variable=2**variable_gap,
                target_spans_for_one_fixed=2**fixed_gap,
                expected_variable_hits_per_gib=expected_hits(seeds, 1024**3, variable_span),
                expected_fixed_hits_per_gib=expected_hits(seeds, 1024**3, fixed_span),
            )
        )
    return rows


def hardware_rows(config: ModelConfig, max_seed_len: int) -> list[HardwareRow]:
    profile = HARDWARE_PROFILES[config.profile]
    rows: list[HardwareRow] = []
    for depth in config.seed_depths:
        if depth > max_seed_len:
            continue
        tiers = span_tier_rows(config, depth)
        table_bytes = sum(row.target_table_bytes for row in tiers)
        chunks = max(1, ceil_div(table_bytes, profile.target_table_memory_budget_bytes))
        seeds = seed_count(depth, config.seed_limit)
        seed_expansions = seeds * chunks
        lookup_count = seeds * len(tiers) * chunks
        avg_key_len = sum(config.span_lens) / len(config.span_lens)
        expansion_seconds = seed_expansions / profile.seed_expansions_per_sec
        lookup_seconds = lookup_count * avg_key_len / profile.lookup_key_bytes_per_sec
        table_build_seconds = table_bytes * chunks / profile.target_table_build_bytes_per_sec
        io_seconds = (config.input_bytes * 2) / profile.io_bytes_per_sec
        total_seconds = expansion_seconds + lookup_seconds + table_build_seconds + io_seconds
        rows.append(
            HardwareRow(
                max_seed_len=depth,
                seed_count=seeds,
                tier_count=len(tiers),
                table_bytes=table_bytes,
                chunks=chunks,
                seed_expansions=seed_expansions,
                lookup_count=lookup_count,
                expansion_seconds=expansion_seconds,
                lookup_seconds=lookup_seconds,
                table_build_seconds=table_build_seconds,
                io_seconds=io_seconds,
                total_seconds=total_seconds,
            )
        )
    return rows


def pass_rows(config: ModelConfig, max_seed_len: int) -> list[PassRow]:
    rows: list[PassRow] = []
    current_bytes = config.input_bytes
    active_multiplier = config.preset_hit_multiplier * config.bundle_multiplier
    stopped = False
    for pass_index in range(1, config.passes + 1):
        if stopped:
            break
        tiers = span_tier_rows(config, max_seed_len, input_bytes=current_bytes, multiplier=active_multiplier)
        expected_raw = sum(row.expected_raw_hits for row in tiers)
        expected_profitable = sum(row.expected_profitable_hits_variable for row in tiers)
        selected_hits = sum(row.selected_hits_variable for row in tiers)
        selected_bytes = sum(row.selected_hits_variable * row.span_len for row in tiers)
        saved_bytes = sum(row.expected_saved_bytes_variable for row in tiers)
        literal_bytes = max(current_bytes - selected_bytes, 0.0)
        literal_runs = max(1, math.ceil(selected_hits) + 1)
        mean_literal_run = max(1, math.ceil(literal_bytes / literal_runs))
        literal_overhead = literal_runs * v2_literal_overhead_bits(mean_literal_run) / 8.0
        payload_bytes = max(0, math.ceil(current_bytes - saved_bytes + literal_overhead))
        rate = (payload_bytes - current_bytes) / current_bytes if current_bytes else 0.0
        if selected_hits <= 0:
            stop_reason = "expected_null"
        elif payload_bytes >= current_bytes:
            stop_reason = "non_compressive_layer"
        elif pass_index == config.passes:
            stop_reason = "pass_limit"
        else:
            stop_reason = "continue"
        rows.append(
            PassRow(
                pass_index=pass_index,
                input_bytes=current_bytes,
                expected_raw_hits=expected_raw,
                expected_profitable_hits=expected_profitable,
                selected_hits=selected_hits,
                selected_bytes=selected_bytes,
                saved_bytes=saved_bytes,
                literal_runs_estimate=literal_runs,
                literal_overhead_bytes=literal_overhead,
                payload_bytes=payload_bytes,
                rate_of_change=rate,
                active_multiplier=active_multiplier,
                stop_reason=stop_reason,
            )
        )
        if stop_reason in {"expected_null", "non_compressive_layer"}:
            stopped = True
        current_bytes = payload_bytes
        active_multiplier *= config.pass_multiplier_growth
    return rows


def toy_probability_rows() -> list[dict[str, float | int]]:
    rows = []
    target_spans = 256
    universe_bits = 16
    for seeds in (16, 64, 256, 1024):
        expected = seeds * target_spans / float(2**universe_bits)
        rows.append(
            {
                "universe_bits": universe_bits,
                "seed_count": seeds,
                "target_span_count": target_spans,
                "expected_hits": expected,
                "p_at_least_one": 1 - probability_zero(expected),
            }
        )
    return rows


def toy_empirical_success(seed_count_value: int, target_span_count_value: int, universe_bits: int) -> float:
    mask = (1 << universe_bits) - 1
    trials = 400
    successes = 0
    rng = random.Random(0x544C4D52)
    for trial in range(trials):
        targets = {rng.getrandbits(universe_bits) for _ in range(target_span_count_value)}
        hit = False
        for seed_idx in range(seed_count_value):
            digest = hashlib.sha256(f"{trial}:{seed_idx}".encode("ascii")).digest()
            value = int.from_bytes(digest[:4], "big") & mask
            if value in targets:
                hit = True
                break
        if hit:
            successes += 1
    return successes / trials


def proof_scenarios() -> list[Scenario]:
    laptop_depth3 = scenario(
        name="laptop-depth3-one-million-span8",
        seed_count_value=seed_count(3),
        target_span_count_value=1_000_000,
        span_len_bytes=8,
    )
    depth6_one_million = scenario(
        name="depth6-one-million-span8",
        seed_count_value=seed_count(6),
        target_span_count_value=1_000_000,
        span_len_bytes=8,
    )
    return [laptop_depth3, depth6_one_million]


def default_config() -> ModelConfig:
    return ModelConfig(
        input_bytes=DEFAULT_INPUT_BYTES,
        span_lens=DEFAULT_SPAN_LENS,
        seed_depths=DEFAULT_SEED_DEPTHS,
        seed_limit=None,
        span_step=1,
        passes=4,
        profile="laptop-cpu",
        preset_hit_multiplier=1.0,
        bundle_multiplier=1.0,
        superposition_retention=1.0,
        pass_multiplier_growth=1.0,
        duplicate_factor=1.0,
    )


def model_payload(config: ModelConfig) -> dict[str, Any]:
    max_depth = max(config.seed_depths)
    return {
        "config": asdict(config),
        "hardware_profile": asdict(HARDWARE_PROFILES[config.profile]),
        "proof_scenarios": [asdict(item) for item in proof_scenarios()],
        "minimum_profitable_frontier": [asdict(row) for row in minimum_profitable_frontier()],
        "span_tiers_at_max_depth": [asdict(row) for row in span_tier_rows(config, max_depth)],
        "hardware_rows": [asdict(row) for row in hardware_rows(config, max_depth)],
        "pass_rows": [asdict(row) for row in pass_rows(config, max_depth)],
        "toy_probability_rows": toy_probability_rows(),
    }


def render_frontier_table(rows: list[FrontierRow]) -> list[str]:
    lines = [
        "| max seed len | variable min span | variable record bits | variable gap bits | fixed min span | fixed record bits | fixed gap bits | E variable per GiB |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            "| {depth} | {vspan} | {vbits} | {vgap:.2f} | {fspan} | {fbits} | {fgap:.2f} | {egib:.3e} |".format(
                depth=row.max_seed_len,
                vspan=row.min_profitable_span_variable,
                vbits=row.record_bits_at_variable_frontier,
                vgap=row.raw_gap_bits_variable,
                fspan=row.min_profitable_span_fixed,
                fbits=row.fixed_record_bits,
                fgap=row.raw_gap_bits_fixed,
                egib=row.expected_variable_hits_per_gib,
            )
        )
    return lines


def render_span_tier_table(rows: list[SpanTierRow]) -> list[str]:
    lines = [
        "| span bytes | windows | unique est. | table MiB | variable bits | fixed bits | E candidate hits | p(any distinct hit) | E selected variable | E saved bytes |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            "| {span} | {windows} | {unique} | {table:.2f} | {vbits} | {fbits} | {raw} | {phit} | {selected} | {saved} |".format(
                span=row.span_len,
                windows=fmt_int(row.windows),
                unique=fmt_int(row.unique_spans_estimate),
                table=row.target_table_bytes / 1024**2,
                vbits=row.record_bits_variable,
                fbits=row.record_bits_fixed,
                raw=fmt_float(row.expected_raw_hits),
                phit=fmt_float(row.p_at_least_one_distinct),
                selected=fmt_float(row.selected_hits_variable),
                saved=fmt_float(row.expected_saved_bytes_variable),
            )
        )
    return lines


def render_hardware_table(rows: list[HardwareRow]) -> list[str]:
    lines = [
        "| seed depth | seeds | table MiB | chunks | seed expansions | lookups | expansion | lookup | total |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            "| {depth} | {seeds} | {table:.2f} | {chunks} | {expansions} | {lookups} | {exp_time} | {lookup_time} | {total} |".format(
                depth=row.max_seed_len,
                seeds=fmt_int(row.seed_count),
                table=row.table_bytes / 1024**2,
                chunks=row.chunks,
                expansions=fmt_int(row.seed_expansions),
                lookups=fmt_int(row.lookup_count),
                exp_time=fmt_seconds(row.expansion_seconds),
                lookup_time=fmt_seconds(row.lookup_seconds),
                total=fmt_seconds(row.total_seconds),
            )
        )
    return lines


def render_pass_table(rows: list[PassRow]) -> list[str]:
    lines = [
        "| pass | input bytes | E raw | E profitable | E selected | saved bytes | literal overhead | payload bytes | rate | stop reason |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            "| {pass_index} | {input_bytes} | {raw} | {profitable} | {selected} | {saved} | {overhead} | {payload} | {rate:.5f} | {stop} |".format(
                pass_index=row.pass_index,
                input_bytes=fmt_int(row.input_bytes),
                raw=fmt_float(row.expected_raw_hits),
                profitable=fmt_float(row.expected_profitable_hits),
                selected=fmt_float(row.selected_hits),
                saved=fmt_float(row.saved_bytes),
                overhead=fmt_float(row.literal_overhead_bytes),
                payload=fmt_int(row.payload_bytes),
                rate=row.rate_of_change,
                stop=row.stop_reason,
            )
        )
    return lines


def render_markdown(config: ModelConfig | None = None) -> str:
    config = default_config() if config is None else config
    max_depth = max(config.seed_depths)
    half_success_seeds = seed_count_for_success_probability(0.50, 1_000_000, 8)
    high_success_seeds = seed_count_for_success_probability(0.95, 1_000_000, 8)
    frontier = minimum_profitable_frontier()
    tiers = span_tier_rows(config, max_depth)
    hardware = hardware_rows(config, max_depth)
    passes = pass_rows(config, max_depth)
    profile = HARDWARE_PROFILES[config.profile]

    lines = [
        "# Telomere Power Model",
        "",
        "This is the first-principles notebook-style model agents must use before",
        "interpreting a raw search. It is a deterministic calculator for whether a",
        "search was powered, what a null result means, what the metadata frontier is,",
        "and which scaling direction is worth paying for.",
        "",
        "It performs no broad seed search over real corpora. Small empirical checks in",
        "`--check` are toy powered universes whose probability law is known before",
        "the test runs.",
        "",
        "## Core Event",
        "",
        "For raw seed expansion, the event is exact byte equality:",
        "",
        "```text",
        "expand(seed)[0..span_len] == target_span",
        "```",
        "",
        "For a structure-blind expander, use:",
        "",
        "```text",
        "expected_hits = seed_count * target_span_count / 2^(8 * span_len)",
        "p_zero ~= exp(-expected_hits)",
        "```",
        "",
        "A null result only says something broad if the pre-run expected hit count",
        "made zero hits unlikely. Otherwise it is calibration, not falsification.",
        "",
        "## Counting Boundary",
        "",
        "Telomere does not claim that all strings can be compressed. For a fixed",
        "record budget shorter than `L` bytes, there are fewer possible compact",
        "records than `L`-byte strings. Therefore most `L`-byte strings cannot have",
        "shorter Telomere records.",
        "",
        "The claim is conditional: when a target span is in the image of the public",
        "deterministic seed universe and the record cost is below the span cost,",
        "Telomere can store the shorter seed record and decode exactly. Literal",
        "fallback handles everything else.",
        "",
        "## Native V2 Record Cost Frontier",
        "",
        "This model mirrors the active v2 Lotus record accounting instead of using the",
        "old byte-tag approximation. A variable seed-span record is:",
        "",
        "```text",
        "Lotus(tag=0) + Lotus(span_len - 1) + Lotus(seed_index)",
        "```",
        "",
        "A fixed-span seed record omits `Lotus(span_len - 1)` because the layer",
        "descriptor fixes span length. This matters: metadata is part of the research",
        "object, and smaller metadata moves the profitable frontier.",
        "",
        *render_frontier_table(frontier),
        "",
        "The raw random-like frontier is still expensive, but the bit-accurate v2",
        "model is less pessimistic than the old fixed byte estimate. The important",
        "lesson is not that laptop searches should magically hit; it is that record",
        "format choices move the scale required for powered evidence.",
        "",
        "## Laptop Null Versus Powered Regime",
        "",
        "| scenario | seeds | spans | span bytes | expected hits | p_zero | evidence class |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for item in proof_scenarios():
        lines.append(
            "| {name} | {seed_count} | {target_span_count} | {span_len_bytes} | {expected_hits:.3e} | {p_zero:.9f} | {evidence_class} |".format(
                **asdict(item)
            )
        )

    lines.extend(
        [
            "",
            "For one million 8-byte target spans, depth 3 gives about `9.13e-7`",
            "expected hits and `0.999999087` probability of zero. A null result there",
            "is exactly what the math predicts.",
            "",
            "For the same target-span count at span 8:",
            "",
            f"- 50% chance of at least one raw hit needs about `{half_success_seeds}` seeds.",
            f"- 95% chance of at least one raw hit needs about `{high_success_seeds}` seeds.",
            "- Those are partial depth-6-scale searches, not laptop depth-3 searches.",
            "",
            "## Span, Match-Table, And Replacement Sweep",
            "",
            "### Match Table Costs",
            "",
            f"Default report config: input bytes `{config.input_bytes}`, span step",
            f"`{config.span_step}`, seed depths `{','.join(str(v) for v in config.seed_depths)}`,",
            f"seed limit `{config.seed_limit if config.seed_limit is not None else 'full depth'}`,",
            f"max modeled depth `{max_depth}`, multiplier",
            f"`{config.preset_hit_multiplier * config.bundle_multiplier:g}`.",
            "",
            *render_span_tier_table(tiers),
            "",
            "`E candidate hits` counts candidate occurrences across target windows.",
            "`p(any distinct hit)` uses deduplicated target strings, because repeated",
            "copies do not make the first exact byte string easier to find. Repetition",
            "matters after a hit because it can multiply replacement opportunities.",
            "",
            "### Selection, Overlap, Bundling, And Superposition",
            "",
            "The selected-hit estimate applies a simple interval-overlap correction:",
            "",
            "```text",
            "selected ~= profitable_hits / (1 + profitable_hits * span_len / input_bytes)",
            "```",
            "",
            "That is deliberately an approximation. It is useful because it exposes the",
            "parameter that matters: sparse hits survive almost unchanged; dense hits",
            "start competing for the same bytes and need weighted selection.",
            "",
            "## Hardware Scaling Model",
            "",
            f"Profile `{profile.name}` is an explicit assumption: {profile.note}",
            "The streaming path expands each seed once per target chunk and checks the",
            "generated prefixes against every active span tier. Chunking lowers peak",
            "table memory but repeats seed scans.",
            "",
            *render_hardware_table(hardware),
            "",
            "The key hardware distinction is not just hash throughput. Target-table",
            "construction, lookup bandwidth, chunk count, and I/O decide whether faster",
            "expansion actually helps.",
            "",
            "## Multi-Pass Recurrence",
            "",
            "Recursive passes are modeled as a recurrence over the previous layer payload:",
            "",
            "```text",
            "next_payload ~= input_bytes - selected_savings + literal_record_overhead",
            "```",
            "",
            "A later pass only matters if an earlier pass changes the byte landscape",
            "enough to create more profitable exact spans. The model exposes that as",
            "`--pass-multiplier-growth`; the default is `1.0`, meaning no magic extra",
            "density appears just because another pass exists.",
            "",
            *render_pass_table(passes),
            "",
            "## Public Preset / Transform Separation",
            "",
            "Raw hash expansion, public presets, reversible transforms, planted controls,",
            "and source-family mechanisms are separate lanes. The multipliers in this",
            "model are not evidence by themselves. They answer a planning question:",
            "how much hit-density improvement would a mechanism need before the economics",
            "change?",
            "",
            "Correct use:",
            "",
            "- raw baseline: multiplier `1`",
            "- public preset or transform proposal: multiplier is a hypothesis to prove",
            "- planted control: proves implementation/accounting behavior",
            "- native held-out controlled win: evidence for that named mechanism only",
            "",
            "Incorrect use:",
            "",
            "- claiming ordinary structure helps raw cryptographic expansion",
            "- treating a multiplier sweep as empirical evidence",
            "- treating transform-only byte reduction as Telomere seed-span compression",
            "",
            "## Powered Toy Regime",
            "",
            "A laptop can still show the probability law if the universe is deliberately",
            "scaled down. In a 16-bit toy universe with 256 target spans, the phase",
            "transition is predicted before the test runs:",
            "",
            "| toy seeds | target spans | universe bits | expected hits | predicted p(hit >= 1) |",
            "| ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in toy_probability_rows():
        lines.append(
            "| {seed_count} | {target_span_count} | {universe_bits} | {expected_hits:.4f} | {p_at_least_one:.4f} |".format(
                **row
            )
        )

    lines.extend(
        [
            "",
            "That is the right kind of small test: the model predicts the hit rate first,",
            "then the toy experiment checks the law in a regime where the experiment is",
            "actually powered.",
            "",
            "## Scaling Direction",
            "",
            "Scale toward:",
            "",
            "- reducing record bits, especially fixed-span and descriptor-amortized modes",
            "- increasing target windows only when match-table memory and chunk rescans are affordable",
            "- measuring CPU/GPU semantic parity on small powered controls before acceleration work",
            "- domain-shaped public mechanisms only when they are frozen, versioned, held-out, and decode-accounted",
            "- proof certificates that let expensive searches be independently verified cheaply",
            "",
            "Avoid:",
            "",
            "- larger laptop searches whose expected profitable hits are still near zero",
            "- search reports without expected-hit math and metadata cost",
            "- acceleration over a distribution that has no repeatable profitable workload",
            "- generated ledgers that do not change the model or proof obligations",
            "- broad claims from public-preset, transform, planted, or raw-search lanes bleeding into each other",
            "",
            "## Commands",
            "",
            "```powershell",
            "python scripts/telomere_power_model.py --write-doc",
            "python scripts/telomere_power_model.py --check",
            "python scripts/telomere_power_model.py --json",
            "```",
        ]
    )
    return "\n".join(lines) + "\n"


def assert_close(name: str, observed: float, expected: float, tolerance: float) -> None:
    if abs(observed - expected) > tolerance:
        raise SystemExit(f"{name} changed: observed {observed}, expected {expected}")


def check() -> None:
    doc = POWER_MODEL_MD.read_text(encoding="utf-8")
    expected_doc = render_markdown(default_config())
    if doc != expected_doc:
        raise SystemExit("POWER_MODEL.md is stale; run scripts/telomere_power_model.py --write-doc")
    required = [
        "expected_hits = seed_count * target_span_count / 2^(8 * span_len)",
        "Counting Boundary",
        "Native V2 Record Cost Frontier",
        "Span, Match-Table, And Replacement Sweep",
        "Match Table Costs",
        "Selection, Overlap, Bundling, And Superposition",
        "Hardware Scaling Model",
        "Multi-Pass Recurrence",
        "Public Preset / Transform Separation",
        "Powered Toy Regime",
        "Scaling Direction",
    ]
    missing = [snippet for snippet in required if snippet not in doc]
    if missing:
        raise SystemExit(f"POWER_MODEL.md missing required snippets: {', '.join(missing)}")

    if lotus_encoded_bit_len(0) != 6:
        raise SystemExit("Lotus J3D2 tag bit length changed")
    if lotus_encoded_bit_len(7) != 10:
        raise SystemExit("Lotus J3D2 span_len=8 bit length changed")
    if lotus_encoded_bit_len(42) != 12:
        raise SystemExit("Lotus J3D2 value 42 bit length changed")
    if v2_seed_span_record_bits_for_seed_index(8, 0) != 22:
        raise SystemExit("v2 span=8 seed0 variable record bits changed")
    if (
        v2_seed_span_record_bits_for_seed_index(16, 0)
        - v2_fixed_seed_span_record_bits_for_seed_index(0)
        != 11
    ):
        raise SystemExit("v2 fixed-span savings fixture changed")
    if v2_fixed_seed_span_record_bits_for_seed_index(0) != 12:
        raise SystemExit("v2 fixed seed0 record bits changed")

    laptop = proof_scenarios()[0]
    assert_close("laptop null expected hits", laptop.expected_hits, 9.130612932395366e-7, 1e-12)
    if not (0.999999 < laptop.p_zero < 1.0):
        raise SystemExit("laptop null p_zero calculation changed")

    rows = toy_probability_rows()
    predicted = [row["p_at_least_one"] for row in rows]
    empirical = [
        toy_empirical_success(int(row["seed_count"]), int(row["target_span_count"]), int(row["universe_bits"]))
        for row in rows
    ]
    if empirical != sorted(empirical):
        raise SystemExit(f"toy empirical transition is not monotonic: {empirical}")
    for expected, observed in zip(predicted, empirical):
        if abs(float(expected) - observed) > 0.16:
            raise SystemExit(
                f"toy empirical result {observed:.3f} is too far from predicted {float(expected):.3f}"
            )

    zero_hit_config = default_config()
    zero_pass = pass_rows(zero_hit_config, 3)[0]
    if zero_pass.payload_bytes < zero_pass.input_bytes:
        raise SystemExit("expected-null pass should not appear compressive")

    powered_config = ModelConfig(
        input_bytes=1_000_000,
        span_lens=(8,),
        seed_depths=(6,),
        seed_limit=None,
        span_step=1,
        passes=2,
        profile="laptop-cpu",
        preset_hit_multiplier=1.0,
        bundle_multiplier=1.0,
        superposition_retention=1.0,
        pass_multiplier_growth=1.0,
        duplicate_factor=1.0,
    )
    powered = pass_rows(powered_config, 6)[0]
    if powered.expected_raw_hits < 15:
        raise SystemExit("powered depth-6 sanity scenario lost expected hits")


def build_config(args: argparse.Namespace) -> ModelConfig:
    return ModelConfig(
        input_bytes=args.input_bytes,
        span_lens=args.span_lens,
        seed_depths=args.seed_depths,
        seed_limit=args.seed_limit,
        span_step=args.span_step,
        passes=args.passes,
        profile=args.profile,
        preset_hit_multiplier=args.preset_hit_multiplier,
        bundle_multiplier=args.bundle_multiplier,
        superposition_retention=args.superposition_retention,
        pass_multiplier_growth=args.pass_multiplier_growth,
        duplicate_factor=args.duplicate_factor,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-doc", action="store_true", help="write docs/POWER_MODEL.md")
    parser.add_argument("--check", action="store_true", help="check the model and docs")
    parser.add_argument("--json", action="store_true", help="print compact model data as JSON")
    parser.add_argument("--input-bytes", type=int, default=DEFAULT_INPUT_BYTES)
    parser.add_argument("--span-lens", type=parse_int_list, default=DEFAULT_SPAN_LENS)
    parser.add_argument("--seed-depths", type=parse_int_list, default=DEFAULT_SEED_DEPTHS)
    parser.add_argument("--seed-limit", type=int, default=None)
    parser.add_argument("--span-step", type=int, default=1)
    parser.add_argument("--passes", type=int, default=4)
    parser.add_argument("--profile", choices=sorted(HARDWARE_PROFILES), default="laptop-cpu")
    parser.add_argument("--preset-hit-multiplier", type=float, default=1.0)
    parser.add_argument("--bundle-multiplier", type=float, default=1.0)
    parser.add_argument("--superposition-retention", type=float, default=1.0)
    parser.add_argument("--pass-multiplier-growth", type=float, default=1.0)
    parser.add_argument("--duplicate-factor", type=float, default=1.0)
    args = parser.parse_args()

    if args.input_bytes <= 0:
        raise SystemExit("--input-bytes must be positive")
    if args.span_step <= 0:
        raise SystemExit("--span-step must be positive")
    if args.passes <= 0:
        raise SystemExit("--passes must be positive")
    if any(depth <= 0 for depth in args.seed_depths):
        raise SystemExit("--seed-depths must be positive")
    if args.seed_limit is not None and args.seed_limit <= 0:
        raise SystemExit("--seed-limit must be positive when provided")
    if args.preset_hit_multiplier <= 0 or args.bundle_multiplier <= 0:
        raise SystemExit("multipliers must be positive")
    if args.superposition_retention <= 0 or args.superposition_retention > 1:
        raise SystemExit("--superposition-retention must be in (0, 1]")
    if args.pass_multiplier_growth <= 0:
        raise SystemExit("--pass-multiplier-growth must be positive")
    if args.duplicate_factor < 1:
        raise SystemExit("--duplicate-factor must be >= 1")

    config = build_config(args)
    if args.write_doc:
        POWER_MODEL_MD.write_text(render_markdown(config), encoding="utf-8")
    if args.check:
        check()
    if args.json:
        print(json.dumps(model_payload(config), indent=2))
    if not (args.write_doc or args.check or args.json):
        print(render_markdown(config))


if __name__ == "__main__":
    main()
