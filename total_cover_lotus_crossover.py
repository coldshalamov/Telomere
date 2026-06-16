#!/usr/bin/env python3
"""Total-cover Telomere crossover model.

This branch intentionally excludes sparse replacement costs. Every pass fully
rewrites the layer, every decoded item is a record, and every record opens.
Records are only:

    [arity][seed witness]

The script samples the shortest matching seed witness for every interval under
the uniform hash law, runs an optimal non-overlapping full-cover DP, and charges
only arity plus witness costs.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from statistics import mean
from typing import Callable, Iterable


ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model_analysis.proof_kernel.costs import (  # noqa: E402
    MAX_PAYLOAD_WIDTH_BITS,
    arity_cost,
    j3d1_cost_for_payload_width,
    record_cost_for_payload_width,
)


B_GRID = (4, 6, 8, 12, 24)
K_GRID = (5, 8, 16, 24, 32, 48, 64, 96, 128)


def fixed_arity_bits(max_arity: int, arity: int) -> int:
    """Parseable total-cover arity code for non-v1 experiments."""

    if max_arity == 2:
        return 1
    if max_arity <= 5:
        return arity_cost(arity)
    return math.ceil(math.log2(max_arity))


def log2_factorial(n: int) -> float:
    return math.lgamma(n + 1) / math.log(2.0)


def multinomial_bits(counts: Counter[object]) -> float:
    total = sum(counts.values())
    return log2_factorial(total) - sum(log2_factorial(count) for count in counts.values())


def sample_first_rank(target_bits: int, rng: random.Random) -> int:
    """Sample first matching seed rank under the uniform hash law."""

    q = 2.0 ** (-target_bits)
    u = rng.random()
    if target_bits <= 48:
        return math.ceil(math.log1p(-u) / math.log1p(-q))
    return math.ceil(2.0 ** (target_bits + math.log2(rng.expovariate(1.0))))


def sample_log2_first_rank(target_bits: int, rng: random.Random) -> float:
    """Sample log2(first matching seed rank) under the uniform hash law.

    For small targets, use an exact geometric draw. For large targets, use the
    exponential race approximation: rank / 2^target_bits -> Exp(1).
    """

    return math.log2(sample_first_rank(target_bits, rng))


def lotus_payload_width_from_log_rank(log2_rank: float) -> int:
    """Smallest J3D1 payload width whose <=width seed set can include rank.

    costs.payload_width_count_le(p) = 2^(p+1)-3, so p ~= ceil(log2(rank)-1).
    """

    return max(1, math.ceil(log2_rank - 1.0))


def local_payload_bits_from_log_rank(log2_rank: float) -> int:
    """Local fixed-width payload bits for a first-2^w custom witness field."""

    return max(1, math.ceil(log2_rank))


@dataclass(frozen=True)
class EdgeSample:
    rank: int
    log2_rank: float
    lotus_payload_width: int
    local_payload_bits: int
    target_bits: int


@dataclass(frozen=True)
class SelectedRecord:
    arity: int
    rank: int
    target_bits: int
    lotus_payload_width: int
    local_payload_bits: int
    cost_bits: float


@dataclass(frozen=True)
class CoverStats:
    covered: bool
    charged_bits: float
    records: tuple[SelectedRecord, ...]


@dataclass(frozen=True)
class Mode:
    name: str
    description: str
    local_cost: Callable[[EdgeSample, int, int, int], float | None]
    post_cost: Callable[[tuple[SelectedRecord, ...], int, int], float] | None = None
    exact_v1: bool = False
    joint_markov1: bool = False


def class_set(width: int, count: int, style: str) -> tuple[int, ...]:
    width = max(1, width)
    if count <= 1:
        return (width,)
    if style == "tail":
        return tuple(range(max(1, width - count + 1), width + 1))
    if style == "log":
        offsets = [0, 1, 2, 4, 8, 13, 21, 34, 55, 89, 144, 233]
        values = sorted({max(1, width - offset) for offset in offsets[:count]})
        while len(values) < count and values[0] > 1:
            values.insert(0, values[0] - 1)
        return tuple(values)
    if style == "uniform":
        return tuple(sorted({max(1, math.ceil(width * i / count)) for i in range(1, count + 1)}))
    raise ValueError(style)


def make_modes() -> list[Mode]:
    def oracle_free(edge: EdgeSample, arity: int, max_arity: int, frontier: int) -> float | None:
        if edge.lotus_payload_width > frontier:
            return None
        return fixed_arity_bits(max_arity, arity) + edge.lotus_payload_width

    def exact_v1(edge: EdgeSample, arity: int, max_arity: int, frontier: int) -> float | None:
        if arity > 5 or edge.lotus_payload_width > min(frontier, MAX_PAYLOAD_WIDTH_BITS):
            return None
        return float(record_cost_for_payload_width(arity, edge.lotus_payload_width))

    def extended_j3d1(edge: EdgeSample, arity: int, max_arity: int, frontier: int) -> float | None:
        if edge.lotus_payload_width > min(frontier, MAX_PAYLOAD_WIDTH_BITS):
            return None
        return fixed_arity_bits(max_arity, arity) + j3d1_cost_for_payload_width(edge.lotus_payload_width)

    def fixed_width(edge: EdgeSample, arity: int, max_arity: int, frontier: int) -> float | None:
        if edge.local_payload_bits > frontier:
            return None
        return fixed_arity_bits(max_arity, arity) + frontier

    def width_classes(count: int, style: str) -> Callable[[EdgeSample, int, int, int], float | None]:
        def cost(edge: EdgeSample, arity: int, max_arity: int, frontier: int) -> float | None:
            classes = class_set(frontier, count, style)
            if edge.local_payload_bits > classes[-1]:
                return None
            selected = next(value for value in classes if value >= edge.local_payload_bits)
            class_bits = math.ceil(math.log2(len(classes)))
            return fixed_arity_bits(max_arity, arity) + class_bits + selected

        return cost

    def entropy_select(edge: EdgeSample, arity: int, max_arity: int, frontier: int) -> float | None:
        if edge.lotus_payload_width > frontier:
            return None
        # Optimistic selection cost. Final parseable cost is charged in post_cost.
        return edge.lotus_payload_width

    def entropy_lotus_post(records: tuple[SelectedRecord, ...], max_arity: int, frontier: int) -> float:
        symbols = Counter((record.arity, record.lotus_payload_width) for record in records)
        return sum(record.lotus_payload_width for record in records) + multinomial_bits(symbols)

    def entropy_local_select(edge: EdgeSample, arity: int, max_arity: int, frontier: int) -> float | None:
        if edge.local_payload_bits > frontier:
            return None
        return edge.local_payload_bits

    def entropy_local_post(records: tuple[SelectedRecord, ...], max_arity: int, frontier: int) -> float:
        symbols = Counter((record.arity, record.local_payload_bits) for record in records)
        return sum(record.local_payload_bits for record in records) + multinomial_bits(symbols)

    def arity2_only(edge: EdgeSample, arity: int, max_arity: int, frontier: int) -> float | None:
        if arity > 2 or edge.lotus_payload_width > min(frontier, MAX_PAYLOAD_WIDTH_BITS):
            return None
        return 1.0 + j3d1_cost_for_payload_width(edge.lotus_payload_width)

    def arity2_arith_select(edge: EdgeSample, arity: int, max_arity: int, frontier: int) -> float | None:
        if arity > 2 or edge.lotus_payload_width > frontier:
            return None
        return edge.lotus_payload_width

    def arity2_arith_post(records: tuple[SelectedRecord, ...], max_arity: int, frontier: int) -> float:
        symbols = Counter((record.arity, record.lotus_payload_width) for record in records)
        return sum(record.lotus_payload_width for record in records) + multinomial_bits(symbols) + 1.0

    def markov1_lotus_post(records: tuple[SelectedRecord, ...], max_arity: int, frontier: int) -> float:
        symbols = [(record.arity, record.lotus_payload_width) for record in records]
        total = len(symbols)
        if total == 0:
            return 0.0
        # First symbol: iid marginal entropy
        counts = Counter(symbols)
        bits = -sum((c / total) * math.log2(c / total) for c in counts.values())
        # Remaining: conditional entropy H(symbol_i | symbol_{i-1})
        if total >= 2:
            prev_counts = Counter(symbols[i] for i in range(total - 1))
            cond: dict[tuple, Counter] = {}
            for i in range(total - 1):
                prev = symbols[i]
                curr = symbols[i + 1]
                if prev not in cond:
                    cond[prev] = Counter()
                cond[prev][curr] += 1
            cond_bits = 0.0
            for prev, cnt in prev_counts.items():
                sub = cond[prev]
                sub_total = sum(sub.values())
                p = cnt / (total - 1)
                h = -sum((c / sub_total) * math.log2(c / sub_total) for c in sub.values())
                cond_bits += p * h
            bits += (total - 1) * cond_bits
        return sum(record.lotus_payload_width for record in records) + bits

    def markov2_lotus_post(records: tuple[SelectedRecord, ...], max_arity: int, frontier: int) -> float:
        symbols = [(record.arity, record.lotus_payload_width) for record in records]
        total = len(symbols)
        if total == 0:
            return 0.0
        if total == 1:
            counts = Counter(symbols)
            bits = -sum((c / total) * math.log2(c / total) for c in counts.values())
            return sum(record.lotus_payload_width for record in records) + bits
        # First symbol: iid marginal entropy
        counts = Counter(symbols)
        bits = -sum((c / total) * math.log2(c / total) for c in counts.values())
        # Second symbol: conditional entropy H(symbol_1 | symbol_0)
        prev_counts = Counter(symbols[i] for i in range(total - 1))
        cond: dict[tuple, Counter] = {}
        for i in range(total - 1):
            prev = symbols[i]
            curr = symbols[i + 1]
            if prev not in cond:
                cond[prev] = Counter()
            cond[prev][curr] += 1
        cond_bits_1 = 0.0
        for prev, cnt in prev_counts.items():
            sub = cond[prev]
            sub_total = sum(sub.values())
            p = cnt / (total - 1)
            h = -sum((c / sub_total) * math.log2(c / sub_total) for c in sub.values())
            cond_bits_1 += p * h
        bits += cond_bits_1
        # Remaining: conditional entropy H(symbol_i | symbol_{i-1}, symbol_{i-2})
        if total >= 3:
            prev2_counts = Counter((symbols[i], symbols[i + 1]) for i in range(total - 2))
            cond2: dict[tuple, Counter] = {}
            for i in range(total - 2):
                key = (symbols[i], symbols[i + 1])
                curr = symbols[i + 2]
                if key not in cond2:
                    cond2[key] = Counter()
                cond2[key][curr] += 1
            cond_bits_2 = 0.0
            for key, cnt in prev2_counts.items():
                sub = cond2[key]
                sub_total = sum(sub.values())
                p = cnt / (total - 2)
                h = -sum((c / sub_total) * math.log2(c / sub_total) for c in sub.values())
                cond_bits_2 += p * h
            bits += (total - 2) * cond_bits_2
        return sum(record.lotus_payload_width for record in records) + bits

    def markov1_geometric_rank_post(records: tuple[SelectedRecord, ...], max_arity: int, frontier: int) -> float:
        # Markov1 entropy of (arity, width) symbols.
        symbols = [(record.arity, record.lotus_payload_width) for record in records]
        total = len(symbols)
        stream_bits = 0.0
        if total > 0:
            counts = Counter(symbols)
            bits = -sum((c / total) * math.log2(c / total) for c in counts.values())
            if total >= 2:
                prev_counts = Counter(symbols[i] for i in range(total - 1))
                cond: dict[tuple, Counter] = {}
                for i in range(total - 1):
                    prev = symbols[i]
                    curr = symbols[i + 1]
                    if prev not in cond:
                        cond[prev] = Counter()
                    cond[prev][curr] += 1
                cond_bits = 0.0
                for prev, cnt in prev_counts.items():
                    sub = cond[prev]
                    sub_total = sum(sub.values())
                    p = cnt / (total - 1)
                    h = -sum((c / sub_total) * math.log2(c / sub_total) for c in sub.values())
                    cond_bits += p * h
                bits += (total - 1) * cond_bits / total
            stream_bits = bits * total
        # Geometric entropy of exact rank within each (arity, width) class.
        def truncated_geometric_entropy(target_bits: int, width: int) -> float:
            if width < 1:
                return 0.0
            q = 2.0 ** (-target_bits)
            lo = 1 << (width - 1)
            hi = (1 << width) - 1
            if lo > hi:
                return 0.0
            # Z = P(lo <= r <= hi)
            z = (1 - q) ** (lo - 1) - (1 - q) ** hi
            if z <= 0:
                return 0.0
            # E[r | lo <= r <= hi]
            # sum_{r=a}^{b} r q (1-q)^{r-1} = S(b) - S(a-1)
            # where S(n) = (1 - (1-q)^n (1 + n q)) / q
            def s(n: int) -> float:
                if n <= 0:
                    return 0.0
                return (1.0 - (1 - q) ** n * (1 + n * q)) / q

            mean_r = (s(hi) - s(lo - 1)) / z
            # H = -log2(q) - log2(1-q)*(mean_r - 1) + log2(z)
            return -math.log2(q) - math.log2(1 - q) * (mean_r - 1.0) + math.log2(z)

        grouped: dict[tuple[int, int], list[SelectedRecord]] = {}
        for record in records:
            key = (record.arity, record.lotus_payload_width)
            grouped.setdefault(key, []).append(record)
        rank_bits = sum(
            len(recs) * truncated_geometric_entropy(recs[0].target_bits, recs[0].lotus_payload_width)
            for recs in grouped.values()
        )
        return stream_bits + rank_bits

    return [
        Mode("free_boundary_oracle", "arity + raw first-hit Lotus payload width", oracle_free),
        Mode("exact_v1_j3d1", "current V1 arity 1..5 + exact J3D1", exact_v1, exact_v1=True),
        Mode("extended_j3d1_fixed_arity", "fixed K-bit arity alphabet + exact J3D1 seed", extended_j3d1),
        Mode("global_fixed_seed_width", "one seed payload width per layer", fixed_width),
        Mode("width_classes4_log", "4 global log-spaced width classes + class id", width_classes(4, "log")),
        Mode("width_classes8_log", "8 global log-spaced width classes + class id", width_classes(8, "log")),
        Mode("width_classes4_uniform", "4 global uniform width classes + class id", width_classes(4, "uniform")),
        Mode(
            "arith_arity_width_lotus_payload",
            "front-coded arithmetic arity/width bins + local Lotus payload",
            entropy_select,
            entropy_lotus_post,
        ),
        Mode(
            "whole_cover_local_payload_stream",
            "whole-cover arity/width stream + first-2^w local payloads",
            entropy_local_select,
            entropy_local_post,
        ),
        Mode("arity2_exact_j3d1", "arity 1..2 only, 1-bit arity + exact J3D1 seed", arity2_only),
        Mode(
            "arity2_arith_width_lotus_payload",
            "arity 1..2 only, 1-bit arity + front-coded width bins + local Lotus payload",
            arity2_arith_select,
            arity2_arith_post,
        ),
        Mode(
            "markov1_arith_width_lotus_payload",
            "first-order Markov (arity,width) entropy + local Lotus payload",
            entropy_select,
            markov1_lotus_post,
        ),
        Mode(
            "markov2_arith_width_lotus_payload",
            "second-order Markov (arity,width) entropy + local Lotus payload",
            entropy_select,
            markov2_lotus_post,
        ),
        Mode(
            "markov1_joint_dp",
            "joint-cost DP optimizing first-order Markov witness stream",
            entropy_select,
            markov1_lotus_post,
            joint_markov1=True,
        ),
        Mode(
            "markov1_geometric_rank",
            "first-order Markov (arity,width) + geometric exact-rank coding",
            entropy_select,
            markov1_geometric_rank_post,
        ),
    ] + make_markov_with_penalty_modes()


def make_markov_with_penalty_modes() -> list[Mode]:
    def entropy_select(edge: EdgeSample, arity: int, max_arity: int, frontier: int) -> float | None:
        if edge.lotus_payload_width > frontier:
            return None
        return edge.lotus_payload_width

    def markov1_base_post(records: tuple[SelectedRecord, ...]) -> float:
        # Same as markov1_lotus_post but without unused max_arity/frontier args.
        symbols = [(record.arity, record.lotus_payload_width) for record in records]
        total = len(symbols)
        if total == 0:
            return 0.0
        counts = Counter(symbols)
        bits = -sum((c / total) * math.log2(c / total) for c in counts.values())
        if total >= 2:
            prev_counts = Counter(symbols[i] for i in range(total - 1))
            cond: dict[tuple, Counter] = {}
            for i in range(total - 1):
                prev = symbols[i]
                curr = symbols[i + 1]
                if prev not in cond:
                    cond[prev] = Counter()
                cond[prev][curr] += 1
            cond_bits = 0.0
            for prev, cnt in prev_counts.items():
                sub = cond[prev]
                sub_total = sum(sub.values())
                p = cnt / (total - 1)
                h = -sum((c / sub_total) * math.log2(c / sub_total) for c in sub.values())
                cond_bits += p * h
            bits += (total - 1) * cond_bits
        return sum(record.lotus_payload_width for record in records) + bits

    modes = []
    for penalty in (0.05, 0.10, 0.15, 0.20):

        def post(records: tuple[SelectedRecord, ...], max_arity: int, frontier: int, penalty: float = penalty) -> float:
            return markov1_base_post(records) + penalty * len(records)

        modes.append(
            Mode(
                f"markov1_penalty_{penalty:.2f}",
                f"first-order Markov + {penalty} bits/record adaptive overhead",
                entropy_select,
                post,
            )
        )
    return modes


def d_candidates(max_frontier: int, max_count: int) -> list[int]:
    values: set[int] = set()
    for d in range(1, min(max_frontier, 96) + 1):
        values.add(d)
    step = 4
    d = 100
    while d <= max_frontier:
        values.add(d)
        d += step
        if d >= 192:
            step = 8
        if d >= 384:
            step = 16
        if d >= 768:
            step = 32
        if d >= 1536:
            step = 64
    values.add(max_frontier)
    ordered = sorted(value for value in values if 1 <= value <= max_frontier)
    if len(ordered) <= max_count:
        return ordered
    keep: set[int] = set()
    keep.update(value for value in ordered if value <= 32)
    keep.add(max_frontier)
    remaining = max(1, max_count - len(keep))
    for index in range(remaining):
        position = round(index * (len(ordered) - 1) / max(1, remaining - 1))
        keep.add(ordered[position])
    return sorted(keep)


def generate_samples(
    block_bits: int,
    max_arity: int,
    atoms: int,
    trials: int,
    seed: int,
) -> list[list[list[EdgeSample]]]:
    rng = random.Random(seed)
    all_trials: list[list[list[EdgeSample]]] = []
    for _ in range(trials):
        trial: list[list[EdgeSample]] = []
        for index in range(atoms):
            row: list[EdgeSample] = []
            for arity in range(1, min(max_arity, atoms - index) + 1):
                target_bits = arity * block_bits
                rank = sample_first_rank(target_bits, rng)
                log2_rank = math.log2(rank)
                row.append(
                    EdgeSample(
                        rank=rank,
                        log2_rank=log2_rank,
                        lotus_payload_width=lotus_payload_width_from_log_rank(log2_rank),
                        local_payload_bits=local_payload_bits_from_log_rank(log2_rank),
                        target_bits=target_bits,
                    )
                )
            trial.append(row)
        all_trials.append(trial)
    return all_trials


def run_one_cover(
    trial: list[list[EdgeSample]],
    block_bits: int,
    max_arity: int,
    frontier: int,
    mode: Mode,
) -> CoverStats:
    atoms = len(trial)
    dp = [float("inf")] * (atoms + 1)
    prev: list[tuple[int, int, EdgeSample, float] | None] = [None] * (atoms + 1)
    dp[0] = 0.0
    for index in range(atoms):
        base = dp[index]
        if base == float("inf"):
            continue
        for offset, edge in enumerate(trial[index], start=1):
            cost = mode.local_cost(edge, offset, max_arity, frontier)
            if cost is None:
                continue
            candidate = base + cost
            end = index + offset
            if candidate < dp[end]:
                dp[end] = candidate
                prev[end] = (index, offset, edge, cost)
    if dp[atoms] == float("inf"):
        return CoverStats(False, float("inf"), ())
    cursor = atoms
    records: list[SelectedRecord] = []
    while cursor > 0:
        entry = prev[cursor]
        if entry is None:
            raise AssertionError("missing predecessor in covered DP")
        prior, arity, edge, cost = entry
        records.append(
            SelectedRecord(
                arity=arity,
                rank=edge.rank,
                target_bits=edge.target_bits,
                lotus_payload_width=edge.lotus_payload_width,
                local_payload_bits=edge.local_payload_bits,
                cost_bits=cost,
            )
        )
        cursor = prior
    records.reverse()
    selected = tuple(records)
    charged = mode.post_cost(selected, max_arity, frontier) if mode.post_cost else dp[atoms]
    return CoverStats(True, charged, selected)


def _cover_to_symbols(records: tuple[SelectedRecord, ...]) -> list[tuple[int, int]]:
    return [(record.arity, record.lotus_payload_width) for record in records]


def _estimate_markov1_model(symbols: list[tuple[int, int]]) -> tuple[dict, dict]:
    """Return marginal P(sym) and conditional P(sym | prev) as log-probability maps."""
    total = len(symbols)
    marginal: dict[tuple[int, int], float] = {}
    if total > 0:
        counts = Counter(symbols)
        for sym, c in counts.items():
            marginal[sym] = -math.log2(c / total)
    conditional: dict[tuple[int, int], dict[tuple[int, int], float]] = {}
    if total >= 2:
        prev_counts = Counter(symbols[i] for i in range(total - 1))
        cond: dict[tuple[int, int], Counter] = {}
        for i in range(total - 1):
            prev = symbols[i]
            curr = symbols[i + 1]
            if prev not in cond:
                cond[prev] = Counter()
            cond[prev][curr] += 1
        for prev, cnt in prev_counts.items():
            sub = cond[prev]
            sub_total = sum(sub.values())
            conditional[prev] = {}
            for curr, c in sub.items():
                conditional[prev][curr] = -math.log2(c / sub_total)
    return marginal, conditional


def run_one_cover_markov1(
    trial: list[list[EdgeSample]],
    max_arity: int,
    frontier: int,
    iterations: int = 3,
) -> CoverStats:
    """Joint-cost DP optimizing first-order Markov-coded witness stream."""
    atoms = len(trial)

    # Initial width-minimizing cover.
    dp0 = [float("inf")] * (atoms + 1)
    prev0: list[tuple[int, int, EdgeSample] | None] = [None] * (atoms + 1)
    dp0[0] = 0.0
    for index in range(atoms):
        base = dp0[index]
        if base == float("inf"):
            continue
        for offset, edge in enumerate(trial[index], start=1):
            if offset > max_arity or edge.lotus_payload_width > frontier:
                continue
            candidate = base + edge.lotus_payload_width
            end = index + offset
            if candidate < dp0[end]:
                dp0[end] = candidate
                prev0[end] = (index, offset, edge)
    if dp0[atoms] == float("inf"):
        return CoverStats(False, float("inf"), ())

    def traceback(prev_list: list) -> tuple[SelectedRecord, ...]:
        cursor = atoms
        records: list[SelectedRecord] = []
        while cursor > 0:
            entry = prev_list[cursor]
            if entry is None:
                raise AssertionError("missing predecessor")
            prior, arity, edge = entry
            records.append(
                SelectedRecord(
                    arity=arity,
                    rank=edge.rank,
                    target_bits=edge.target_bits,
                    lotus_payload_width=edge.lotus_payload_width,
                    local_payload_bits=edge.local_payload_bits,
                    cost_bits=edge.lotus_payload_width,
                )
            )
            cursor = prior
        records.reverse()
        return tuple(records)

    selected = traceback(prev0)

    for _ in range(iterations):
        symbols = _cover_to_symbols(selected)
        marginal, conditional = _estimate_markov1_model(symbols)
        # DP with first-order Markov cost.
        START: tuple[int, int] | None = None
        symbols_set = set(marginal.keys())
        # Also allow transitions to any symbol seen after any previous symbol.
        for prev_map in conditional.values():
            symbols_set.update(prev_map.keys())
        # dp[pos][prev_symbol]
        INF = float("inf")
        dp: dict[int, dict[tuple[int, int] | None, float]] = {0: {START: 0.0}}
        back: dict[
            int, dict[tuple[int, int] | None, tuple[int, int, EdgeSample, tuple[int, int] | None] | None]
        ] = {0: {START: None}}
        for pos in range(atoms):
            if pos not in dp:
                continue
            for prev_sym, base in dp[pos].items():
                for offset, edge in enumerate(trial[pos], start=1):
                    if offset > max_arity or edge.lotus_payload_width > frontier:
                        continue
                    sym = (offset, edge.lotus_payload_width)
                    if prev_sym is START:
                        code_cost = marginal.get(sym, 20.0)  # penalty for unseen
                    else:
                        code_cost = conditional.get(prev_sym, {}).get(sym, 20.0)
                    candidate = base + edge.lotus_payload_width + code_cost
                    end = pos + offset
                    if end not in dp:
                        dp[end] = {}
                        back[end] = {}
                    if candidate < dp[end].get(sym, INF):
                        dp[end][sym] = candidate
                        back[end][sym] = (pos, offset, edge, prev_sym)
        if atoms not in dp:
            break
        # Pick best final state.
        best_sym = min(dp[atoms], key=lambda s: dp[atoms][s])
        # Traceback.
        cursor = atoms
        prev_sym = best_sym
        records: list[SelectedRecord] = []
        while cursor > 0:
            entry = back[cursor][prev_sym]
            if entry is None:
                break
            prior, arity, edge, _ = entry
            records.append(
                SelectedRecord(
                    arity=arity,
                    rank=edge.rank,
                    target_bits=edge.target_bits,
                    lotus_payload_width=edge.lotus_payload_width,
                    local_payload_bits=edge.local_payload_bits,
                    cost_bits=edge.lotus_payload_width,
                )
            )
            cursor = prior
            prev_sym = entry[3]
        records.reverse()
        selected = tuple(records)

    # Final charged cost using empirical Markov1 entropy.
    symbols = _cover_to_symbols(selected)
    total = len(symbols)
    if total == 0:
        return CoverStats(True, 0.0, selected)
    counts = Counter(symbols)
    stream_bits = -sum((c / total) * math.log2(c / total) for c in counts.values()) * total
    if total >= 2:
        prev_counts = Counter(symbols[i] for i in range(total - 1))
        cond: dict[tuple[int, int], Counter] = {}
        for i in range(total - 1):
            prev = symbols[i]
            curr = symbols[i + 1]
            if prev not in cond:
                cond[prev] = Counter()
            cond[prev][curr] += 1
        cond_bits = 0.0
        for prev, cnt in prev_counts.items():
            sub = cond[prev]
            sub_total = sum(sub.values())
            p = cnt / (total - 1)
            h = -sum((c / sub_total) * math.log2(c / sub_total) for c in sub.values())
            cond_bits += p * h
        stream_bits += (total - 1) * cond_bits
    charged = sum(record.lotus_payload_width for record in selected) + stream_bits
    return CoverStats(True, charged, selected)


@dataclass(frozen=True)
class SummaryRow:
    mode: str
    block_bits: int
    max_arity: int
    frontier: int
    max_span_bytes: float
    cover_rate: float
    gain_per_atom: float
    gain_per_byte: float
    records_per_atom: float
    avg_selected_arity: float
    avg_lotus_payload_width: float
    avg_local_payload_bits: float
    arity_bits_per_record: float
    witness_bits_per_record: float
    total_bits_per_record: float
    missing_bits_per_record: float


def summarize_covers(
    covers: list[CoverStats],
    block_bits: int,
    max_arity: int,
    frontier: int,
    mode_name: str,
) -> SummaryRow:
    covered = [cover for cover in covers if cover.covered]
    cover_rate = len(covered) / len(covers) if covers else 0.0
    atoms = 0
    if covered:
        # All trials have the same atom count; infer it from selected arities.
        atoms = sum(record.arity for record in covered[0].records)
    raw_bits = atoms * block_bits if atoms else 0
    gain_per_atom = mean((raw_bits - cover.charged_bits) / atoms for cover in covered) if covered else float("-inf")
    record_counts = [len(cover.records) for cover in covered]
    records_per_atom = mean(count / atoms for count in record_counts) if covered else 0.0
    all_records = [record for cover in covered for record in cover.records]
    avg_arity = mean(record.arity for record in all_records) if all_records else 0.0
    avg_lotus = mean(record.lotus_payload_width for record in all_records) if all_records else 0.0
    avg_local = mean(record.local_payload_bits for record in all_records) if all_records else 0.0
    arity_bits = mean(fixed_arity_bits(max_arity, record.arity) for record in all_records) if all_records else 0.0
    total_bits = mean(cover.charged_bits / len(cover.records) for cover in covered) if covered else float("inf")
    witness_bits = total_bits - arity_bits if covered else float("inf")
    missing = max(0.0, -gain_per_atom / records_per_atom) if records_per_atom else float("inf")
    return SummaryRow(
        mode=mode_name,
        block_bits=block_bits,
        max_arity=max_arity,
        frontier=frontier,
        max_span_bytes=(max_arity * block_bits) / 8.0,
        cover_rate=cover_rate,
        gain_per_atom=gain_per_atom,
        gain_per_byte=gain_per_atom * (8.0 / block_bits) if gain_per_atom != float("-inf") else float("-inf"),
        records_per_atom=records_per_atom,
        avg_selected_arity=avg_arity,
        avg_lotus_payload_width=avg_lotus,
        avg_local_payload_bits=avg_local,
        arity_bits_per_record=arity_bits,
        witness_bits_per_record=witness_bits,
        total_bits_per_record=total_bits,
        missing_bits_per_record=missing,
    )


def evaluate(
    samples: list[list[list[EdgeSample]]],
    block_bits: int,
    max_arity: int,
    frontier: int,
    mode: Mode,
) -> SummaryRow:
    if mode.joint_markov1:
        covers = [run_one_cover_markov1(trial, max_arity, frontier) for trial in samples]
    else:
        covers = [run_one_cover(trial, block_bits, max_arity, frontier, mode) for trial in samples]
    return summarize_covers(covers, block_bits, max_arity, frontier, mode.name)


def first_positive_or_nearest(
    samples: list[list[list[EdgeSample]]],
    block_bits: int,
    max_arity: int,
    mode: Mode,
    coverage_threshold: float,
    max_frontier: int,
    max_frontier_candidates: int,
) -> tuple[SummaryRow | None, SummaryRow | None, list[SummaryRow]]:
    if mode.exact_v1:
        max_frontier = min(max_frontier, MAX_PAYLOAD_WIDTH_BITS)
        effective_arity = min(max_arity, 5)
    else:
        effective_arity = max_arity
    max_frontier = max(1, max_frontier)
    candidates = d_candidates(max_frontier, max_frontier_candidates)
    rows: list[SummaryRow] = []
    first: SummaryRow | None = None
    nearest: SummaryRow | None = None
    for frontier in candidates:
        row = evaluate(samples, block_bits, effective_arity, frontier, mode)
        rows.append(row)
        if (
            first is None
            and row.cover_rate >= coverage_threshold
            and row.gain_per_atom > 0
        ):
            first = row
            previous = max(1, frontier - 8)
            for refined in range(previous, frontier + 1):
                refined_row = evaluate(samples, block_bits, effective_arity, refined, mode)
                if refined_row.cover_rate >= coverage_threshold and refined_row.gain_per_atom > 0:
                    first = refined_row
                    break
            break
    for row in rows:
        if row.cover_rate < coverage_threshold:
            continue
        if nearest is None or row.gain_per_atom > nearest.gain_per_atom:
            nearest = row
    if nearest is None:
        nearest = max(rows, key=lambda row: (row.cover_rate, row.gain_per_atom), default=None)
    return first, nearest, rows


def row_to_dict(row: SummaryRow | None) -> dict | None:
    if row is None:
        return None
    return {
        "mode": row.mode,
        "B": row.block_bits,
        "K": row.max_arity,
        "D": row.frontier,
        "max_span_bytes": row.max_span_bytes,
        "cover_rate": row.cover_rate,
        "gain_per_atom": row.gain_per_atom,
        "gain_per_byte": row.gain_per_byte,
        "records_per_atom": row.records_per_atom,
        "avg_selected_arity": row.avg_selected_arity,
        "avg_lotus_payload_width": row.avg_lotus_payload_width,
        "avg_local_payload_bits": row.avg_local_payload_bits,
        "arity_bits_per_record": row.arity_bits_per_record,
        "witness_bits_per_record": row.witness_bits_per_record,
        "total_bits_per_record": row.total_bits_per_record,
        "missing_bits_per_record": row.missing_bits_per_record,
    }


def markdown_table(rows: Iterable[SummaryRow]) -> str:
    lines = [
        "| mode | B | K | D | cover | gain/atom | gain/byte | rec/atom | avg arity | avg pw | arity bits/rec | witness bits/rec | missing bits/rec |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row.mode} | {row.block_bits} | {row.max_arity} | {row.frontier} | "
            f"{row.cover_rate:.3f} | {row.gain_per_atom:.4f} | {row.gain_per_byte:.4f} | "
            f"{row.records_per_atom:.4f} | {row.avg_selected_arity:.2f} | "
            f"{row.avg_lotus_payload_width:.2f} | {row.arity_bits_per_record:.2f} | "
            f"{row.witness_bits_per_record:.2f} | {row.missing_bits_per_record:.3f} |"
        )
    return "\n".join(lines)


def run(args: argparse.Namespace) -> dict:
    modes = make_modes()
    selected_modes = [mode for mode in modes if mode.name in set(args.modes)]
    if not selected_modes:
        raise SystemExit("no modes selected")
    all_results: list[dict] = []
    first_rows: list[SummaryRow] = []
    nearest_rows: list[SummaryRow] = []
    for block_bits in args.block_bits:
        for max_arity in args.max_arity:
            samples = generate_samples(
                block_bits,
                max_arity,
                args.atoms,
                args.trials,
                args.seed + block_bits * 1009 + max_arity * 9173,
            )
            max_frontier = max_arity * block_bits
            for mode in selected_modes:
                if mode.exact_v1 and max_arity != 5:
                    continue
                first, nearest, _ = first_positive_or_nearest(
                    samples,
                    block_bits,
                    max_arity,
                    mode,
                    args.coverage,
                    max_frontier,
                    args.max_frontiers,
                )
                if first is not None:
                    first_rows.append(first)
                if nearest is not None:
                    nearest_rows.append(nearest)
                all_results.append(
                    {
                        "B": block_bits,
                        "K": max_arity,
                        "mode": mode.name,
                        "first_positive": row_to_dict(first),
                        "nearest": row_to_dict(nearest),
                    }
                )
    return {
        "config": {
            "atoms": args.atoms,
            "trials": args.trials,
            "coverage_threshold": args.coverage,
            "seed": args.seed,
            "block_bits": args.block_bits,
            "max_arity": args.max_arity,
            "modes": args.modes,
        },
        "results": all_results,
        "first_rows": [row_to_dict(row) for row in first_rows],
        "nearest_rows": [row_to_dict(row) for row in nearest_rows],
    }


def render_report(data: dict) -> str:
    config = data["config"]
    first_rows = [
        SummaryRow(**{
            "mode": row["mode"],
            "block_bits": row["B"],
            "max_arity": row["K"],
            "frontier": row["D"],
            "max_span_bytes": row["max_span_bytes"],
            "cover_rate": row["cover_rate"],
            "gain_per_atom": row["gain_per_atom"],
            "gain_per_byte": row["gain_per_byte"],
            "records_per_atom": row["records_per_atom"],
            "avg_selected_arity": row["avg_selected_arity"],
            "avg_lotus_payload_width": row["avg_lotus_payload_width"],
            "avg_local_payload_bits": row["avg_local_payload_bits"],
            "arity_bits_per_record": row["arity_bits_per_record"],
            "witness_bits_per_record": row["witness_bits_per_record"],
            "total_bits_per_record": row["total_bits_per_record"],
            "missing_bits_per_record": row["missing_bits_per_record"],
        })
        for row in data["first_rows"]
    ]
    nearest_rows = [
        SummaryRow(**{
            "mode": row["mode"],
            "block_bits": row["B"],
            "max_arity": row["K"],
            "frontier": row["D"],
            "max_span_bytes": row["max_span_bytes"],
            "cover_rate": row["cover_rate"],
            "gain_per_atom": row["gain_per_atom"],
            "gain_per_byte": row["gain_per_byte"],
            "records_per_atom": row["records_per_atom"],
            "avg_selected_arity": row["avg_selected_arity"],
            "avg_lotus_payload_width": row["avg_lotus_payload_width"],
            "avg_local_payload_bits": row["avg_local_payload_bits"],
            "arity_bits_per_record": row["arity_bits_per_record"],
            "witness_bits_per_record": row["witness_bits_per_record"],
            "total_bits_per_record": row["total_bits_per_record"],
            "missing_bits_per_record": row["missing_bits_per_record"],
        })
        for row in data["nearest_rows"]
    ]
    first_sorted = sorted(first_rows, key=lambda row: (row.mode, row.block_bits, row.max_arity, row.frontier))
    nearest_sorted = sorted(nearest_rows, key=lambda row: row.gain_per_atom, reverse=True)
    lines = [
        "# Total-Cover Lotus Crossover Results",
        "",
        "This branch fully rewrites every layer. There are no carried records,",
        "open/carry maps, birth-pass tags, sparse hit bitmaps, final-position",
        "notes, or PCTB ledgers in these numbers. A record is only",
        "`[arity][seed witness]`.",
        "",
        "The model samples uniform-hash first-hit seed ranks for every interval",
        "and runs an optimal non-overlapping full-cover DP. A row is counted as",
        f"first-positive only if full-cover rate is at least `{config['coverage_threshold']}`",
        "and charged gain is positive.",
        "",
        "## Run Config",
        "",
        "```json",
        json.dumps(config, indent=2),
        "```",
        "",
        "## First Positive Rows",
        "",
    ]
    lines.append(markdown_table(first_sorted) if first_sorted else "No first-positive rows found.")
    lines.extend([
        "",
        "## Nearest Miss / Best Rows",
        "",
        markdown_table(nearest_sorted[:40]),
        "",
        "## Mode Notes",
        "",
        "- `free_boundary_oracle` charges arity plus raw first-hit Lotus payload width; it is the unpaid-boundary lower bound.",
        "- `exact_v1_j3d1` uses `record_cost_for_payload_width(arity, payload_width)` and arities 1..5 only.",
        "- `extended_j3d1_fixed_arity` keeps exact J3D1 seed witnesses but uses a fixed extended arity alphabet for `K > 5`.",
        "- `global_fixed_seed_width` uses one fixed first-2^D seed field per layer.",
        "- `width_classes*` modes use a small public global width set plus a per-record class id.",
        "- `arith_arity_width_lotus_payload` front-codes selected `(arity,width)` bins and then stores local Lotus payload bits.",
        "- `whole_cover_local_payload_stream` front-codes selected `(arity,width)` bins and uses first-2^w local payloads.",
        "",
        "## Next Target",
        "",
    ])
    paid_mode_names = {
        "exact_v1_j3d1",
        "extended_j3d1_fixed_arity",
        "global_fixed_seed_width",
        "width_classes4_log",
        "width_classes8_log",
        "width_classes4_uniform",
        "arith_arity_width_lotus_payload",
        "whole_cover_local_payload_stream",
    }
    positive_custom = [
        row for row in first_sorted
        if row.mode in paid_mode_names
    ]
    paid_nearest = [row for row in nearest_sorted if row.mode in paid_mode_names]
    if positive_custom:
        best = max(positive_custom, key=lambda row: row.gain_per_atom)
        lines.append(
            f"The best paid custom first-positive row is `{best.mode}` at "
            f"`B={best.block_bits}, K={best.max_arity}, D={best.frontier}`, "
            f"with gain `{best.gain_per_atom:.4f}` bits/input atom."
        )
    elif paid_nearest:
        best = paid_nearest[0]
        lines.append(
            f"No paid custom first-positive row crossed in this run. The nearest target is "
            f"`{best.mode}` at `B={best.block_bits}, K={best.max_arity}, D={best.frontier}`, "
            f"gain `{best.gain_per_atom:.4f}` bits/input atom and missing "
            f"`{best.missing_bits_per_record:.3f}` bits/record."
        )
    else:
        lines.append("No evaluated row produced a cover.")
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    modes = [mode.name for mode in make_modes()]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--atoms", type=int, default=128)
    parser.add_argument("--trials", type=int, default=24)
    parser.add_argument("--coverage", type=float, default=0.95)
    parser.add_argument("--seed", type=int, default=20260615)
    parser.add_argument("--max-frontiers", type=int, default=64)
    parser.add_argument("--block-bits", type=int, nargs="+", default=list(B_GRID))
    parser.add_argument("--max-arity", type=int, nargs="+", default=list(K_GRID))
    parser.add_argument("--modes", nargs="+", default=modes, choices=modes)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--md-out", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data = run(args)
    if args.json_out:
        args.json_out.write_text(json.dumps(data, indent=2), encoding="utf-8")
    report = render_report(data)
    if args.md_out:
        args.md_out.write_text(report, encoding="utf-8")
    else:
        print(report)


if __name__ == "__main__":
    main()
