#!/usr/bin/env python3
"""H115 - two-epoch record-layer accounting for the H114 target.

H114 crossed in a fixed-B atom DP. Its skip action represented "carry the
current atom" at zero delta, and visible seed parity replaced the H2
ready/carry map under a two-epoch age bound.

This kernel asks whether the crossing survives when the layer is actually a
stream of self-delimiting items:

* new records have variable bit lengths;
* carried records can live for one pass;
* records that would live for a second carry must be refreshed or literalized;
* the frozen delta law is trained on independent layers, then held fixed.

It is still a toy kernel. It does not claim to implement SPEC_V1. The purpose
is to price the hidden channel H114 was most likely to have missed.
"""

from __future__ import annotations

import argparse
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


@dataclass(frozen=True)
class Config:
    name: str
    block_bits: int
    initial_item_bits: int
    atoms: int
    max_arity: int
    frontier: int
    literal_marker_bits: int
    class_bits: int = 1


@dataclass(frozen=True)
class Item:
    bits: int
    raw_bits: int
    record_age: int | None

    @property
    def is_record(self) -> bool:
        return self.record_age is not None


@dataclass(frozen=True)
class Edge:
    start: int
    arity: int
    payload_width: int
    target_bits: int
    raw_bits: int
    arity_bits: int

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
class DeltaModel:
    context: str
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
    expired_records: int
    expiry_tax_bits: int


@dataclass(frozen=True)
class TrialStats:
    mode: str
    config: Config
    passes: int
    total_delta_bits: float
    delta_per_raw_atom: float
    delta_per_raw_atom_pass: float
    final_bits: int
    final_items: int
    selected_records_per_atom_pass: float
    expired_records_per_atom_pass: float
    expiry_tax_per_atom_pass: float
    avg_rewrite_fraction: float
    failed: bool


@dataclass(frozen=True)
class Row:
    mode: str
    config: Config
    context: str
    slack: int
    passes: int
    trials: int
    delta_per_atom: float
    delta_per_atom_pass: float
    final_bits_per_atom: float
    final_items_per_atom: float
    selected_records_per_atom_pass: float
    expired_records_per_atom_pass: float
    expiry_tax_per_atom_pass: float
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


def context_for(mode: str, edge: Edge) -> tuple[int, ...]:
    if mode == "global":
        return ()
    if mode == "arity_bucket":
        return (arity_bucket(edge.arity),)
    if mode == "target_arity_bucket":
        return (target_bucket(edge.target_bits), arity_bucket(edge.arity))
    raise ValueError(mode)


def delta_range(edge: Edge, slack: int) -> tuple[int, int]:
    return edge.arity_bits - slack, edge.target_bits - 1


def delta_cost(model: DeltaModel, edge: Edge) -> float:
    lower, upper = delta_range(edge, model.slack)
    if edge.delta_value < lower or edge.delta_value > upper:
        return float("inf")
    support = max(1, upper - lower + 1)
    counts = model.counts.get(context_for(model.context, edge), Counter())
    denom_count = sum(counts.get(delta, 0) for delta in range(lower, upper + 1))
    denom = denom_count + model.alpha * support
    return -math.log2((counts.get(edge.delta_value, 0) + model.alpha) / denom)


def initial_items(config: Config) -> list[Item]:
    return [
        Item(bits=config.initial_item_bits, raw_bits=config.block_bits, record_age=None)
        for _ in range(config.atoms)
    ]


def literalized_items(config: Config, raw_bits: int, marker_mode: str) -> list[Item]:
    blocks = math.ceil(raw_bits / config.block_bits)
    if marker_mode == "raw_one_item":
        return [Item(bits=raw_bits, raw_bits=raw_bits, record_age=None)]
    if marker_mode == "literal_items":
        return [
            Item(
                bits=config.block_bits + config.literal_marker_bits,
                raw_bits=config.block_bits,
                record_age=None,
            )
            for _ in range(blocks)
        ]
    raise ValueError(marker_mode)


def sample_edges(config: Config, items: list[Item], slack: int, rng: random.Random) -> list[list[Edge]]:
    prefix_bits = [0]
    prefix_raw = [0]
    for item in items:
        prefix_bits.append(prefix_bits[-1] + item.bits)
        prefix_raw.append(prefix_raw[-1] + item.raw_bits)

    edges_by_start: list[list[Edge]] = [[] for _ in items]
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
            edge = Edge(
                start=start,
                arity=arity,
                payload_width=payload_width,
                target_bits=target_bits,
                raw_bits=raw_bits,
                arity_bits=fixed_arity_bits(config.max_arity, arity),
            )
            if edge.local_delta <= slack:
                edges_by_start[start].append(edge)
    return edges_by_start


