#!/usr/bin/env python3
"""H110 - partial-refresh Pareto frontier.

H98 tested the user's "+1/+2 slack refresh" story with a few budgeted
recursive simulations. H110 asks the same question as a one-pass frontier:

    for every possible rewritten fraction q,
    what is the cheapest matching interval cover that rewrites q atoms?

Then it charges the most generous possible stateless ready/carry lower bound:

    N * H2(q) bits

This directly prices the proposed sweet spot between "rewrite almost nothing"
and "rewrite every atom". If no q with nontrivial freshness has negative
delta after this lower bound, deeper search alone is not the missing channel.
"""

from __future__ import annotations

import math
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model_analysis.proof_kernel.costs import MAX_PAYLOAD_WIDTH_BITS, j3d1_cost_for_payload_width
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
    delta: float
    cost: float


@dataclass(frozen=True)
class FrontierPoint:
    rewritten: int
    raw_delta: float
    h2_delta: float
    literal_delta: float


@dataclass(frozen=True)
class Row:
    config: Config
    slack: int
    mode: str
    trials: int
    best_unpaid_delta_per_atom: float
    best_h2_delta_per_atom: float
    best_literal_delta_per_atom: float
    best_h2_q: float
    best_h2_nonzero_q: float
    best_h2_nonzero_delta: float
    best_h2_q10_delta: float
    best_h2_q50_delta: float
    best_h2_q90_delta: float
    best_unpaid_q10_delta: float


def h2(p: float) -> float:
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -(p * math.log2(p) + (1.0 - p) * math.log2(1.0 - p))


def record_cost(mode: str, max_arity: int, arity: int, log2_rank: float) -> float:
    payload = local_payload_bits_from_log_rank(log2_rank)
    if mode == "zero_arity_oracle":
        return payload
    if mode == "local_width_oracle":
        return fixed_arity_bits(max_arity, arity) + payload
    if mode == "j3d1_parseable":
        if payload > MAX_PAYLOAD_WIDTH_BITS:
            return float("inf")
        return fixed_arity_bits(max_arity, arity) + j3d1_cost_for_payload_width(payload)
    raise ValueError(mode)


def sample_edges(config: Config, slack: int, mode: str, rng: random.Random) -> list[list[Edge]]:
    edges_by_start: list[list[Edge]] = [[] for _ in range(config.atoms)]
    for start in range(config.atoms):
        max_arity = min(config.max_arity, config.atoms - start)
        for arity in range(1, max_arity + 1):
            target_bits = arity * config.block_bits
            log2_rank = sample_log2_first_rank(target_bits, rng)
            payload = local_payload_bits_from_log_rank(log2_rank)
            if payload > config.frontier:
                continue
            cost = record_cost(mode, config.max_arity, arity, log2_rank)
            if cost == float("inf"):
                continue
            delta = cost - target_bits
            if delta <= slack:
                edges_by_start[start].append(Edge(start, arity, delta, cost))
    return edges_by_start


def pareto_points(config: Config, slack: int, mode: str, rng: random.Random) -> list[FrontierPoint]:
    """Return cheapest deltas for each rewritten atom count."""

    edges_by_start = sample_edges(config, slack, mode, rng)
    n = config.atoms
    inf = float("inf")
    dp = [[inf] * (n + 1) for _ in range(n + 1)]
    dp[0][0] = 0.0
    for pos in range(n):
        for rewritten in range(n + 1):
            base = dp[pos][rewritten]
            if base == inf:
                continue
            if base < dp[pos + 1][rewritten]:
                dp[pos + 1][rewritten] = base
            for edge in edges_by_start[pos]:
                new_rewritten = rewritten + edge.arity
                candidate = base + edge.delta
                end = pos + edge.arity
                if candidate < dp[end][new_rewritten]:
                    dp[end][new_rewritten] = candidate
    points: list[FrontierPoint] = []
    for rewritten, raw_delta in enumerate(dp[n]):
        if raw_delta == inf:
            continue
        q = rewritten / n
        h2_delta = raw_delta + n * h2(q)
        literal_delta = raw_delta + (n - rewritten) * 3.0
        points.append(
            FrontierPoint(
                rewritten=rewritten,
                raw_delta=raw_delta,
                h2_delta=h2_delta,
                literal_delta=literal_delta,
            )
        )
    return points


