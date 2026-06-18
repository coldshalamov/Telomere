#!/usr/bin/env python3
"""H126 - one paid raw segment for markerless fallback atoms.

H125's fixed modulo raw lanes are parseable but too rigid. This kernel tests
the user's delineation idea more directly:

    [record region][raw atom segment][record region]...

The raw segments are markerless, but their start/end boundaries are paid once
per layer. This is a middle ground between H124's magic markerless raw atoms
and a full bitmap of raw positions.
"""

from __future__ import annotations

import argparse
import importlib.util
import math
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean

H125_PATH = Path(__file__).with_name("H125-public_raw_lane_repair.py")
H125_SPEC = importlib.util.spec_from_file_location("h125_public_raw_lane", H125_PATH)
if H125_SPEC is None or H125_SPEC.loader is None:
    raise RuntimeError(f"could not load {H125_PATH}")
h125 = importlib.util.module_from_spec(H125_SPEC)
sys.modules[H125_SPEC.name] = h125
H125_SPEC.loader.exec_module(h125)
h123 = h125.h123
h116 = h125.h116
h115 = h125.h115


@dataclass(frozen=True)
class StepStats:
    delta_bits: float
    input_bits: int
    output_bits: int
    boundary_bits: float
    rewritten_raw_bits: int
    selected_records: int
    due_records_seen: int
    due_records_covered: int
    expired_records: int
    expiry_tax_bits: int
    padding_bits: int
    raw_items: int
    record_items: int


@dataclass(frozen=True)
class Row:
    config_name: str
    context_name: str
    quantile: float
    atoms: int
    passes: int
    trials: int
    min_rewrite: float
    boundary_mode: str
    max_segments: int
    delta_per_atom: float
    delta_per_atom_pass: float
    boundary_bits_per_atom_pass: float
    selected_records_per_atom_pass: float
    expired_records_per_atom_pass: float
    expiry_tax_per_atom_pass: float
    avg_rewrite_fraction: float
    due_cover_rate: float
    padding_bits_per_selected: float
    raw_fraction: float
    fail_rate: float
    fallback_gap: int
    avg_table_gap: float
    table_entries: int


def segment_boundary_bits(output_items: int, boundary_mode: str, max_segments: int) -> float:
    if boundary_mode == "free":
        return 0.0
    if boundary_mode == "paid_segment":
        # Choose up to S nonempty contiguous raw segments among N items.
        # The number of binary masks with exactly s runs of 1s is C(N+1, 2s).
        count = 1
        for segments in range(1, max_segments + 1):
            if 2 * segments <= output_items + 1:
                count += math.comb(output_items + 1, 2 * segments)
        return math.log2(count)
    raise ValueError(boundary_mode)


def is_raw_outputs(config: h115.Config, outputs: list[h115.Item]) -> bool:
    return all(h125.is_markerless_raw_atom(config, item) for item in outputs)


def is_record_outputs(config: h115.Config, outputs: list[h115.Item]) -> bool:
    return all(not h125.is_markerless_raw_atom(config, item) for item in outputs)


