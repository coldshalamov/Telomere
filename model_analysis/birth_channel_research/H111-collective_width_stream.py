#!/usr/bin/env python3
"""H111 - collective payload-width stream.

H110 isolated a live-looking gap: partial refresh crosses with a local payload
width oracle, but misses when every record pays J3D1 to delimit its seed.

H111 asks whether the missing payload widths can be transmitted collectively:

    arity stream first -> decoder knows each record's target span
    width/delta stream second -> decoder can split the payload stream
    payload bits third

This is parseable if the width/delta stream is paid. The kernel separates:

* local_oracle: no width stream, hidden channel.
* fixed_delta: per-record fixed delta in the legal slack range.
* fixed_width: per-record fixed payload width in 1..D.
* j3d1: current parseable self-delimiting record field.
* enum counts-free: lower bound with per-file delta counts given free.
* enum count-paid: enumerative delta sequence plus the composition/count bill.

All rows also include the optimistic H2 ready/carry lower bound for the
rewritten atom fraction q. Full cover-shape placement is still not charged, so
positive rows here would be targets, not finished codecs.
"""

from __future__ import annotations

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

    @property
    def local_cost(self) -> int:
        return self.arity_bits + self.width

    @property
    def local_delta(self) -> int:
        return self.local_cost - self.target_bits

    @property
    def delta_value(self) -> int:
        return self.target_bits - self.width


@dataclass(frozen=True)
class CoverChoice:
    edge: Edge


@dataclass(frozen=True)
class TrialResult:
    local: float
    fixed_delta: float
    fixed_width: float
    j3d1: float
    enum_counts_free: float
    enum_count_paid: float
    q: float
    records_per_atom: float
    avg_arity: float
    avg_width: float


@dataclass(frozen=True)
class Row:
    config: Config
    slack: int
    min_q: float
    trials: int
    local: float
    fixed_delta: float
    fixed_width: float
    j3d1: float
    enum_counts_free: float
    enum_count_paid: float
    q: float
    records_per_atom: float
    avg_arity: float
    avg_width: float


def h2(p: float) -> float:
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -(p * math.log2(p) + (1.0 - p) * math.log2(1.0 - p))


def log2_comb(n: int, k: int) -> float:
    if k < 0 or k > n:
        return float("inf")
    return (math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)) / math.log(2.0)


def log2_multinomial(counts: Counter[int]) -> float:
    total = sum(counts.values())
    return (
        math.lgamma(total + 1) - sum(math.lgamma(count + 1) for count in counts.values())
    ) / math.log(2.0)


def delta_range(edge: Edge, slack: int) -> tuple[int, int]:
    lower = edge.arity_bits - slack
    upper = edge.target_bits - 1
    return lower, upper


def delta_range_size(edge: Edge, slack: int) -> int:
    lower, upper = delta_range(edge, slack)
    return max(0, upper - lower + 1)


def sample_edges(config: Config, slack: int, rng: random.Random) -> list[list[Edge]]:
    edges_by_start: list[list[Edge]] = [[] for _ in range(config.atoms)]
    arity_bits = fixed_arity_bits(config.max_arity, 1)
    for start in range(config.atoms):
        max_arity = min(config.max_arity, config.atoms - start)
        for arity in range(1, max_arity + 1):
            target_bits = arity * config.block_bits
            width = local_payload_bits_from_log_rank(sample_log2_first_rank(target_bits, rng))
            if width > config.frontier:
                continue
            bits = fixed_arity_bits(config.max_arity, arity)
            # fixed_arity_bits is constant for these high-arity custom alphabets,
            # but call it per edge to keep the row honest if configs change.
            arity_bits = bits
            edge = Edge(start, arity, width, target_bits, arity_bits)
            if edge.local_delta <= slack:
                edges_by_start[start].append(edge)
    return edges_by_start


