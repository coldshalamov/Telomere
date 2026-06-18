#!/usr/bin/env python3
"""H123 - frozen public gap tables for an optimistic typed board.

H122 showed that a paid per-record gap alphabet is close but still misses.
This kernel removes the per-record gap selector: a public table maps visible
context to a fixed gap G(context), and the decoder derives:

    W = T_pub - G(context)

The table is trained on independent local-oracle covers and then frozen. It is
a public profile constant, not per-file metadata. As in H121/H122, this is an
optimistic typed-board lower bound because T_pub is set to the actual interval
length; a real board must make that length public or pay H(T).
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

H116_PATH = Path(__file__).with_name("H116-public_width_law_search.py")
H116_SPEC = importlib.util.spec_from_file_location("h116_public_width", H116_PATH)
if H116_SPEC is None or H116_SPEC.loader is None:
    raise RuntimeError(f"could not load {H116_PATH}")
h116 = importlib.util.module_from_spec(H116_SPEC)
sys.modules[H116_SPEC.name] = h116
H116_SPEC.loader.exec_module(h116)
h115 = h116.h115


@dataclass(frozen=True)
class ContextSpec:
    name: str
    visibility: str
    period: int = 16
    phase: int = 0


@dataclass(frozen=True)
class GapTable:
    context: ContextSpec
    gaps: dict[tuple[int, ...], int]
    fallback_gap: int
    quantile: float


@dataclass(frozen=True)
class StepStats:
    delta_bits: float
    input_bits: int
    output_bits: int
    rewritten_raw_bits: int
    selected_records: int
    due_records_seen: int
    due_records_covered: int
    padding_bits: int
    supply_candidates: int
    local_candidates: int


@dataclass(frozen=True)
class TrialStats:
    config_name: str
    context_name: str
    visibility: str
    quantile: float
    passes: int
    total_delta_bits: float
    delta_per_raw_atom: float
    delta_per_raw_atom_pass: float
    selected_records_per_atom_pass: float
    avg_rewrite_fraction: float
    due_cover_rate: float
    padding_bits_per_selected: float
    supply_ratio: float
    supply_loss_bits: float
    failed: bool


@dataclass(frozen=True)
class Row:
    config_name: str
    context_name: str
    visibility: str
    quantile: float
    atoms: int
    passes: int
    trials: int
    min_rewrite: float
    delta_per_atom: float
    delta_per_atom_pass: float
    selected_records_per_atom_pass: float
    avg_rewrite_fraction: float
    due_cover_rate: float
    padding_bits_per_selected: float
    supply_ratio: float
    supply_loss_bits: float
    fail_rate: float
    fallback_gap: int
    avg_table_gap: float
    table_entries: int


def arity_bucket(arity: int) -> int:
    if arity <= 1:
        return 0
    return min(12, int(math.log2(arity)))


def target_bucket(target_bits: int) -> int:
    if target_bits <= 1:
        return 0
    return min(16, int(math.log2(target_bits)))


def public_lane_count(start: int, arity: int, period: int, phase: int) -> int:
    return sum(1 for pos in range(start, start + arity) if (pos + phase) % period == 0)


def small_count(value: int) -> int:
    return min(8, value)


def context_for(spec: ContextSpec, edge: h116.RichEdge) -> tuple[int, ...]:
    if spec.name == "global":
        return ()
    if spec.name == "arity_bucket":
        return (arity_bucket(edge.arity),)
    if spec.name == "exact_arity":
        return (edge.arity,)
    if spec.name == "lane_exact_arity":
        return (
            small_count(public_lane_count(edge.start, edge.arity, spec.period, spec.phase)),
            edge.arity,
        )
    if spec.name == "start_mod_exact_arity":
        return (edge.start % spec.period, edge.arity)
    if spec.name == "target_exact_arity":
        return (target_bucket(edge.target_bits), edge.arity)
    raise ValueError(spec.name)


def quantile_gap(values: list[int], q: float) -> int:
    if not values:
        return 1
    values = sorted(max(1, value) for value in values)
    index = min(len(values) - 1, max(0, math.ceil(q * len(values)) - 1))
    return values[index]


def sample_edges(config: h115.Config, items: list[h115.Item], slack: int, seed: int) -> list[list[h116.RichEdge]]:
    return h116.sample_rich_edges(config, items, slack, random.Random(seed))


def actual_gap(edge: h116.RichEdge) -> int:
    return max(0, edge.target_bits - edge.payload_width)


def is_gap_candidate(edge: h116.RichEdge, gap: int) -> bool:
    width = edge.target_bits - gap
    return width >= 0 and edge.payload_width <= width


def gap_for(table: GapTable, edge: h116.RichEdge) -> int:
    return table.gaps.get(context_for(table.context, edge), table.fallback_gap)


def gap_delta(edge: h116.RichEdge, gap: int) -> int:
    return edge.arity_bits - gap


def select_step(
    config: h115.Config,
    items: list[h115.Item],
    slack: int,
    min_rewrite_raw_fraction: float,
    seed: int,
    table: GapTable | None,
    collect_edges: bool = False,
) -> tuple[list[h115.Item] | None, StepStats, list[h116.RichEdge]]:
    edges_by_start = sample_edges(config, items, slack, seed)
    total_raw = sum(item.raw_bits for item in items)
    due_seen = sum(1 for item in items if item.record_age == 1)
    local_candidates = sum(len(edges) for edges in edges_by_start)
    supply_candidates = local_candidates if table is None else sum(
        1
        for edges in edges_by_start
        for edge in edges
        if is_gap_candidate(edge, gap_for(table, edge))
    )
    n = len(items)
    inf = float("inf")
    dp = [[inf] * (total_raw + 1) for _ in range(n + 1)]
    prev: list[list[tuple[int, int, str, h116.RichEdge | None, list[h115.Item], int] | None]] = [
        [None] * (total_raw + 1) for _ in range(n + 1)
    ]
    dp[0][0] = 0.0

    for pos in range(n):
        for raw_done in range(total_raw + 1):
            base = dp[pos][raw_done]
            if base == inf:
                continue

            skip_delta, outputs, _expired, _tax = h115.skip_outputs(config, items[pos], "force_refresh")
            if math.isfinite(skip_delta):
                candidate = base + skip_delta
                if candidate < dp[pos + 1][raw_done]:
                    dp[pos + 1][raw_done] = candidate
                    prev[pos + 1][raw_done] = (pos, raw_done, "skip", None, outputs, 0)

            for edge in edges_by_start[pos]:
                if table is None:
                    delta = edge.local_delta
                    record_bits = edge.local_cost
                    padding = 0
                else:
                    gap = gap_for(table, edge)
                    if not is_gap_candidate(edge, gap):
                        continue
                    delta = gap_delta(edge, gap)
                    width = edge.target_bits - gap
                    record_bits = edge.arity_bits + width
                    padding = width - edge.payload_width
                end = pos + edge.arity
                new_raw = min(total_raw, raw_done + edge.raw_bits)
                output = [
                    h115.Item(
                        bits=math.ceil(record_bits),
                        raw_bits=edge.raw_bits,
                        record_age=0,
                    )
                ]
                candidate = base + delta
                if candidate < dp[end][new_raw]:
                    dp[end][new_raw] = candidate
                    prev[end][new_raw] = (pos, raw_done, "edge", edge, output, padding)

    min_raw = math.ceil(total_raw * min_rewrite_raw_fraction)
    best_raw = -1
    best_delta = inf
    for raw_done in range(min_raw, total_raw + 1):
        if dp[n][raw_done] < best_delta:
            best_delta = dp[n][raw_done]
            best_raw = raw_done
    if best_raw < 0:
        input_bits = sum(item.bits for item in items)
        return None, StepStats(inf, input_bits, input_bits, 0, 0, due_seen, 0, 0, supply_candidates, local_candidates), []

    output_chunks: list[list[h115.Item]] = []
    selected = 0
    due_covered = 0
    padding_bits = 0
    selected_edges: list[h116.RichEdge] = []
    pos = n
    raw = best_raw
    while pos > 0:
        entry = prev[pos][raw]
        if entry is None:
            raise AssertionError("missing predecessor")
        prior_pos, prior_raw, kind, edge, outputs, padding = entry
        output_chunks.append(outputs)
        if kind == "edge":
            selected += 1
            padding_bits += padding
            if edge is None:
                raise AssertionError("selected edge missing")
            due_covered += edge.old_count
            if collect_edges:
                selected_edges.append(edge)
        pos = prior_pos
        raw = prior_raw

    next_items = [item for chunk in reversed(output_chunks) for item in chunk]
    input_bits = sum(item.bits for item in items)
    output_bits = sum(item.bits for item in next_items)
    selected_edges.reverse()
    return next_items, StepStats(
        delta_bits=best_delta,
        input_bits=input_bits,
        output_bits=output_bits,
        rewritten_raw_bits=best_raw,
        selected_records=selected,
        due_records_seen=due_seen,
        due_records_covered=due_covered,
        padding_bits=padding_bits,
        supply_candidates=supply_candidates,
        local_candidates=local_candidates,
    ), selected_edges


def collect_local_edges(
    config: h115.Config,
    slack: int,
    passes: int,
    seed: int,
    min_rewrite_raw_fraction: float,
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
    context: ContextSpec,
    quantile: float,
    passes: int,
    train_trials: int,
    seed: int,
    min_rewrite_raw_fraction: float,
) -> GapTable:
    buckets: dict[tuple[int, ...], list[int]] = defaultdict(list)
    all_gaps: list[int] = []
    for trial in range(train_trials):
        edges = collect_local_edges(
            config,
            slack,
            passes,
            seed + trial * 1_000_003,
            min_rewrite_raw_fraction,
        )
        for edge in edges:
            gap = actual_gap(edge)
            buckets[context_for(context, edge)].append(gap)
            all_gaps.append(gap)
    fallback = quantile_gap(all_gaps, quantile)
    gaps = {key: quantile_gap(values, quantile) for key, values in buckets.items()}
    return GapTable(context=context, gaps=gaps, fallback_gap=fallback, quantile=quantile)


def simulate_trial(
    config: h115.Config,
    slack: int,
    table: GapTable,
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
    padding = 0
    supply_candidates = 0
    local_candidates = 0
    rewrite_fracs: list[float] = []
    for step in range(passes):
        total_raw = sum(item.raw_bits for item in items)
        next_items, stats, _edges = select_step(
            config,
            items,
            slack,
            min_rewrite_raw_fraction,
            seed + step * 1_000_003,
            table,
            collect_edges=False,
        )
        supply_candidates += stats.supply_candidates
        local_candidates += stats.local_candidates
        if next_items is None:
            ratio = supply_candidates / max(1, local_candidates)
            return TrialStats(
                config_name=config.name,
                context_name=table.context.name,
                visibility=table.context.visibility,
                quantile=table.quantile,
                passes=passes,
                total_delta_bits=float("inf"),
                delta_per_raw_atom=float("inf"),
                delta_per_raw_atom_pass=float("inf"),
                selected_records_per_atom_pass=selected / raw_atoms / max(1, step + 1),
                avg_rewrite_fraction=mean(rewrite_fracs) if rewrite_fracs else 0.0,
                due_cover_rate=0.0 if due_seen == 0 else due_covered / due_seen,
                padding_bits_per_selected=padding / max(1, selected),
                supply_ratio=ratio,
                supply_loss_bits=-math.log2(ratio) if ratio > 0 else float("inf"),
                failed=True,
            )
        total_delta += stats.delta_bits
        selected += stats.selected_records
        due_seen += stats.due_records_seen
        due_covered += stats.due_records_covered
        padding += stats.padding_bits
        rewrite_fracs.append(stats.rewritten_raw_bits / max(1, total_raw))
        items = next_items

    ratio = supply_candidates / max(1, local_candidates)
    return TrialStats(
        config_name=config.name,
        context_name=table.context.name,
        visibility=table.context.visibility,
        quantile=table.quantile,
        passes=passes,
        total_delta_bits=total_delta,
        delta_per_raw_atom=total_delta / raw_atoms,
        delta_per_raw_atom_pass=total_delta / raw_atoms / passes,
        selected_records_per_atom_pass=selected / raw_atoms / passes,
        avg_rewrite_fraction=mean(rewrite_fracs) if rewrite_fracs else 0.0,
        due_cover_rate=1.0 if due_seen == 0 else due_covered / due_seen,
        padding_bits_per_selected=padding / max(1, selected),
        supply_ratio=ratio,
        supply_loss_bits=-math.log2(ratio) if ratio > 0 else float("inf"),
        failed=False,
    )


def evaluate(
    config: h115.Config,
    slack: int,
    context: ContextSpec,
    quantile: float,
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
    )
    trials = [
        simulate_trial(
            config,
            slack,
            table,
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
        finite_supply = [trial.supply_loss_bits for trial in trials if math.isfinite(trial.supply_loss_bits)]
        return Row(
            config_name=config.name,
            context_name=context.name,
            visibility=context.visibility,
            quantile=quantile,
            atoms=config.atoms,
            passes=passes,
            trials=eval_trials,
            min_rewrite=min_rewrite_raw_fraction,
            delta_per_atom=float("inf"),
            delta_per_atom_pass=float("inf"),
            selected_records_per_atom_pass=0.0,
            avg_rewrite_fraction=0.0,
            due_cover_rate=0.0,
            padding_bits_per_selected=0.0,
            supply_ratio=mean(trial.supply_ratio for trial in trials),
            supply_loss_bits=mean(finite_supply) if finite_supply else float("inf"),
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
        atoms=config.atoms,
        passes=passes,
        trials=eval_trials,
        min_rewrite=min_rewrite_raw_fraction,
        delta_per_atom=mean(trial.delta_per_raw_atom for trial in finite),
        delta_per_atom_pass=mean(trial.delta_per_raw_atom_pass for trial in finite),
        selected_records_per_atom_pass=mean(trial.selected_records_per_atom_pass for trial in finite),
        avg_rewrite_fraction=mean(trial.avg_rewrite_fraction for trial in finite),
        due_cover_rate=mean(trial.due_cover_rate for trial in finite),
        padding_bits_per_selected=mean(trial.padding_bits_per_selected for trial in finite),
        supply_ratio=mean(trial.supply_ratio for trial in finite),
        supply_loss_bits=mean(trial.supply_loss_bits for trial in finite),
        fail_rate=fail_rate,
        fallback_gap=table.fallback_gap,
        avg_table_gap=mean(table_gaps) if table_gaps else float(table.fallback_gap),
        table_entries=len(table.gaps),
    )


def default_contexts(period: int, phase: int) -> list[ContextSpec]:
    return [
        ContextSpec("global", "public", period, phase),
        ContextSpec("arity_bucket", "public", period, phase),
        ContextSpec("exact_arity", "public", period, phase),
        ContextSpec("lane_exact_arity", "public", period, phase),
        ContextSpec("start_mod_exact_arity", "public", period, phase),
        ContextSpec("target_exact_arity", "hidden", period, phase),
    ]


def format_float(value: float) -> str:
    if math.isinf(value):
        return "inf"
    return f"{value:.6f}"


def print_rows(rows: list[Row]) -> None:
    print(
        "config,context,vis,q,atoms,passes,trials,min_rewrite,delta/atom,"
        "delta/atom/pass,sel/atom/pass,rewrite_frac,due_cover,padding/sel,"
        "supply_ratio,supply_loss,fail,fallbackG,avgG,entries"
    )
    for row in rows:
        print(
            f"{row.config_name},{row.context_name},{row.visibility},{row.quantile:.2f},"
            f"{row.atoms},{row.passes},{row.trials},{row.min_rewrite:.3f},"
            f"{format_float(row.delta_per_atom)},"
            f"{format_float(row.delta_per_atom_pass)},"
            f"{format_float(row.selected_records_per_atom_pass)},"
            f"{format_float(row.avg_rewrite_fraction)},"
            f"{format_float(row.due_cover_rate)},"
            f"{format_float(row.padding_bits_per_selected)},"
            f"{format_float(row.supply_ratio)},"
            f"{format_float(row.supply_loss_bits)},"
            f"{format_float(row.fail_rate)},"
            f"{row.fallback_gap},"
            f"{format_float(row.avg_table_gap)},"
            f"{row.table_entries}"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--passes", type=int, default=4)
    parser.add_argument("--train-trials", type=int, default=6)
    parser.add_argument("--eval-trials", type=int, default=6)
    parser.add_argument("--seed", type=int, default=123_001)
    parser.add_argument("--slack", type=int, default=4)
    parser.add_argument("--atoms", type=int, default=128)
    parser.add_argument("--min-rewrite-raw-frac", type=float, default=0.25)
    parser.add_argument("--period", type=int, default=16)
    parser.add_argument("--phase", type=int, default=0)
    parser.add_argument("--quantile", type=float, action="append", default=[])
    parser.add_argument("--config-filter", action="append", default=[])
    parser.add_argument("--context-filter", action="append", default=[])
    args = parser.parse_args()

    configs = h116.default_configs(args.atoms)
    if args.config_filter:
        wanted_configs = set(args.config_filter)
        configs = [config for config in configs if config.name in wanted_configs]

    contexts = default_contexts(args.period, args.phase)
    if args.context_filter:
        wanted_contexts = set(args.context_filter)
        contexts = [context for context in contexts if context.name in wanted_contexts]

    quantiles = args.quantile or [0.1, 0.25, 0.5, 0.75, 0.9]
    rows: list[Row] = []
    for config in configs:
        for context in contexts:
            for offset, quantile in enumerate(quantiles):
                rows.append(
                    evaluate(
                        config=config,
                        slack=args.slack,
                        context=context,
                        quantile=quantile,
                        passes=args.passes,
                        train_trials=args.train_trials,
                        eval_trials=args.eval_trials,
                        seed=args.seed + offset * 10_000_019,
                        min_rewrite_raw_fraction=args.min_rewrite_raw_frac,
                    )
                )
    print_rows(rows)


if __name__ == "__main__":
    main()