def select_step(
    config: h115.Config,
    items: list[h115.Item],
    slack: int,
    min_rewrite_raw_fraction: float,
    seed: int,
    table: h125.GapTable | None,
    boundary_mode: str,
    max_segments: int,
    collect_edges: bool = False,
) -> tuple[list[h115.Item] | None, StepStats, list[h116.RichEdge]]:
    edges_by_start = h123.sample_edges(config, items, slack, seed)
    total_raw = sum(item.raw_bits for item in items)
    due_seen = sum(1 for item in items if item.record_age == 1)
    n = len(items)
    # State: (raw_done, segments_started, in_raw_segment).
    dp: list[dict[tuple[int, int, int], float]] = [dict() for _ in range(n + 1)]
    prev: dict[
        tuple[int, int, int, int],
        tuple[int, int, int, int, str, h116.RichEdge | None, list[h115.Item], int, int, int],
    ] = {}
    dp[0][(0, 0, 0)] = 0.0

    def update(
        end: int,
        raw_done: int,
        segments_started: int,
        in_raw: int,
        candidate: float,
        prior: tuple[int, int, int, int, str, h116.RichEdge | None, list[h115.Item], int, int, int],
    ) -> None:
        key = (raw_done, segments_started, in_raw)
        if candidate < dp[end].get(key, float("inf")):
            dp[end][key] = candidate
            prev[(end, raw_done, segments_started, in_raw)] = prior

    for pos in range(n):
        for (raw_done, segments_started, in_raw), base in list(dp[pos].items()):
            skip_delta, outputs, expired, tax = h125.raw_atom_outputs(config, items[pos])
            if math.isfinite(skip_delta) and is_raw_outputs(config, outputs):
                if in_raw:
                    update(
                        pos + 1,
                        raw_done,
                        segments_started,
                        1,
                        base + skip_delta,
                        (pos, raw_done, segments_started, in_raw, "skip", None, outputs, expired, tax, 0),
                    )
                elif segments_started < max_segments:
                    update(
                        pos + 1,
                        raw_done,
                        segments_started + 1,
                        1,
                        base + skip_delta,
                        (pos, raw_done, segments_started, in_raw, "skip", None, outputs, expired, tax, 0),
                    )
            elif math.isfinite(skip_delta) and is_record_outputs(config, outputs):
                update(
                    pos + 1,
                    raw_done,
                    segments_started,
                    0,
                    base + skip_delta,
                    (pos, raw_done, segments_started, in_raw, "skip", None, outputs, expired, tax, 0),
                )

            for edge in edges_by_start[pos]:
                if table is None:
                    delta = edge.local_delta
                    width = edge.payload_width
                    padding = 0
                else:
                    gap = h125.gap_for(table, edge)
                    if not h123.is_gap_candidate(edge, gap):
                        continue
                    delta = h123.gap_delta(edge, gap)
                    width = edge.target_bits - gap
                    padding = width - edge.payload_width
                end = pos + edge.arity
                new_raw = min(total_raw, raw_done + edge.raw_bits)
                output = [h115.Item(bits=edge.arity_bits + width, raw_bits=edge.raw_bits, record_age=0)]
                update(
                    end,
                    new_raw,
                    segments_started,
                    0,
                    base + delta,
                    (pos, raw_done, segments_started, in_raw, "edge", edge, output, 0, 0, padding),
                )

    min_raw = math.ceil(total_raw * min_rewrite_raw_fraction)
    best_key: tuple[int, int, int] | None = None
    best_delta = float("inf")
    for (raw_done, segments_started, in_raw), delta in dp[n].items():
        if raw_done >= min_raw and delta < best_delta:
            best_delta = delta
            best_key = (raw_done, segments_started, in_raw)
    if best_key is None:
        input_bits = sum(item.bits for item in items)
        return None, StepStats(float("inf"), input_bits, input_bits, 0.0, 0, 0, due_seen, 0, 0, 0, 0, 0, 0), []

    output_chunks: list[list[h115.Item]] = []
    selected = 0
    due_covered = 0
    expired_records = 0
    expiry_tax = 0
    padding_bits = 0
    raw_items = 0
    record_items = 0
    selected_edges: list[h116.RichEdge] = []
    pos = n
    raw, segments_started, in_raw = best_key
    while pos > 0:
        entry = prev[(pos, raw, segments_started, in_raw)]
        prior_pos, prior_raw, prior_segments, prior_in_raw, kind, edge, outputs, expired, tax, padding = entry
        for item in outputs:
            if h125.is_markerless_raw_atom(config, item):
                raw_items += 1
            else:
                record_items += 1
        output_chunks.append(outputs)
        if kind == "edge":
            selected += 1
            padding_bits += padding
            if edge is None:
                raise AssertionError("selected edge missing")
            due_covered += edge.old_count
            if collect_edges:
                selected_edges.append(edge)
        expired_records += expired
        expiry_tax += tax
        pos = prior_pos
        raw = prior_raw
        segments_started = prior_segments
        in_raw = prior_in_raw

    next_items = [item for chunk in reversed(output_chunks) for item in chunk]
    output_count = len(next_items)
    boundary_bits = segment_boundary_bits(output_count, boundary_mode, max_segments)
    input_bits = sum(item.bits for item in items)
    output_bits = sum(item.bits for item in next_items)
    selected_edges.reverse()
    return next_items, StepStats(
        delta_bits=best_delta + boundary_bits,
        input_bits=input_bits,
        output_bits=output_bits,
        boundary_bits=boundary_bits,
        rewritten_raw_bits=best_key[0],
        selected_records=selected,
        due_records_seen=due_seen,
        due_records_covered=due_covered,
        expired_records=expired_records,
        expiry_tax_bits=expiry_tax,
        padding_bits=padding_bits,
        raw_items=raw_items,
        record_items=record_items,
    ), selected_edges


def collect_local_edges(
    config: h115.Config,
    slack: int,
    passes: int,
    seed: int,
    min_rewrite_raw_fraction: float,
    max_segments: int,
) -> list[h116.RichEdge]:
    items = h115.initial_items(config)
    edges: list[h116.RichEdge] = []
    for step in range(passes):
        next_items, _stats, selected = select_step(
            config,
            items,
            slack,
            min_rewrite_raw_fraction,
            seed + step * 1_000_003,
            None,
            "free",
            max_segments,
            collect_edges=True,
        )
        if next_items is None:
            break
        edges.extend(selected)
        items = next_items
    return edges


