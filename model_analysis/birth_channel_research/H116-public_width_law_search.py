#!/usr/bin/env python3
"""H116 - search for public width laws for forced two-epoch refresh.

H115 found the first serious hole in H114: a fixed-atom width/delta law does
not survive the real record-layer stream once old compact records must refresh
before their seed-class parity aliases.

This kernel keeps the H115 transition and asks a narrower question:

    Which context features recover the local-width oracle, and are those
    features public to the decoder before the seed witness is read?

Rows are deliberately labeled as either:

* public: arity, output item index modulo a public period, and scheduled lanes;
* hidden: target length or actual age/literal composition of the interval.

A positive hidden row is not a codec. It only identifies the information that a
future position/lane geometry would have to make public and pay for.
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

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from total_cover_lotus_crossover import (
    fixed_arity_bits,
    local_payload_bits_from_log_rank,
    sample_log2_first_rank,
)

H115_PATH = Path(__file__).with_name("H115-two_epoch_record_layer.py")
H115_SPEC = importlib.util.spec_from_file_location("h115_record_layer", H115_PATH)
if H115_SPEC is None or H115_SPEC.loader is None:
    raise RuntimeError(f"could not load {H115_PATH}")
h115 = importlib.util.module_from_spec(H115_SPEC)
sys.modules[H115_SPEC.name] = h115
H115_SPEC.loader.exec_module(h115)


@dataclass(frozen=True)
class RichEdge:
    start: int
    arity: int
    payload_width: int
    target_bits: int
    raw_bits: int
    arity_bits: int
    item_count: int
    literal_count: int
    young_count: int
    old_count: int

    @property
    def delta_value(self) -> int:
        return self.target_bits - self.payload_width

    @property
    def local_cost(self) -> int:
        return self.arity_bits + self.payload_width

    @property
    def local_delta(self) -> int:
        return self.local_cost - self.target_bits


@dataclass(frozen=True)
class ContextSpec:
    name: str
    visibility: str
    period: int = 16
    phase: int = 0


@dataclass(frozen=True)
class WidthModel:
    context: ContextSpec
    counts: dict[tuple[int, ...], Counter[int]]
    alpha: float
    slack: int


@dataclass(frozen=True)
class StepStats:
    delta_bits: float
    input_bits: int
    output_bits: int
    rewritten_raw_bits: int
    selected_records: int
    due_records_seen: int
    due_records_covered: int


@dataclass(frozen=True)
class TrialStats:
    config_name: str
    context_name: str
    visibility: str
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


def arity_bucket(arity: int) -> int:
    if arity <= 1:
        return 0
    return min(12, int(math.log2(arity)))


def target_bucket(target_bits: int) -> int:
    if target_bits <= 1:
        return 0
    return min(16, int(math.log2(target_bits)))


def small_count(value: int) -> int:
    return min(8, value)


def public_lane_count(start: int, arity: int, period: int, phase: int) -> int:
    return sum(1 for pos in range(start, start + arity) if (pos + phase) % period == 0)


def context_for(spec: ContextSpec, edge: RichEdge) -> tuple[int, ...]:
    """Return the modeled context.

    Public contexts are known from the record arity and public output-item
    clock. Hidden contexts use facts about the target interval that the decoder
    does not know until after reading and expanding the seed witness.
    """

    if spec.name == "global":
        return ()
    if spec.name == "arity":
        return (arity_bucket(edge.arity),)
    if spec.name == "start_mod_arity":
        return (edge.start % spec.period, arity_bucket(edge.arity))
    if spec.name == "lane_due_arity":
        return (
            small_count(public_lane_count(edge.start, edge.arity, spec.period, spec.phase)),
            arity_bucket(edge.arity),
        )
    if spec.name == "target_arity":
        return (target_bucket(edge.target_bits), arity_bucket(edge.arity))
    if spec.name == "target_lane_arity":
        return (
            target_bucket(edge.target_bits),
            small_count(public_lane_count(edge.start, edge.arity, spec.period, spec.phase)),
            arity_bucket(edge.arity),
        )
    if spec.name == "composition":
        return (
            target_bucket(edge.target_bits),
            arity_bucket(edge.arity),
            small_count(edge.literal_count),
            small_count(edge.young_count),
            small_count(edge.old_count),
        )
    if spec.name == "age_only":
        return (
            arity_bucket(edge.arity),
            small_count(edge.young_count),
            small_count(edge.old_count),
        )
    raise ValueError(spec.name)


def delta_range(edge: RichEdge, slack: int) -> tuple[int, int]:
    return edge.arity_bits - slack, edge.target_bits - 1


def delta_cost(model: WidthModel, edge: RichEdge) -> float:
    lower, upper = delta_range(edge, model.slack)
    if edge.delta_value < lower or edge.delta_value > upper:
        return float("inf")
    support = max(1, upper - lower + 1)
    counts = model.counts.get(context_for(model.context, edge), Counter())
    denom_count = sum(counts.get(delta, 0) for delta in range(lower, upper + 1))
    denom = denom_count + model.alpha * support
    return -math.log2((counts.get(edge.delta_value, 0) + model.alpha) / denom)


def sample_rich_edges(config: h115.Config, items: list[h115.Item], slack: int, rng: random.Random) -> list[list[RichEdge]]:
    prefix_bits = [0]
    prefix_raw = [0]
    prefix_lit = [0]
    prefix_young = [0]
    prefix_old = [0]
    for item in items:
        prefix_bits.append(prefix_bits[-1] + item.bits)
        prefix_raw.append(prefix_raw[-1] + item.raw_bits)
        prefix_lit.append(prefix_lit[-1] + (1 if item.record_age is None else 0))
        prefix_young.append(prefix_young[-1] + (1 if item.record_age == 0 else 0))
        prefix_old.append(prefix_old[-1] + (1 if item.record_age == 1 else 0))

    edges_by_start: list[list[RichEdge]] = [[] for _ in items]
    for start in range(len(items)):
        legal = min(config.max_arity, len(items) - start)
        for arity in range(1, legal + 1):
            end = start + arity
            target_bits = prefix_bits[end] - prefix_bits[start]
            raw_bits = prefix_raw[end] - prefix_raw[start]
            local_width = local_payload_bits_from_log_rank(sample_log2_first_rank(target_bits, rng))
            payload_width = local_width + config.class_bits
            if payload_width > config.frontier:
                continue
            edge = RichEdge(
                start=start,
                arity=arity,
                payload_width=payload_width,
                target_bits=target_bits,
                raw_bits=raw_bits,
                arity_bits=fixed_arity_bits(config.max_arity, arity),
                item_count=arity,
                literal_count=prefix_lit[end] - prefix_lit[start],
                young_count=prefix_young[end] - prefix_young[start],
                old_count=prefix_old[end] - prefix_old[start],
            )
            if edge.local_delta <= slack:
                edges_by_start[start].append(edge)
    return edges_by_start


def edge_delta(edge: RichEdge, model: WidthModel | None) -> float:
    if model is None:
        return float(edge.local_delta)
    return edge.local_delta + delta_cost(model, edge)


def select_step(
    config: h115.Config,
    items: list[h115.Item],
    slack: int,
    min_rewrite_raw_fraction: float,
    seed: int,
    model: WidthModel | None,
    collect_edges: bool = False,
) -> tuple[list[h115.Item] | None, StepStats, list[RichEdge]]:
    edges_by_start = sample_rich_edges(config, items, slack, random.Random(seed))
    total_raw = sum(item.raw_bits for item in items)
    due_seen = sum(1 for item in items if item.record_age == 1)
    n = len(items)
    inf = float("inf")
    dp = [[inf] * (total_raw + 1) for _ in range(n + 1)]
    prev: list[list[tuple[int, int, str, RichEdge | None, list[h115.Item]] | None]] = [
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
                    record_bits += delta_cost(model, edge)
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
        return None, StepStats(inf, input_bits, input_bits, 0, 0, due_seen, 0), []

    output_chunks: list[list[h115.Item]] = []
    selected = 0
    due_covered = 0
    selected_edges: list[RichEdge] = []
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
    return next_items, StepStats(
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
) -> list[RichEdge]:
    items = h115.initial_items(config)
    edges: list[RichEdge] = []
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
    context: ContextSpec,
    passes: int,
    train_trials: int,
    seed: int,
    min_rewrite_raw_fraction: float,
) -> WidthModel:
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
            counts[context_for(context, edge)][edge.delta_value] += 1
    return WidthModel(context=context, counts=dict(counts), alpha=0.05, slack=slack)


def simulate_trial(
    config: h115.Config,
    slack: int,
    context: ContextSpec,
    passes: int,
    seed: int,
    model: WidthModel,
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
    context: ContextSpec,
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


def default_configs(atoms: int) -> list[h115.Config]:
    return [
        h115.Config(
            name="H114_raw_lower",
            block_bits=4,
            initial_item_bits=4,
            atoms=atoms,
            max_arity=32,
            frontier=128,
            literal_marker_bits=3,
            class_bits=1,
        ),
        h115.Config(
            name="public_lane_raw",
            block_bits=4,
            initial_item_bits=4,
            atoms=atoms,
            max_arity=32,
            frontier=128,
            literal_marker_bits=3,
            class_bits=0,
        ),
        h115.Config(
            name="literal_wrapped",
            block_bits=4,
            initial_item_bits=7,
            atoms=atoms,
            max_arity=32,
            frontier=128,
            literal_marker_bits=3,
            class_bits=1,
        ),
    ]


def default_contexts(period: int, phase: int) -> list[ContextSpec]:
    return [
        ContextSpec("global", "public", period, phase),
        ContextSpec("arity", "public", period, phase),
        ContextSpec("start_mod_arity", "public", period, phase),
        ContextSpec("lane_due_arity", "public", period, phase),
        ContextSpec("target_arity", "hidden", period, phase),
        ContextSpec("target_lane_arity", "hidden", period, phase),
        ContextSpec("age_only", "hidden", period, phase),
        ContextSpec("composition", "hidden", period, phase),
    ]


def format_float(value: float) -> str:
    if math.isinf(value):
        return "inf"
    return f"{value:.6f}"


def print_rows(rows: list[Row]) -> None:
    print(
        "config,context,vis,slack,passes,trials,"
        "delta/atom,delta/atom/pass,finalb/atom,items/atom,"
        "sel/atom/pass,due_cover,rewrite_frac,fail"
    )
    for row in rows:
        print(
            f"{row.config_name},{row.context_name},{row.visibility},{row.slack},"
            f"{row.passes},{row.trials},{format_float(row.delta_per_atom)},"
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
    parser.add_argument("--train-trials", type=int, default=12)
    parser.add_argument("--eval-trials", type=int, default=12)
    parser.add_argument("--seed", type=int, default=116_001)
    parser.add_argument("--slack", type=int, default=4)
    parser.add_argument("--min-rewrite-raw-frac", type=float, default=0.0)
    parser.add_argument("--period", type=int, default=16)
    parser.add_argument("--phase", type=int, default=0)
    parser.add_argument("--atoms", type=int, default=128)
    parser.add_argument("--config-filter", action="append", default=[])
    parser.add_argument("--context-filter", action="append", default=[])
    args = parser.parse_args()

    configs = default_configs(args.atoms)
    if args.config_filter:
        wanted = set(args.config_filter)
        configs = [config for config in configs if config.name in wanted]

    contexts = default_contexts(args.period, args.phase)
    if args.context_filter:
        wanted = set(args.context_filter)
        contexts = [context for context in contexts if context.name in wanted]

    rows: list[Row] = []
    for config in configs:
        for offset, context in enumerate(contexts):
            rows.append(
                evaluate(
                    config=config,
                    slack=args.slack,
                    context=context,
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
