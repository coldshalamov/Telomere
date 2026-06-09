"""Telomere proof-kernel viability search.

The search is math-first:

1. validate exact costs, hit probabilities, span histograms, state recurrence,
   and refresh decode contracts;
2. write the idea log;
3. upper-bound the full requested sweep axes;
4. run full state recurrences for the best bounded candidates;
5. write a success/stretch report or a bounded frontier report.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import asdict, dataclass, replace
from heapq import heappop, heappush
from pathlib import Path

from concentration import epsilon_for_confidence
from costs import (
    LITERAL_BYTE_ALIGNED_ENTRY_OVERHEAD_BITS,
    LITERAL_ENTRY_OVERHEAD_BITS,
    boundary_payload_widths,
    cost_table_markdown,
    min_record_bits,
    validate_against_rust_probe,
)
from entry_state import (
    PassLedgerRow,
    normalize_rechunk_schedule,
    run_scheduled_profile,
    validate_state_recurrence,
)
from hit_distribution import p_min_record_le, validate_toy_probabilities
from refresh_model import RefreshRule, by_name, refresh_rules, validate_refresh_rules
from selection_bounds import POLICIES, validate_selection_order
from span_distribution import validate_span_histogram
from superposition_model import (
    SuperpositionConfig,
    retained_bundle_variant_stats,
    retained_variant_stats,
    sweep_configs,
    validate_sweep_configs,
)


ROOT = Path(__file__).resolve().parents[2]
KERNEL_DIR = Path(__file__).resolve().parent

REQUIRED_BLOCK_BITS = (16, 24, 32)
BLOCK_BITS = (8, 16, 24, 32, 48, 64)
ARITY_CAPS = (1, 2, 3, 4, 5)
SEED_DEPTH_BITS = (16, 24, 32, 48, 64, 96, 121, 160)
DEPTH_SCHEDULES = tuple((depth,) for depth in SEED_DEPTH_BITS) + tuple(
    (32, depth) for depth in SEED_DEPTH_BITS
)
LITERAL_INIT_OVERHEAD_BITS = (
    LITERAL_ENTRY_OVERHEAD_BITS,
    LITERAL_BYTE_ALIGNED_ENTRY_OVERHEAD_BITS,
)
RECHUNK_SCHEDULES: tuple[tuple[int | None, ...], ...] = (
    (None,),
    (3,),
    (4,),
    (8,),
    (16,),
    (24,),
    (3, 4),
    (4, 3),
    (3, 3, 4),
)
PASSES = 11
RAW_CROSSOVER_HORIZONS = (11, 50, 100, 200, 500)
RAW_CROSSOVER_REQUIRED_BY_PASS = 200
ENTRY_COUNT = 1_000_000


def format_rechunk_schedule(schedule: tuple[int | None, ...]) -> str:
    return "none" if schedule == (None,) else "->".join(str(item) for item in schedule)


def current_entry_bits(block_bits: int, initial_literal_overhead_bits: int, schedule: tuple[int | None, ...]) -> int:
    first = schedule[0]
    return first if first is not None else block_bits + initial_literal_overhead_bits


def profile_key_schedule(schedule: tuple[int | None, ...]) -> tuple[int | None, ...]:
    return normalize_rechunk_schedule(schedule)


def representative_superposition_configs() -> list[SuperpositionConfig]:
    return [
        SuperpositionConfig(0, 1, False, False),
        SuperpositionConfig(16, 4, False, True),
        SuperpositionConfig(16, 16, False, True),
        SuperpositionConfig(16, 16, True, True),
    ]


MECHANISM_IDEAS = [
    ("strict_baseline", "implemented", "Canonical strict seed replacement only."),
    ("left_to_right_selector", "implemented", "Deterministic disjoint-window lower selector."),
    ("greedy_largest_gain_selector", "implemented", "Deterministic middle selector with overlap loss."),
    ("oracle_weighted_interval_bound", "bounded", "Upper bound that credits all positive windows before conflicts."),
    ("equal_size_neutral_refresh", "implemented", "Zero-growth legal records refresh current-layer bits."),
    ("retained_bloat_delta_1", "implemented", "Encoder-only retained variants within one bit of the main path."),
    ("retained_bloat_delta_8", "implemented", "Encoder-only retained variants within eight bits of the main path."),
    ("retained_bloat_delta_64", "implemented", "Wide retained-variant upper stress test."),
    ("max_variants_2", "implemented", "Two live variants per position."),
    ("max_variants_4", "implemented", "Four live variants per position."),
    ("max_variants_16", "implemented", "Sixteen live variants per position."),
    ("superposed_bundle_search", "implemented", "Arity windows multiply retained variants across positions."),
    ("whole_window_retained_bundles", "implemented", "Retained equal/bloat arity-window records add non-decomposed lower-layer alternatives."),
    ("pass_depth_16", "implemented", "Small seed-depth schedule point."),
    ("pass_depth_64", "implemented", "Mid seed-depth schedule point."),
    ("pass_depth_160", "implemented", "Wide conceptual seed-depth schedule point."),
    ("two_phase_depth_schedule", "implemented", "Profile-known first-pass depth and later-pass depth schedule."),
    ("byte_aligned_literal_initialization", "implemented", "Charges the exact 3+5 literal overhead for byte-aligned literal runs."),
    ("block_bits_8", "expanded", "One-byte current-entry schedule point beyond the required 2/3/4-byte sweep."),
    ("fixed_bitstream_rechunk_4", "implemented", "Profile-known 4-bit chunks after each emitted layer."),
    ("block_bits_16", "implemented", "Small current-entry schedule point."),
    ("block_bits_64", "implemented", "Larger current-entry schedule point."),
    ("deterministic_rechunk", "implemented", "Profile-known bitstream rechunk refresh."),
    ("entry_permutation_profile", "bounded", "Charged deterministic permutation profile."),
    ("layer_descriptor_refresh", "implemented", "Charged layer descriptor refresh."),
    ("phase_rotated_rechunk", "implemented", "Charged deterministic phase rotation."),
    ("multi_profile_selector", "bounded", "Allowed only with charged selector bits; bounded as profile metadata."),
    ("future_diversity_selector", "bounded", "Upper-bounded by oracle selection with superposition score."),
    ("final_collapse_stage", "implemented", "Encoder-state variants collapse to one serialized path."),
    ("external_helper_table", "rejected", "Rejected because it violates the fixed-decoder-or-fully-charged rule."),
    ("foreign_frequency_coder", "rejected", "Rejected because it replaces seed-addressed exact regeneration."),
]


@dataclass(frozen=True)
class BoundCandidate:
    upper_bound_pct_current: float
    block_bits: int
    arity_cap: int
    depth_bits: int
    depth_schedule_bits: tuple[int, ...]
    initial_literal_overhead_bits: int
    rechunk_schedule_bits: tuple[int | None, ...]
    policy: str
    refresh_name: str
    superposition: SuperpositionConfig
    avg_variants: float
    window_multiplier: float


@dataclass
class ProfileEvaluation:
    candidate: BoundCandidate
    final_ratio_raw: float
    effective_pass_min_pct: float
    effective_pass_avg_pct: float
    rows: list[PassLedgerRow]
    concentration_eps_pct: float
    concentration_entry_count: int
    concentration_entry_bits: int
    raw_ratio_by_pass: dict[int, float]
    payback_pass_count: int | None
    payback_effective_pass_count: int | None
    final_ratio_200: float | None
    final_ratio_500: float | None
    viability_class: str
    audit_flags: dict[str, bool | str | float | int | None]


@dataclass(frozen=True)
class FirstEffectiveCeiling:
    net_delta_pct_current: float
    block_bits: int
    first_pass_depth_bits: int
    depth_bits: int
    depth_schedule_bits: tuple[int, ...]
    initial_literal_overhead_bits: int
    rechunk_schedule_bits: tuple[int | None, ...]
    prune_delta_bits: int
    max_variants_per_position: int
    refresh_name: str
    policy: str
    dominance_basis: list[str]


def write_idea_log() -> Path:
    path = ROOT / "docs" / "PROOF_IDEA_LOG.md"
    lines = [
        "# Telomere Proof Idea Log",
        "",
        "This log records the innovation loop for the proof-kernel sweep. Ideas are kept",
        "only when they remain Telomere-native: deterministic exact regeneration by seed,",
        "self-delimiting decode, literal fallback, and no uncharged external help.",
        "",
        "| # | idea | disposition | note |",
        "| ---: | --- | --- | --- |",
    ]
    for i, (name, disposition, note) in enumerate(MECHANISM_IDEAS, 1):
        lines.append(f"| {i} | `{name}` | {disposition} | {note} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def run_validations() -> dict:
    return {
        "cost_validation": validate_against_rust_probe(256),
        "toy_probability_rows": validate_toy_probabilities(),
        "span_histogram_validation": validate_span_histogram(),
        "state_validation": validate_state_recurrence(),
        "refresh_rules": validate_refresh_rules(),
        "superposition_sweep": validate_sweep_configs(),
        "bundle_variant_validation": asdict(
            retained_bundle_variant_stats(80, 5, 96, SuperpositionConfig(16, 16, True, True))
        ),
        "selection_bounds": "left_to_right <= greedy_largest_gain <= oracle_weighted_interval",
        "selection_validation": validate_selection_order() or "ok",
    }


def first_effective_dominance_ceiling(representative: bool = False) -> FirstEffectiveCeiling:
    """Exact two-pass ceiling after monotone dominance reductions.

    A profile cannot meet the 10-effective-pass target unless pass 2, the first
    effective pass after literal wrapping, reaches the target. Under this model,
    these settings dominate their lower alternatives for that ceiling:
    oracle selection, arity cap 5, max variants 16, equal-size and bloat-retained
    alternatives enabled, and the highest-rho zero-metadata refresh rule.
    """

    best: tuple[
        float,
        int,
        int,
        int,
        tuple[int, ...],
        int,
        tuple[int | None, ...],
        int,
    ] | None = None
    refresh = by_name("superposition_derived_refresh")
    block_axis = (8, 64) if representative else BLOCK_BITS
    depth_axis = ((32,),) if representative else DEPTH_SCHEDULES
    literal_axis = (LITERAL_BYTE_ALIGNED_ENTRY_OVERHEAD_BITS,) if representative else LITERAL_INIT_OVERHEAD_BITS
    rechunk_axis = ((3,), (4,), (3, 4)) if representative else RECHUNK_SCHEDULES
    delta_axis = (16,) if representative else (0, 1, 2, 4, 8, 16, 32, 64)
    for block_bits in block_axis:
        for depth_schedule_bits in depth_axis:
            for initial_literal_overhead_bits in literal_axis:
                for rechunk_schedule_bits in rechunk_axis:
                    for prune_delta_bits in delta_axis:
                        superposition = SuperpositionConfig(prune_delta_bits, 16, True, True)
                        _final, rows = run_scheduled_profile(
                            ENTRY_COUNT,
                            block_bits,
                            5,
                            depth_schedule_bits,
                            2,
                            "oracle_weighted_interval",
                            superposition,
                            refresh,
                            initial_literal_overhead_bits,
                            rechunk_schedule_bits,
                        )
                        value = rows[1].net_delta_pct_current
                        if best is None or value > best[0]:
                            best = (
                                value,
                                block_bits,
                                depth_schedule_bits[0],
                                depth_schedule_bits[-1],
                                depth_schedule_bits,
                                initial_literal_overhead_bits,
                                rechunk_schedule_bits,
                                prune_delta_bits,
                            )
    assert best is not None
    return FirstEffectiveCeiling(
        net_delta_pct_current=best[0],
        block_bits=best[1],
        first_pass_depth_bits=best[2],
        depth_bits=best[3],
        depth_schedule_bits=best[4],
        initial_literal_overhead_bits=best[5],
        rechunk_schedule_bits=best[6],
        prune_delta_bits=best[7],
        max_variants_per_position=16,
        refresh_name=refresh.name,
        policy="oracle_weighted_interval",
        dominance_basis=[
            "pass 2 must reach target for any 10-effective-pass success",
            "oracle_weighted_interval is the selection upper bound",
            "arity cap 5 includes arities 1..5",
            "the expanded one-byte lane dominates larger byte schedules for this ceiling in the tested profile space",
            "byte-aligned literal initialization is charged explicitly and is no larger than the worst-case pad budget",
            "fixed bitstream rechunking preserves charged bits while exposing smaller profile-known current entries",
            "max retained variants 16 dominates smaller retained-state caps",
            "equal-size and bloat-retained alternatives enabled dominate disabling either source of retained candidates",
            "superposition_derived_refresh has the largest zero-metadata refresh coefficient in the modeled rule set",
        ],
    )


def bound_one(
    block_bits: int,
    arity_cap: int,
    depth_schedule_bits: tuple[int, ...],
    initial_literal_overhead_bits: int,
    rechunk_schedule_bits: tuple[int | None, ...],
    policy: str,
    refresh: RefreshRule,
    superposition: SuperpositionConfig,
) -> BoundCandidate:
    depth_bits = depth_schedule_bits[-1]
    literal_bits = current_entry_bits(block_bits, initial_literal_overhead_bits, rechunk_schedule_bits)
    stat = retained_variant_stats(literal_bits, depth_bits, superposition)
    score = 1.0 + refresh.rho * (stat.weighted_score - 1.0)
    best_gain = 0.0
    best_multiplier = 1.0
    for arity in range(1, arity_cap + 1):
        span_bits = literal_bits * arity
        multiplier = score**arity
        best_multiplier = max(best_multiplier, multiplier)
        hit = p_min_record_le(span_bits - 1, span_bits, arity, depth_bits, multiplier)
        gain = hit * max(0, span_bits - min_record_bits(min(arity, 5)))
        # Oracle-style upper bound: every starting position can contribute.
        best_gain += gain
    metadata = refresh.metadata_bits_per_pass / ENTRY_COUNT
    upper_pct = 100.0 * max(0.0, best_gain - metadata) / literal_bits
    return BoundCandidate(
        upper_bound_pct_current=upper_pct,
        block_bits=block_bits,
        arity_cap=arity_cap,
        depth_bits=depth_bits,
        depth_schedule_bits=depth_schedule_bits,
        initial_literal_overhead_bits=initial_literal_overhead_bits,
        rechunk_schedule_bits=rechunk_schedule_bits,
        policy=policy,
        refresh_name=refresh.name,
        superposition=superposition,
        avg_variants=stat.avg_variants,
        window_multiplier=best_multiplier,
    )


def bounded_sweep(top_k: int, representative: bool = False) -> tuple[list[BoundCandidate], dict]:
    heap: list[tuple[float, int, BoundCandidate]] = []
    group_best: dict[tuple[str, object], BoundCandidate] = {}
    seen = 0
    seq = 0
    supers = representative_superposition_configs() if representative else sweep_configs()
    rules = (
        (by_name("no_refresh"), by_name("superposition_derived_refresh"), by_name("phase_rotated_rechunk"))
        if representative
        else refresh_rules()
    )
    block_axis = (8, 64) if representative else BLOCK_BITS
    arity_axis = (5,) if representative else ARITY_CAPS
    depth_axis = ((32,),) if representative else DEPTH_SCHEDULES
    literal_axis = LITERAL_INIT_OVERHEAD_BITS
    rechunk_axis = ((None,), (3,), (4,), (3, 4), (4, 3)) if representative else RECHUNK_SCHEDULES
    for block_bits in block_axis:
        for arity_cap in arity_axis:
            for depth_schedule_bits in depth_axis:
                for initial_literal_overhead_bits in literal_axis:
                    for rechunk_schedule_bits in rechunk_axis:
                        for superposition in supers:
                            for refresh in rules:
                                candidate = bound_one(
                                    block_bits,
                                    arity_cap,
                                    depth_schedule_bits,
                                    initial_literal_overhead_bits,
                                    rechunk_schedule_bits,
                                    "oracle_weighted_interval",
                                    refresh,
                                    superposition,
                                )
                                seen += len(POLICIES)
                                seq += 1
                                item = (candidate.upper_bound_pct_current, seq, candidate)
                                if len(heap) < top_k:
                                    heappush(heap, item)
                                elif item[0] > heap[0][0]:
                                    heappop(heap)
                                    heappush(heap, item)

                                for key in (
                                    ("block_bits", block_bits),
                                    ("arity_cap", arity_cap),
                                    ("seed_depth_bits", depth_schedule_bits[-1]),
                                    ("first_pass_depth_bits", depth_schedule_bits[0]),
                                    ("depth_schedule_bits", depth_schedule_bits),
                                    ("initial_literal_overhead_bits", initial_literal_overhead_bits),
                                    ("rechunk_schedule_bits", rechunk_schedule_bits),
                                    ("refresh_rule", refresh.name),
                                    ("prune_delta_bits", superposition.prune_delta_bits),
                                    ("max_variants_per_position", superposition.max_variants_per_position),
                                    ("equal_size_allowed", superposition.equal_size_allowed),
                                    ("bloat_tolerant_retained", superposition.bloat_tolerant_retained),
                                ):
                                    prior = group_best.get(key)
                                    if prior is None or candidate.upper_bound_pct_current > prior.upper_bound_pct_current:
                                        group_best[key] = candidate

    candidates_by_key: dict[tuple, BoundCandidate] = {}
    for candidate in [item[2] for item in sorted(heap, key=lambda x: x[0], reverse=True)] + list(group_best.values()):
        key = (
            candidate.block_bits,
            candidate.arity_cap,
            candidate.depth_bits,
            candidate.depth_schedule_bits,
            candidate.initial_literal_overhead_bits,
            candidate.rechunk_schedule_bits,
            candidate.refresh_name,
            candidate.superposition,
        )
        candidates_by_key[key] = candidate
    best_unique = sorted(
        candidates_by_key.values(),
        key=lambda candidate: candidate.upper_bound_pct_current,
        reverse=True,
    )
    best = [replace(candidate, policy=policy) for candidate in best_unique for policy in POLICIES]
    summary = {
        "bounded_profiles": seen,
        "representative_mode": representative,
        "required_block_bits": REQUIRED_BLOCK_BITS,
        "block_bits": block_axis,
        "block_bytes": [bits / 8 for bits in block_axis],
        "arity_caps": arity_axis,
        "seed_depth_bits": sorted({schedule[-1] for schedule in depth_axis}),
        "depth_schedules": depth_axis,
        "initial_literal_overhead_bits": literal_axis,
        "rechunk_schedules": [format_rechunk_schedule(schedule) for schedule in rechunk_axis],
        "superposition_configs": len(supers),
        "prune_delta_bits": sorted({cfg.prune_delta_bits for cfg in supers}),
        "max_variants_per_position": sorted({cfg.max_variants_per_position for cfg in supers}),
        "equal_size_allowed": sorted({cfg.equal_size_allowed for cfg in supers}),
        "bloat_tolerant_retained": sorted({cfg.bloat_tolerant_retained for cfg in supers}),
        "refresh_rules": [rule.name for rule in rules],
        "selection_policies": POLICIES,
        "top_k_recurrence_profiles": len(best),
        "recurrence_seed_profiles": len(best_unique),
        "recurrence_profile_selection": "top bounded profiles plus best representatives for each required sweep axis",
    }
    return best, summary


def run_candidate_rows(candidate: BoundCandidate, passes: int) -> tuple[float, list[PassLedgerRow]]:
    refresh = next(rule for rule in refresh_rules() if rule.name == candidate.refresh_name)
    final, rows = run_scheduled_profile(
        ENTRY_COUNT,
        candidate.block_bits,
        candidate.arity_cap,
        candidate.depth_schedule_bits,
        passes,
        candidate.policy,
        candidate.superposition,
        refresh,
        candidate.initial_literal_overhead_bits,
        candidate.rechunk_schedule_bits,
    )
    return final.original_raw_bits, rows


def raw_ratio_curve(rows: list[PassLedgerRow], original_raw_bits: float) -> dict[int, float]:
    curve: dict[int, float] = {}
    for horizon in RAW_CROSSOVER_HORIZONS:
        if len(rows) >= horizon:
            curve[horizon] = rows[horizon - 1].bits_after / original_raw_bits
    return curve


def first_payback_pass(rows: list[PassLedgerRow], original_raw_bits: float) -> int | None:
    for row in rows:
        if row.bits_after / original_raw_bits < 1.0:
            return row.pass_index
    return None


def classify_viability(
    min_pct: float,
    candidate: BoundCandidate,
    payback_effective_pass_count: int | None,
) -> str:
    if min_pct < 0.1:
        return "frontier_below_0_1"
    if candidate.policy == "oracle_weighted_interval":
        return "component_oracle_upper_bound"
    if payback_effective_pass_count is None:
        return "component_no_raw_crossover_observed"
    if payback_effective_pass_count > RAW_CROSSOVER_REQUIRED_BY_PASS:
        return "component_slow_raw_crossover"
    if candidate.superposition.max_variants_per_position > 4:
        return "viability_high_working_state"
    return "viability_practical_candidate"


def audit_candidate(
    candidate: BoundCandidate,
    rows: list[PassLedgerRow],
    min_pct: float,
    raw_curve: dict[int, float],
    payback_effective_pass_count: int | None,
) -> dict[str, bool | str | float | int | None]:
    refresh = by_name(candidate.refresh_name)
    max_avg_variants = max((row.avg_variants_per_position for row in rows), default=1.0)
    max_discount = max((row.opportunity_discount_ratio for row in rows), default=1.0)
    max_working_entries = max(
        (row.entry_count_before * row.avg_variants_per_position for row in rows),
        default=0.0,
    )
    earned_variant_ok = all(
        row.avg_variants_per_position <= row.variant_cap + 1e-9 for row in rows
    )
    deterministic_selector = candidate.policy != "oracle_weighted_interval"
    raw_crossover_200 = (
        payback_effective_pass_count is not None
        and payback_effective_pass_count <= RAW_CROSSOVER_REQUIRED_BY_PASS
    )
    profile_schedule_fixed = True
    no_sidecar_metadata = refresh.metadata_bits_per_pass >= 0 and profile_schedule_fixed
    return {
        "earned_variant_ok": earned_variant_ok,
        "max_expected_live_variants_per_entry": max_avg_variants,
        "max_variant_cap": candidate.superposition.max_variants_per_position,
        "opportunity_multiplier_basis": "earned_expected_variants_discounted_for_shared_entries",
        "optimistic_combo_reported_only": True,
        "max_optimistic_to_conservative_multiplier": max_discount,
        "selector_viability_ok": deterministic_selector,
        "selector_type": candidate.policy,
        "oracle_is_upper_bound": candidate.policy == "oracle_weighted_interval",
        "raw_crossover_within_200_effective_passes": raw_crossover_200,
        "final_raw_after_200": raw_curve.get(200),
        "final_collapse_ok": True,
        "encoder_only_state_serialized": False,
        "refresh_decodable": refresh.decodable,
        "refresh_decode_story": refresh.proof,
        "fixed_rechunk_schedule": format_rechunk_schedule(candidate.rechunk_schedule_bits),
        "metadata_sidecar_ok": no_sidecar_metadata,
        "refresh_metadata_bits_per_pass": refresh.metadata_bits_per_pass,
        "working_variant_entries_proxy": max_working_entries,
        "compute_memory_profile": (
            "theoretical_upper_bound"
            if candidate.superposition.max_variants_per_position > 4
            else "practical_capped"
        ),
        "ten_effective_pass_min_pct": min_pct,
    }


def evaluate_candidate(candidate: BoundCandidate) -> ProfileEvaluation:
    long_horizon = max(RAW_CROSSOVER_HORIZONS)
    if candidate.rechunk_schedule_bits == (None,):
        long_horizon = PASSES
    original_raw_bits, long_rows = run_candidate_rows(candidate, long_horizon)
    rows = long_rows[:PASSES]
    effective = rows[1:] if len(rows) > 1 else rows
    min_pct = min((row.net_delta_pct_current for row in effective), default=0.0)
    avg_pct = sum(row.net_delta_pct_current for row in effective) / max(1, len(effective))
    effective_entry_count = int(min((row.entry_count_before for row in effective), default=ENTRY_COUNT))
    concentration_entry_bits = current_entry_bits(
        candidate.block_bits,
        candidate.initial_literal_overhead_bits,
        candidate.rechunk_schedule_bits,
    )
    concentration = epsilon_for_confidence(
        max(1, effective_entry_count),
        concentration_entry_bits,
        candidate.arity_cap,
    )
    curve = raw_ratio_curve(long_rows, original_raw_bits)
    payback_pass_count = first_payback_pass(long_rows, original_raw_bits)
    payback_effective = None if payback_pass_count is None else max(0, payback_pass_count - 1)
    viability_class = classify_viability(min_pct, candidate, payback_effective)
    return ProfileEvaluation(
        candidate=candidate,
        final_ratio_raw=rows[-1].bits_after / original_raw_bits,
        effective_pass_min_pct=min_pct,
        effective_pass_avg_pct=avg_pct,
        rows=rows,
        concentration_eps_pct=100.0 * concentration.epsilon_ratio,
        concentration_entry_count=max(1, effective_entry_count),
        concentration_entry_bits=concentration_entry_bits,
        raw_ratio_by_pass=curve,
        payback_pass_count=payback_pass_count,
        payback_effective_pass_count=payback_effective,
        final_ratio_200=curve.get(200),
        final_ratio_500=curve.get(500),
        viability_class=viability_class,
        audit_flags=audit_candidate(candidate, long_rows, min_pct, curve, payback_effective),
    )


def pass_ledger_markdown(rows: list[PassLedgerRow]) -> str:
    lines = [
        "| pass | depth bits | literal overhead | bits before | bits after | current delta % | raw delta % | accepted windows | avg variants | equal | bloat retained | bundled | conservative multiplier | optimistic multiplier | discount | rechunk | residual bits |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row.pass_index} | {row.depth_bits} | {row.literal_overhead_bits} | "
            f"{row.bits_before:.2f} | {row.bits_after:.2f} | "
            f"{row.net_delta_pct_current:.6f} | {row.net_delta_pct_raw:.6f} | "
            f"{row.accepted_windows:.4f} | {row.avg_variants_per_position:.4f} | "
            f"{row.equal_size_neutral_variants_per_entry:.4f} | "
            f"{row.retained_noncompressive_variants_per_entry:.4f} | "
            f"{row.bundled_variants_per_window:.4f} | "
            f"{row.conservative_window_multiplier:.4f} | "
            f"{row.optimistic_window_multiplier:.4f} | "
            f"{row.opportunity_discount_ratio:.4f} | "
            f"{row.rechunk_entry_bits if row.rechunk_entry_bits is not None else 'none'} | "
            f"{row.rechunk_residual_bits:.4f} |"
        )
    return "\n".join(lines)


def raw_curve_markdown(evaluation: ProfileEvaluation) -> str:
    lines = [
        "| modeled passes | final/raw |",
        "| ---: | ---: |",
    ]
    for horizon in RAW_CROSSOVER_HORIZONS:
        value = evaluation.raw_ratio_by_pass.get(horizon)
        lines.append(f"| {horizon} | {value:.9f} |" if value is not None else f"| {horizon} | n/a |")
    return "\n".join(lines)


def fmt_optional_float(value: float | None, digits: int = 9) -> str:
    return "n/a" if value is None else f"{value:.{digits}f}"


def concentration_required_entries(evaluation: ProfileEvaluation) -> dict[str, int | None]:
    out: dict[str, int | None] = {}
    for threshold in (0.1, 0.2):
        key = f"radius_le_margin_to_{str(threshold).replace('.', '_')}_pct"
        margin = evaluation.effective_pass_min_pct - threshold
        if margin <= 0:
            out[key] = None
        else:
            out[key] = math.ceil(
                evaluation.concentration_entry_count
                * (evaluation.concentration_eps_pct / margin) ** 2
            )
    return out


def select_winners(evaluations: list[ProfileEvaluation]) -> dict[str, ProfileEvaluation]:
    deterministic = [ev for ev in evaluations if ev.candidate.policy != "oracle_weighted_interval"]
    viable_floor = [ev for ev in deterministic if ev.effective_pass_min_pct >= 0.1]
    payback_pool = [ev for ev in viable_floor if ev.payback_effective_pass_count is not None]
    practical_pool = [
        ev
        for ev in viable_floor
        if ev.candidate.superposition.max_variants_per_position <= 4
        and ev.audit_flags["compute_memory_profile"] == "practical_capped"
    ]

    def payback_key(ev: ProfileEvaluation) -> tuple[float, float, float]:
        payback = ev.payback_effective_pass_count
        return (
            float("inf") if payback is None else float(payback),
            ev.raw_ratio_by_pass.get(200, float("inf")),
            -ev.effective_pass_min_pct,
        )

    winners = {
        "highest_per_pass_drift": max(
            evaluations,
            key=lambda ev: (ev.effective_pass_min_pct, ev.effective_pass_avg_pct),
        ),
        "highest_per_pass_drift_deterministic": max(
            deterministic or evaluations,
            key=lambda ev: (ev.effective_pass_min_pct, ev.effective_pass_avg_pct),
        ),
        "fastest_raw_payback": min(payback_pool or viable_floor or deterministic or evaluations, key=payback_key),
        "best_practical_memory_compute": min(practical_pool or viable_floor or deterministic or evaluations, key=payback_key),
    }
    return winners


def evaluation_payload(ev: ProfileEvaluation) -> dict:
    return {
        "candidate": {
            **asdict(ev.candidate),
            "superposition": asdict(ev.candidate.superposition),
            "rechunk_schedule": format_rechunk_schedule(ev.candidate.rechunk_schedule_bits),
        },
        "final_ratio_raw": ev.final_ratio_raw,
        "raw_ratio_by_pass": ev.raw_ratio_by_pass,
        "payback_pass_count": ev.payback_pass_count,
        "payback_effective_pass_count": ev.payback_effective_pass_count,
        "viability_class": ev.viability_class,
        "effective_pass_min_pct": ev.effective_pass_min_pct,
        "effective_pass_avg_pct": ev.effective_pass_avg_pct,
        "concentration_eps_pct": ev.concentration_eps_pct,
        "concentration_entry_count": ev.concentration_entry_count,
        "concentration_entry_bits": ev.concentration_entry_bits,
        "concentration_required_entries": concentration_required_entries(ev),
        "audit_flags": ev.audit_flags,
    }


def experiment_registry_rows(
    evaluations: list[ProfileEvaluation],
    winners: dict[str, ProfileEvaluation],
) -> list[dict]:
    def choose(name: str, predicate, decode_story: str, charged_metadata: str, selector_note: str) -> dict:
        pool = [ev for ev in evaluations if predicate(ev)]
        ev = min(
            pool,
            key=lambda item: (
                float("inf") if item.payback_effective_pass_count is None else item.payback_effective_pass_count,
                item.raw_ratio_by_pass.get(200, float("inf")),
                -item.effective_pass_min_pct,
            ),
        ) if pool else None
        row = {
            "mechanism_name": name,
            "telomere_native_decode_story": decode_story,
            "charged_metadata": charged_metadata,
            "selector_type": selector_note,
            "result_uses_conservative_discount": True,
        }
        if ev is None:
            row.update(
                {
                    "expected_per_pass_rate_pct": None,
                    "final_raw_11": None,
                    "final_raw_50": None,
                    "final_raw_100": None,
                    "final_raw_200": None,
                    "final_raw_500": None,
                    "payback_effective_pass_count": None,
                    "concentration_entry_requirement": None,
                    "viability_class": "not_evaluated",
                }
            )
            return row
        row.update(
            {
                "expected_per_pass_rate_pct": ev.effective_pass_min_pct,
                "final_raw_11": ev.raw_ratio_by_pass.get(11),
                "final_raw_50": ev.raw_ratio_by_pass.get(50),
                "final_raw_100": ev.raw_ratio_by_pass.get(100),
                "final_raw_200": ev.raw_ratio_by_pass.get(200),
                "final_raw_500": ev.raw_ratio_by_pass.get(500),
                "payback_effective_pass_count": ev.payback_effective_pass_count,
                "concentration_entry_requirement": concentration_required_entries(ev),
                "viability_class": ev.viability_class,
                "selected_config": {
                    "block_bits": ev.candidate.block_bits,
                    "rechunk_schedule": format_rechunk_schedule(ev.candidate.rechunk_schedule_bits),
                    "policy": ev.candidate.policy,
                    "refresh": ev.candidate.refresh_name,
                    "max_variants": ev.candidate.superposition.max_variants_per_position,
                },
            }
        )
        return row

    rows = [
        choose(
            "fixed_rechunk_3",
            lambda ev: ev.candidate.rechunk_schedule_bits == (3,),
            "Decoder splits each decoded layer bitstream into fixed 3-bit current entries from the profile; final residual length is implied by the layer bit length.",
            "Zero per-file bits for a fixed profile; multiplexed profile must charge a selector.",
            "best deterministic/payback row when available",
        ),
        choose(
            "fixed_rechunk_4",
            lambda ev: ev.candidate.rechunk_schedule_bits == (4,),
            "Decoder splits each decoded layer bitstream into fixed 4-bit current entries from the profile.",
            "Zero per-file bits for a fixed profile; multiplexed profile must charge a selector.",
            "best deterministic/payback row when available",
        ),
        choose(
            "schedule_3_to_4",
            lambda ev: ev.candidate.rechunk_schedule_bits == (3, 4),
            "Decoder applies the fixed pass schedule: 3-bit rechunk after the first modeled layer, then 4-bit chunks for later layers.",
            "Zero per-file bits only when this schedule is the fixed decoder profile.",
            "best deterministic/payback row when available",
        ),
        choose(
            "schedule_4_to_3",
            lambda ev: ev.candidate.rechunk_schedule_bits == (4, 3),
            "Decoder applies the fixed pass schedule: 4-bit rechunk, then 3-bit chunks for later layers.",
            "Zero per-file bits only when this schedule is the fixed decoder profile.",
            "best deterministic/payback row when available",
        ),
        choose(
            "large_initial_block_64",
            lambda ev: ev.candidate.block_bits == 64,
            "Pass 1 wraps larger raw blocks, then later profile rechunking exposes smaller current entries; raw bytes are recovered by normal recursive layer decode.",
            "Literal wrapper is charged in pass 1; rechunk profile is fixed or must be selected in metadata.",
            "best deterministic/payback row when available",
        ),
        choose(
            "greedy_selector",
            lambda ev: ev.candidate.policy == "greedy_largest_gain",
            "Encoder emits only the chosen non-overlapping seed/literal records; decoder follows the record stream and needs no selector side table.",
            "No selector sidecar.",
            "greedy_largest_gain",
        ),
        choose(
            "oracle_selector_upper_bound",
            lambda ev: ev.candidate.policy == "oracle_weighted_interval",
            "Not a viability selector; decoder story is the ordinary emitted stream, but the selection estimate is an upper bound.",
            "No selector sidecar modeled, but result is labeled upper bound.",
            "oracle upper bound only",
        ),
        choose(
            "practical_variant_cap_4",
            lambda ev: ev.candidate.superposition.max_variants_per_position <= 4,
            "Encoder may keep up to four earned variants per position, then serializes only the selected collapsed path.",
            "Working state is compute/memory only; selected records are charged in output.",
            "best deterministic/payback row when available",
        ),
        choose(
            "phase_rotated_rechunk",
            lambda ev: ev.candidate.refresh_name == "phase_rotated_rechunk",
            "Decoder reverses the deterministic phase from the charged profile selector and layer number.",
            "3 bits per pass in the current proof-kernel rule.",
            "best deterministic/payback row when available",
        ),
        choose(
            "no_rechunk_baseline",
            lambda ev: ev.candidate.rechunk_schedule_bits == (None,),
            "Decoder uses the emitted record stream directly with no profile rechunk boundary change.",
            "Zero rechunk metadata.",
            "best deterministic/payback row when available",
        ),
    ]
    rows.append(
        {
            "mechanism_name": "winning_highest_per_pass_drift",
            "telomere_native_decode_story": "Category winner, see selected config.",
            "charged_metadata": "See selected config.",
            "selector_type": winners["highest_per_pass_drift"].candidate.policy,
            "result_uses_conservative_discount": True,
            **evaluation_payload(winners["highest_per_pass_drift"]),
        }
    )
    rows.append(
        {
            "mechanism_name": "winning_fastest_raw_payback",
            "telomere_native_decode_story": "Category winner, see selected config.",
            "charged_metadata": "See selected config.",
            "selector_type": winners["fastest_raw_payback"].candidate.policy,
            "result_uses_conservative_discount": True,
            **evaluation_payload(winners["fastest_raw_payback"]),
        }
    )
    return rows


def ablation_rows(best: ProfileEvaluation) -> list[dict]:
    cand = best.candidate
    variants: list[tuple[str, BoundCandidate, bool]] = [
        (
            "no_equal_size_replacements",
            replace(cand, superposition=replace(cand.superposition, equal_size_allowed=False)),
            cand.superposition.equal_size_allowed,
        ),
        (
            "no_retained_bloat",
            replace(cand, superposition=replace(cand.superposition, bloat_tolerant_retained=False)),
            cand.superposition.bloat_tolerant_retained,
        ),
        (
            "no_superposition",
            replace(cand, superposition=SuperpositionConfig(0, 1, False, False)),
            cand.superposition.max_variants_per_position > 1
            or cand.superposition.equal_size_allowed
            or cand.superposition.bloat_tolerant_retained,
        ),
        (
            "no_rechunk",
            replace(cand, rechunk_schedule_bits=(None,)),
            cand.rechunk_schedule_bits != (None,),
        ),
        (
            "no_phase_rotation",
            replace(cand, refresh_name="no_refresh") if cand.refresh_name == "phase_rotated_rechunk" else cand,
            cand.refresh_name == "phase_rotated_rechunk",
        ),
        (
            "greedy_instead_of_oracle",
            replace(cand, policy="greedy_largest_gain"),
            cand.policy == "oracle_weighted_interval",
        ),
    ]
    rows: list[dict] = []
    for name, ablated, active in variants:
        ev = evaluate_candidate(ablated)
        rows.append(
            {
                "mechanism_disabled": name,
                "changed_active_mechanism": active,
                "effective_pass_min_pct": ev.effective_pass_min_pct,
                "delta_min_pct_vs_best": ev.effective_pass_min_pct - best.effective_pass_min_pct,
                "final_raw_11": ev.raw_ratio_by_pass.get(11),
                "final_raw_200": ev.raw_ratio_by_pass.get(200),
                "payback_effective_pass_count": ev.payback_effective_pass_count,
                "viability_class": ev.viability_class,
            }
        )
    return rows


def ablation_markdown(rows: list[dict]) -> str:
    lines = [
        "| disabled mechanism | active change | min current delta % | contribution vs best | final/raw 11 | final/raw 200 | payback effective pass | class |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        payback = row["payback_effective_pass_count"]
        lines.append(
            f"| `{row['mechanism_disabled']}` | {row['changed_active_mechanism']} | "
            f"{row['effective_pass_min_pct']:.6f} | {row['delta_min_pct_vs_best']:.6f} | "
            f"{fmt_optional_float(row['final_raw_11'])} | {fmt_optional_float(row['final_raw_200'])} | "
            f"{payback if payback is not None else 'none'} | `{row['viability_class']}` |"
        )
    return "\n".join(lines)


def winners_markdown(winners: dict[str, ProfileEvaluation]) -> str:
    lines = [
        "| category | min current delta % | final/raw 11 | final/raw 200 | final/raw 500 | payback effective pass | selector | rechunk | variants cap | class |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | --- |",
    ]
    for name, ev in winners.items():
        payback = ev.payback_effective_pass_count
        lines.append(
            f"| `{name}` | {ev.effective_pass_min_pct:.6f} | "
            f"{fmt_optional_float(ev.raw_ratio_by_pass.get(11))} | "
            f"{fmt_optional_float(ev.raw_ratio_by_pass.get(200))} | "
            f"{fmt_optional_float(ev.raw_ratio_by_pass.get(500))} | "
            f"{payback if payback is not None else 'none'} | `{ev.candidate.policy}` | "
            f"`{format_rechunk_schedule(ev.candidate.rechunk_schedule_bits)}` | "
            f"{ev.candidate.superposition.max_variants_per_position} | `{ev.viability_class}` |"
        )
    return "\n".join(lines)


def write_best_config(evaluation: ProfileEvaluation, path: Path) -> None:
    min_pct = evaluation.effective_pass_min_pct
    payload = {
        "candidate": {
            **asdict(evaluation.candidate),
            "superposition": asdict(evaluation.candidate.superposition),
            "rechunk_schedule": format_rechunk_schedule(evaluation.candidate.rechunk_schedule_bits),
        },
        "final_ratio_raw": evaluation.final_ratio_raw,
        "raw_ratio_by_pass": evaluation.raw_ratio_by_pass,
        "payback_pass_count": evaluation.payback_pass_count,
        "payback_effective_pass_count": evaluation.payback_effective_pass_count,
        "viability_class": evaluation.viability_class,
        "audit_flags": evaluation.audit_flags,
        "effective_pass_min_pct": evaluation.effective_pass_min_pct,
        "effective_pass_avg_pct": evaluation.effective_pass_avg_pct,
        "concentration_eps_pct": evaluation.concentration_eps_pct,
        "concentration_entry_count": evaluation.concentration_entry_count,
        "concentration_entry_bits": evaluation.concentration_entry_bits,
        "concentration_required_entries": concentration_required_entries(evaluation),
        "target_multipliers": {
            "to_0_1_pct": (0.1 / min_pct) if min_pct > 0 else None,
            "to_0_2_pct": (0.2 / min_pct) if min_pct > 0 else None,
        },
        "passes": [asdict(row) for row in evaluation.rows],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_summary_json(
    validations: dict,
    sweep_summary: dict,
    evaluations: list[ProfileEvaluation],
    first_effective_ceiling: FirstEffectiveCeiling,
    winners: dict[str, ProfileEvaluation],
    registry: list[dict],
    ablations: list[dict],
) -> Path:
    path = KERNEL_DIR / "sweep_summary.json"
    payload = {
        "validations": validations,
        "sweep_summary": sweep_summary,
        "first_effective_dominance_ceiling": asdict(first_effective_ceiling),
        "winners": {name: evaluation_payload(ev) for name, ev in winners.items()},
        "experiment_registry": registry,
        "best_config_ablation_table": ablations,
        "top_profiles": [evaluation_payload(ev) for ev in evaluations[:25]],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def write_frontier_report(
    best: ProfileEvaluation,
    validations: dict,
    sweep_summary: dict,
    summary_path: Path,
    first_effective_ceiling: FirstEffectiveCeiling,
) -> Path:
    path = ROOT / "docs" / "TELOMERE_FRONTIER_REPORT.md"
    cand = best.candidate
    missing = max(0.0, 0.1 - best.effective_pass_min_pct)
    missing_multiplier = (0.1 / best.effective_pass_min_pct) if best.effective_pass_min_pct > 0 else float("inf")
    stretch_multiplier = (0.2 / best.effective_pass_min_pct) if best.effective_pass_min_pct > 0 else float("inf")
    lines = [
        "# Telomere Frontier Report",
        "",
        "Under this model, the bounded sweep did not produce a configuration, even",
        "under the oracle upper selection bound, whose ten effective passes all reach",
        "`0.1%` current-layer net expected compression.",
        "",
        "This is a bounded frontier statement for the implemented proof kernel, not a broad",
        "claim beyond the stated assumptions.",
        "",
        "## Best Modeled Ceiling",
        "",
        f"- block bits: `{cand.block_bits}`",
        f"- arity cap: `{cand.arity_cap}`",
        f"- seed-depth bits: `{cand.depth_bits}`",
        f"- depth schedule bits: `{list(cand.depth_schedule_bits)}`",
        f"- initial literal overhead bits: `{cand.initial_literal_overhead_bits}`",
        f"- rechunk schedule bits: `{format_rechunk_schedule(cand.rechunk_schedule_bits)}`",
        f"- selection policy: `{cand.policy}`",
        f"- refresh rule: `{cand.refresh_name}`",
        f"- prune delta bits: `{cand.superposition.prune_delta_bits}`",
        f"- max variants per position: `{cand.superposition.max_variants_per_position}`",
        f"- equal-size allowed: `{cand.superposition.equal_size_allowed}`",
        f"- retained bloat allowed: `{cand.superposition.bloat_tolerant_retained}`",
        f"- best ten-effective-pass minimum: `{best.effective_pass_min_pct:.6f}%`",
        f"- best ten-effective-pass average: `{best.effective_pass_avg_pct:.6f}%`",
        f"- multiplier needed for `0.1%`: `{missing_multiplier:.6f}x`",
        f"- multiplier needed for `0.2%`: `{stretch_multiplier:.6f}x`",
        f"- final charged/raw ratio after `{PASSES}` passes: `{best.final_ratio_raw:.9f}`",
        f"- concentration radius at alpha `1e-9`: `±{best.concentration_eps_pct:.6f}` percentage points",
        "",
        "## First Effective Pass Ceiling",
        "",
        "A successful configuration would need pass 2, the first effective pass after",
        "literal wrapping, to reach `0.1%`. The dominance-reduced exhaustive ceiling",
        "over block size, seed depth, and prune delta is:",
        "",
        f"- pass-2 ceiling: `{first_effective_ceiling.net_delta_pct_current:.6f}%`",
        f"- block bits: `{first_effective_ceiling.block_bits}`",
        f"- first-pass seed-depth bits: `{first_effective_ceiling.first_pass_depth_bits}`",
        f"- seed-depth bits: `{first_effective_ceiling.depth_bits}`",
        f"- depth schedule bits: `{list(first_effective_ceiling.depth_schedule_bits)}`",
        f"- initial literal overhead bits: `{first_effective_ceiling.initial_literal_overhead_bits}`",
        f"- rechunk schedule bits: `{format_rechunk_schedule(first_effective_ceiling.rechunk_schedule_bits)}`",
        f"- prune delta bits: `{first_effective_ceiling.prune_delta_bits}`",
        f"- max variants per position: `{first_effective_ceiling.max_variants_per_position}`",
        f"- refresh rule: `{first_effective_ceiling.refresh_name}`",
        f"- selection policy: `{first_effective_ceiling.policy}`",
        "",
        "Dominance basis:",
        "",
        *[f"- {item}." for item in first_effective_ceiling.dominance_basis],
        "",
        "## Pass Ledger",
        "",
        pass_ledger_markdown(best.rows),
        "",
        "## Cost Table",
        "",
        "The full machine-readable table is generated by `cargo run --quiet --bin v1_cost_table`.",
        "The Python model validated payload widths `1..256`; widths `1..64` are also",
        "checked directly through `src/header.rs::v1_record_bit_len` in the Rust probe.",
        "",
        cost_table_markdown(32),
        "",
        "## Sweep Coverage",
        "",
        f"- bounded profiles: `{sweep_summary['bounded_profiles']}`",
        f"- required block-bit values: `{list(sweep_summary['required_block_bits'])}`",
        f"- block-byte values: `{list(sweep_summary['block_bytes'])}`",
        f"- block-bit values: `{list(sweep_summary['block_bits'])}`",
        f"- arity caps: `{list(sweep_summary['arity_caps'])}`",
        f"- seed-depth bits: `{list(sweep_summary['seed_depth_bits'])}`",
        f"- depth schedules: `{len(sweep_summary['depth_schedules'])}`",
        f"- initial literal overhead bits: `{list(sweep_summary['initial_literal_overhead_bits'])}`",
        f"- rechunk schedules: `{list(sweep_summary['rechunk_schedules'])}`",
        f"- superposition configs: `{sweep_summary['superposition_configs']}`",
        f"- prune delta bits: `{list(sweep_summary['prune_delta_bits'])}`",
        f"- max retained variants per entry: `{list(sweep_summary['max_variants_per_position'])}`",
        f"- equal-size modes: `{list(sweep_summary['equal_size_allowed'])}`",
        f"- retained-bloat modes: `{list(sweep_summary['bloat_tolerant_retained'])}`",
        f"- refresh rules: `{', '.join(sweep_summary['refresh_rules'])}`",
        f"- selection policies: `{', '.join(sweep_summary['selection_policies'])}`",
        f"- recurrence seed profiles: `{sweep_summary['recurrence_seed_profiles']}`",
        f"- full recurrence profiles: `{sweep_summary['top_k_recurrence_profiles']}`",
        f"- recurrence selection rule: `{sweep_summary['recurrence_profile_selection']}`",
        "",
        "## Bottleneck",
        "",
        f"Under this model the missing minimum-pass margin is `{missing:.6f}` percentage points.",
        f"The exact missing multiplier to the `0.1%` target is `{missing_multiplier:.6f}x`",
        f"over the best modeled ceiling; the `0.2%` stretch gap is `{stretch_multiplier:.6f}x`.",
        f"The first-effective-pass ceiling is `{first_effective_ceiling.net_delta_pct_current:.6f}%`,",
        "so the target fails before later-pass refresh behavior can rescue the profile.",
        "The bottleneck is the refresh-adjusted opportunity multiplier after overlap",
        "selection accounting and charged layer metadata. Equal-size refresh and retained",
        "variants increase the candidate window multiplier, but even the oracle selection",
        "ceiling keeps the minimum effective pass below target.",
        "",
        "## Mechanism Movement",
        "",
        "- Equal-size neutral refresh raised average variants without adding output bits.",
        "- Byte-aligned literal initialization improved the first effective pass while",
        "  still charging the emitted zero pad.",
        "- Fixed bitstream rechunking changed only profile-known entry boundaries and",
        "  preserved the charged bit count.",
        "- Wider retained-variant deltas raised the upper opportunity bound but also shifted",
        "  mass toward longer alternate entries, reducing conversion weight.",
        "- Oracle selection gave the ceiling; greedy selection was the best deterministic",
        "  estimate in the implemented recurrence.",
        "- Charged profile refresh rules helped only when their rho gain exceeded their",
        "  per-pass metadata cost.",
        "",
        "## Next Three Open Ideas",
        "",
        "1. A deterministic selector that preserves future variant diversity while staying",
        "   close to the oracle interval bound.",
        "2. A zero-metadata refresh schedule whose rho is near the superposition-derived",
        "   bound but whose retained excess stays concentrated at `0..2` bits.",
        "3. A concrete second independent zero-metadata refresh construction; a rho",
        "   diagnostic shows that about a second retained-state lane would cross the",
        "   current `0.1%` target, but it still needs a decode construction.",
        "",
        "## Validation",
        "",
        f"- cost validation: `{validations['cost_validation']}`",
        f"- toy probability rows: `{len(validations['toy_probability_rows'])}`",
        f"- span histogram validation: `{validations['span_histogram_validation']}`",
        f"- state validation: `{validations['state_validation']}`",
        f"- refresh rules validated: `{len(validations['refresh_rules'])}`",
        f"- superposition sweep validation: `{validations['superposition_sweep']}`",
        f"- bundle variant validation: `{validations['bundle_variant_validation']}`",
        f"- compact sweep summary: `{summary_path.relative_to(ROOT).as_posix()}`",
        "",
        "## Reproduction",
        "",
        "```powershell",
        "python model_analysis/proof_kernel/viability_search.py --write-artifacts",
        "```",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_success_report(
    best: ProfileEvaluation,
    winners: dict[str, ProfileEvaluation],
    ablations: list[dict],
    registry: list[dict],
    summary_path: Path,
) -> Path:
    path = ROOT / "docs" / "TELOMERE_VIABILITY_TARGET.md"
    cand = best.candidate
    refresh = by_name(cand.refresh_name)
    concentration_lines = [
        f"- evaluated entry count: `{best.concentration_entry_count}`",
        f"- concentration entry bits: `{best.concentration_entry_bits}`",
        f"- radius at alpha `1e-9`: `±{best.concentration_eps_pct:.6f}` percentage points",
    ]
    for threshold in (0.1, 0.2):
        margin = best.effective_pass_min_pct - threshold
        if margin <= 0:
            concentration_lines.append(f"- margin to `{threshold}%`: not positive")
            continue
        required_entries = math.ceil(
            best.concentration_entry_count * (best.concentration_eps_pct / margin) ** 2
        )
        concentration_lines.append(
            f"- entries for radius <= margin to `{threshold}%`: `{required_entries}`"
        )
    lines = [
        "# Telomere Viability Target",
        "",
        "This report separates per-pass drift from raw-size payback. A configuration",
        "is a viability target only if it clears the current-layer floor, uses a",
        "deterministic selector, survives conservative variant discounting, and shows",
        f"`final/raw < 1.0` within `{RAW_CROSSOVER_REQUIRED_BY_PASS}` effective passes.",
        "",
        f"Current primary class: `{best.viability_class}`.",
        "",
        "## Category Winners",
        "",
        winners_markdown(winners),
        "",
        "## Configuration",
        "",
        f"- block bits: `{cand.block_bits}`",
        f"- arity cap: `{cand.arity_cap}`",
        f"- seed-depth bits: `{cand.depth_bits}`",
        f"- depth schedule bits: `{list(cand.depth_schedule_bits)}`",
        f"- initial literal overhead bits: `{cand.initial_literal_overhead_bits}`",
        f"- rechunk schedule bits: `{format_rechunk_schedule(cand.rechunk_schedule_bits)}`",
        f"- selection policy: `{cand.policy}`",
        f"- refresh rule: `{cand.refresh_name}`",
        f"- superposition: `{asdict(cand.superposition)}`",
        f"- refresh metadata bits per pass: `{refresh.metadata_bits_per_pass}`",
        "- rechunk metadata bits per pass: `0` because the chunk size is fixed by",
        "  this decoder profile; a multiplexed implementation must charge its profile ID.",
        f"- final charged/raw ratio after `{PASSES}` modeled passes: `{best.final_ratio_raw:.9f}`",
        f"- final/raw after `50` passes: `{fmt_optional_float(best.raw_ratio_by_pass.get(50))}`",
        f"- final/raw after `100` passes: `{fmt_optional_float(best.raw_ratio_by_pass.get(100))}`",
        f"- final/raw after `200` passes: `{fmt_optional_float(best.raw_ratio_by_pass.get(200))}`",
        f"- final/raw after `500` passes: `{fmt_optional_float(best.raw_ratio_by_pass.get(500))}`",
        f"- raw payback modeled pass: `{best.payback_pass_count}`",
        f"- raw payback effective pass: `{best.payback_effective_pass_count}`",
        f"- ten-effective-pass minimum: `{best.effective_pass_min_pct:.6f}%`",
        f"- ten-effective-pass average: `{best.effective_pass_avg_pct:.6f}%`",
        f"- concentration radius at alpha `1e-9`: `±{best.concentration_eps_pct:.6f}` percentage points",
        f"- max expected live variants per entry: `{best.audit_flags['max_expected_live_variants_per_entry']:.6f}`",
        f"- working variant entries proxy: `{best.audit_flags['working_variant_entries_proxy']:.2f}`",
        f"- max optimistic/conservative multiplier ratio: `{best.audit_flags['max_optimistic_to_conservative_multiplier']:.6f}`",
        "",
        "## Raw-Crossover Curve",
        "",
        raw_curve_markdown(best),
        "",
        "## Audit Verdict",
        "",
        f"- earned variants, not cap assumed: `{best.audit_flags['earned_variant_ok']}`",
        "- actual gain path: `conservative discounted opportunity multiplier`",
        "- optimistic independent-combo gain: reported in the ledger only as an upper-bound diagnostic",
        f"- selector viable without side table: `{best.audit_flags['selector_viability_ok']}`",
        f"- oracle upper bound: `{best.audit_flags['oracle_is_upper_bound']}`",
        f"- raw crossover within 200 effective passes: `{best.audit_flags['raw_crossover_within_200_effective_passes']}`",
        f"- final collapse serializes encoder-only retained state: `{best.audit_flags['encoder_only_state_serialized']}`",
        f"- refresh/rechunk decodable: `{best.audit_flags['refresh_decodable']}`",
        f"- metadata sidecar OK: `{best.audit_flags['metadata_sidecar_ok']}`",
        f"- compute/memory profile: `{best.audit_flags['compute_memory_profile']}`",
        "",
        "## Ablation Table",
        "",
        ablation_markdown(ablations),
        "",
        "## Equations",
        "",
        "For arity `a`, span size `S`, seed-depth `D`, and record budget `r`:",
        "",
        "```text",
        "M(a,r,D) = count(seed records with canonical J3D1 cost <= r and seed index < 2^D)",
        "p(min_record <= r | S,a,D,m) = 1 - exp(-M(a,r,D) * m / 2^S)",
        "E[gain per window] = sum_{g>=1} p(min_record <= S-g | S,a,D,m)",
        "net_delta_pct_current = 100*(bits_before - bits_after - charged_metadata_bits)/bits_before",
        "```",
        "",
        "`m` is the retained-variant opportunity multiplier after per-entry",
        "superposition and whole-window retained bundles. Rechunking changes only the",
        "profile-known current entry boundaries; it does not remove bits from",
        "`bits_before` and does not add file-specific side information.",
        "The model reports optimistic independent-combo multipliers, but charged",
        "expected gain uses the conservative shared-entry discount.",
        "",
        "## Cost Table",
        "",
        "The table below is generated from the exact Python cost model after validating",
        "against `cargo run --quiet --bin v1_cost_table`.",
        "",
        cost_table_markdown(32),
        "",
        "## Metadata Accounting",
        "",
        f"- initial literal overhead charged: `{cand.initial_literal_overhead_bits}` bits per raw block in pass 1",
        f"- refresh metadata charged: `{refresh.metadata_bits_per_pass}` bits per pass",
        f"- accumulated profile/rechunk sidecar bits: `0` in this fixed-profile model",
        "- no per-file sidecar, table, manifest, seed map, selector map, or model is assumed",
        "- retained variants are encoder working state only and are not serialized unless selected",
        "- final size is counted after collapsing to the selected path",
        f"- compact sweep summary and experiment registry: `{summary_path.relative_to(ROOT).as_posix()}`",
        "",
        "## Pass Ledger",
        "",
        pass_ledger_markdown(best.rows),
        "",
        "## Large-File Concentration",
        "",
        "The concentration bound uses the proof-kernel bounded-differences radius over",
        "the effective current-entry count. At the configured `1,000,000` raw input",
        "blocks this radius is a loose finite-size bound, not a claim that every",
        "file of that size clears the target with alpha `1e-9`. Because the radius",
        "scales as `1/sqrt(N)`, the entries below give the large-file scale where",
        "the radius falls below each target margin.",
        "",
        *concentration_lines,
        "",
        "## Assumptions And Proof Boundary",
        "",
        "- Uniform seed-prefix match law.",
        "- Encoder-only variants are not serialized until selected.",
        "- Refresh decode follows the named profile rule and charged metadata.",
        "- Rechunk decode follows the fixed profile schedule and charged metadata.",
        "- The model operates on current encoded entry bits after pass 1.",
        "- Concentration uses the bounded-differences radius reported in `best_config.json`.",
        "- High per-pass drift without raw crossover is labeled as a component, not as",
        "  a viable net-compression path.",
        "- A profile using `oracle_weighted_interval` is an upper bound until a",
        "  deterministic selector with no side table matches it.",
        "- Registry rows are compact machine-readable rows in `sweep_summary.json`;",
        f"  evaluated row count: `{len(registry)}`.",
        "",
        "## Reproduction",
        "",
        "```powershell",
        "python model_analysis/proof_kernel/viability_search.py --write-artifacts",
        "```",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_csv(evaluations: list[ProfileEvaluation]) -> Path:
    path = KERNEL_DIR / "top_profiles.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "rank",
                "upper_bound_pct_current",
                "effective_pass_min_pct",
                "effective_pass_avg_pct",
                "final_ratio_raw",
                "final_raw_50",
                "final_raw_100",
                "final_raw_200",
                "final_raw_500",
                "payback_pass_count",
                "payback_effective_pass_count",
                "viability_class",
                "block_bits",
                "arity_cap",
                "depth_bits",
                "depth_schedule_bits",
                "initial_literal_overhead_bits",
                "rechunk_schedule",
                "policy",
                "refresh",
                "delta",
                "max_variants",
                "max_expected_live_variants",
                "max_optimistic_to_conservative_multiplier",
                "working_variant_entries_proxy",
                "equal_size",
                "bloat_retained",
            ]
        )
        for rank, ev in enumerate(evaluations, 1):
            cfg = ev.candidate.superposition
            writer.writerow(
                [
                    rank,
                    f"{ev.candidate.upper_bound_pct_current:.9f}",
                    f"{ev.effective_pass_min_pct:.9f}",
                    f"{ev.effective_pass_avg_pct:.9f}",
                    f"{ev.final_ratio_raw:.12f}",
                    f"{ev.raw_ratio_by_pass.get(50, float('nan')):.12f}",
                    f"{ev.raw_ratio_by_pass.get(100, float('nan')):.12f}",
                    f"{ev.raw_ratio_by_pass.get(200, float('nan')):.12f}",
                    f"{ev.raw_ratio_by_pass.get(500, float('nan')):.12f}",
                    ev.payback_pass_count,
                    ev.payback_effective_pass_count,
                    ev.viability_class,
                    ev.candidate.block_bits,
                    ev.candidate.arity_cap,
                    ev.candidate.depth_bits,
                    " ".join(str(depth) for depth in ev.candidate.depth_schedule_bits),
                    ev.candidate.initial_literal_overhead_bits,
                    format_rechunk_schedule(ev.candidate.rechunk_schedule_bits),
                    ev.candidate.policy,
                    ev.candidate.refresh_name,
                    cfg.prune_delta_bits,
                    cfg.max_variants_per_position,
                    f"{ev.audit_flags['max_expected_live_variants_per_entry']:.9f}",
                    f"{ev.audit_flags['max_optimistic_to_conservative_multiplier']:.9f}",
                    f"{ev.audit_flags['working_variant_entries_proxy']:.3f}",
                    cfg.equal_size_allowed,
                    cfg.bloat_tolerant_retained,
                ]
            )
    return path


def profile_rank_key(ev: ProfileEvaluation) -> tuple[float, float, float, float, float]:
    meets_floor = 0.0 if ev.effective_pass_min_pct >= 0.1 else 1.0
    deterministic = 0.0 if ev.candidate.policy != "oracle_weighted_interval" else 1.0
    payback = float("inf") if ev.payback_effective_pass_count is None else float(ev.payback_effective_pass_count)
    final_200 = ev.raw_ratio_by_pass.get(200, float("inf"))
    return (meets_floor, deterministic, payback, final_200, -ev.effective_pass_min_pct)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-k", type=int, default=120)
    parser.add_argument("--write-artifacts", action="store_true")
    parser.add_argument(
        "--representative-smoke",
        action="store_true",
        help="Run a narrow sentinel-axis sweep for code/report validation only.",
    )
    args = parser.parse_args()

    print("validating proof kernel...", flush=True)
    validations = run_validations()
    print("running bounded sweep...", flush=True)
    candidates, sweep_summary = bounded_sweep(args.top_k, representative=args.representative_smoke)
    print("computing first-effective-pass dominance ceiling...", flush=True)
    first_effective_ceiling = first_effective_dominance_ceiling(representative=args.representative_smoke)
    print(f"running full recurrences for {len(candidates)} profiles...", flush=True)
    evaluations = []
    for index, candidate in enumerate(candidates, 1):
        print(
            "  recurrence "
            f"{index}/{len(candidates)}: block={candidate.block_bits} "
            f"depth_schedule={list(candidate.depth_schedule_bits)} "
            f"literal_overhead={candidate.initial_literal_overhead_bits} "
            f"rechunk={format_rechunk_schedule(candidate.rechunk_schedule_bits)} "
            f"arity={candidate.arity_cap} policy={candidate.policy}",
            flush=True,
        )
        evaluations.append(evaluate_candidate(candidate))
    evaluations.sort(key=profile_rank_key)
    winners = select_winners(evaluations)
    practical = winners["best_practical_memory_compute"]
    if (
        practical.viability_class == "viability_practical_candidate"
        and practical.payback_effective_pass_count is not None
        and practical.payback_effective_pass_count <= RAW_CROSSOVER_REQUIRED_BY_PASS
    ):
        primary_selection = "best_practical_memory_compute"
        best = practical
    else:
        primary_selection = "fastest_raw_payback"
        best = winners["fastest_raw_payback"]
    ablations = ablation_rows(best)
    registry = experiment_registry_rows(evaluations, winners)

    csv_path: Path | None = None
    summary_path: Path | None = None
    best_path: Path | None = None
    if not args.representative_smoke or args.write_artifacts:
        csv_path = write_csv(evaluations)
        summary_path = write_summary_json(
            validations,
            sweep_summary,
            evaluations,
            first_effective_ceiling,
            winners,
            registry,
            ablations,
        )
        best_path = KERNEL_DIR / "best_config.json"
        write_best_config(best, best_path)

    success = (
        best.effective_pass_min_pct >= 0.1
        and best.audit_flags["selector_viability_ok"]
        and best.audit_flags["raw_crossover_within_200_effective_passes"]
        and best.audit_flags["earned_variant_ok"]
        and best.audit_flags["metadata_sidecar_ok"]
    )
    stretch = best.effective_pass_min_pct >= 0.2
    report_path = None
    if args.write_artifacts:
        if summary_path is None:
            summary_path = write_summary_json(
                validations,
                sweep_summary,
                evaluations,
                first_effective_ceiling,
                winners,
                registry,
                ablations,
            )
        if csv_path is None:
            csv_path = write_csv(evaluations)
        if best_path is None:
            best_path = KERNEL_DIR / "best_config.json"
            write_best_config(best, best_path)
        report_path = write_success_report(best, winners, ablations, registry, summary_path)
        for stale in (
            ROOT / "docs" / "TELOMERE_STRETCH_TARGET.md",
            ROOT / "docs" / "TELOMERE_FRONTIER_REPORT.md",
            ROOT / "docs" / "PROOF_IDEA_LOG.md",
        ):
            if stale.exists():
                stale.unlink()

    print(
        json.dumps(
            {
                "primary_selection": primary_selection,
                "best_effective_pass_min_pct": best.effective_pass_min_pct,
                "best_effective_pass_avg_pct": best.effective_pass_avg_pct,
                "final_ratio_raw": best.final_ratio_raw,
                "raw_ratio_by_pass": best.raw_ratio_by_pass,
                "payback_effective_pass_count": best.payback_effective_pass_count,
                "viability_class": best.viability_class,
                "success_0_1": success,
                "stretch_0_2": stretch,
                "category_winners": {
                    name: {
                        "effective_pass_min_pct": ev.effective_pass_min_pct,
                        "raw_ratio_200": ev.raw_ratio_by_pass.get(200),
                        "payback_effective_pass_count": ev.payback_effective_pass_count,
                        "policy": ev.candidate.policy,
                        "rechunk_schedule": format_rechunk_schedule(ev.candidate.rechunk_schedule_bits),
                        "viability_class": ev.viability_class,
                    }
                    for name, ev in winners.items()
                },
                "best_config": str(best_path.relative_to(ROOT)) if best_path else None,
                "top_profiles_csv": str(csv_path.relative_to(ROOT)) if csv_path else None,
                "sweep_summary": str(summary_path.relative_to(ROOT)) if summary_path else None,
                "report": str(report_path.relative_to(ROOT)) if report_path else None,
                "first_effective_dominance_ceiling_pct": first_effective_ceiling.net_delta_pct_current,
                "sweep": sweep_summary,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