def edge_delta(edge: Edge, model: DeltaModel | None, mode: str) -> float:
    if mode == "local":
        return float(edge.local_delta)
    if mode == "frozen":
        if model is None:
            raise ValueError("frozen mode needs model")
        return edge.local_delta + delta_cost(model, edge)
    raise ValueError(mode)


def skip_outputs(config: Config, item: Item, expiry_mode: str) -> tuple[float, list[Item], int, int]:
    if item.record_age is None:
        return 0.0, [item], 0, 0
    if item.record_age == 0:
        return 0.0, [Item(bits=item.bits, raw_bits=item.raw_bits, record_age=1)], 0, 0
    if item.record_age != 1:
        raise AssertionError("record age must be 0 or 1")

    if expiry_mode == "no_expiry_lower_bound":
        return 0.0, [item], 0, 0
    if expiry_mode == "force_refresh":
        return float("inf"), [], 0, 0

    marker_mode = "raw_one_item" if expiry_mode == "expire_raw_lower_bound" else "literal_items"
    outputs = literalized_items(config, item.raw_bits, marker_mode)
    output_bits = sum(out.bits for out in outputs)
    tax = output_bits - item.bits
    return float(tax), outputs, 1, tax


def select_step(
    config: Config,
    items: list[Item],
    slack: int,
    min_rewrite_raw_fraction: float,
    seed: int,
    selection_mode: str,
    model: DeltaModel | None,
    expiry_mode: str,
) -> tuple[list[Item] | None, StepStats]:
    edges_by_start = sample_edges(config, items, slack, random.Random(seed))
    total_raw = sum(item.raw_bits for item in items)
    n = len(items)
    inf = float("inf")
    dp = [[inf] * (total_raw + 1) for _ in range(n + 1)]
    prev: list[list[tuple[int, int, str, Edge | None, list[Item], int, int] | None]] = [
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
                    prev[pos + 1][raw_done] = (pos, raw_done, "skip", None, outputs, expired, tax)

            for edge in edges_by_start[pos]:
                delta = edge_delta(edge, model, selection_mode)
                if not math.isfinite(delta):
                    continue
                end = pos + edge.arity
                new_raw = min(total_raw, raw_done + edge.raw_bits)
                record_bits = edge.local_cost
                if selection_mode == "frozen" and model is not None:
                    record_bits += delta_cost(model, edge)
                # record_bits can be fractional when arithmetic-coded under the
                # frozen public model. Keep the DP in bits, but round output
                # item bits up for the next layer because a real stream cannot
                # expose fractional item lengths.
                output = [
                    Item(
                        bits=math.ceil(record_bits),
                        raw_bits=edge.raw_bits,
                        record_age=0,
                    )
                ]
                candidate = base + delta
                if candidate < dp[end][new_raw]:
                    dp[end][new_raw] = candidate
                    prev[end][new_raw] = (pos, raw_done, "edge", edge, output, 0, 0)

    min_raw = math.ceil(total_raw * min_rewrite_raw_fraction)
    best_raw = -1
    best_delta = inf
    for raw_done in range(min_raw, total_raw + 1):
        if dp[n][raw_done] < best_delta:
            best_delta = dp[n][raw_done]
            best_raw = raw_done
    if best_raw < 0:
        input_bits = sum(item.bits for item in items)
        return None, StepStats(inf, input_bits, input_bits, 0, 0, 0, 0)

    output_chunks: list[list[Item]] = []
    selected = 0
    expired_records = 0
    expiry_tax = 0
    pos = n
    raw = best_raw
    while pos > 0:
        entry = prev[pos][raw]
        if entry is None:
            raise AssertionError("missing predecessor")
        prior_pos, prior_raw, kind, _edge, outputs, expired, tax = entry
        output_chunks.append(outputs)
        if kind == "edge":
            selected += 1
        expired_records += expired
        expiry_tax += tax
        pos = prior_pos
        raw = prior_raw

    next_items = [item for chunk in reversed(output_chunks) for item in chunk]
    input_bits = sum(item.bits for item in items)
    output_bits = sum(item.bits for item in next_items)
    return next_items, StepStats(
        delta_bits=best_delta,
        input_bits=input_bits,
        output_bits=output_bits,
        rewritten_raw_bits=best_raw,
        selected_records=selected,
        expired_records=expired_records,
        expiry_tax_bits=expiry_tax,
    )


def simulate_trial(
    config: Config,
    slack: int,
    context: str,
    passes: int,
    seed: int,
    selection_mode: str,
    model: DeltaModel | None,
    expiry_mode: str,
    min_rewrite_raw_fraction: float,
) -> tuple[TrialStats, list[Edge]]:
    items = initial_items(config)
    total_delta = 0.0
    selected = 0
    expired = 0
    expiry_tax = 0
    rewrite_fracs: list[float] = []
    selected_edges: list[Edge] = []

    for step in range(passes):
        before_items = items
        next_items, stats = select_step(
            config,
            before_items,
            slack,
            min_rewrite_raw_fraction,
            seed + step * 1_000_003,
            selection_mode,
            model,
            expiry_mode,
        )
        if next_items is None:
            raw_atoms = sum(item.raw_bits for item in initial_items(config)) / config.block_bits
            return TrialStats(
                mode=expiry_mode,
                config=config,
                passes=passes,
                total_delta_bits=float("inf"),
                delta_per_raw_atom=float("inf"),
                delta_per_raw_atom_pass=float("inf"),
                final_bits=sum(item.bits for item in before_items),
                final_items=len(before_items),
                selected_records_per_atom_pass=0.0,
                expired_records_per_atom_pass=0.0,
                expiry_tax_per_atom_pass=0.0,
                avg_rewrite_fraction=0.0,
                failed=True,
            ), selected_edges
        total_delta += stats.delta_bits
        selected += stats.selected_records
        expired += stats.expired_records
        expiry_tax += stats.expiry_tax_bits
        rewrite_fracs.append(stats.rewritten_raw_bits / max(1, sum(item.raw_bits for item in before_items)))
        # Re-sample the same step's edges to collect local-training observations
        # only when requested by caller through selection_mode="local".
        if selection_mode == "local":
            # Cheap reconstruction of selected edge statistics is not needed for
            # transition correctness. Collect by walking the output records: the
            # selected edge deltas are sampled again deterministically with the
            # same seed in fit_model where exact choices are needed.
            pass
        items = next_items

    raw_atoms = sum(item.raw_bits for item in initial_items(config)) / config.block_bits
    return TrialStats(
        mode=expiry_mode,
        config=config,
        passes=passes,
        total_delta_bits=total_delta,
        delta_per_raw_atom=total_delta / raw_atoms,
        delta_per_raw_atom_pass=total_delta / raw_atoms / passes,
        final_bits=sum(item.bits for item in items),
        final_items=len(items),
        selected_records_per_atom_pass=selected / raw_atoms / passes,
        expired_records_per_atom_pass=expired / raw_atoms / passes,
        expiry_tax_per_atom_pass=expiry_tax / raw_atoms / passes,
        avg_rewrite_fraction=mean(rewrite_fracs) if rewrite_fracs else 0.0,
        failed=False,
    ), selected_edges


def collect_local_edges(
    config: Config,
    slack: int,
    passes: int,
    seed: int,
    expiry_mode: str,
    min_rewrite_raw_fraction: float,
) -> list[Edge]:
    """Run a local-oracle transition and collect selected edge observations."""

    items = initial_items(config)
    selected_edges: list[Edge] = []
    for step in range(passes):
        # Duplicate select_step with traceback collection kept simple by using a
        # temporary model that returns local edges through predecessor entries.
        edges_by_start = sample_edges(config, items, slack, random.Random(seed + step * 1_000_003))
        total_raw = sum(item.raw_bits for item in items)
        n = len(items)
        inf = float("inf")
        dp = [[inf] * (total_raw + 1) for _ in range(n + 1)]
        prev: list[list[tuple[int, int, Edge | None, list[Item]] | None]] = [
            [None] * (total_raw + 1) for _ in range(n + 1)
        ]
        dp[0][0] = 0.0
        for pos in range(n):
            for raw_done in range(total_raw + 1):
                base = dp[pos][raw_done]
                if base == inf:
                    continue
                skip_delta, outputs, _, _ = skip_outputs(config, items[pos], expiry_mode)
                if math.isfinite(skip_delta) and base + skip_delta < dp[pos + 1][raw_done]:
                    dp[pos + 1][raw_done] = base + skip_delta
                    prev[pos + 1][raw_done] = (pos, raw_done, None, outputs)
                for edge in edges_by_start[pos]:
                    end = pos + edge.arity
                    new_raw = min(total_raw, raw_done + edge.raw_bits)
                    candidate = base + edge.local_delta
                    if candidate < dp[end][new_raw]:
                        dp[end][new_raw] = candidate
                        prev[end][new_raw] = (
                            pos,
                            raw_done,
                            edge,
                            [Item(bits=edge.local_cost, raw_bits=edge.raw_bits, record_age=0)],
                        )
        min_raw = math.ceil(total_raw * min_rewrite_raw_fraction)
        best_raw = min(range(min_raw, total_raw + 1), key=lambda raw: dp[n][raw])
        if dp[n][best_raw] == inf:
            break
        chunks: list[list[Item]] = []
        pos = n
        raw = best_raw
        while pos > 0:
            entry = prev[pos][raw]
            if entry is None:
                raise AssertionError("missing predecessor")
            prior_pos, prior_raw, edge, outputs = entry
            if edge is not None:
                selected_edges.append(edge)
            chunks.append(outputs)
            pos = prior_pos
            raw = prior_raw
        items = [item for chunk in reversed(chunks) for item in chunk]
    return selected_edges


def fit_model(
    config: Config,
    slack: int,
    context: str,
    passes: int,
    train_trials: int,
    seed: int,
    expiry_mode: str,
    min_rewrite_raw_fraction: float,
) -> DeltaModel:
    counts: dict[tuple[int, ...], Counter[int]] = defaultdict(Counter)
    for trial in range(train_trials):
        edges = collect_local_edges(
            config,
            slack,
            passes,
            seed + trial * 1_000_003,
            expiry_mode,
            min_rewrite_raw_fraction,
        )
        for edge in edges:
            counts[context_for(context, edge)][edge.delta_value] += 1
    return DeltaModel(context=context, counts=dict(counts), alpha=0.05, slack=slack)


def evaluate(
    config: Config,
    slack: int,
    context: str,
    passes: int,
    train_trials: int,
    eval_trials: int,
    seed: int,
    expiry_mode: str,
    min_rewrite_raw_fraction: float,
) -> Row:
    model = fit_model(
        config,
        slack,
        context,
        passes,
        train_trials,
        seed,
        expiry_mode,
        min_rewrite_raw_fraction,
    )
    trials = [
        simulate_trial(
            config,
            slack,
            context,
            passes,
            seed + 99_991 + trial * 1_000_003,
            "frozen",
            model,
            expiry_mode,
            min_rewrite_raw_fraction,
        )[0]
        for trial in range(eval_trials)
    ]
    failed = [trial for trial in trials if trial.failed]
    ok = [trial for trial in trials if not trial.failed]
    if not ok:
        return Row(
            mode=expiry_mode,
            config=config,
            context=context,
            slack=slack,
            passes=passes,
            trials=eval_trials,
            delta_per_atom=float("inf"),
            delta_per_atom_pass=float("inf"),
            final_bits_per_atom=float("inf"),
            final_items_per_atom=float("inf"),
            selected_records_per_atom_pass=0.0,
            expired_records_per_atom_pass=0.0,
            expiry_tax_per_atom_pass=0.0,
            avg_rewrite_fraction=0.0,
            fail_rate=len(failed) / eval_trials,
        )
    raw_atoms = config.atoms
    return Row(
        mode=expiry_mode,
        config=config,
        context=context,
        slack=slack,
        passes=passes,
        trials=eval_trials,
        delta_per_atom=mean(trial.delta_per_raw_atom for trial in ok),
        delta_per_atom_pass=mean(trial.delta_per_raw_atom_pass for trial in ok),
        final_bits_per_atom=mean(trial.final_bits / raw_atoms for trial in ok),
        final_items_per_atom=mean(trial.final_items / raw_atoms for trial in ok),
        selected_records_per_atom_pass=mean(trial.selected_records_per_atom_pass for trial in ok),
        expired_records_per_atom_pass=mean(trial.expired_records_per_atom_pass for trial in ok),
        expiry_tax_per_atom_pass=mean(trial.expiry_tax_per_atom_pass for trial in ok),
        avg_rewrite_fraction=mean(trial.avg_rewrite_fraction for trial in ok),
        fail_rate=len(failed) / eval_trials,
    )


def configs() -> list[Config]:
    return [
        Config(
            name="H114_raw_lower",
            block_bits=4,
            initial_item_bits=4,
            atoms=64,
            max_arity=32,
            frontier=128,
            literal_marker_bits=3,
            class_bits=1,
        ),
        Config(
            name="public_lane_raw",
            block_bits=4,
            initial_item_bits=4,
            atoms=64,
            max_arity=32,
            frontier=128,
            literal_marker_bits=3,
            class_bits=0,
        ),
        Config(
            name="literal_wrapped",
            block_bits=4,
            initial_item_bits=7,
            atoms=64,
            max_arity=32,
            frontier=128,
            literal_marker_bits=3,
            class_bits=1,
        ),
        Config(
            name="public_lane_lit",
            block_bits=4,
            initial_item_bits=7,
            atoms=64,
            max_arity=32,
            frontier=128,
            literal_marker_bits=3,
            class_bits=0,
        ),
    ]


def fmt(value: float) -> str:
    return "inf" if not math.isfinite(value) else f"{value:.6f}"


def print_rows(rows: list[Row]) -> None:
    print("== two-epoch record-layer accounting ==")
    print("delta columns are bits per original raw atom. Negative means shrink.")
    print(
        f"{'config':<16} {'mode':<22} {'ctx':<8} {'s':>2} {'P':>2} "
        f"{'delta':>10} {'d/pass':>10} {'finalb/a':>9} {'items/a':>8} "
        f"{'sel/a/p':>8} {'exp/a/p':>8} {'tax/a/p':>8} {'qraw':>6} {'fail':>6}"
    )
    for row in rows:
        print(
            f"{row.config.name:<16} {row.mode:<22} {row.context:<8} {row.slack:2d} "
            f"{row.passes:2d} {fmt(row.delta_per_atom):>10} "
            f"{fmt(row.delta_per_atom_pass):>10} {fmt(row.final_bits_per_atom):>9} "
            f"{fmt(row.final_items_per_atom):>8} {fmt(row.selected_records_per_atom_pass):>8} "
            f"{fmt(row.expired_records_per_atom_pass):>8} {fmt(row.expiry_tax_per_atom_pass):>8} "
            f"{fmt(row.avg_rewrite_fraction):>6} {row.fail_rate:6.3f}"
        )
    print()


def print_reading(rows: list[Row]) -> None:
    print("== reading ==")
    for mode in ("no_expiry_lower_bound", "force_refresh", "expire_raw_lower_bound", "expire_literal_items"):
        mode_rows = [row for row in rows if row.mode == mode]
        if not mode_rows:
            continue
        best = min(mode_rows, key=lambda row: row.delta_per_atom_pass)
        print(
            f"Best {mode}: {best.config.name}, ctx={best.context}, "
            f"delta/pass={best.delta_per_atom_pass:.6f}, total={best.delta_per_atom:.6f}, "
            f"fail={best.fail_rate:.3f}."
        )
    print(
        "If only no_expiry crosses, H114 was hiding the age channel. If "
        "force_refresh crosses, the two-epoch invariant is plausible without "
        "literalization. If expire_* crosses, the result survives even when "
        "old records that miss refresh are expanded."
    )
    print(
        "The public_lane_* configs are optimistic positional-class rows with "
        "the visible seed-class bit removed. They still need a separate proof "
        "that lane membership is public and does not hide a subset selector."
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--passes", type=int, default=4)
    parser.add_argument("--train-trials", type=int, default=8)
    parser.add_argument("--eval-trials", type=int, default=8)
    parser.add_argument("--seed", type=int, default=115115)
    parser.add_argument("--min-rewrite-raw-frac", type=float, default=0.50)
    parser.add_argument("--config-filter", action="append", default=[])
    parser.add_argument("--mode-filter", action="append", default=[])
    args = parser.parse_args(argv)

    selected_configs = [
        config for config in configs()
        if not args.config_filter or config.name in set(args.config_filter)
    ]
    selected_modes = [
        mode for mode in (
            "no_expiry_lower_bound",
            "force_refresh",
            "expire_raw_lower_bound",
            "expire_literal_items",
        )
        if not args.mode_filter or mode in set(args.mode_filter)
    ]
    rows = [
        evaluate(
            config=config,
            slack=4,
            context=context,
            passes=args.passes,
            train_trials=args.train_trials,
            eval_trials=args.eval_trials,
            seed=args.seed,
            expiry_mode=mode,
            min_rewrite_raw_fraction=args.min_rewrite_raw_frac,
        )
        for config in selected_configs
        for mode in selected_modes
        for context in ("global", "arity_bucket")
    ]
    print_rows(rows)
    print_reading(rows)


if __name__ == "__main__":
    main()
