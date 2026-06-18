#!/usr/bin/env python3
"""H113 - seed-class readiness for partial refresh.

H110 charged a content-selected partial refresh with the binary lower bound
N*H2(q): the decoder needs to know which atoms open now and which carry.

The user's parity/rejection idea is a different paid channel:

    pass t uses a public seed class, e.g. seed parity = t mod 2

Then a current record can self-identify through its seed witness. This file
prices that channel in the partial-refresh DP. It is honest only under a live
epoch bound: parity distinguishes two epochs, not an arbitrary-age carry.

For visible global seed classes, the witness payload width is the class-local
rank width plus class_bits; exact J3D1 is charged on that wider payload. For
many live epochs, the unresolved age entropy is added explicitly.
"""

from __future__ import annotations

import math
import random
import sys
import argparse
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
    width: int
    target_bits: int
    arity_bits: int


@dataclass(frozen=True)
class Mode:
    name: str
    kind: str
    class_bits: int = 0
    live_epochs: int = 1
    h2_map: bool = False


@dataclass(frozen=True)
class Trial:
    delta_per_atom: float
    q: float
    records_per_atom: float
    avg_arity: float
    avg_width: float


@dataclass(frozen=True)
class Row:
    config: Config
    mode: Mode
    slack: int
    min_q: float
    trials: int
    delta_per_atom: float
    q: float
    records_per_atom: float
    avg_arity: float
    avg_width: float


def h2(p: float) -> float:
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -(p * math.log2(p) + (1.0 - p) * math.log2(1.0 - p))


def residual_age_bits(mode: Mode) -> float:
    if mode.live_epochs <= 1:
        return 0.0
    return max(0.0, math.log2(mode.live_epochs) - mode.class_bits)


def payload_width(edge: Edge, mode: Mode) -> int:
    if mode.class_bits > 0:
        return edge.width + mode.class_bits
    return edge.width


def edge_delta(edge: Edge, mode: Mode, slack: int, frontier: int) -> float:
    width = payload_width(edge, mode)
    if width > frontier:
        return float("inf")
    if mode.kind in {"j3d1", "visible_class"}:
        if width > MAX_PAYLOAD_WIDTH_BITS:
            return float("inf")
        cost = edge.arity_bits + j3d1_cost_for_payload_width(width)
        cost += residual_age_bits(mode)
    elif mode.kind == "fixed_delta":
        lower = edge.arity_bits - slack
        upper = edge.target_bits - 1
        range_size = max(0, upper - lower + 1)
        if range_size <= 0:
            return float("inf")
        cost = edge.arity_bits + width + math.ceil(math.log2(range_size))
        cost += residual_age_bits(mode)
    elif mode.kind == "local_oracle":
        cost = edge.arity_bits + width + residual_age_bits(mode)
    else:
        raise ValueError(mode.kind)
    delta = cost - edge.target_bits
    return delta if delta <= slack else float("inf")


def sample_edges(config: Config, rng: random.Random) -> list[list[Edge]]:
    edges_by_start: list[list[Edge]] = [[] for _ in range(config.atoms)]
    for start in range(config.atoms):
        legal = min(config.max_arity, config.atoms - start)
        for arity in range(1, legal + 1):
            target_bits = arity * config.block_bits
            width = local_payload_bits_from_log_rank(sample_log2_first_rank(target_bits, rng))
            if width > config.frontier:
                continue
            edges_by_start[start].append(
                Edge(
                    start=start,
                    arity=arity,
                    width=width,
                    target_bits=target_bits,
                    arity_bits=fixed_arity_bits(config.max_arity, arity),
                )
            )
    return edges_by_start


def select_cover(config: Config, mode: Mode, slack: int, min_q: float, seed: int) -> Trial:
    edges_by_start = sample_edges(config, random.Random(seed))
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
                delta = edge_delta(edge, mode, slack, config.frontier)
                if delta == inf:
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
        q = rewritten / n
        if q < min_q or raw_delta == inf:
            continue
        total = raw_delta + (n * h2(q) if mode.h2_map else 0.0)
        if total < best_total:
            best_total = total
            best_rewritten = rewritten

    if best_rewritten < 0:
        return Trial(inf, 0.0, 0.0, 0.0, 0.0)

    choices: list[Edge] = []
    pos = n
    rewritten = best_rewritten
    while pos > 0:
        entry = prev[pos][rewritten]
        if entry is None:
            raise AssertionError("missing predecessor")
        prior_pos, prior_rewritten, edge = entry
        if edge.arity > 0:
            choices.append(edge)
        pos = prior_pos
        rewritten = prior_rewritten

    return Trial(
        delta_per_atom=best_total / n,
        q=best_rewritten / n,
        records_per_atom=len(choices) / n,
        avg_arity=mean(edge.arity for edge in choices) if choices else 0.0,
        avg_width=mean(payload_width(edge, mode) for edge in choices) if choices else 0.0,
    )


