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
from entry_state import PassLedgerRow, run_scheduled_profile, validate_state_recurrence
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
RECHUNK_BITS = (None, 4, 8, 16, 24)
PASSES = 11
ENTRY_COUNT = 1_000_000


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
    rechunk_bits: int | None
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


@dataclass(frozen=True)
class FirstEffectiveCeiling:
    net_delta_pct_current: float
    block_bits: int
    first_pass_depth_bits: int
    depth_bits: int
    depth_schedule_bits: tuple[int, ...]
    initial_literal_overhead_bits: int
    rechunk_bits: int | None
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


def first_effective_dominance_ceiling() -> FirstEffectiveCeiling:
    """Exact two-pass ceiling after monotone dominance reductions.

    A profile cannot meet the 10-effective-pass target unless pass 2, the first
    effective pass after literal wrapping, reaches the target. Under this model,
    these settings dominate their lower alternatives for that ceiling:
    oracle selection, arity cap 5, max variants 16, equal-size and bloat-retained
    alternatives enabled, and the highest-rho zero-metadata refresh rule.
    """

    best: tuple[float, int, int, int, tuple[int, ...], int, int | None, int] | None = None
    refresh = by_name("superposition_derived_refresh")
    for block_bits in BLOCK_BITS:
        for depth_schedule_bits in DEPTH_SCHEDULES:
            for initial_literal_overhead_bits in LITERAL_INIT_OVERHEAD_BITS:
                for rechunk_bits in RECHUNK_BITS:
                    for prune_delta_bits in (0, 1, 2, 4, 8, 16, 32, 64):
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
                            rechunk_bits,
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
                                rechunk_bits,
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
        rechunk_bits=best[6],
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
    rechunk_bits: int | None,
    policy: str,
    refresh: RefreshRule,
    superposition: SuperpositionConfig,
) -> BoundCandidate:
    depth_bits = depth_schedule_bits[-1]
    literal_bits = rechunk_bits or (block_bits + initial_literal_overhead_bits)
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
        rechunk_bits=rechunk_bits,
        policy=policy,
        refresh_name=refresh.name,
        superposition=superposition,
        avg_variants=stat.avg_variants,
        window_multiplier=best_multiplier,
    )