def best_delta(points: list[FrontierPoint], attr: str, min_q: float, n: int) -> float:
    eligible = [point for point in points if point.rewritten / n >= min_q]
    if not eligible:
        return float("inf")
    return min(getattr(point, attr) for point in eligible) / n


def best_q(points: list[FrontierPoint], attr: str, n: int) -> float:
    if not points:
        return 0.0
    best = min(points, key=lambda point: getattr(point, attr))
    return best.rewritten / n


def evaluate(config: Config, slack: int, mode: str, trials: int, seed: int) -> Row:
    all_points: list[list[FrontierPoint]] = []
    for trial in range(trials):
        rng = random.Random(seed + 1_000_003 * trial)
        all_points.append(pareto_points(config, slack, mode, rng))
    n = config.atoms
    return Row(
        config=config,
        slack=slack,
        mode=mode,
        trials=trials,
        best_unpaid_delta_per_atom=mean(best_delta(points, "raw_delta", 0.0, n) for points in all_points),
        best_h2_delta_per_atom=mean(best_delta(points, "h2_delta", 0.0, n) for points in all_points),
        best_literal_delta_per_atom=mean(best_delta(points, "literal_delta", 0.0, n) for points in all_points),
        best_h2_q=mean(best_q(points, "h2_delta", n) for points in all_points),
        best_h2_nonzero_q=mean(best_q([p for p in points if p.rewritten > 0], "h2_delta", n) for points in all_points),
        best_h2_nonzero_delta=mean(best_delta(points, "h2_delta", 1.0 / n, n) for points in all_points),
        best_h2_q10_delta=mean(best_delta(points, "h2_delta", 0.10, n) for points in all_points),
        best_h2_q50_delta=mean(best_delta(points, "h2_delta", 0.50, n) for points in all_points),
        best_h2_q90_delta=mean(best_delta(points, "h2_delta", 0.90, n) for points in all_points),
        best_unpaid_q10_delta=mean(best_delta(points, "raw_delta", 0.10, n) for points in all_points),
    )


def configs() -> list[Config]:
    return [
        Config("B4_K16_D64", 4, 64, 16, 64),
        Config("B4_K32_D128", 4, 64, 32, 128),
        Config("B4_K64_D256", 4, 96, 64, 256),
        Config("B4_K128_D512", 4, 128, 128, 512),
        Config("B8_K32_D256", 8, 64, 32, 256),
        Config("B8_K64_D512", 8, 96, 64, 512),
    ]


def print_rows(rows: list[Row]) -> None:
    print("== partial-refresh Pareto frontier ==")
    print("delta columns are bits/input atom; negative means current-pass shrink.")
    print("H2 is only the binary ready/carry lower bound, not full cover-shape cost.")
    print(
        f"{'config':<14} {'mode':<17} {'s':>2} {'raw*':>8} {'H2*':>8} "
        f"{'lit*':>8} {'q@H2':>7} {'H2 q>0':>8} {'H2 q10':>8} "
        f"{'H2 q50':>8} {'H2 q90':>8} {'raw q10':>8}"
    )
    for row in rows:
        print(
            f"{row.config.name:<14} {row.mode:<17} {row.slack:2d} "
            f"{row.best_unpaid_delta_per_atom:8.4f} "
            f"{row.best_h2_delta_per_atom:8.4f} "
            f"{row.best_literal_delta_per_atom:8.4f} "
            f"{row.best_h2_q:7.3f} "
            f"{row.best_h2_nonzero_delta:8.4f} "
            f"{row.best_h2_q10_delta:8.4f} "
            f"{row.best_h2_q50_delta:8.4f} "
            f"{row.best_h2_q90_delta:8.4f} "
            f"{row.best_unpaid_q10_delta:8.4f}"
        )
    print()


