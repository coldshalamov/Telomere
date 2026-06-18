#!/usr/bin/env python3
"""H125 - public raw lanes for markerless fallback atoms.

H124 found that frozen public gap tables can stay negative when stale/due
records expire to raw atoms without literal markers. That is still not a
codec unless the decoder can identify those raw atoms.

This kernel makes the raw/not-ready channel public: output item ordinal modulo
`period` determines type. A contiguous raw run of length `raw_run_len` inside
each period carries fixed B-bit raw atoms. Non-raw positions carry records. The
decoder can parse the stream from the root/end header and the public lane
schedule; no per-item literal marker or open/carry bitmap is charged.

This is still a lower-bound geometry target, because the public lane schedule
may waste supply and the typed-board target length is still modeled by the
H123 gap table. The question is whether H124's markerless raw fallback survives
once raw atoms are forced into parseable positions.
"""

from __future__ import annotations

import argparse
import importlib.util
import math
import random
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean

H123_PATH = Path(__file__).with_name("H123-public_gap_table.py")
H123_SPEC = importlib.util.spec_from_file_location("h123_public_gap_table", H123_PATH)
if H123_SPEC is None or H123_SPEC.loader is None:
    raise RuntimeError(f"could not load {H123_PATH}")
h123 = importlib.util.module_from_spec(H123_SPEC)
sys.modules[H123_SPEC.name] = h123
H123_SPEC.loader.exec_module(h123)
h116 = h123.h116
h115 = h123.h115


@dataclass(frozen=True)
class GapTable:
    context: h123.ContextSpec
    gaps: dict[tuple[int, ...], int]
    fallback_gap: int
    quantile: float


@dataclass(frozen=True)
class LaneSchedule:
    period: int
    phase: int
    raw_run_len: int


@dataclass(frozen=True)
class StepStats:
    delta_bits: float
    input_bits: int
    output_bits: int
    rewritten_raw_bits: int
    selected_records: int
    due_records_seen: int
    due_records_covered: int
    expired_records: int
    expiry_tax_bits: int
    padding_bits: int
    raw_lane_items: int
    record_lane_items: int


@dataclass(frozen=True)
class TrialStats:
    config_name: str
    context_name: str
    quantile: float
    period: int
    phase: int
    raw_run_len: int
    passes: int
    total_delta_bits: float
    delta_per_raw_atom: float
    delta_per_raw_atom_pass: float
    selected_records_per_atom_pass: float
    expired_records_per_atom_pass: float
    expiry_tax_per_atom_pass: float
    avg_rewrite_fraction: float
    due_cover_rate: float
    padding_bits_per_selected: float
    raw_lane_fraction: float
    failed: bool


@dataclass(frozen=True)
class Row:
    config_name: str
    context_name: str
    quantile: float
    atoms: int
    passes: int
    trials: int
    min_rewrite: float
    period: int
    phase: int
    raw_run_len: int
    delta_per_atom: float
    delta_per_atom_pass: float
    selected_records_per_atom_pass: float
    expired_records_per_atom_pass: float
    expiry_tax_per_atom_pass: float
    avg_rewrite_fraction: float
    due_cover_rate: float
    padding_bits_per_selected: float
    raw_lane_fraction: float
    fail_rate: float
    fallback_gap: int
    avg_table_gap: float
    table_entries: int


def is_raw_lane(out_index: int, schedule: LaneSchedule) -> bool:
    return (out_index + schedule.phase) % schedule.period < schedule.raw_run_len


def is_markerless_raw_atom(config: h115.Config, item: h115.Item) -> bool:
    return item.record_age is None and item.bits == config.block_bits and item.raw_bits == config.block_bits


def outputs_fit_lanes(config: h115.Config, outputs: list[h115.Item], out_mod: int, schedule: LaneSchedule) -> bool:
    for offset, item in enumerate(outputs):
        lane = is_raw_lane(out_mod + offset, schedule)
        if is_markerless_raw_atom(config, item):
            if not lane:
                return False
        elif lane:
            return False
    return True


def advance_mod(out_mod: int, item_count: int, schedule: LaneSchedule) -> int:
    return (out_mod + item_count) % schedule.period


