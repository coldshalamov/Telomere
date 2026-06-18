#!/usr/bin/env python3
"""H143 - optimistic near-total public-board bound.

H128 showed that a public board with rare exceptions needs roughly
99.8-99.94% public opening under the measured margins. H140 showed that exact
J3D1 slack supply is far below that for +1/+2 slack, and H141/H142 closed the
"hide the width in the seed" loophole.

H143 asks a stronger, deliberately generous question:

    If each input atom could choose the cheapest successful public interval
    among every interval containing it, and we charged only the near-total
    exception ledger, can the public-board branch cross?

This ignores non-overlapping cover consistency and the choice metadata for
which interval won, so it is an upper bound on what a real stateless board can
do. Missing here is strong evidence against the public near-total branch under
the same witness law.
"""

from __future__ import annotations

import math
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model_analysis.proof_kernel.costs import (  # noqa: E402
    MAX_PAYLOAD_WIDTH_BITS,
    j3d1_cost_for_payload_width,
    payload_width_count_exact,
)
from total_cover_lotus_crossover import fixed_arity_bits  # noqa: E402


@dataclass(frozen=True)
class CandidateLaw:
    block_bits: int
    max_arity: int
    slack_bits: int
    frontier_bits: int
    lambda_total: float
    open_probability: float
    exception_fraction: float
    expected_record_delta_per_atom: float
    expected_delta_if_open: float
    best_mark: float


@dataclass(frozen=True)
class NetRow:
    block_bits: int
    max_arity: int
    slack_bits: int
    passes: int
    fallback_bits_per_exception_atom: float
    open_probability: float
    exception_fraction: float
    expected_record_delta_per_atom: float
    exception_ledger_bits: float
    total_delta_per_atom: float
    expected_delta_if_open: float
    best_mark: float


@dataclass(frozen=True)
class ThresholdRow:
    margin_name: str
    margin_bits: float
    passes: int
    required_open_probability: float
    best_open_probability: float
    best_slack_bits: int
    open_gap: float
    best_total_delta: float


def h2(p: float) -> float:
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -(p * math.log2(p) + (1.0 - p) * math.log2(1.0 - p))


def exception_ledger(eps: float, passes: int, fallback_bits_per_exception_atom: float) -> float:
    return h2(eps) + eps * math.log2(max(1, passes - 1)) + eps * fallback_bits_per_exception_atom


def solve_eps(margin: float, passes: int) -> float:
    lo = 0.0
    hi = 0.5
    for _ in range(96):
        mid = (lo + hi) / 2.0
        if h2(mid) + mid * math.log2(max(1, passes - 1)) <= margin:
            lo = mid
        else:
            hi = mid
    return lo


def add_exp2(value: float) -> float:
    if value < -1070.0:
        return 0.0
    if value > 700.0:
        return float("inf")
    return 2.0**value


def candidate_law(block_bits: int, max_arity: int, slack_bits: int) -> CandidateLaw:
    frontier_bits = min(block_bits * max_arity, MAX_PAYLOAD_WIDTH_BITS)
    by_mark: dict[float, float] = defaultdict(float)
    for arity in range(1, max_arity + 1):
        raw_bits = arity * block_bits
        arity_bits = fixed_arity_bits(max_arity, arity)
        for payload_width in range(1, frontier_bits + 1):
            cost = arity_bits + j3d1_cost_for_payload_width(payload_width)
            delta = cost - raw_bits
            if delta > slack_bits:
                continue
            # A central atom is contained in arity placements. The expected
            # number of matching seeds in this width bucket is count / 2^raw.
            log_lambda = (
                math.log2(arity)
                + math.log2(payload_width_count_exact(payload_width))
                - raw_bits
            )
            mark = delta / arity
            by_mark[mark] += add_exp2(log_lambda)

    total_lambda = sum(by_mark.values())
    eps = math.exp(-total_lambda) if total_lambda < 745.0 else 0.0
    q = 1.0 - eps
    cumulative = 0.0
    expected = 0.0
    best_mark = float("inf")
    for mark in sorted(by_mark):
        lam = by_mark[mark]
        if lam <= 0.0:
            continue
        best_mark = min(best_mark, mark)
        prior_none = math.exp(-cumulative) if cumulative < 745.0 else 0.0
        this_wins = prior_none * (1.0 - math.exp(-lam) if lam < 745.0 else 1.0)
        expected += mark * this_wins
        cumulative += lam
    expected_if_open = expected / q if q > 0.0 else float("inf")
    return CandidateLaw(
        block_bits=block_bits,
        max_arity=max_arity,
        slack_bits=slack_bits,
        frontier_bits=frontier_bits,
        lambda_total=total_lambda,
        open_probability=q,
        exception_fraction=eps,
        expected_record_delta_per_atom=expected,
        expected_delta_if_open=expected_if_open,
        best_mark=best_mark,
    )


def net_row(
    law: CandidateLaw,
    passes: int,
    fallback_bits_per_exception_atom: float,
) -> NetRow:
    ex = exception_ledger(
        law.exception_fraction,
        passes,
        fallback_bits_per_exception_atom,
    )
    return NetRow(
        block_bits=law.block_bits,
        max_arity=law.max_arity,
        slack_bits=law.slack_bits,
        passes=passes,
        fallback_bits_per_exception_atom=fallback_bits_per_exception_atom,
        open_probability=law.open_probability,
        exception_fraction=law.exception_fraction,
        expected_record_delta_per_atom=law.expected_record_delta_per_atom,
        exception_ledger_bits=ex,
        total_delta_per_atom=law.expected_record_delta_per_atom + ex,
        expected_delta_if_open=law.expected_delta_if_open,
        best_mark=law.best_mark,
    )


