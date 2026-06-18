#!/usr/bin/env python3
"""H117 - parseable payload-width symbols for forced due refresh.

H116 used the H114/H115 delta language: encode a symbol for

    delta = target_bits - payload_width

That is parseable for fixed atoms because `target_bits = arity * B` is known
after reading arity. It is not automatically parseable for heterogeneous record
streams, because the decoder generally does not know the generated target span
length before it has read the seed payload.

This kernel repeats the H116 forced-refresh experiment but codes the payload
width itself. The decoder can read:

    [arity][width-symbol][payload bits]

without a circular dependency on target length. Delta mode is retained only as
a labeled comparison.
"""

from __future__ import annotations

import argparse
import importlib.util
import math
import random
import sys
from collections import Counter, defaultdict
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
class SymbolModel:
    symbol: str
    context: h116.ContextSpec
    counts: dict[tuple[int, ...], Counter[int]]
    alpha: float
    slack: int
    frontier: int


@dataclass(frozen=True)
class TrialStats:
    config_name: str
    context_name: str
    visibility: str
    symbol: str
    passes: int
    total_delta_bits: float
    delta_per_raw_atom: float
    delta_per_raw_atom_pass: float
    final_bits_per_atom: float
    final_items_per_atom: float
    selected_records_per_atom_pass: float
    due_cover_rate: float
    avg_rewrite_fraction: float
    failed: bool


@dataclass(frozen=True)
class Row:
    config_name: str
    context_name: str
    visibility: str
    symbol: str
    slack: int
    passes: int
    trials: int
    delta_per_atom: float
    delta_per_atom_pass: float
    final_bits_per_atom: float
    final_items_per_atom: float
    selected_records_per_atom_pass: float
    due_cover_rate: float
    avg_rewrite_fraction: float
    fail_rate: float


def symbol_value(model: SymbolModel, edge: h116.RichEdge) -> int:
    if model.symbol == "width":
        return edge.payload_width
    if model.symbol == "delta":
        return edge.delta_value
    raise ValueError(model.symbol)


def support_values(model: SymbolModel, edge: h116.RichEdge) -> range:
    if model.symbol == "width":
        return range(1, model.frontier + 1)
    if model.symbol == "delta":
        lower, upper = h116.delta_range(edge, model.slack)
        return range(lower, upper + 1)
    raise ValueError(model.symbol)


def symbol_cost(model: SymbolModel, edge: h116.RichEdge) -> float:
    values = support_values(model, edge)
    value = symbol_value(model, edge)
    if value not in values:
        return float("inf")
    counts = model.counts.get(h116.context_for(model.context, edge), Counter())
    support = max(1, len(values))
    denom_count = sum(counts.get(candidate, 0) for candidate in values)
    denom = denom_count + model.alpha * support
    return -math.log2((counts.get(value, 0) + model.alpha) / denom)


def edge_delta(edge: h116.RichEdge, model: SymbolModel | None) -> float:
    if model is None:
        return float(edge.local_delta)
    cost = symbol_cost(model, edge)
    if not math.isfinite(cost):
        return float("inf")
    return edge.local_delta + cost