def raw_atom_outputs(config: h115.Config, item: h115.Item) -> tuple[float, list[h115.Item], int, int]:
    if item.record_age is None:
        return 0.0, [item], 0, 0
    if item.record_age == 0:
        return 0.0, [h115.Item(bits=item.bits, raw_bits=item.raw_bits, record_age=1)], 0, 0
    if item.record_age != 1:
        raise AssertionError("record age must be 0 or 1")

    blocks = math.ceil(item.raw_bits / config.block_bits)
    outputs = [
        h115.Item(bits=config.block_bits, raw_bits=config.block_bits, record_age=None)
        for _ in range(blocks)
    ]
    output_bits = sum(out.bits for out in outputs)
    tax = output_bits - item.bits
    return float(tax), outputs, 1, tax


def gap_for(table: GapTable, edge: h116.RichEdge) -> int:
    return table.gaps.get(h123.context_for(table.context, edge), table.fallback_gap)


def select_step(
    config: h115.Config,
    items: list[h115.Item],
    slack: int,
    min_rewrite_raw_fraction: float,
    seed: int,
    table: GapTable | None,
    schedule: LaneSchedule,
    collect_edges: bool = False,
) -> tuple[list[h115.Item] | None, StepStats, list[h116.RichEdge]]:
    edges_by_start = h123.sample_edges(config, items, slack, seed)
    total_raw = sum(item.raw_bits for item in items)
    due_seen = sum(1 for item in items if item.record_age == 1)
    n = len(items)
    dp: list[dict[tuple[int, int], float]] = [dict() for _ in range(n + 1)]
    prev: dict[
        tuple[int, int, int],
        tuple[int, int, int, str, h116.RichEdge | None, list[h115.Item], int, int, int],
    ] = {}
    dp[0][(0, 0)] = 0.0

    def update(
        end: int,
        new_raw: int,
        new_mod: int,
        candidate: float,
        prior: tuple[int, int, int, str, h116.RichEdge | None, list[h115.Item], int, int, int],
    ) -> None:
        key = (new_raw, new_mod)
        if candidate < dp[end].get(key, float("inf")):
            dp[end][key] = candidate
            prev[(end, new_raw, new_mod)] = prior

    for pos in range(n):
        for (raw_done, out_mod), base in list(dp[pos].items()):
            skip_delta, outputs, expired, tax = raw_atom_outputs(config, items[pos])
            if math.isfinite(skip_delta) and outputs_fit_lanes(config, outputs, out_mod, schedule):
                new_mod = advance_mod(out_mod, len(outputs), schedule)
                update(
                    pos + 1,
                    raw_done,
                    new_mod,
                    base + skip_delta,
                    (pos, raw_done, out_mod, "skip", None, outputs, expired, tax, 0),
                )

            if is_raw_lane(out_mod, schedule):
                continue
            for edge in edges_by_start[pos]:
                if table is None:
                    delta = edge.local_delta
                    width = edge.payload_width
                    padding = 0
                else:
                    gap = gap_for(table, edge)
                    if not h123.is_gap_candidate(edge, gap):
                        continue
                    delta = h123.gap_delta(edge, gap)
                    width = edge.target_bits - gap
                    padding = width - edge.payload_width
                end = pos + edge.arity
                new_raw = min(total_raw, raw_done + edge.raw_bits)
                output = [h115.Item(bits=edge.arity_bits + width, raw_bits=edge.raw_bits, record_age=0)]
                new_mod = advance_mod(out_mod, 1, schedule)
                update(
                    end,
                    new_raw,
                    new_mod,
                    base + delta,
                    (pos, raw_done, out_mod, "edge", edge, output, 0, 0, padding),
                )

    min_raw = math.ceil(total_raw * min_rewrite_raw_fraction)
    best_key: tuple[int, int] | None = None
    best_delta = float("inf")
    for (raw_done, out_mod), delta in dp[n].items():
        if raw_done >= min_raw and delta < best_delta:
            best_delta = delta
            best_key = (raw_done, out_mod)
    if best_key is None:
        input_bits = sum(item.bits for item in items)
        return None, StepStats(float("inf"), input_bits, input_bits, 0, 0, due_seen, 0, 0, 0, 0, 0, 0), []

    output_chunks: list[list[h115.Item]] = []
    selected = 0
    due_covered = 0
    expired_records = 0
    expiry_tax = 0
    padding_bits = 0
    selected_edges: list[h116.RichEdge] = []
    raw_lane_items = 0
    record_lane_items = 0
    pos = n
    raw, out_mod = best_key
    while pos > 0:
        entry = prev[(pos, raw, out_mod)]
        prior_pos, prior_raw, prior_mod, kind, edge, outputs, expired, tax, padding = entry
        for offset, item in enumerate(outputs):
            if is_markerless_raw_atom(config, item):
                raw_lane_items += 1
            else:
                record_lane_items += 1
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
        out_mod = prior_mod

    next_items = [item for chunk in reversed(output_chunks) for item in chunk]
    input_bits = sum(item.bits for item in items)
    output_bits = sum(item.bits for item in next_items)
    selected_edges.reverse()
    return next_items, StepStats(
        delta_bits=best_delta,
        input_bits=input_bits,
        output_bits=output_bits,
        rewritten_raw_bits=best_key[0],
        selected_records=selected,
        due_records_seen=due_seen,
        due_records_covered=due_covered,
        expired_records=expired_records,
        expiry_tax_bits=expiry_tax,
        padding_bits=padding_bits,
        raw_lane_items=raw_lane_items,
        record_lane_items=record_lane_items,
    ), selected_edges