def bounded_sweep(top_k: int) -> tuple[list[BoundCandidate], dict]:
    heap: list[tuple[float, int, BoundCandidate]] = []
    group_best: dict[tuple[str, object], BoundCandidate] = {}
    seen = 0
    seq = 0
    supers = sweep_configs()
    rules = refresh_rules()
    for block_bits in BLOCK_BITS:
        for arity_cap in ARITY_CAPS:
            for depth_schedule_bits in DEPTH_SCHEDULES:
                for initial_literal_overhead_bits in LITERAL_INIT_OVERHEAD_BITS:
                    for rechunk_bits in RECHUNK_BITS:
                        for superposition in supers:
                            for refresh in rules:
                                candidate = bound_one(
                                    block_bits,
                                    arity_cap,
                                    depth_schedule_bits,
                                    initial_literal_overhead_bits,
                                    rechunk_bits,
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
                                    ("rechunk_bits", rechunk_bits),
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
            candidate.rechunk_bits,
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
        "required_block_bits": REQUIRED_BLOCK_BITS,
        "block_bits": BLOCK_BITS,
        "block_bytes": [bits / 8 for bits in BLOCK_BITS],
        "arity_caps": ARITY_CAPS,
        "seed_depth_bits": SEED_DEPTH_BITS,
        "depth_schedules": DEPTH_SCHEDULES,
        "initial_literal_overhead_bits": LITERAL_INIT_OVERHEAD_BITS,
        "rechunk_bits": RECHUNK_BITS,
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


def evaluate_candidate(candidate: BoundCandidate) -> ProfileEvaluation:
    refresh = next(rule for rule in refresh_rules() if rule.name == candidate.refresh_name)
    final, rows = run_scheduled_profile(
        ENTRY_COUNT,
        candidate.block_bits,
        candidate.arity_cap,
        candidate.depth_schedule_bits,
        PASSES,
        candidate.policy,
        candidate.superposition,
        refresh,
        candidate.initial_literal_overhead_bits,
        candidate.rechunk_bits,
    )
    effective = rows[1:] if len(rows) > 1 else rows
    min_pct = min((row.net_delta_pct_current for row in effective), default=0.0)
    avg_pct = sum(row.net_delta_pct_current for row in effective) / max(1, len(effective))
    effective_entry_count = int(min((row.entry_count_before for row in effective), default=ENTRY_COUNT))
    concentration_entry_bits = candidate.rechunk_bits or candidate.block_bits
    concentration = epsilon_for_confidence(
        max(1, effective_entry_count),
        concentration_entry_bits,
        candidate.arity_cap,
    )
    return ProfileEvaluation(
        candidate=candidate,
        final_ratio_raw=final.total_charged_bits / final.original_raw_bits,
        effective_pass_min_pct=min_pct,
        effective_pass_avg_pct=avg_pct,
        rows=rows,
        concentration_eps_pct=100.0 * concentration.epsilon_ratio,
        concentration_entry_count=max(1, effective_entry_count),
        concentration_entry_bits=concentration_entry_bits,
    )


def pass_ledger_markdown(rows: list[PassLedgerRow]) -> str:
    lines = [
        "| pass | depth bits | literal overhead | bits before | bits after | current delta % | raw delta % | accepted windows | avg variants | max multiplier |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row.pass_index} | {row.depth_bits} | {row.literal_overhead_bits} | "
            f"{row.bits_before:.2f} | {row.bits_after:.2f} | "
            f"{row.net_delta_pct_current:.6f} | {row.net_delta_pct_raw:.6f} | "
            f"{row.accepted_windows:.4f} | {row.avg_variants_per_position:.4f} | "
            f"{row.max_window_multiplier:.4f} |"
        )
    return "\n".join(lines)


def write_best_config(evaluation: ProfileEvaluation, path: Path) -> None:
    min_pct = evaluation.effective_pass_min_pct
    payload = {
        "candidate": {
            **asdict(evaluation.candidate),
            "superposition": asdict(evaluation.candidate.superposition),
        },
        "final_ratio_raw": evaluation.final_ratio_raw,
        "effective_pass_min_pct": evaluation.effective_pass_min_pct,
        "effective_pass_avg_pct": evaluation.effective_pass_avg_pct,
        "concentration_eps_pct": evaluation.concentration_eps_pct,
        "concentration_entry_count": evaluation.concentration_entry_count,
        "concentration_entry_bits": evaluation.concentration_entry_bits,
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
) -> Path:
    path = KERNEL_DIR / "sweep_summary.json"
    payload = {
        "validations": validations,
        "sweep_summary": sweep_summary,
        "first_effective_dominance_ceiling": asdict(first_effective_ceiling),
        "top_profiles": [
            {
                "candidate": {
                    **asdict(ev.candidate),
                    "superposition": asdict(ev.candidate.superposition),
                },
                "final_ratio_raw": ev.final_ratio_raw,
                "effective_pass_min_pct": ev.effective_pass_min_pct,
                "effective_pass_avg_pct": ev.effective_pass_avg_pct,
                "concentration_eps_pct": ev.concentration_eps_pct,
                "concentration_entry_count": ev.concentration_entry_count,
                "concentration_entry_bits": ev.concentration_entry_bits,
            }
            for ev in evaluations[:25]
        ],
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
        f"- rechunk bits: `{cand.rechunk_bits}`",
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
        f"- rechunk bits: `{first_effective_ceiling.rechunk_bits}`",
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
        f"- rechunk bits: `{list(sweep_summary['rechunk_bits'])}`",
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


def write_success_report(best: ProfileEvaluation, stretch: bool) -> Path:
    path = ROOT / "docs" / ("TELOMERE_STRETCH_TARGET.md" if stretch else "TELOMERE_VIABILITY_TARGET.md")
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
        "# Telomere Stretch Target" if stretch else "# Telomere Viability Target",
        "",
        "Under this model, the configuration below reaches the stated current-layer",
        "net expected compression target for ten effective passes after charged metadata.",
        "",
        "## Configuration",
        "",
        f"- block bits: `{cand.block_bits}`",
        f"- arity cap: `{cand.arity_cap}`",
        f"- seed-depth bits: `{cand.depth_bits}`",
        f"- depth schedule bits: `{list(cand.depth_schedule_bits)}`",
        f"- initial literal overhead bits: `{cand.initial_literal_overhead_bits}`",
        f"- rechunk bits: `{cand.rechunk_bits}`",
        f"- selection policy: `{cand.policy}`",
        f"- refresh rule: `{cand.refresh_name}`",
        f"- superposition: `{asdict(cand.superposition)}`",
        f"- refresh metadata bits per pass: `{refresh.metadata_bits_per_pass}`",
        "- rechunk metadata bits per pass: `0` because the chunk size is fixed by",
        "  this decoder profile; a multiplexed implementation must charge its profile ID.",
        f"- final charged/raw ratio after `{PASSES}` modeled passes: `{best.final_ratio_raw:.9f}`",
        f"- ten-effective-pass minimum: `{best.effective_pass_min_pct:.6f}%`",
        f"- ten-effective-pass average: `{best.effective_pass_avg_pct:.6f}%`",
        f"- concentration radius at alpha `1e-9`: `±{best.concentration_eps_pct:.6f}` percentage points",
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
                "block_bits",
                "arity_cap",
                "depth_bits",
                "depth_schedule_bits",
                "initial_literal_overhead_bits",
                "rechunk_bits",
                "policy",
                "refresh",
                "delta",
                "max_variants",
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
                    ev.candidate.block_bits,
                    ev.candidate.arity_cap,
                    ev.candidate.depth_bits,
                    " ".join(str(depth) for depth in ev.candidate.depth_schedule_bits),
                    ev.candidate.initial_literal_overhead_bits,
                    ev.candidate.rechunk_bits,
                    ev.candidate.policy,
                    ev.candidate.refresh_name,
                    cfg.prune_delta_bits,
                    cfg.max_variants_per_position,
                    cfg.equal_size_allowed,
                    cfg.bloat_tolerant_retained,
                ]
            )
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-k", type=int, default=120)
    parser.add_argument("--write-artifacts", action="store_true")
    args = parser.parse_args()

    print("validating proof kernel...", flush=True)
    validations = run_validations()
    print("running bounded sweep...", flush=True)
    candidates, sweep_summary = bounded_sweep(args.top_k)
    print("computing first-effective-pass dominance ceiling...", flush=True)
    first_effective_ceiling = first_effective_dominance_ceiling()
    print(f"running full recurrences for {len(candidates)} profiles...", flush=True)
    evaluations = []
    for index, candidate in enumerate(candidates, 1):
        print(
            "  recurrence "
            f"{index}/{len(candidates)}: block={candidate.block_bits} "
            f"depth_schedule={list(candidate.depth_schedule_bits)} "
            f"literal_overhead={candidate.initial_literal_overhead_bits} "
            f"rechunk={candidate.rechunk_bits} "
            f"arity={candidate.arity_cap} policy={candidate.policy}",
            flush=True,
        )
        evaluations.append(evaluate_candidate(candidate))
    evaluations.sort(key=lambda ev: (ev.effective_pass_min_pct, ev.effective_pass_avg_pct), reverse=True)
    best = evaluations[0]

    csv_path = write_csv(evaluations)
    summary_path = write_summary_json(validations, sweep_summary, evaluations, first_effective_ceiling)
    idea_path = write_idea_log()
    best_path = KERNEL_DIR / "best_config.json"
    write_best_config(best, best_path)

    success = best.effective_pass_min_pct >= 0.1
    stretch = best.effective_pass_min_pct >= 0.2
    report_path = None
    if args.write_artifacts:
        if success:
            report_path = write_success_report(best, stretch=False)
            if stretch:
                report_path = write_success_report(best, stretch=True)
        else:
            report_path = write_frontier_report(
                best,
                validations,
                sweep_summary,
                summary_path,
                first_effective_ceiling,
            )

    print(
        json.dumps(
            {
                "best_effective_pass_min_pct": best.effective_pass_min_pct,
                "best_effective_pass_avg_pct": best.effective_pass_avg_pct,
                "final_ratio_raw": best.final_ratio_raw,
                "success_0_1": success,
                "stretch_0_2": stretch,
                "idea_log": str(idea_path.relative_to(ROOT)),
                "best_config": str(best_path.relative_to(ROOT)),
                "top_profiles_csv": str(csv_path.relative_to(ROOT)),
                "sweep_summary": str(summary_path.relative_to(ROOT)),
                "report": str(report_path.relative_to(ROOT)) if report_path else None,
                "first_effective_dominance_ceiling_pct": first_effective_ceiling.net_delta_pct_current,
                "sweep": sweep_summary,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