def fit_table(
    config: h115.Config,
    slack: int,
    context: h123.ContextSpec,
    quantile: float,
    passes: int,
    train_trials: int,
    seed: int,
    min_rewrite_raw_fraction: float,
    max_segments: int,
) -> h125.GapTable:
    buckets: dict[tuple[int, ...], list[int]] = defaultdict(list)
    all_gaps: list[int] = []
    for trial in range(train_trials):
        edges = collect_local_edges(
            config,
            slack,
            passes,
            seed + trial * 1_000_003,
            min_rewrite_raw_fraction,
            max_segments,
        )
        for edge in edges:
            gap = h123.actual_gap(edge)
            buckets[h123.context_for(context, edge)].append(gap)
            all_gaps.append(gap)
    fallback = h123.quantile_gap(all_gaps, quantile)
    gaps = {key: h123.quantile_gap(values, quantile) for key, values in buckets.items()}
    return h125.GapTable(context=context, gaps=gaps, fallback_gap=fallback, quantile=quantile)


@dataclass(frozen=True)
class TrialStats:
    failed: bool
    delta_per_atom: float
    delta_per_atom_pass: float
    boundary_bits_per_atom_pass: float
    selected_per_atom_pass: float
    expired_per_atom_pass: float
    expiry_tax_per_atom_pass: float
    avg_rewrite_fraction: float
    due_cover_rate: float
    padding_per_selected: float
    raw_fraction: float


