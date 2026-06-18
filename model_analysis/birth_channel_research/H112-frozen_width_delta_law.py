#!/usr/bin/env python3
"""H112 - frozen public width/delta law for partial refresh.

H111 showed:

    local width oracle crosses
    counts-free enumerative width stream crosses
    count-paid enumerative width stream misses

So the hidden channel is the per-file selected width/delta law. H112 tests the
next honest move: train a public P(delta | context) on independent uniform-law
layers, freeze it, and use it to encode held-out selected widths.

The stream shape is parseable:

    arity stream -> public target bits
    delta stream under frozen law -> payload widths
    payload bits

All rows include the optimistic H2 ready/carry lower bound. Cover-shape
placement is still not charged, so a positive row would be a target, not a
finished codec.
"""

from __future__ import annotations

import math
import random
import sys
import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model_analysis.proof_kernel.costs import j3d1_cost_for_payload_width
from total_cover_lotus_crossover import (
    fixed_arity_bits,
    local_payload_bits_from_log_rank,
    sample_log2_first_rank,
)


@dataclass(frozen=True)
class Config:
    name: str
    block_bits: int
    atoms: int
    max_arity: int
    frontier: int


@dataclass(frozen=True)
class Edge:
    start: int
    arity: int
    width: int
    target_bits: int
    arity_bits: int

    @property
    def delta_value(self) -> int:
        return self.target_bits - self.width

    @property
    def local_cost(self) -> int:
        return self.arity_bits + self.width

    @property
    def local_delta(self) -> int:
        return self.local_cost - self.target_bits


@dataclass(frozen=True)
class Choice:
    edge: Edge


@dataclass(frozen=True)
class DeltaModel:
    context: str
    counts: dict[tuple[int, ...], Counter[int]]
    alpha: float
    max_arity: int
    block_bits: int
    slack: int


@dataclass(frozen=True)
class EvalRow:
    config: Config
    slack: int
    min_q: float
    context: str
    train_delta: float
    eval_delta: float
    q: float
    records_per_atom: float
    avg_arity: float
    avg_width: float
    delta_bits_per_record: float
    coverage: float


def h2(p: float) -> float:
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -(p * math.log2(p) + (1.0 - p) * math.log2(1.0 - p))


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
    if mode == "target_bucket":
        return (target_bucket(edge.target_bits),)
    if mode == "arity_exact":
        return (edge.arity,)
    if mode == "target_arity_bucket":
        return (target_bucket(edge.target_bits), arity_bucket(edge.arity))
    raise ValueError(mode)


def delta_range(edge: Edge, slack: int) -> tuple[int, int]:
    return edge.arity_bits - slack, edge.target_bits - 1


def delta_range_size(edge: Edge, slack: int) -> int:
    lower, upper = delta_range(edge, slack)
    return max(0, upper - lower + 1)


def sample_edges(config: Config, slack: int, rng: random.Random) -> list[list[Edge]]:
    edges_by_start: list[list[Edge]] = [[] for _ in range(config.atoms)]
    for start in range(config.atoms):
        legal = min(config.max_arity, config.atoms - start)
        for arity in range(1, legal + 1):
            target_bits = arity * config.block_bits
            width = local_payload_bits_from_log_rank(sample_log2_first_rank(target_bits, rng))
            if width > config.frontier:
                continue
            edge = Edge(
                start=start,
                arity=arity,
                width=width,
                target_bits=target_bits,
                arity_bits=fixed_arity_bits(config.max_arity, arity),
            )
            if edge.local_delta <= slack:
                edges_by_start[start].append(edge)
    return edges_by_start


def delta_cost(model: DeltaModel, edge: Edge) -> float:
    lower, upper = delta_range(edge, model.slack)
    if edge.delta_value < lower or edge.delta_value > upper:
        return float("inf")
    support = max(1, upper - lower + 1)
    counts = model.counts.get(context_for(model.context, edge), Counter())
    denom_count = sum(counts.get(delta, 0) for delta in range(lower, upper + 1))
    denom = denom_count + model.alpha * support
    return -math.log2((counts.get(edge.delta_value, 0) + model.alpha) / denom)


def edge_delta(edge: Edge, config: Config, slack: int, mode: str, model: DeltaModel | None) -> float:
    if mode == "local":
        cost = edge.local_cost
    elif mode == "frozen":
        if model is None:
            raise ValueError("frozen mode needs model")
        cost = edge.local_cost + delta_cost(model, edge)
    elif mode == "fixed_delta":
        cost = edge.local_cost + math.ceil(math.log2(delta_range_size(edge, slack)))
    elif mode == "j3d1":
        cost = edge.arity_bits + j3d1_cost_for_payload_width(edge.width)
    else:
        raise ValueError(mode)
    return cost - edge.target_bits


