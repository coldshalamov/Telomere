#!/usr/bin/env python3
"""H124 - fallback repair for frozen public gap tables.

H123 found negative finite rows only when many held-out trials failed the
forced due-refresh constraint. This kernel asks whether those failed rows can
be repaired by expiring due records instead of treating failure as fatal.

Modes:

* force_refresh: age-1 records must be covered by a new record;
* expire_raw_lower_bound: due records may expand to raw bits without literal
  markers and with grouping preserved, an optimistic lower bound;
* expire_raw_atoms: due records expand to fixed raw atoms without literal
  markers, a closer target for a scheduled raw/not-ready region;
* expire_literal_items: due records expand to literal-marked block items.

If fallback repair makes the negative H123 rows positive, the apparent crossing
was just an unpaid stale-record exception channel.
"""

from __future__ import annotations

import argparse
import importlib.util
import math
import random
import sys
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


def log2_choose(n: int, k: int) -> float:
    if k < 0 or k > n:
        return float("inf")
    return (math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)) / math.log(2.0)


def is_markerless_raw_atom(config: h115.Config, item: h115.Item) -> bool:
    return item.record_age is None and item.bits == config.block_bits and item.raw_bits == config.block_bits


def type_stream_costs(config: h115.Config, items: list[h115.Item]) -> tuple[int, int, float, float]:
    flags = [is_markerless_raw_atom(config, item) for item in items]
    raw_items = sum(1 for flag in flags if flag)
    raw_runs = 0
    previous = False
    for flag in flags:
        if flag and not previous:
            raw_runs += 1
        previous = flag
    output_items = len(flags)
    bitmap_bits = log2_choose(output_items, raw_items)
    run_bits = 0.0 if raw_runs == 0 else log2_choose(output_items + 1, 2 * raw_runs)
    return raw_items, raw_runs, bitmap_bits, run_bits


def skip_outputs(config: h115.Config, item: h115.Item, expiry_mode: str) -> tuple[float, list[h115.Item], int, int]:
    if expiry_mode != "expire_raw_atoms":
        return h115.skip_outputs(config, item, expiry_mode)
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
    output_items: int
    raw_items: int
    raw_runs: int
    type_bitmap_bits: float
    type_run_bits: float


@dataclass(frozen=True)
class TrialStats:
    config_name: str
    context_name: str
    visibility: str
    quantile: float
    expiry_mode: str
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
    output_items_per_atom_pass: float
    raw_items_per_atom_pass: float
    raw_runs_per_atom_pass: float
    type_bitmap_bits_per_atom_pass: float
    type_run_bits_per_atom_pass: float
    failed: bool


@dataclass(frozen=True)
class Row:
    config_name: str
    context_name: str
    visibility: str
    quantile: float
    expiry_mode: str
    atoms: int
    passes: int
    trials: int
    min_rewrite: float
    delta_per_atom: float
    delta_per_atom_pass: float
    selected_records_per_atom_pass: float
    expired_records_per_atom_pass: float
    expiry_tax_per_atom_pass: float
    avg_rewrite_fraction: float
    due_cover_rate: float
    padding_bits_per_selected: float
    output_items_per_atom_pass: float
    raw_items_per_atom_pass: float
    raw_runs_per_atom_pass: float
    type_bitmap_bits_per_atom_pass: float
    type_run_bits_per_atom_pass: float
    fail_rate: float
    fallback_gap: int
    avg_table_gap: float
    table_entries: int