def evaluate(config: Config, mode: Mode, slack: int, min_q: float, trials: int, seed: int) -> Row:
    results = [
        select_cover(config, mode, slack, min_q, seed + trial * 1_000_003)
        for trial in range(trials)
    ]
    finite = [result for result in results if math.isfinite(result.delta_per_atom)]
    if not finite:
        return Row(config, mode, slack, min_q, trials, float("inf"), 0.0, 0.0, 0.0, 0.0)
    return Row(
        config=config,
        mode=mode,
        slack=slack,
        min_q=min_q,
        trials=trials,
        delta_per_atom=mean(result.delta_per_atom for result in finite),
        q=mean(result.q for result in finite),
        records_per_atom=mean(result.records_per_atom for result in finite),
        avg_arity=mean(result.avg_arity for result in finite if result.avg_arity > 0.0),
        avg_width=mean(result.avg_width for result in finite if result.avg_width > 0.0),
    )


def configs(broad: bool) -> list[Config]:
    base = [
        Config("B4_K16_D64", 4, 64, 16, 64),
        Config("B4_K32_D128", 4, 64, 32, 128),
        Config("B8_K32_D256", 8, 64, 32, 256),
    ]
    if not broad:
        return base
    return base + [
        Config("B4_K64_D256", 4, 96, 64, 256),
        Config("B4_K128_D512", 4, 128, 128, 512),
        Config("B6_K64_D384", 6, 96, 64, 384),
        Config("B8_K64_D512", 8, 96, 64, 512),
    ]


def modes(targeted: bool) -> list[Mode]:
    target = [
        Mode("fixedD + parity 2-epoch", "fixed_delta", class_bits=1, live_epochs=2),
        Mode("J3D1 + parity 2-epoch", "visible_class", class_bits=1, live_epochs=2),
        Mode("local + parity 2-epoch", "local_oracle", class_bits=1, live_epochs=2),
    ]
    if targeted:
        return target
    return [
        Mode("local + H2 map", "local_oracle", h2_map=True),
        Mode("J3D1 + H2 map", "j3d1", h2_map=True),
        Mode("fixedD + H2 map", "fixed_delta", h2_map=True),
        *target[:2],
        Mode("J3D1 + parity 64-epoch", "visible_class", class_bits=1, live_epochs=64),
        Mode("J3D1 + exact 64-class", "visible_class", class_bits=6, live_epochs=64),
        target[2],
    ]


def fmt(value: float) -> str:
    return "inf" if not math.isfinite(value) else f"{value:.4f}"


def print_rows(rows: list[Row]) -> None:
    print("== seed-class partial refresh ==")
    print("delta is bits/input atom; negative means shrink. Parity rows do not charge H2(q).")
    print("They are honest only if the stated live-epoch bound is enforced.")
    print(
        f"{'config':<14} {'mode':<25} {'s':>2} {'qmin':>5} {'delta':>8} "
        f"{'q':>5} {'rec/a':>7} {'arity':>7} {'width':>7}"
    )
    for row in rows:
        print(
            f"{row.config.name:<14} {row.mode.name:<25} {row.slack:2d} {row.min_q:5.2f} "
            f"{fmt(row.delta_per_atom):>8} {row.q:5.3f} {row.records_per_atom:7.4f} "
            f"{row.avg_arity:7.2f} {row.avg_width:7.2f}"
        )
    print()


def print_reading(rows: list[Row]) -> None:
    print("== reading ==")
    best_by_mode: dict[str, Row] = {}
    for row in rows:
        old = best_by_mode.get(row.mode.name)
        if old is None or row.delta_per_atom < old.delta_per_atom:
            best_by_mode[row.mode.name] = row
    for name, row in best_by_mode.items():
        print(
            f"Best {name}: {row.config.name}, slack={row.slack}, qmin={row.min_q:.2f}, "
            f"delta={row.delta_per_atom:.6f}, q={row.q:.3f}, rec/a={row.records_per_atom:.4f}."
        )
    print(
        "If two-epoch parity beats H2, the win is not free; it is a finite-age "
        "forced-refresh design. If the 64-epoch rows lose, static parity by "
        "itself still aliases exactly as expected."
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--broad", action="store_true", help="include larger K/D configs")
    parser.add_argument("--targeted", action="store_true", help="only run the parity lanes")
    parser.add_argument("--trials", type=int, default=8)
    args = parser.parse_args(argv)

    slacks = (1, 2, 4, 6, 8) if args.targeted else (1, 2, 4)
    min_qs = (0.50, 0.75, 0.90) if args.targeted else (0.50, 0.90)
    rows = [
        evaluate(config, mode, slack, min_q, trials=args.trials, seed=113113)
        for config in configs(args.broad)
        for mode in modes(args.targeted)
        for slack in slacks
        for min_q in min_qs
    ]
    print_rows(rows)
    print_reading(rows)


if __name__ == "__main__":
    main()