def select_cover(
    config: Config,
    slack: int,
    min_q: float,
    seed: int,
    mode: str,
    model: DeltaModel | None,
) -> tuple[float, list[Choice], float, float]:
    edges_by_start = sample_edges(config, slack, random.Random(seed))
    n = config.atoms
    inf = float("inf")
    dp = [[inf] * (n + 1) for _ in range(n + 1)]
    prev: list[list[tuple[int, int, Edge] | None]] = [[None] * (n + 1) for _ in range(n + 1)]
    dp[0][0] = 0.0
    for pos in range(n):
        for rewritten in range(n + 1):
            base = dp[pos][rewritten]
            if base == inf:
                continue
            if base < dp[pos + 1][rewritten]:
                dp[pos + 1][rewritten] = base
                prev[pos + 1][rewritten] = (pos, rewritten, Edge(pos, 0, 0, 0, 0))
            for edge in edges_by_start[pos]:
                delta = edge_delta(edge, config, slack, mode, model)
                if not math.isfinite(delta):
                    continue
                end = pos + edge.arity
                new_rewritten = rewritten + edge.arity
                candidate = base + delta
                if candidate < dp[end][new_rewritten]:
                    dp[end][new_rewritten] = candidate
                    prev[end][new_rewritten] = (pos, rewritten, edge)

    best_rewritten = -1
    best_total = inf
    for rewritten, raw_delta in enumerate(dp[n]):
        if rewritten / n < min_q or raw_delta == inf:
            continue
        total = raw_delta + n * h2(rewritten / n)
        if total < best_total:
            best_total = total
            best_rewritten = rewritten
    if best_rewritten < 0:
        return inf, [], 0.0, 0.0

    choices: list[Choice] = []
    delta_bits = 0.0
    pos = n
    rewritten = best_rewritten
    while pos > 0:
        entry = prev[pos][rewritten]
        if entry is None:
            raise AssertionError("missing predecessor")
        prior_pos, prior_rewritten, edge = entry
        if edge.arity > 0:
            choices.append(Choice(edge))
            if mode == "frozen" and model is not None:
                delta_bits += delta_cost(model, edge)
        pos = prior_pos
        rewritten = prior_rewritten
    choices.reverse()
    return best_total / n, choices, best_rewritten / n, delta_bits


def fit_model(
    config: Config,
    slack: int,
    min_q: float,
    context: str,
    alpha: float,
    train_trials: int,
    seed: int,
    bootstrap_mode: str,
) -> DeltaModel:
    empty = DeltaModel(context, {}, alpha, config.max_arity, config.block_bits, slack)
    counts: dict[tuple[int, ...], Counter[int]] = defaultdict(Counter)
    for trial in range(train_trials):
        mode = "fixed_delta" if bootstrap_mode == "fixed_delta" else "local"
        _, choices, _, _ = select_cover(
            config,
            slack,
            min_q,
            seed + trial * 1_000_003,
            mode,
            empty,
        )
        for choice in choices:
            counts[context_for(context, choice.edge)][choice.edge.delta_value] += 1
    return DeltaModel(context, dict(counts), alpha, config.max_arity, config.block_bits, slack)


def eval_model(
    config: Config,
    slack: int,
    min_q: float,
    model: DeltaModel,
    trials: int,
    seed: int,
) -> tuple[float, float, float, float, float, float]:
    deltas: list[float] = []
    qs: list[float] = []
    recs: list[float] = []
    arities: list[float] = []
    widths: list[float] = []
    delta_bits_per_record: list[float] = []
    covered = 0
    for trial in range(trials):
        delta, choices, q, delta_bits = select_cover(
            config,
            slack,
            min_q,
            seed + trial * 1_000_003,
            "frozen",
            model,
        )
        if not math.isfinite(delta):
            continue
        covered += 1
        deltas.append(delta)
        qs.append(q)
        if choices:
            recs.append(len(choices) / config.atoms)
            arities.append(mean(choice.edge.arity for choice in choices))
            widths.append(mean(choice.edge.width for choice in choices))
            delta_bits_per_record.append(delta_bits / len(choices))
    return (
        mean(deltas) if deltas else float("inf"),
        mean(qs) if qs else 0.0,
        mean(recs) if recs else 0.0,
        mean(arities) if arities else 0.0,
        mean(widths) if widths else 0.0,
        mean(delta_bits_per_record) if delta_bits_per_record else 0.0,
        covered / trials if trials else 0.0,
    )


def evaluate(
    config: Config,
    slack: int,
    min_q: float,
    context: str,
    train_trials: int,
    eval_trials: int,
    alpha: float,
    seed: int,
    bootstrap_mode: str,
) -> EvalRow:
    model = fit_model(
        config,
        slack,
        min_q,
        context,
        alpha,
        train_trials,
        seed,
        bootstrap_mode,
    )
    train_delta, _, _, _, _, _, _ = eval_model(
        config,
        slack,
        min_q,
        model,
        train_trials,
        seed + 17,
    )
    eval_delta, q, recs, arity, width, delta_bits, coverage = eval_model(
        config,
        slack,
        min_q,
        model,
        eval_trials,
        seed + 99_991,
    )
    return EvalRow(
        config=config,
        slack=slack,
        min_q=min_q,
        context=context,
        train_delta=train_delta,
        eval_delta=eval_delta,
        q=q,
        records_per_atom=recs,
        avg_arity=arity,
        avg_width=width,
        delta_bits_per_record=delta_bits,
        coverage=coverage,
    )


