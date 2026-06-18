#!/usr/bin/env python3
"""H140 - slack-refresh supply bound.

The user's partial-refresh argument has two real multipliers:

* allowing +s bloating bits gives more acceptable seeds;
* a block belongs to 1 + 2 + ... + K possible bundle placements.

H140 prices those multipliers before selection. For a central input atom, it
computes the expected number of slack-legal matching intervals that contain the
atom under the uniform hash law, then converts it to a Poisson "has at least
one option" estimate.

Two witness ledgers are compared:

* local_width_oracle: arity bits plus a raw local payload width. This is the
  optimistic model that H110 found can cross, but the decoder is not told where
  the payload ends.
* j3d1_parseable: arity bits plus exact J3D1 payload-width syntax. This is
  parseable, but spends the width/boundary dividend.

This is a counting model only. It does not claim an optimal non-overlapping
cover; it asks whether there is enough replacement supply to keep freshness
alive after paying the binary ready/carry lower bound H2(q).
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model_analysis.proof_kernel.costs import (  # noqa: E402
    MAX_PAYLOAD_WIDTH_BITS,
    j3d1_cost_for_payload_width,
    payload_width_count_le,
)
from total_cover_lotus_crossover import fixed_arity_bits  # noqa: E402


@dataclass(frozen=True)
class SupplyRow:
    mode: str
    block_bits: int
    max_arity: int
    frontier_bits: int
    slack_bits: int
    expected_options: float
    option_probability: float
    ready_bits_per_atom: float
    ready_bits_per_rewritten_atom: float
    best_arity: int
    best_interval_probability: float
    best_payload_width: int


@dataclass(frozen=True)
class CrossingRow:
    mode: str
    block_bits: int
    slack_bits: int
    target_q: float
    first_k: int | None
    option_probability: float
    ready_bits_per_rewritten_atom: float


def h2(p: float) -> float:
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -(p * math.log2(p) + (1.0 - p) * math.log2(1.0 - p))


def log2_count_le_lotus_payload_width(payload_width: int) -> float:
    if payload_width < 1:
        return float("-inf")
    if payload_width <= 256:
        return math.log2(payload_width_count_le(payload_width))
    # payload_width_count_le(w) = 2^(w+1)-3.
    return payload_width + 1.0


def pstar_j3d1(record_budget_bits: int, arity_bits: int) -> int:
    budget = record_budget_bits - arity_bits
    if budget < 0:
        return 0
    lo = 0
    hi = MAX_PAYLOAD_WIDTH_BITS
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if j3d1_cost_for_payload_width(mid) <= budget:
            lo = mid
        else:
            hi = mid - 1
    return lo


def interval_probability(
    mode: str,
    block_bits: int,
    max_arity: int,
    arity: int,
    frontier_bits: int,
    slack_bits: int,
) -> tuple[float, int]:
    target_bits = arity * block_bits
    arity_bits = fixed_arity_bits(max_arity, arity)
    record_budget = target_bits + slack_bits
    if mode == "local_width_oracle":
        payload_width = max(0, record_budget - arity_bits)
        log2_seed_count = min(float(payload_width), float(frontier_bits))
    elif mode == "j3d1_parseable":
        payload_width = pstar_j3d1(record_budget, arity_bits)
        log2_seed_count = min(
            log2_count_le_lotus_payload_width(payload_width),
            float(frontier_bits),
        )
    else:
        raise ValueError(mode)

    if payload_width <= 0:
        return 0.0, 0
    log2_p = log2_seed_count - target_bits
    if log2_p >= 0.0:
        return 1.0, payload_width
    if log2_p < -1070.0:
        return 0.0, payload_width
    return 2.0**log2_p, payload_width


def supply_row(mode: str, block_bits: int, max_arity: int, slack_bits: int) -> SupplyRow:
    frontier_bits = max_arity * block_bits
    expected_options = 0.0
    best_p = 0.0
    best_arity = 0
    best_payload_width = 0
    for arity in range(1, max_arity + 1):
        p, payload_width = interval_probability(
            mode,
            block_bits,
            max_arity,
            arity,
            frontier_bits,
            slack_bits,
        )
        # A central atom is contained in arity distinct intervals of this size.
        expected_options += arity * p
        if p > best_p:
            best_p = p
            best_arity = arity
            best_payload_width = payload_width
    option_probability = 1.0 - math.exp(-expected_options)
    ready_bits = h2(option_probability)
    ready_per_rewritten = ready_bits / option_probability if option_probability > 0.0 else float("inf")
    return SupplyRow(
        mode=mode,
        block_bits=block_bits,
        max_arity=max_arity,
        frontier_bits=frontier_bits,
        slack_bits=slack_bits,
        expected_options=expected_options,
        option_probability=option_probability,
        ready_bits_per_atom=ready_bits,
        ready_bits_per_rewritten_atom=ready_per_rewritten,
        best_arity=best_arity,
        best_interval_probability=best_p,
        best_payload_width=best_payload_width,
    )


def crossing_rows() -> list[CrossingRow]:
    rows: list[CrossingRow] = []
    k_grid = [5, 8, 16, 24, 32, 48, 64, 96, 128, 192, 256, 384, 512, 768, 1024, 1536, 2048, 3072, 4096]
    for mode in ("local_width_oracle", "j3d1_parseable"):
        for block_bits in (4, 8):
            for slack_bits in (0, 1, 2, 4, 8):
                for target_q in (0.10, 0.50, 0.90):
                    winner: SupplyRow | None = None
                    for max_arity in k_grid:
                        row = supply_row(mode, block_bits, max_arity, slack_bits)
                        if row.option_probability >= target_q:
                            winner = row
                            break
                    rows.append(
                        CrossingRow(
                            mode=mode,
                            block_bits=block_bits,
                            slack_bits=slack_bits,
                            target_q=target_q,
                            first_k=winner.max_arity if winner is not None else None,
                            option_probability=winner.option_probability if winner is not None else 0.0,
                            ready_bits_per_rewritten_atom=(
                                winner.ready_bits_per_rewritten_atom if winner is not None else float("inf")
                            ),
                        )
                    )
    return rows


def fmt(value: float) -> str:
    if value == float("inf"):
        return "inf"
    if abs(value) >= 1000.0 or (0.0 < abs(value) < 0.001):
        return f"{value:.3e}"
    return f"{value:.6f}"


def print_supply_rows(rows: list[SupplyRow]) -> None:
    print("== slack-refresh central-atom supply ==")
    print("D is fixed to K*B. q is the probability a central atom has at least one slack-legal replacement option.")
    print(
        f"{'mode':<20} {'B':>2} {'K':>4} {'s':>2} {'lambda':>10} "
        f"{'q':>10} {'H2(q)':>9} {'H2/q':>9} {'best k':>7} {'best p':>10} {'pwidth':>6}"
    )
    for row in rows:
        print(
            f"{row.mode:<20} {row.block_bits:2d} {row.max_arity:4d} {row.slack_bits:2d} "
            f"{fmt(row.expected_options):>10} {fmt(row.option_probability):>10} "
            f"{fmt(row.ready_bits_per_atom):>9} {fmt(row.ready_bits_per_rewritten_atom):>9} "
            f"{row.best_arity:7d} {fmt(row.best_interval_probability):>10} {row.best_payload_width:6d}"
        )
    print()


def print_crossings(rows: list[CrossingRow]) -> None:
    print("== first K where option supply reaches q target ==")
    print("None means not reached by K=4096 with D=K*B.")
    print(
        f"{'mode':<20} {'B':>2} {'s':>2} {'q target':>8} "
        f"{'first K':>8} {'q at K':>10} {'H2/q':>9}"
    )
    for row in rows:
        first_k = str(row.first_k) if row.first_k is not None else "None"
        print(
            f"{row.mode:<20} {row.block_bits:2d} {row.slack_bits:2d} {row.target_q:8.2f} "
            f"{first_k:>8} {fmt(row.option_probability):>10} {fmt(row.ready_bits_per_rewritten_atom):>9}"
        )
    print()


def print_reading() -> None:
    print("== reading ==")
    print(
        "The O(K^2) interval multiplier is real in the local-width oracle. "
        "That is why H110's underpriced rows can cross: the decoder is silently "
        "getting a payload boundary/width decision."
    )
    print(
        "Exact J3D1 spends that boundary. Its width tier removes the quadratic "
        "advantage in these finite grids, so +1/+2 slack supplies far fewer "
        "fresh options than the oracle suggests."
    )
    print(
        "Even if q options exist, partial refresh owes at least H2(q) bits per "
        "input atom for the ready/carry set unless the layout is public or "
        "decoder-derived. At q=0.10 that bill is about 4.69 bits per rewritten "
        "atom; at q=0.50 it is 2 bits per rewritten atom."
    )


def main() -> None:
    rows = [
        supply_row(mode, block_bits, max_arity, slack_bits)
        for mode in ("local_width_oracle", "j3d1_parseable")
        for block_bits in (4, 8)
        for max_arity in (32, 128, 512)
        for slack_bits in (0, 1, 2, 4, 8)
    ]
    print_supply_rows(rows)
    print_crossings(crossing_rows())
    print_reading()


if __name__ == "__main__":
    main()