def collect_local_edges(
    config: h115.Config,
    slack: int,
    passes: int,
    seed: int,
    min_rewrite_raw_fraction: float,
    schedule: LaneSchedule,
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
            schedule,
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
    schedule: LaneSchedule,
) -> GapTable:
    buckets: dict[tuple[int, ...], list[int]] = defaultdict(list)
    all_gaps: list[int] = []
    for trial in range(train_trials):
        for edge in collect_local_edges(
            config,
            slack,
            passes,
            seed + trial * 1_000_003,
            min_rewrite_raw_fraction,
            schedule,
        ):
            gap = h123.actual_gap(edge)
            buckets[h123.context_for(context, edge)].append(gap)
            all_gaps.append(gap)
    fallback = h123.quantile_gap(all_gaps, quantile)
    gaps = {key: h123.quantile_gap(values, quantile) for key, values in buckets.items()}
    return GapTable(context=context, gaps=gaps, fallback_gap=fallback, quantile=quantile)


def simulate_trial(
    config: h115.Config,
    slack: int,
    table: GapTable,
    schedule: LaneSchedule,
    passes: int,
    seed: int,
    min_rewrite_raw_fraction: float,
) -> TrialStats:
    items = h115.initial_items(config)
    raw_atoms = sum(item.raw_bits for item in items) / config.block_bits
    total_delta = 0.0
    selected = 0
    due_seen = 0
    due_covered = 0
    expired = 0
    expiry_tax = 0
    padding = 0
    raw_lane = 0
    record_lane = 0
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
            schedule,
        )
        if next_items is None:
            return TrialStats(
                config.name,
                table.context.name,
                table.quantile,
                schedule.period,
                schedule.phase,
                schedule.raw_run_len,
                passes,
                float("inf"),
                float("inf"),
                float("inf"),
                selected / raw_atoms / max(1, step + 1),
                expired / raw_atoms / max(1, step + 1),
                expiry_tax / raw_atoms / max(1, step + 1),
                mean(rewrite_fracs) if rewrite_fracs else 0.0,
                0.0 if due_seen == 0 else due_covered / due_seen,
                padding / max(1, selected),
                raw_lane / max(1, raw_lane + record_lane),
                True,
            )
        total_delta += stats.delta_bits
        selected += stats.selected_records
        due_seen += stats.due_records_seen
        due_covered += stats.due_records_covered
        expired += stats.expired_records
        expiry_tax += stats.expiry_tax_bits
        padding += stats.padding_bits
        raw_lane += stats.raw_lane_items
        record_lane += stats.record_lane_items
        rewrite_fracs.append(stats.rewritten_raw_bits / max(1, total_raw))
        items = next_items

    return TrialStats(
        config.name,
        table.context.name,
        table.quantile,
        schedule.period,
        schedule.phase,
        schedule.raw_run_len,
        passes,
        total_delta,
        total_delta / raw_atoms,
        total_delta / raw_atoms / passes,
        selected / raw_atoms / passes,
        expired / raw_atoms / passes,
        expiry_tax / raw_atoms / passes,
        mean(rewrite_fracs) if rewrite_fracs else 0.0,
        1.0 if due_seen == 0 else due_covered / due_seen,
        padding / max(1, selected),
        raw_lane / max(1, raw_lane + record_lane),
        False,
    )