def baseline(
    config: Config,
    slack: int,
    min_q: float,
    mode: str,
    trials: int,
    seed: int,
) -> float:
    values = [
        select_cover(config, slack, min_q, seed + trial * 1_000_003, mode, None)[0]
        for trial in range(trials)
    ]
    return mean(values)


def configs(broad: bool) -> list[Config]:
    if not broad:
        # The decisive diagnostic is the strongest H111 counts-free crossing.
        # Broader rows are available behind --broad, but default runtime should
        # stay small enough to keep this a proof-kernel, not a search run.
        return [Config("B4_K16_D64", 4, 64, 16, 64)]
    return [
        Config("B4_K16_D64", 4, 64, 16, 64),
        Config("B4_K128_D512", 4, 128, 128, 512),
        Config("B8_K64_D512", 8, 96, 64, 512),
    ]


def stable_seed(config: Config, slack: int, min_q: float, context: str) -> int:
    text = f"{config.name}:{slack}:{min_q:.2f}:{context}"
    value = 0
    for char in text:
        value = (value * 131 + ord(char)) % 1_000_000_007
    return 112112 + value % 100_000


def print_rows(rows: list[EvalRow]) -> None:
    print("== frozen public width/delta law ==")
    print("Rows are held-out eval bits/input atom after H2(q).")
    print(
        f"{'config':<14} {'s':>2} {'qmin':>5} {'ctx':<19} {'train':>8} "
        f"{'eval':>8} {'q':>5} {'rec/a':>7} {'arity':>7} {'width':>7} {'dBits':>7} {'cover':>6}"
    )
    for row in rows:
        print(
            f"{row.config.name:<14} {row.slack:2d} {row.min_q:5.2f} {row.context:<19} "
            f"{row.train_delta:8.4f} {row.eval_delta:8.4f} {row.q:5.3f} "
            f"{row.records_per_atom:7.4f} {row.avg_arity:7.2f} {row.avg_width:7.2f} "
            f"{row.delta_bits_per_record:7.3f} {row.coverage:6.3f}"
        )
    print()


def print_reading(rows: list[EvalRow]) -> None:
    print("== reading ==")
    best_train = min(rows, key=lambda row: row.train_delta)
    best_eval = min(rows, key=lambda row: row.eval_delta)
    print(
        f"Train-selected row: {best_train.config.name}, slack={best_train.slack}, "
        f"qmin={best_train.min_q:.2f}, ctx={best_train.context}, "
        f"held-out delta={best_train.eval_delta:.6f} bits/atom."
    )
    print(
        f"Best held-out diagnostic: {best_eval.config.name}, slack={best_eval.slack}, "
        f"qmin={best_eval.min_q:.2f}, ctx={best_eval.context}, "
        f"delta={best_eval.eval_delta:.6f} bits/atom."
    )
    print(
        "A negative train-selected row would be a live parseable width-law target. "
        "A positive train-selected row means the per-file width histogram from H111 "
        "has not been replaced by this public law."
    )


def print_baselines() -> None:
    print("== baselines ==")
    target = Config("B4_K16_D64", 4, 64, 16, 64)
    for mode in ("local", "fixed_delta", "j3d1"):
        value = baseline(target, 4, 0.10, mode, trials=10, seed=212112)
        print(f"{target.name} slack=4 qmin=.10 {mode}: {value:.6f} bits/atom")
    print()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--broad", action="store_true", help="run the slower multi-config diagnostic")
    parser.add_argument("--train-trials", type=int, default=8)
    parser.add_argument("--eval-trials", type=int, default=8)
    args = parser.parse_args(argv)

    slacks = (4, 8) if args.broad else (4,)
    min_qs = (0.10, 0.50) if args.broad else (0.10,)
    contexts = (
        ("global", "arity_bucket", "target_arity_bucket", "target_bucket")
        if args.broad
        else ("global", "arity_bucket", "target_arity_bucket")
    )

    rows = [
        evaluate(
            config,
            slack,
            min_q,
            context,
            train_trials=args.train_trials,
            eval_trials=args.eval_trials,
            alpha=0.05,
            seed=stable_seed(config, slack, min_q, context),
            bootstrap_mode="local",
        )
        for config in configs(args.broad)
        for slack in slacks
        for min_q in min_qs
        for context in contexts
    ]
    print_rows(rows)
    print_reading(rows)
    print_baselines()


if __name__ == "__main__":
    main()