def select_step(
    config: h115.Config,
    items: list[h115.Item],
    slack: int,
    min_rewrite_raw_fraction: float,
    seed: int,
    model: SymbolModel | None,
    collect_edges: bool = False,
) -> tuple[list[h115.Item] | None, h116.StepStats, list[h116.RichEdge]]:
    edges_by_start = h116.sample_rich_edges(config, items, slack, random.Random(seed))
    total_raw = sum(item.raw_bits for item in items)
    due_seen = sum(1 for item in items if item.record_age == 1)
    n = len(items)
    inf = float("inf")
    dp = [[inf] * (total_raw + 1) for _ in range(n + 1)]
    prev: list[list[tuple[int, int, str, h116.RichEdge | None, list[h115.Item]] | None]] = [
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
                    prev[pos + 1][raw_done] = (pos, raw_done, "skip", None, outputs)

            for edge in edges_by_start[pos]:
                delta = edge_delta(edge, model)
                if not math.isfinite(delta):
                    continue
                end = pos + edge.arity
                new_raw = min(total_raw, raw_done + edge.raw_bits)
                record_bits = edge.local_cost
                if model is not None:
                    record_bits += symbol_cost(model, edge)
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
                    prev[end][new_raw] = (pos, raw_done, "edge", edge, output)

    min_raw = math.ceil(total_raw * min_rewrite_raw_fraction)
    best_raw = -1
    best_delta = inf
    for raw_done in range(min_raw, total_raw + 1):
        if dp[n][raw_done] < best_delta:
            best_delta = dp[n][raw_done]
            best_raw = raw_done
    if best_raw < 0:
        input_bits = sum(item.bits for item in items)
        return None, h116.StepStats(inf, input_bits, input_bits, 0, 0, due_seen, 0), []

    output_chunks: list[list[h115.Item]] = []
    selected = 0
    due_covered = 0
    selected_edges: list[h116.RichEdge] = []
    pos = n
    raw = best_raw
    while pos > 0:
        entry = prev[pos][raw]
        if entry is None:
            raise AssertionError("missing predecessor")
        prior_pos, prior_raw, kind, edge, outputs = entry
        output_chunks.append(outputs)
        if kind == "edge":
            selected += 1
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
    return next_items, h116.StepStats(
        delta_bits=best_delta,
        input_bits=input_bits,
        output_bits=output_bits,
        rewritten_raw_bits=best_raw,
        selected_records=selected,
        due_records_seen=due_seen,
        due_records_covered=due_covered,
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


def fit_model(
    config: h115.Config,
    slack: int,
    context: h116.ContextSpec,
    symbol: str,
    passes: int,
    train_trials: int,
    seed: int,
    min_rewrite_raw_fraction: float,
) -> SymbolModel:
    stub = SymbolModel(
        symbol=symbol,
        context=context,
        counts={},
        alpha=0.05,
        slack=slack,
        frontier=config.frontier,
    )
    counts: dict[tuple[int, ...], Counter[int]] = defaultdict(Counter)
    for trial in range(train_trials):
        edges = collect_local_edges(
            config,
            slack,
            passes,
            seed + trial * 1_000_003,
            min_rewrite_raw_fraction,
        )
        for edge in edges:
            counts[h116.context_for(context, edge)][symbol_value(stub, edge)] += 1
    return SymbolModel(
        symbol=symbol,
        context=context,
        counts=dict(counts),
        alpha=0.05,
        slack=slack,
        frontier=config.frontier,
    )


def simulate_trial(
    config: h115.Config,
    slack: int,
    context: h116.ContextSpec,
    symbol: str,
    passes: int,
    seed: int,
    model: SymbolModel,
    min_rewrite_raw_fraction: float,
) -> TrialStats:
    items = h115.initial_items(config)
    raw_atoms = sum(item.raw_bits for item in items) / config.block_bits
    total_delta = 0.0
    selected = 0
    due_seen = 0
    due_covered = 0
    rewrite_fracs: list[float] = []

    for step in range(passes):
        total_raw = sum(item.raw_bits for item in items)
        next_items, stats, _edges = select_step(
            config,
            items,
            slack,
            min_rewrite_raw_fraction,
            seed + step * 1_000_003,
            model,
            collect_edges=False,
        )
        if next_items is None:
            return TrialStats(
                config_name=config.name,
                context_name=context.name,
                visibility=context.visibility,
                symbol=symbol,
                passes=passes,
                total_delta_bits=float("inf"),
                delta_per_raw_atom=float("inf"),
                delta_per_raw_atom_pass=float("inf"),
                final_bits_per_atom=sum(item.bits for item in items) / raw_atoms,
                final_items_per_atom=len(items) / raw_atoms,
                selected_records_per_atom_pass=selected / raw_atoms / max(1, step + 1),
                due_cover_rate=0.0 if due_seen == 0 else due_covered / due_seen,
                avg_rewrite_fraction=mean(rewrite_fracs) if rewrite_fracs else 0.0,
                failed=True,
            )
        total_delta += stats.delta_bits
        selected += stats.selected_records
        due_seen += stats.due_records_seen
        due_covered += stats.due_records_covered
        rewrite_fracs.append(stats.rewritten_raw_bits / max(1, total_raw))
        items = next_items

    return TrialStats(
        config_name=config.name,
        context_name=context.name,
        visibility=context.visibility,
        symbol=symbol,
        passes=passes,
        total_delta_bits=total_delta,
        delta_per_raw_atom=total_delta / raw_atoms,
        delta_per_raw_atom_pass=total_delta / raw_atoms / passes,
        final_bits_per_atom=sum(item.bits for item in items) / raw_atoms,
        final_items_per_atom=len(items) / raw_atoms,
        selected_records_per_atom_pass=selected / raw_atoms / passes,
        due_cover_rate=1.0 if due_seen == 0 else due_covered / due_seen,
        avg_rewrite_fraction=mean(rewrite_fracs) if rewrite_fracs else 0.0,
        failed=False,
    )


def evaluate(
    config: h115.Config,
    slack: int,
    context: h116.ContextSpec,
    symbol: str,
    passes: int,
    train_trials: int,
    eval_trials: int,
    seed: int,
    min_rewrite_raw_fraction: float,
) -> Row:
    model = fit_model(
        config,
        slack,
        context,
        symbol,
        passes,
        train_trials,
        seed,
        min_rewrite_raw_fraction,
    )
    trials = [
        simulate_trial(
            config,
            slack,
            context,
            symbol,
            passes,
            seed + 99_999_937 + trial * 1_000_003,
            model,
            min_rewrite_raw_fraction,
        )
        for trial in range(eval_trials)
    ]
    finite = [trial for trial in trials if not trial.failed]
    fail_rate = 1.0 - len(finite) / len(trials)
    if not finite:
        return Row(
            config_name=config.name,
            context_name=context.name,
            visibility=context.visibility,
            symbol=symbol,
            slack=slack,
            passes=passes,
            trials=eval_trials,
            delta_per_atom=float("inf"),
            delta_per_atom_pass=float("inf"),
            final_bits_per_atom=float("inf"),
            final_items_per_atom=float("inf"),
            selected_records_per_atom_pass=0.0,
            due_cover_rate=0.0,
            avg_rewrite_fraction=0.0,
            fail_rate=fail_rate,
        )
    return Row(
        config_name=config.name,
        context_name=context.name,
        visibility=context.visibility,
        symbol=symbol,
        slack=slack,
        passes=passes,
        trials=eval_trials,
        delta_per_atom=mean(trial.delta_per_raw_atom for trial in finite),
        delta_per_atom_pass=mean(trial.delta_per_raw_atom_pass for trial in finite),
        final_bits_per_atom=mean(trial.final_bits_per_atom for trial in finite),
        final_items_per_atom=mean(trial.final_items_per_atom for trial in finite),
        selected_records_per_atom_pass=mean(trial.selected_records_per_atom_pass for trial in finite),
        due_cover_rate=mean(trial.due_cover_rate for trial in finite),
        avg_rewrite_fraction=mean(trial.avg_rewrite_fraction for trial in finite),
        fail_rate=fail_rate,
    )


def format_float(value: float) -> str:
    if math.isinf(value):
        return "inf"
    return f"{value:.6f}"


def print_rows(rows: list[Row]) -> None:
    print(
        "config,context,vis,symbol,slack,passes,trials,"
        "delta/atom,delta/atom/pass,finalb/atom,items/atom,"
        "sel/atom/pass,due_cover,rewrite_frac,fail"
    )
    for row in rows:
        print(
            f"{row.config_name},{row.context_name},{row.visibility},{row.symbol},"
            f"{row.slack},{row.passes},{row.trials},"
            f"{format_float(row.delta_per_atom)},"
            f"{format_float(row.delta_per_atom_pass)},"
            f"{format_float(row.final_bits_per_atom)},"
            f"{format_float(row.final_items_per_atom)},"
            f"{format_float(row.selected_records_per_atom_pass)},"
            f"{format_float(row.due_cover_rate)},"
            f"{format_float(row.avg_rewrite_fraction)},"
            f"{format_float(row.fail_rate)}"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--passes", type=int, default=4)
    parser.add_argument("--train-trials", type=int, default=6)
    parser.add_argument("--eval-trials", type=int, default=6)
    parser.add_argument("--seed", type=int, default=117_001)
    parser.add_argument("--slack", type=int, default=4)
    parser.add_argument("--min-rewrite-raw-frac", type=float, default=0.0)
    parser.add_argument("--period", type=int, default=16)
    parser.add_argument("--phase", type=int, default=0)
    parser.add_argument("--atoms", type=int, default=96)
    parser.add_argument("--symbol", choices=["width", "delta"], default="width")
    parser.add_argument("--config-filter", action="append", default=[])
    parser.add_argument("--context-filter", action="append", default=[])
    args = parser.parse_args()

    configs = h116.default_configs(args.atoms)
    if args.config_filter:
        wanted_configs = set(args.config_filter)
        configs = [config for config in configs if config.name in wanted_configs]

    contexts = h116.default_contexts(args.period, args.phase)
    if args.context_filter:
        wanted_contexts = set(args.context_filter)
        contexts = [context for context in contexts if context.name in wanted_contexts]

    rows: list[Row] = []
    for config in configs:
        for offset, context in enumerate(contexts):
            rows.append(
                evaluate(
                    config=config,
                    slack=args.slack,
                    context=context,
                    symbol=args.symbol,
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