def evaluate(
    config: h115.Config,
    slack: int,
    context: h123.ContextSpec,
    quantile: float,
    schedule: LaneSchedule,
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
        schedule,
    )
    trials = [
        simulate_trial(
            config,
            slack,
            table,
            schedule,
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
            schedule.period,
            schedule.phase,
            schedule.raw_run_len,
            float("inf"),
            float("inf"),
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
        schedule.period,
        schedule.phase,
        schedule.raw_run_len,
        mean(trial.delta_per_raw_atom for trial in finite),
        mean(trial.delta_per_raw_atom_pass for trial in finite),
        mean(trial.selected_records_per_atom_pass for trial in finite),
        mean(trial.expired_records_per_atom_pass for trial in finite),
        mean(trial.expiry_tax_per_atom_pass for trial in finite),
        mean(trial.avg_rewrite_fraction for trial in finite),
        mean(trial.due_cover_rate for trial in finite),
        mean(trial.padding_bits_per_selected for trial in finite),
        mean(trial.raw_lane_fraction for trial in finite),
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
        "config,context,q,period,phase,raw_run,atoms,passes,trials,min_rewrite,"
        "delta/atom,delta/atom/pass,sel/atom/pass,expired/atom/pass,"
        "expiry_tax/atom/pass,rewrite_frac,due_cover,padding/sel,"
        "raw_lane_frac,fail,fallbackG,avgG,entries"
    )
    for row in rows:
        print(
            f"{row.config_name},{row.context_name},{row.quantile:.2f},"
            f"{row.period},{row.phase},{row.raw_run_len},{row.atoms},{row.passes},{row.trials},"
            f"{row.min_rewrite:.3f},{format_float(row.delta_per_atom)},"
            f"{format_float(row.delta_per_atom_pass)},"
            f"{format_float(row.selected_records_per_atom_pass)},"
            f"{format_float(row.expired_records_per_atom_pass)},"
            f"{format_float(row.expiry_tax_per_atom_pass)},"
            f"{format_float(row.avg_rewrite_fraction)},"
            f"{format_float(row.due_cover_rate)},"
            f"{format_float(row.padding_bits_per_selected)},"
            f"{format_float(row.raw_lane_fraction)},"
            f"{format_float(row.fail_rate)},"
            f"{row.fallback_gap},{format_float(row.avg_table_gap)},"
            f"{row.table_entries}"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--passes", type=int, default=4)
    parser.add_argument("--train-trials", type=int, default=4)
    parser.add_argument("--eval-trials", type=int, default=8)
    parser.add_argument("--seed", type=int, default=125_001)
    parser.add_argument("--slack", type=int, default=4)
    parser.add_argument("--atoms", type=int, default=128)
    parser.add_argument("--min-rewrite-raw-frac", type=float, default=0.25)
    parser.add_argument("--period", type=int, action="append", default=[])
    parser.add_argument("--phase", type=int, default=0)
    parser.add_argument("--raw-run-len", type=int, action="append", default=[])
    parser.add_argument("--quantile", type=float, action="append", default=[])
    parser.add_argument("--config-filter", action="append", default=[])
    parser.add_argument("--context-filter", action="append", default=[])
    args = parser.parse_args()

    configs = h116.default_configs(args.atoms)
    if args.config_filter:
        wanted_configs = set(args.config_filter)
        configs = [config for config in configs if config.name in wanted_configs]

    periods = args.period or [2, 3, 4, 8]
    raw_run_lens = args.raw_run_len or [1]
    quantiles = args.quantile or [0.10]
    rows: list[Row] = []
    for config in configs:
        for period in periods:
            contexts = h123.default_contexts(period=period, phase=args.phase)
            if args.context_filter:
                wanted_contexts = set(args.context_filter)
                contexts = [context for context in contexts if context.name in wanted_contexts]
            for raw_run_len in raw_run_lens:
                if raw_run_len < 1 or raw_run_len >= period:
                    continue
                for context in contexts:
                    for quantile in quantiles:
                        schedule = LaneSchedule(
                            period=period,
                            phase=args.phase,
                            raw_run_len=raw_run_len,
                        )
                        rows.append(
                            evaluate(
                                config=config,
                                slack=args.slack,
                                context=context,
                                quantile=quantile,
                                schedule=schedule,
                                passes=args.passes,
                                train_trials=args.train_trials,
                                eval_trials=args.eval_trials,
                                seed=args.seed + period * 10_000_019 + raw_run_len * 1_000_003,
                                min_rewrite_raw_fraction=args.min_rewrite_raw_frac,
                            )
                        )
    print_rows(rows)


if __name__ == "__main__":
    main()
