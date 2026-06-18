#!/usr/bin/env python3
"""H128 - near-total public-board exception threshold.

Bohr's order-insensitive audit narrows the live stateless shape to public
coordinate boards where almost every slot opens. If every public slot opens,
the decoder does not need a raw/record bitmap or birth-pass ledger. If a small
exception set remains, the exception ledger must fit inside the measured margin.

This kernel solves the finite threshold:

    H2(eps) + eps * log2(P - 1) <= margin_bits_per_atom_pass

for several margins. The expression is the per-atom cost of saying "this atom
is an exception" plus, for exceptions, which older pass/class it belongs to.
For P=1 the pass term is zero. For P=2 it is also zero.

The output is a target, not a codec: a candidate public board must empirically
maintain exception fractions below these epsilons while still getting the stated
margin from actual Telomere records.
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass


@dataclass(frozen=True)
class ThresholdRow:
    margin_name: str
    margin_bits: float
    passes: int
    eps_max: float
    coverage_min: float
    exceptions_per_million: float
    ledger_bits: float
    bits_per_exception: float


def h2(p: float) -> float:
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -(p * math.log2(p) + (1.0 - p) * math.log2(1.0 - p))


def ledger_bits(eps: float, passes: int) -> float:
    return h2(eps) + eps * math.log2(max(1, passes - 1))


def solve_eps(margin: float, passes: int) -> float:
    lo = 0.0
    hi = 0.5
    while ledger_bits(hi, passes) < margin and hi < 1.0:
        hi = min(1.0, hi * 1.5)
    for _ in range(96):
        mid = (lo + hi) / 2.0
        if ledger_bits(mid, passes) <= margin:
            lo = mid
        else:
            hi = mid
    return lo


def default_margins() -> list[tuple[str, float]]:
    return [
        ("H124 exact_arity raw-atom apparent", 0.014587),
        ("H124 lane_exact raw-atom apparent", 0.023438),
        ("optimistic 0.05 bits/atom/pass", 0.050000),
        ("optimistic 0.10 bits/atom/pass", 0.100000),
    ]


def fmt(value: float) -> str:
    if math.isinf(value):
        return "inf"
    return f"{value:.9f}"


def print_rows(rows: list[ThresholdRow]) -> None:
    print(
        "margin,margin_bits,passes,eps_max,coverage_min,"
        "exceptions_per_million,ledger_bits,bits_per_exception"
    )
    for row in rows:
        print(
            f"{row.margin_name},{row.margin_bits:.6f},{row.passes},"
            f"{fmt(row.eps_max)},{fmt(row.coverage_min)},"
            f"{fmt(row.exceptions_per_million)},"
            f"{fmt(row.ledger_bits)},"
            f"{fmt(row.bits_per_exception)}"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--passes", type=int, action="append", default=[])
    parser.add_argument("--margin", action="append", default=[])
    args = parser.parse_args()

    margins = default_margins()
    for item in args.margin:
        if ":" in item:
            name, raw_value = item.split(":", 1)
        else:
            name, raw_value = f"custom {item}", item
        margins.append((name, float(raw_value)))

    passes_values = args.passes or [2, 4, 16, 64, 256, 4096]
    rows: list[ThresholdRow] = []
    for name, margin in margins:
        for passes in passes_values:
            eps = solve_eps(margin, passes)
            bits = ledger_bits(eps, passes)
            rows.append(
                ThresholdRow(
                    margin_name=name,
                    margin_bits=margin,
                    passes=passes,
                    eps_max=eps,
                    coverage_min=1.0 - eps,
                    exceptions_per_million=eps * 1_000_000.0,
                    ledger_bits=bits,
                    bits_per_exception=bits / eps if eps > 0 else float("inf"),
                )
            )
    print_rows(rows)


if __name__ == "__main__":
    main()