def edge_delta(edge: Edge, mode: str, config: Config, slack: int) -> float:
    if mode == "local":
        cost = edge.local_cost
    elif mode == "fixed_delta":
        size = delta_range_size(edge, slack)
        cost = edge.local_cost + math.ceil(math.log2(size))
    elif mode == "fixed_width":
        cost = edge.local_cost + math.ceil(math.log2(config.frontier))
    elif mode == "j3d1":
        if edge.width > MAX_PAYLOAD_WIDTH_BITS:
            return float("inf")
        cost = edge.arity_bits + j3d1_cost_for_payload_width(edge.width)
    else:
        raise ValueError(mode)
    return cost - edge.target_bits


def select_cover(
    config: Config,
    slack: int,
    rng: random.Random,
    mode: str,
    min_q: float,
) -> tuple[float, list[CoverChoice], float]:
    """Select the cheapest cover in an additive width mode."""

    edges_by_start = sample_edges(config, slack, rng)
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
                delta = edge_delta(edge, mode, config, slack)
                if delta == inf:
                    continue
                new_rewritten = rewritten + edge.arity
                end = pos + edge.arity
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
        return inf, [], 0.0

    choices: list[CoverChoice] = []
    pos = n
    rewritten = best_rewritten
    while pos > 0:
        entry = prev[pos][rewritten]
        if entry is None:
            raise AssertionError("missing predecessor")
        prior_pos, prior_rewritten, edge = entry
        if edge.arity > 0:
            choices.append(CoverChoice(edge))
        pos = prior_pos
        rewritten = prior_rewritten
    choices.reverse()
    return best_total, choices, best_rewritten / n


def enum_width_bits(choices: list[CoverChoice], slack: int, count_paid: bool) -> float:
    """Enumerative delta stream cost grouped by arity.

    Given the public arity stream, decoder knows which group each record belongs
    to. For each arity group, charge sequence order. If count_paid is true,
    also charge the weak composition/count vector over the full legal delta
    range for that arity.
    """

    by_arity: dict[int, list[Edge]] = defaultdict(list)
    for choice in choices:
        by_arity[choice.edge.arity].append(choice.edge)

    total = 0.0
    for edges in by_arity.values():
        counts = Counter(edge.delta_value for edge in edges)
        total += log2_multinomial(counts)
        if count_paid:
            # All edges in this arity share target_bits/arity_bits in this model.
            range_size = delta_range_size(edges[0], slack)
            total += log2_comb(len(edges) + range_size - 1, range_size - 1)
    return total


def eval_trial(config: Config, slack: int, min_q: float, seed: int) -> TrialResult:
    local_total, local_choices, q = select_cover(
        config,
        slack,
        random.Random(seed),
        "local",
        min_q,
    )
    fixed_delta, fixed_delta_choices, q_fixed_delta = select_cover(
        config,
        slack,
        random.Random(seed),
        "fixed_delta",
        min_q,
    )
    fixed_width, _, _ = select_cover(config, slack, random.Random(seed), "fixed_width", min_q)
    j3d1, _, _ = select_cover(config, slack, random.Random(seed), "j3d1", min_q)

    if not local_choices:
        enum_free = float("inf")
        enum_paid = float("inf")
        records_per_atom = 0.0
        avg_arity = 0.0
        avg_width = 0.0
    else:
        # Re-score the local selected cover with a collective width stream.
        local_raw_delta = sum(choice.edge.local_delta for choice in local_choices)
        enum_free = (
            local_raw_delta
            + enum_width_bits(local_choices, slack, count_paid=False)
            + config.atoms * h2(q)
        ) / config.atoms
        enum_paid = (
            local_raw_delta
            + enum_width_bits(local_choices, slack, count_paid=True)
            + config.atoms * h2(q)
        ) / config.atoms
        records_per_atom = len(local_choices) / config.atoms
        avg_arity = mean(choice.edge.arity for choice in local_choices)
        avg_width = mean(choice.edge.width for choice in local_choices)

    return TrialResult(
        local=local_total / config.atoms,
        fixed_delta=fixed_delta / config.atoms,
        fixed_width=fixed_width / config.atoms,
        j3d1=j3d1 / config.atoms,
        enum_counts_free=enum_free,
        enum_count_paid=enum_paid,
        q=q_fixed_delta if math.isfinite(fixed_delta) else q,
        records_per_atom=records_per_atom,
        avg_arity=avg_arity,
        avg_width=avg_width,
    )