def laws() -> list[CandidateLaw]:
    return [
        candidate_law(block_bits, max_arity, slack)
        for block_bits in (4, 8)
        for max_arity in (5, 32, 128, 512)
        for slack in (-4, -2, -1, 0, 1, 2, 4, 8)
    ]


def net_rows(items: list[CandidateLaw]) -> list[NetRow]:
    return [
        net_row(law, passes, fallback)
        for law in items
        for passes in (2, 64, 4096)
        for fallback in (0.0, 3.0)
    ]


def threshold_rows(items: list[CandidateLaw]) -> list[ThresholdRow]:
    margins = [
        ("H124 exact apparent", 0.014587),
        ("H124 lane apparent", 0.023438),
        ("optimistic 0.10", 0.100000),
    ]
    rows: list[ThresholdRow] = []
    for margin_name, margin in margins:
        for passes in (2, 64, 4096):
            required_open = 1.0 - solve_eps(margin, passes)
            eligible = [law for law in items if law.slack_bits <= 2]
            best_law = max(eligible, key=lambda law: law.open_probability)
            best_net = min(
                (
                    net_row(law, passes, 0.0)
                    for law in eligible
                ),
                key=lambda row: row.total_delta_per_atom,
            )
            rows.append(
                ThresholdRow(
                    margin_name=margin_name,
                    margin_bits=margin,
                    passes=passes,
                    required_open_probability=required_open,
                    best_open_probability=best_law.open_probability,
                    best_slack_bits=best_law.slack_bits,
                    open_gap=required_open - best_law.open_probability,
                    best_total_delta=best_net.total_delta_per_atom,
                )
            )
    return rows


def fmt(value: float) -> str:
    if value == float("inf"):
        return "inf"
    if abs(value) >= 1000.0 or (0.0 < abs(value) < 0.0001):
        return f"{value:.3e}"
    return f"{value:.9f}"


def print_laws(items: list[CandidateLaw]) -> None:
    print("== optimistic public-board opening law ==")
    print("q is per-atom chance that at least one public candidate interval succeeds.")
    print(
        f"{'B':>2} {'K':>4} {'s':>3} {'lambda':>10} {'q':>11} "
        f"{'eps':>11} {'E rec d':>10} {'E d|open':>10} {'best d':>9}"
    )
    for law in items:
        if law.max_arity not in (32, 128, 512) or law.slack_bits not in (-1, 0, 2, 4, 8):
            continue
        if law.block_bits != 4:
            continue
        print(
            f"{law.block_bits:2d} {law.max_arity:4d} {law.slack_bits:3d} "
            f"{fmt(law.lambda_total):>10} {fmt(law.open_probability):>11} "
            f"{fmt(law.exception_fraction):>11} "
            f"{fmt(law.expected_record_delta_per_atom):>10} "
            f"{fmt(law.expected_delta_if_open):>10} {fmt(law.best_mark):>9}"
        )
    print()


def print_best_net(rows: list[NetRow]) -> None:
    print("== best optimistic net rows ==")
    print("total delta includes cheapest-success record delta plus exception ledger. Negative would be shrink.")
    print(
        f"{'B':>2} {'K':>4} {'s':>3} {'P':>5} {'F':>3} {'q':>11} "
        f"{'rec d':>10} {'except':>10} {'total':>10} {'d|open':>10}"
    )
    for passes in (2, 64, 4096):
        subset = [row for row in rows if row.passes == passes and row.fallback_bits_per_exception_atom == 0.0]
        for row in sorted(subset, key=lambda item: item.total_delta_per_atom)[:6]:
            print(
                f"{row.block_bits:2d} {row.max_arity:4d} {row.slack_bits:3d} "
                f"{row.passes:5d} {row.fallback_bits_per_exception_atom:3.0f} "
                f"{fmt(row.open_probability):>11} "
                f"{fmt(row.expected_record_delta_per_atom):>10} "
                f"{fmt(row.exception_ledger_bits):>10} "
                f"{fmt(row.total_delta_per_atom):>10} "
                f"{fmt(row.expected_delta_if_open):>10}"
            )
    print()


def print_thresholds(rows: list[ThresholdRow]) -> None:
    print("== near-total threshold check for slack <= 2 ==")
    print(
        f"{'margin':<21} {'P':>5} {'required q':>12} {'best q':>11} "
        f"{'gap':>11} {'best net':>10}"
    )
    for row in rows:
        print(
            f"{row.margin_name:<21} {row.passes:5d} "
            f"{fmt(row.required_open_probability):>12} "
            f"{fmt(row.best_open_probability):>11} "
            f"{fmt(row.open_gap):>11} {fmt(row.best_total_delta):>10}"
        )
    print()


def print_reading() -> None:
    print("== reading ==")
    print(
        "This is a generous upper bound: it lets each atom use the cheapest "
        "successful interval among all public placements and charges no cover "
        "conflict or winner selector. Real boards can only be worse."
    )
    print(
        "Compressive or near-flat slack does not reach the H128 near-total "
        "opening box. Large slack can reach q close to one, but the winning "
        "records are bloating and the expected record delta stays positive."
    )
    print(
        "Therefore public near-total geometry is still valuable for decoding, "
        "but it is not a content-blind compression source under exact J3D1 "
        "unless a separate witness/fertility mechanism makes the success set "
        "both near-total and net-negative."
    )


def main() -> None:
    items = laws()
    rows = net_rows(items)
    print_laws(items)
    print_best_net(rows)
    print_thresholds(threshold_rows(items))
    print_reading()


if __name__ == "__main__":
    main()