def print_reading(rows: list[Row]) -> None:
    print("== reading ==")
    parseable = [row for row in rows if row.mode == "j3d1_parseable"]
    width_oracle = [row for row in rows if row.mode == "local_width_oracle"]
    best_unpaid_q10 = min(rows, key=lambda row: row.best_unpaid_q10_delta)
    best_h2_q10 = min(rows, key=lambda row: row.best_h2_q10_delta)
    best_h2_any = min(rows, key=lambda row: row.best_h2_nonzero_delta)
    best_h2_q50 = min(rows, key=lambda row: row.best_h2_q50_delta)
    best_oracle = min((row for row in rows if row.mode == "zero_arity_oracle"), key=lambda row: row.best_h2_q10_delta)
    best_parseable_q10 = min(parseable, key=lambda row: row.best_h2_q10_delta)
    best_parseable_q50 = min(parseable, key=lambda row: row.best_h2_q50_delta)
    best_width_q10 = min(width_oracle, key=lambda row: row.best_h2_q10_delta)
    best_width_q50 = min(width_oracle, key=lambda row: row.best_h2_q50_delta)
    print(
        f"Best unpaid q>=10% row: {best_unpaid_q10.config.name}, {best_unpaid_q10.mode}, "
        f"slack={best_unpaid_q10.slack}, delta={best_unpaid_q10.best_unpaid_q10_delta:.6f} bits/atom."
    )
    print(
        f"Best parseable J3D1 q>=10% row: {best_parseable_q10.config.name}, "
        f"slack={best_parseable_q10.slack}, delta={best_parseable_q10.best_h2_q10_delta:.6f} bits/atom."
    )
    print(
        f"Best parseable J3D1 q>=50% row: {best_parseable_q50.config.name}, "
        f"slack={best_parseable_q50.slack}, delta={best_parseable_q50.best_h2_q50_delta:.6f} bits/atom."
    )
    print(
        f"Best local-width oracle q>=10% row: {best_width_q10.config.name}, "
        f"slack={best_width_q10.slack}, delta={best_width_q10.best_h2_q10_delta:.6f} bits/atom."
    )
    print(
        f"Best local-width oracle q>=50% row: {best_width_q50.config.name}, "
        f"slack={best_width_q50.slack}, delta={best_width_q50.best_h2_q50_delta:.6f} bits/atom."
    )
    print(
        f"Best H2-charged q>0 row: {best_h2_any.config.name}, {best_h2_any.mode}, "
        f"slack={best_h2_any.slack}, delta={best_h2_any.best_h2_nonzero_delta:.6f} bits/atom."
    )
    print(
        f"Best H2-charged q>=10% row: {best_h2_q10.config.name}, {best_h2_q10.mode}, "
        f"slack={best_h2_q10.slack}, delta={best_h2_q10.best_h2_q10_delta:.6f} bits/atom."
    )
    print(
        f"Best H2-charged q>=50% row: {best_h2_q50.config.name}, {best_h2_q50.mode}, "
        f"slack={best_h2_q50.slack}, delta={best_h2_q50.best_h2_q50_delta:.6f} bits/atom."
    )
    print(
        f"Even the zero-arity oracle's best q>=10% H2 row is {best_oracle.config.name}, "
        f"slack={best_oracle.slack}, delta={best_oracle.best_h2_q10_delta:.6f} bits/atom."
    )
    print(
        "Interpretation: allowing bloating records can increase the available "
        "rewritten fraction, but if that fraction is content-selected then the "
        "binary ready/carry map alone costs H2(q). A paid sweet spot must be "
        "negative in the H2 q-threshold columns, not just in raw q10. The "
        "local-width oracle crossing means the match lattice has enough option "
        "pressure; the parseable J3D1 miss means payload-width/boundary syntax "
        "is still the current bill."
    )


def main() -> None:
    rows = [
        evaluate(config, slack, mode, trials=12, seed=110110)
        for config in configs()
        for mode in ("j3d1_parseable", "local_width_oracle", "zero_arity_oracle")
        for slack in (0, 1, 2, 4, 8)
    ]
    print_rows(rows)
    print_reading(rows)


if __name__ == "__main__":
    main()