def select_step(
    config: h115.Config,
    items: list[h115.Item],
    slack: int,
    min_rewrite_raw_fraction: float,
    seed: int,
    table: h123.GapTable,
    expiry_mode: str,
) -> tuple[list[h115.Item] | None, StepStats]:
    edges_by_start = h123.sample_edges(config, items, slack, seed)
    total_raw = sum(item.raw_bits for item in items)
    due_seen = sum(1 for item in items if item.record_age == 1)
    n = len(items)
    inf = float("inf")
    dp = [[inf] * (total_raw + 1) for _ in range(n + 1)]
    prev: list[list[tuple[int, int, str, h116.RichEdge | None, list[h115.Item], int, int, int] | None]] = [
        [None] * (total_raw + 1) for _ in range(n + 1)
    ]
    dp[0][0] = 0.0

    for pos in range(n):
        for raw_done in range(total_raw + 1):
            base = dp[pos][raw_done]
            if base == inf:
                continue

            skip_delta, outputs, expired, tax = skip_outputs(config, items[pos], expiry_mode)
            if math.isfinite(skip_delta):
                candidate = base + skip_delta
                if candidate < dp[pos + 1][raw_done]:
                    dp[pos + 1][raw_done] = candidate
                    prev[pos + 1][raw_done] = (pos, raw_done, "skip", None, outputs, expired, tax, 0)

            for edge in edges_by_start[pos]:
                gap = h123.gap_for(table, edge)
                if not h123.is_gap_candidate(edge, gap):
                    continue
                delta = h123.gap_delta(edge, gap)
                end = pos + edge.arity
                new_raw = min(total_raw, raw_done + edge.raw_bits)
                width = edge.target_bits - gap
                padding = width - edge.payload_width
                output = [
                    h115.Item(
                        bits=edge.arity_bits + width,
                        raw_bits=edge.raw_bits,
                        record_age=0,
                    )
                ]
                candidate = base + delta
                if candidate < dp[end][new_raw]:
                    dp[end][new_raw] = candidate
                    prev[end][new_raw] = (pos, raw_done, "edge", edge, output, 0, 0, padding)

    min_raw = math.ceil(total_raw * min_rewrite_raw_fraction)
    best_raw = -1
    best_delta = inf
    for raw_done in range(min_raw, total_raw + 1):
        if dp[n][raw_done] < best_delta:
            best_delta = dp[n][raw_done]
            best_raw = raw_done
    if best_raw < 0:
        input_bits = sum(item.bits for item in items)
        return None, StepStats(inf, input_bits, input_bits, 0, 0, due_seen, 0, 0, 0, 0, 0, 0, 0, 0.0, 0.0)

    output_chunks: list[list[h115.Item]] = []
    selected = 0
    due_covered = 0
    expired_records = 0
    expiry_tax = 0
    padding_bits = 0
    pos = n
    raw = best_raw
    while pos > 0:
        entry = prev[pos][raw]
        if entry is None:
            raise AssertionError("missing predecessor")
        prior_pos, prior_raw, kind, edge, outputs, expired, tax, padding = entry
        output_chunks.append(outputs)
        if kind == "edge":
            selected += 1
            padding_bits += padding
            if edge is None:
                raise AssertionError("selected edge missing")
            due_covered += edge.old_count
        expired_records += expired
        expiry_tax += tax
        pos = prior_pos
        raw = prior_raw

    next_items = [item for chunk in reversed(output_chunks) for item in chunk]
    input_bits = sum(item.bits for item in items)
    output_bits = sum(item.bits for item in next_items)
    raw_items, raw_runs, bitmap_bits, run_bits = type_stream_costs(config, next_items)
    return next_items, StepStats(
        delta_bits=best_delta,
        input_bits=input_bits,
        output_bits=output_bits,
        rewritten_raw_bits=best_raw,
        selected_records=selected,
        due_records_seen=due_seen,
        due_records_covered=due_covered,
        expired_records=expired_records,
        expiry_tax_bits=expiry_tax,
        padding_bits=padding_bits,
        output_items=len(next_items),
        raw_items=raw_items,
        raw_runs=raw_runs,
        type_bitmap_bits=bitmap_bits,
        type_run_bits=run_bits,
    )