def evaluate(config: Config, slack: int, min_q: float, trials: int, seed: int) -> Row:
    results = [
        eval_trial(config, slack, min_q, seed + trial * 1_000_003)
        for trial in range(trials)
    ]
    return Row(
        config=config,
        slack=slack,
        min_q=min_q,
        trials=trials,
        local=mean(result.local for result in results),
        fixed_delta=mean(result.fixed_delta for result in results),
        fixed_width=mean(result.fixed_width for result in results),
        j3d1=mean(result.j3d1 for result in results),
        enum_counts_free=mean(result.enum_counts_free for result in results),
        enum_count_paid=mean(result.enum_count_paid for result in results),
        q=mean(result.q for result in results),
        records_per_atom=mean(result.records_per_atom for result in results),
        avg_arity=mean(result.avg_arity for result in results if result.avg_arity > 0.0),
        avg_width=mean(result.avg_width for result in results if result.avg_width > 0.0),
    )


def configs() -> list[Config]:
    return [
        Config("B4_K16_D64", 4, 64, 16, 64),
        Config("B4_K32_D128", 4, 64, 32, 128),
        Config("B4_K128_D512", 4, 128, 128, 512),
        Config("B8_K32_D256", 8, 64, 32, 256),
        Config("B8_K64_D512", 8, 96, 64, 512),
    ]


def fmt(value: float) -> str:
    return "inf" if not math.isfinite(value) else f"{value:.4f}"


def print_rows(rows: list[Row]) -> None:
    print("== collective payload-width stream ==")
    print("All deltas are bits/input atom after H2(q). Negative rows are targets, not finished codecs.")
    print(
        f"{'config':<14} {'s':>2} {'qmin':>5} {'q':>5} {'local':>8} "
        f"{'fixD':>8} {'enum0':>8} {'enum+':>8} {'J3D1':>8} "
        f"{'rec/a':>7} {'arity':>7} {'width':>7}"
    )
    for row in rows:
        print(
            f"{row.config.name:<14} {row.slack:2d} {row.min_q:5.2f} {row.q:5.3f} "
            f"{fmt(row.local):>8} {fmt(row.fixed_delta):>8} "
            f"{fmt(row.enum_counts_free):>8} {fmt(row.enum_count_paid):>8} "
            f"{fmt(row.j3d1):>8} {row.records_per_atom:7.4f} "
            f"{row.avg_arity:7.2f} {row.avg_width:7.2f}"
        )
    print()


def print_reading(rows: list[Row]) -> None:
    print("== reading ==")
    for name, attr in (
        ("local width oracle", "local"),
        ("fixed delta", "fixed_delta"),
        ("enum counts-free", "enum_counts_free"),
        ("enum count-paid", "enum_count_paid"),
        ("J3D1", "j3d1"),
    ):
        best = min(rows, key=lambda row: getattr(row, attr))
        print(
            f"Best {name}: {best.config.name}, slack={best.slack}, qmin={best.min_q:.2f}, "
            f"delta={getattr(best, attr):.6f} bits/atom."
        )
    print(
        "If enum counts-free crosses but enum count-paid does not, the missing "
        "channel is the per-file width histogram. If both miss, collective "
        "width coding is not enough in this tested frontier."
    )


def main() -> None:
    rows = [
        evaluate(config, slack, min_q, trials=10, seed=111111)
        for config in configs()
        for slack in (2, 4, 8)
        for min_q in (0.10, 0.50)
    ]
    print_rows(rows)
    print_reading(rows)


if __name__ == "__main__":
    main()
