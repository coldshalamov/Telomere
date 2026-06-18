#!/usr/bin/env python3
"""H132 - self-consistent width-aware selection.

H116/H118/H120 showed that width metadata is a major boundary channel. Ohm's
remaining concrete witness-family idea is to make the cover selector internalize
that cost: prefer edges whose payload widths follow a low-entropy public law,
instead of selecting first and trying to hide width later.

This kernel trains a frozen public width model by iteration:

1. select covers using current `-log2 P(width | public context)` cost;
2. update the public width law from the selected edges;
3. repeat on train trials;
4. evaluate held-out with the frozen law.

It is not a compressor. It asks whether width entropy can collapse under its
own paid objective in the forced-refresh record-layer toy.
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
class WidthLaw:
    context: h116.ContextSpec
    counts: dict[tuple[int, ...], Counter[int]]
    alpha: float


@dataclass(frozen=True)
class StepStats:
    delta_bits: float
    input_bits: int
    output_bits: int
    width_bits: float
    rewritten_raw_bits: int
    selected_records: int
    due_records_seen: int
    due_records_covered: int
    selected_edges: tuple[h116.RichEdge, ...]


@dataclass(frozen=True)
class TrialStats:
    failed: bool
    delta_per_atom: float
    delta_per_atom_pass: float
    width_bits_per_record: float
    width_bits_per_atom_pass: float
    selected_records_per_atom_pass: float
    avg_rewrite_fraction: float
    due_cover_rate: float
    final_bits_per_atom: float


@dataclass(frozen=True)
class Row:
    config_name: str
    context_name: str
    visibility: str
    atoms: int
    passes: int
    train_trials: int
    eval_trials: int
    iterations: int
    min_rewrite: float
    delta_per_atom: float
    delta_per_atom_pass: float
    width_bits_per_record: float
    width_bits_per_atom_pass: float
    selected_records_per_atom_pass: float
    avg_rewrite_fraction: float
    due_cover_rate: float
    final_bits_per_atom: float
    fail_rate: float
    model_contexts: int
    model_widths: int


def width_cost(law: WidthLaw, edge: h116.RichEdge) -> float:
    key = h116.context_for(law.context, edge)
    counts = law.counts.get(key, Counter())
    if counts:
        lo = min(counts)
        hi = max(counts)
    else:
        lo = max(0, edge.payload_width - 16)
        hi = edge.payload_width + 16
    lo = min(lo, edge.payload_width)
    hi = max(hi, edge.payload_width)
    support = max(1, hi - lo + 1)
    total = sum(counts.get(width, 0) for width in range(lo, hi + 1))
    numerator = counts.get(edge.payload_width, 0) + law.alpha
    denominator = total + law.alpha * support
    return -math.log2(numerator / denominator)


def select_step(
    config: h115.Config,
    items: list[h115.Item],
    slack: int,
    min_rewrite_raw_fraction: float,
    seed: int,
    law: WidthLaw,
    collect_edges: bool = False,
) -> tuple[list[h115.Item] | None, StepStats]:
    edges_by_start = h116.sample_rich_edges(config, items, slack, random.Random(seed))
    total_raw = sum(item.raw_bits for item in items)
    due_seen = sum(1 for item in items if item.record_age == 1)
    n = len(items)
    inf = float("inf")
    dp = [[inf] * (total_raw + 1) for _ in range(n + 1)]
    prev: list[list[tuple[int, int, str, h116.RichEdge | None, list[h115.Item], float] | None]] = [
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
                    prev[pos + 1][raw_done] = (pos, raw_done, "skip", None, outputs, 0.0)

            for edge in edges_by_start[pos]:
                width_bits = width_cost(law, edge)
                delta = edge.local_delta + width_bits
                if not math.isfinite(delta):
                    continue
                end = pos + edge.arity
                new_raw = min(total_raw, raw_done + edge.raw_bits)
                record_bits = edge.local_cost + width_bits
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
                    prev[end][new_raw] = (pos, raw_done, "edge", edge, output, width_bits)

    min_raw = math.ceil(total_raw * min_rewrite_raw_fraction)
    best_raw = -1
    best_delta = inf
    for raw_done in range(min_raw, total_raw + 1):
        if dp[n][raw_done] < best_delta:
            best_delta = dp[n][raw_done]
            best_raw = raw_done
    if best_raw < 0:
        input_bits = sum(item.bits for item in items)
        return None, StepStats(inf, input_bits, input_bits, 0.0, 0, 0, due_seen, 0, tuple())

    output_chunks: list[list[h115.Item]] = []
    selected = 0
    due_covered = 0
    width_bits_total = 0.0
    selected_edges: list[h116.RichEdge] = []
    pos = n
    raw = best_raw
    while pos > 0:
        entry = prev[pos][raw]
        if entry is None:
            raise AssertionError("missing predecessor")
        prior_pos, prior_raw, kind, edge, outputs, width_bits = entry
        output_chunks.append(outputs)
        if kind == "edge":
            selected += 1
            width_bits_total += width_bits
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
        width_bits=width_bits_total,
        rewritten_raw_bits=best_raw,
        selected_records=selected,
        due_records_seen=due_seen,
        due_records_covered=due_covered,
        selected_edges=tuple(selected_edges),
    )


def collect_edges_for_trials(
    config: h115.Config,
    slack: int,
    law: WidthLaw,
    passes: int,
    trials: int,
    seed: int,
    min_rewrite_raw_fraction: float,
) -> list[h116.RichEdge]:
    edges: list[h116.RichEdge] = []
    for trial in range(trials):
        items = h115.initial_items(config)
        for step in range(passes):
            next_items, stats = select_step(
                config,
                items,
                slack,
                min_rewrite_raw_fraction,
                seed + trial * 1_000_003 + step * 9_176,
                law,
                collect_edges=True,
            )
            if next_items is None:
                break
            edges.extend(stats.selected_edges)
            items = next_items
    return edges


def law_from_edges(context: h116.ContextSpec, edges: list[h116.RichEdge], alpha: float) -> WidthLaw:
    counts: dict[tuple[int, ...], Counter[int]] = defaultdict(Counter)
    for edge in edges:
        counts[h116.context_for(context, edge)][edge.payload_width] += 1
    return WidthLaw(context=context, counts=dict(counts), alpha=alpha)


def initial_law(context: h116.ContextSpec, alpha: float) -> WidthLaw:
    return WidthLaw(context=context, counts={}, alpha=alpha)


def train_law(
    config: h115.Config,
    slack: int,
    context: h116.ContextSpec,
    passes: int,
    train_trials: int,
    seed: int,
    min_rewrite_raw_fraction: float,
    iterations: int,
    alpha: float,
) -> WidthLaw:
    law = initial_law(context, alpha)
    for iteration in range(iterations):
        edges = collect_edges_for_trials(
            config,
            slack,
            law,
            passes,
            train_trials,
            seed + iteration * 10_000_019,
            min_rewrite_raw_fraction,
        )
        law = law_from_edges(context, edges, alpha)
    return law


def simulate_trial(
    config: h115.Config,
    slack: int,
    law: WidthLaw,
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
    width_bits = 0.0
    rewrite_fracs: list[float] = []
    for step in range(passes):
        total_raw = sum(item.raw_bits for item in items)
        next_items, stats = select_step(
            config,
            items,
            slack,
            min_rewrite_raw_fraction,
            seed + step * 1_000_003,
            law,
        )
        if next_items is None:
            return TrialStats(True, float("inf"), float("inf"), 0.0, 0.0, 0.0, 0.0, 0.0, float("inf"))
        total_delta += stats.delta_bits
        selected += stats.selected_records
        due_seen += stats.due_records_seen
        due_covered += stats.due_records_covered
        width_bits += stats.width_bits
        rewrite_fracs.append(stats.rewritten_raw_bits / max(1, total_raw))
        items = next_items
    return TrialStats(
        failed=False,
        delta_per_atom=total_delta / raw_atoms,
        delta_per_atom_pass=total_delta / raw_atoms / passes,
        width_bits_per_record=width_bits / max(1, selected),
        width_bits_per_atom_pass=width_bits / raw_atoms / passes,
        selected_records_per_atom_pass=selected / raw_atoms / passes,
        avg_rewrite_fraction=mean(rewrite_fracs) if rewrite_fracs else 0.0,
        due_cover_rate=1.0 if due_seen == 0 else due_covered / due_seen,
        final_bits_per_atom=sum(item.bits for item in items) / raw_atoms,
    )


def evaluate(
    config: h115.Config,
    slack: int,
    context: h116.ContextSpec,
    passes: int,
    train_trials: int,
    eval_trials: int,
    seed: int,
    min_rewrite_raw_fraction: float,
    iterations: int,
    alpha: float,
) -> Row:
    law = train_law(
        config,
        slack,
        context,
        passes,
        train_trials,
        seed,
        min_rewrite_raw_fraction,
        iterations,
        alpha,
    )
    trials = [
        simulate_trial(
            config,
            slack,
            law,
            passes,
            seed + 99_999_937 + trial * 1_000_003,
            min_rewrite_raw_fraction,
        )
        for trial in range(eval_trials)
    ]
    finite = [trial for trial in trials if not trial.failed]
    fail_rate = 1.0 - len(finite) / len(trials)
    model_widths = sum(len(counter) for counter in law.counts.values())
    if not finite:
        return Row(
            config.name,
            context.name,
            context.visibility,
            config.atoms,
            passes,
            train_trials,
            eval_trials,
            iterations,
            min_rewrite_raw_fraction,
            float("inf"),
            float("inf"),
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            float("inf"),
            fail_rate,
            len(law.counts),
            model_widths,
        )
    return Row(
        config.name,
        context.name,
        context.visibility,
        config.atoms,
        passes,
        train_trials,
        eval_trials,
        iterations,
        min_rewrite_raw_fraction,
        mean(trial.delta_per_atom for trial in finite),
        mean(trial.delta_per_atom_pass for trial in finite),
        mean(trial.width_bits_per_record for trial in finite),
        mean(trial.width_bits_per_atom_pass for trial in finite),
        mean(trial.selected_records_per_atom_pass for trial in finite),
        mean(trial.avg_rewrite_fraction for trial in finite),
        mean(trial.due_cover_rate for trial in finite),
        mean(trial.final_bits_per_atom for trial in finite),
        fail_rate,
        len(law.counts),
        model_widths,
    )


def fmt(value: float) -> str:
    if math.isinf(value):
        return "inf"
    return f"{value:.6f}"


def print_rows(rows: list[Row]) -> None:
    print(
        "config,context,vis,atoms,passes,train,eval,iters,min_rewrite,"
        "delta/atom,delta/atom/pass,width/rec,width/atom/pass,sel/atom/pass,"
        "rewrite_frac,due_cover,final_bits/atom,fail,model_contexts,model_widths"
    )
    for row in rows:
        print(
            f"{row.config_name},{row.context_name},{row.visibility},"
            f"{row.atoms},{row.passes},{row.train_trials},{row.eval_trials},"
            f"{row.iterations},{row.min_rewrite:.3f},"
            f"{fmt(row.delta_per_atom)},{fmt(row.delta_per_atom_pass)},"
            f"{fmt(row.width_bits_per_record)},"
            f"{fmt(row.width_bits_per_atom_pass)},"
            f"{fmt(row.selected_records_per_atom_pass)},"
            f"{fmt(row.avg_rewrite_fraction)},"
            f"{fmt(row.due_cover_rate)},"
            f"{fmt(row.final_bits_per_atom)},"
            f"{fmt(row.fail_rate)},"
            f"{row.model_contexts},{row.model_widths}"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--passes", type=int, default=4)
    parser.add_argument("--train-trials", type=int, default=4)
    parser.add_argument("--eval-trials", type=int, default=8)
    parser.add_argument("--seed", type=int, default=132_001)
    parser.add_argument("--slack", type=int, default=4)
    parser.add_argument("--atoms", type=int, default=128)
    parser.add_argument("--min-rewrite-raw-frac", type=float, default=0.25)
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--config-filter", action="append", default=[])
    parser.add_argument("--context-filter", action="append", default=[])
    args = parser.parse_args()

    configs = h116.default_configs(args.atoms)
    if args.config_filter:
        wanted_configs = set(args.config_filter)
        configs = [config for config in configs if config.name in wanted_configs]

    contexts = h116.default_contexts(period=16, phase=0)
    if args.context_filter:
        wanted_contexts = set(args.context_filter)
        contexts = [context for context in contexts if context.name in wanted_contexts]

    rows: list[Row] = []
    for config in configs:
        for context in contexts:
            rows.append(
                evaluate(
                    config=config,
                    slack=args.slack,
                    context=context,
                    passes=args.passes,
                    train_trials=args.train_trials,
                    eval_trials=args.eval_trials,
                    seed=args.seed,
                    min_rewrite_raw_fraction=args.min_rewrite_raw_frac,
                    iterations=args.iterations,
                    alpha=args.alpha,
                )
            )
    print_rows(rows)


if __name__ == "__main__":
    main()