def simulate_trial(
    config: h115.Config,
    slack: int,
    table: h125.GapTable,
    boundary_mode: str,
    max_segments: int,
    passes: int,
    seed: int,
    min_rewrite_raw_fraction: float,
) -> TrialStats:
    items = h115.initial_items(config)
    raw_atoms = sum(item.raw_bits for item in items) / config.block_bits
    total_delta = 0.0
    boundary_bits = 0.0
    selected = 0
    due_seen = 0
    due_covered = 0
    expired = 0
    expiry_tax = 0
    padding = 0
    raw_items = 0
    record_items = 0
    rewrite_fracs: list[float] = []
    for step in range(passes):
        total_raw = sum(item.raw_bits for item in items)
        next_items, stats, _selected_edges = select_step(
            config,
            items,
            slack,
            min_rewrite_raw_fraction,
            seed + step * 1_000_003,
            table,
            boundary_mode,
            max_segments,
        )
        if next_items is None:
            return TrialStats(True, float("inf"), float("inf"), 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        total_delta += stats.delta_bits
        boundary_bits += stats.boundary_bits
        selected += stats.selected_records
        due_seen += stats.due_records_seen
        due_covered += stats.due_records_covered
        expired += stats.expired_records
        expiry_tax += stats.expiry_tax_bits
        padding += stats.padding_bits
        raw_items += stats.raw_items
        record_items += stats.record_items
        rewrite_fracs.append(stats.rewritten_raw_bits / max(1, total_raw))
        items = next_items
    return TrialStats(
        False,
        total_delta / raw_atoms,
        total_delta / raw_atoms / passes,
        boundary_bits / raw_atoms / passes,
        selected / raw_atoms / passes,
        expired / raw_atoms / passes,
        expiry_tax / raw_atoms / passes,
        mean(rewrite_fracs) if rewrite_fracs else 0.0,
        1.0 if due_seen == 0 else due_covered / due_seen,
        padding / max(1, selected),
        raw_items / max(1, raw_items + record_items),
    )


def evaluate(
    config: h115.Config,
    slack: int,
    context: h123.ContextSpec,
    quantile: float,
    boundary_mode: str,
    max_segments: int,
    passes: int,
    train_trials: int,
    eval_trials: int,
    seed: int,
    min_rewrite_raw_fraction: float,
) -> Row:
    table = fit_table(
        config,
        slack,
        context,
        quantile,
        passes,
        train_trials,
        seed,
        min_rewrite_raw_fraction,
        max_segments,
    )
    trials = [
        simulate_trial(
            config,
            slack,
            table,
            boundary_mode,
            max_segments,
            passes,
            seed + 99_999_937 + trial * 1_000_003,
            min_rewrite_raw_fraction,
        )
        for trial in range(eval_trials)
    ]
    finite = [trial for trial in trials if not trial.failed]
    fail_rate = 1.0 - len(finite) / len(trials)
    table_gaps = list(table.gaps.values())
    if not finite:
        return Row(
            config.name,
            context.name,
            quantile,
            config.atoms,
            passes,
            eval_trials,
            min_rewrite_raw_fraction,
            boundary_mode,
            max_segments,
            float("inf"),
            float("inf"),
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            fail_rate,
            table.fallback_gap,
            mean(table_gaps) if table_gaps else float(table.fallback_gap),
            len(table.gaps),
        )
    return Row(
        config.name,
        context.name,
        quantile,
        config.atoms,
        passes,
        eval_trials,
        min_rewrite_raw_fraction,
        boundary_mode,
        max_segments,
        mean(trial.delta_per_atom for trial in finite),
        mean(trial.delta_per_atom_pass for trial in finite),
        mean(trial.boundary_bits_per_atom_pass for trial in finite),
        mean(trial.selected_per_atom_pass for trial in finite),
        mean(trial.expired_per_atom_pass for trial in finite),
        mean(trial.expiry_tax_per_atom_pass for trial in finite),
        mean(trial.avg_rewrite_fraction for trial in finite),
        mean(trial.due_cover_rate for trial in finite),
        mean(trial.padding_per_selected for trial in finite),
        mean(trial.raw_fraction for trial in finite),
        fail_rate,
        table.fallback_gap,
        mean(table_gaps) if table_gaps else float(table.fallback_gap),
        len(table.gaps),
    )


def format_float(value: float) -> str:
    if math.isinf(value):
        return "inf"
    return f"{value:.6f}"


def print_rows(rows: list[Row]) -> None:
    print(
        "config,context,q,boundary,max_segments,atoms,passes,trials,min_rewrite,"
        "delta/atom,delta/atom/pass,boundary/atom/pass,sel/atom/pass,"
        "expired/atom/pass,expiry_tax/atom/pass,rewrite_frac,due_cover,"
        "padding/sel,raw_frac,fail,fallbackG,avgG,entries"
    )
    for row in rows:
        print(
            f"{row.config_name},{row.context_name},{row.quantile:.2f},"
            f"{row.boundary_mode},{row.max_segments},{row.atoms},{row.passes},{row.trials},"
            f"{row.min_rewrite:.3f},{format_float(row.delta_per_atom)},"
            f"{format_float(row.delta_per_atom_pass)},"
            f"{format_float(row.boundary_bits_per_atom_pass)},"
            f"{format_float(row.selected_records_per_atom_pass)},"
            f"{format_float(row.expired_records_per_atom_pass)},"
            f"{format_float(row.expiry_tax_per_atom_pass)},"
            f"{format_float(row.avg_rewrite_fraction)},"
            f"{format_float(row.due_cover_rate)},"
            f"{format_float(row.padding_bits_per_selected)},"
            f"{format_float(row.raw_fraction)},"
            f"{format_float(row.fail_rate)},"
            f"{row.fallback_gap},{format_float(row.avg_table_gap)},"
            f"{row.table_entries}"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--passes", type=int, default=4)
    parser.add_argument("--train-trials", type=int, default=4)
    parser.add_argument("--eval-trials", type=int, default=8)
    parser.add_argument("--seed", type=int, default=126_001)
    parser.add_argument("--slack", type=int, default=4)
    parser.add_argument("--atoms", type=int, default=128)
    parser.add_argument("--min-rewrite-raw-frac", type=float, default=0.25)
    parser.add_argument("--quantile", type=float, action="append", default=[])
    parser.add_argument("--boundary-mode", action="append", default=[])
    parser.add_argument("--max-segments", type=int, action="append", default=[])
    parser.add_argument("--config-filter", action="append", default=[])
    parser.add_argument("--context-filter", action="append", default=[])
    args = parser.parse_args()

    configs = h116.default_configs(args.atoms)
    if args.config_filter:
        wanted_configs = set(args.config_filter)
        configs = [config for config in configs if config.name in wanted_configs]

    contexts = h123.default_contexts(period=16, phase=0)
    if args.context_filter:
        wanted_contexts = set(args.context_filter)
        contexts = [context for context in contexts if context.name in wanted_contexts]

    quantiles = args.quantile or [0.10]
    boundary_modes = args.boundary_mode or ["free", "paid_segment"]
    segment_counts = args.max_segments or [1]
    rows: list[Row] = []
    for config in configs:
        for context in contexts:
            for quantile in quantiles:
                for boundary_mode in boundary_modes:
                    for max_segments in segment_counts:
                        rows.append(
                            evaluate(
                                config=config,
                                slack=args.slack,
                                context=context,
                                quantile=quantile,
                                boundary_mode=boundary_mode,
                                max_segments=max_segments,
                                passes=args.passes,
                                train_trials=args.train_trials,
                                eval_trials=args.eval_trials,
                                seed=args.seed,
                                min_rewrite_raw_fraction=args.min_rewrite_raw_frac,
                            )
                        )
    print_rows(rows)


if __name__ == "__main__":
    main()