def simulate_trial(
    config: h115.Config,
    slack: int,
    table: h123.GapTable,
    expiry_mode: str,
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
    output_items = 0
    raw_items = 0
    raw_runs = 0
    type_bitmap_bits = 0.0
    type_run_bits = 0.0
    rewrite_fracs: list[float] = []
    for step in range(passes):
        total_raw = sum(item.raw_bits for item in items)
        next_items, stats = select_step(
            config,
            items,
            slack,
            min_rewrite_raw_fraction,
            seed + step * 1_000_003,
            table,
            expiry_mode,
        )
        if next_items is None:
            return TrialStats(
                config_name=config.name,
                context_name=table.context.name,
                visibility=table.context.visibility,
                quantile=table.quantile,
                expiry_mode=expiry_mode,
                passes=passes,
                total_delta_bits=float("inf"),
                delta_per_raw_atom=float("inf"),
                delta_per_raw_atom_pass=float("inf"),
                selected_records_per_atom_pass=selected / raw_atoms / max(1, step + 1),
                expired_records_per_atom_pass=expired / raw_atoms / max(1, step + 1),
                expiry_tax_per_atom_pass=expiry_tax / raw_atoms / max(1, step + 1),
                avg_rewrite_fraction=mean(rewrite_fracs) if rewrite_fracs else 0.0,
                due_cover_rate=0.0 if due_seen == 0 else due_covered / due_seen,
                padding_bits_per_selected=padding / max(1, selected),
                output_items_per_atom_pass=output_items / raw_atoms / max(1, step + 1),
                raw_items_per_atom_pass=raw_items / raw_atoms / max(1, step + 1),
                raw_runs_per_atom_pass=raw_runs / raw_atoms / max(1, step + 1),
                type_bitmap_bits_per_atom_pass=type_bitmap_bits / raw_atoms / max(1, step + 1),
                type_run_bits_per_atom_pass=type_run_bits / raw_atoms / max(1, step + 1),
                failed=True,
            )
        total_delta += stats.delta_bits
        selected += stats.selected_records
        due_seen += stats.due_records_seen
        due_covered += stats.due_records_covered
        expired += stats.expired_records
        expiry_tax += stats.expiry_tax_bits
        padding += stats.padding_bits
        output_items += stats.output_items
        raw_items += stats.raw_items
        raw_runs += stats.raw_runs
        type_bitmap_bits += stats.type_bitmap_bits
        type_run_bits += stats.type_run_bits
        rewrite_fracs.append(stats.rewritten_raw_bits / max(1, total_raw))
        items = next_items

    return TrialStats(
        config_name=config.name,
        context_name=table.context.name,
        visibility=table.context.visibility,
        quantile=table.quantile,
        expiry_mode=expiry_mode,
        passes=passes,
        total_delta_bits=total_delta,
        delta_per_raw_atom=total_delta / raw_atoms,
        delta_per_raw_atom_pass=total_delta / raw_atoms / passes,
        selected_records_per_atom_pass=selected / raw_atoms / passes,
        expired_records_per_atom_pass=expired / raw_atoms / passes,
        expiry_tax_per_atom_pass=expiry_tax / raw_atoms / passes,
        avg_rewrite_fraction=mean(rewrite_fracs) if rewrite_fracs else 0.0,
        due_cover_rate=1.0 if due_seen == 0 else due_covered / due_seen,
        padding_bits_per_selected=padding / max(1, selected),
        output_items_per_atom_pass=output_items / raw_atoms / passes,
        raw_items_per_atom_pass=raw_items / raw_atoms / passes,
        raw_runs_per_atom_pass=raw_runs / raw_atoms / passes,
        type_bitmap_bits_per_atom_pass=type_bitmap_bits / raw_atoms / passes,
        type_run_bits_per_atom_pass=type_run_bits / raw_atoms / passes,
        failed=False,
    )


def evaluate(
    config: h115.Config,
    slack: int,
    context: h123.ContextSpec,
    quantile: float,
    expiry_mode: str,
    passes: int,
    train_trials: int,
    eval_trials: int,
    seed: int,
    min_rewrite_raw_fraction: float,
) -> Row:
    table = h123.fit_table(
        config,
        slack,
        context,
        quantile,
        passes,
        train_trials,
        seed,
        min_rewrite_raw_fraction,
    )
    trials = [
        simulate_trial(
            config,
            slack,
            table,
            expiry_mode,
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
            config_name=config.name,
            context_name=context.name,
            visibility=context.visibility,
            quantile=quantile,
            expiry_mode=expiry_mode,
            atoms=config.atoms,
            passes=passes,
            trials=eval_trials,
            min_rewrite=min_rewrite_raw_fraction,
            delta_per_atom=float("inf"),
            delta_per_atom_pass=float("inf"),
            selected_records_per_atom_pass=0.0,
            expired_records_per_atom_pass=0.0,
            expiry_tax_per_atom_pass=0.0,
            avg_rewrite_fraction=0.0,
            due_cover_rate=0.0,
            padding_bits_per_selected=0.0,
            output_items_per_atom_pass=0.0,
            raw_items_per_atom_pass=0.0,
            raw_runs_per_atom_pass=0.0,
            type_bitmap_bits_per_atom_pass=0.0,
            type_run_bits_per_atom_pass=0.0,
            fail_rate=fail_rate,
            fallback_gap=table.fallback_gap,
            avg_table_gap=mean(table_gaps) if table_gaps else float(table.fallback_gap),
            table_entries=len(table.gaps),
        )
    return Row(
        config_name=config.name,
        context_name=context.name,
        visibility=context.visibility,
        quantile=quantile,
        expiry_mode=expiry_mode,
        atoms=config.atoms,
        passes=passes,
        trials=eval_trials,
        min_rewrite=min_rewrite_raw_fraction,
        delta_per_atom=mean(trial.delta_per_raw_atom for trial in finite),
        delta_per_atom_pass=mean(trial.delta_per_raw_atom_pass for trial in finite),
        selected_records_per_atom_pass=mean(trial.selected_records_per_atom_pass for trial in finite),
        expired_records_per_atom_pass=mean(trial.expired_records_per_atom_pass for trial in finite),
        expiry_tax_per_atom_pass=mean(trial.expiry_tax_per_atom_pass for trial in finite),
        avg_rewrite_fraction=mean(trial.avg_rewrite_fraction for trial in finite),
        due_cover_rate=mean(trial.due_cover_rate for trial in finite),
        padding_bits_per_selected=mean(trial.padding_bits_per_selected for trial in finite),
        output_items_per_atom_pass=mean(trial.output_items_per_atom_pass for trial in finite),
        raw_items_per_atom_pass=mean(trial.raw_items_per_atom_pass for trial in finite),
        raw_runs_per_atom_pass=mean(trial.raw_runs_per_atom_pass for trial in finite),
        type_bitmap_bits_per_atom_pass=mean(trial.type_bitmap_bits_per_atom_pass for trial in finite),
        type_run_bits_per_atom_pass=mean(trial.type_run_bits_per_atom_pass for trial in finite),
        fail_rate=fail_rate,
        fallback_gap=table.fallback_gap,
        avg_table_gap=mean(table_gaps) if table_gaps else float(table.fallback_gap),
        table_entries=len(table.gaps),
    )


def format_float(value: float) -> str:
    if math.isinf(value):
        return "inf"
    return f"{value:.6f}"


def print_rows(rows: list[Row]) -> None:
    print(
        "config,context,vis,q,expiry,atoms,passes,trials,min_rewrite,"
        "delta/atom,delta/atom/pass,sel/atom/pass,expired/atom/pass,"
        "expiry_tax/atom/pass,rewrite_frac,due_cover,padding/sel,"
        "out_items/atom/pass,raw_items/atom/pass,raw_runs/atom/pass,"
        "type_bitmap/atom/pass,type_runs/atom/pass,fail,"
        "fallbackG,avgG,entries"
    )
    for row in rows:
        print(
            f"{row.config_name},{row.context_name},{row.visibility},{row.quantile:.2f},"
            f"{row.expiry_mode},{row.atoms},{row.passes},{row.trials},"
            f"{row.min_rewrite:.3f},{format_float(row.delta_per_atom)},"
            f"{format_float(row.delta_per_atom_pass)},"
            f"{format_float(row.selected_records_per_atom_pass)},"
            f"{format_float(row.expired_records_per_atom_pass)},"
            f"{format_float(row.expiry_tax_per_atom_pass)},"
            f"{format_float(row.avg_rewrite_fraction)},"
            f"{format_float(row.due_cover_rate)},"
            f"{format_float(row.padding_bits_per_selected)},"
            f"{format_float(row.output_items_per_atom_pass)},"
            f"{format_float(row.raw_items_per_atom_pass)},"
            f"{format_float(row.raw_runs_per_atom_pass)},"
            f"{format_float(row.type_bitmap_bits_per_atom_pass)},"
            f"{format_float(row.type_run_bits_per_atom_pass)},"
            f"{format_float(row.fail_rate)},"
            f"{row.fallback_gap},"
            f"{format_float(row.avg_table_gap)},"
            f"{row.table_entries}"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--passes", type=int, default=4)
    parser.add_argument("--train-trials", type=int, default=8)
    parser.add_argument("--eval-trials", type=int, default=16)
    parser.add_argument("--seed", type=int, default=124_001)
    parser.add_argument("--slack", type=int, default=4)
    parser.add_argument("--atoms", type=int, default=128)
    parser.add_argument("--min-rewrite-raw-frac", type=float, default=0.25)
    parser.add_argument("--period", type=int, default=16)
    parser.add_argument("--phase", type=int, default=0)
    parser.add_argument("--quantile", type=float, action="append", default=[])
    parser.add_argument("--expiry-mode", action="append", default=[])
    parser.add_argument("--config-filter", action="append", default=[])
    parser.add_argument("--context-filter", action="append", default=[])
    args = parser.parse_args()

    configs = h116.default_configs(args.atoms)
    if args.config_filter:
        wanted_configs = set(args.config_filter)
        configs = [config for config in configs if config.name in wanted_configs]

    contexts = h123.default_contexts(args.period, args.phase)
    if args.context_filter:
        wanted_contexts = set(args.context_filter)
        contexts = [context for context in contexts if context.name in wanted_contexts]

    quantiles = args.quantile or [0.10]
    expiry_modes = args.expiry_mode or [
        "force_refresh",
        "expire_raw_lower_bound",
        "expire_raw_atoms",
        "expire_literal_items",
    ]
    rows: list[Row] = []
    for config in configs:
        for context in contexts:
            for quantile in quantiles:
                for expiry_mode in expiry_modes:
                    rows.append(
                        evaluate(
                            config=config,
                            slack=args.slack,
                            context=context,
                            quantile=quantile,
                            expiry_mode=expiry_mode,
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
