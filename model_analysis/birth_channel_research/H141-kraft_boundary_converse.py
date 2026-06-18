#!/usr/bin/env python3
"""H141 - Kraft boundary converse for seed-derived width tricks.

H140 showed that the local-width oracle has enormous option pressure, but J3D1
spends much of it making the seed witness self-delimiting. H141 asks whether a
seed-derived boundary rule could recover the oracle:

* use seed residues/trailing patterns/parity/sign lanes to imply width;
* use a canonical minimum seed and let the decoder infer the boundary;
* make the seed witness itself a self-delimiting language.

All of those are prefix or uniquely decodable witness languages. Kraft says the
seed-code inventory satisfies sum 2^-L <= 1. For a slack/delta budget, the
best possible supply is therefore obtained by spending the entire Kraft mass at
one public length L. That is just a fixed-width witness lane. This kernel turns
that converse into the same central-atom and fallback ledgers used by H140.
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model_analysis.proof_kernel.costs import LITERAL_MARKER_BITS  # noqa: E402
from total_cover_lotus_crossover import fixed_arity_bits  # noqa: E402


@dataclass(frozen=True)
class BoundaryRow:
    block_bits: int
    max_arity: int
    delta_bits_per_record: int
    best_arity: int
    arity_bits: int
    lambda_options: float
    option_probability: float
    h2_bits_per_atom: float
    h2_bits_per_rewritten_atom: float
    partial_h2_delta_per_atom: float
    fixed_slot_literal_delta_per_atom: float
    seed_width: int


def h2(p: float) -> float:
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -(p * math.log2(p) + (1.0 - p) * math.log2(1.0 - p))


def lambda_for_arity(block_bits: int, max_arity: int, arity: int, delta_bits: int) -> tuple[float, int]:
    """Expected options for a central atom from one arity under a Kraft code.

    Record cost is constrained to:

        arity_bits + seed_width = arity * block_bits + delta_bits

    If a prefix witness language spends all Kraft mass at that seed_width, it
    has 2^seed_width witnesses. Each hits a target with probability
    2^(-arity*block_bits), and a central atom is contained in arity placements.
    """

    a_bits = fixed_arity_bits(max_arity, arity)
    seed_width = arity * block_bits + delta_bits - a_bits
    if seed_width < 1:
        return 0.0, seed_width
    log2_lambda = math.log2(arity) + seed_width - (arity * block_bits)
    if log2_lambda < -1070.0:
        return 0.0, seed_width
    return 2.0**log2_lambda, seed_width


def best_boundary_row(block_bits: int, max_arity: int, delta_bits: int) -> BoundaryRow:
    best_arity = 0
    best_lambda = 0.0
    best_seed_width = 0
    best_arity_bits = 0
    for arity in range(1, max_arity + 1):
        lam, seed_width = lambda_for_arity(block_bits, max_arity, arity, delta_bits)
        if lam > best_lambda:
            best_lambda = lam
            best_arity = arity
            best_seed_width = seed_width
            best_arity_bits = fixed_arity_bits(max_arity, arity)
    q = 1.0 - math.exp(-best_lambda)
    h = h2(q)
    h_per_rewrite = h / q if q > 0.0 else float("inf")
    # Partial-cover lower bound: selected q fraction pays content-selected H2.
    # The record delta is per selected record, amortized over best_arity atoms.
    partial = h + q * (delta_bits / best_arity) if best_arity else float("inf")
    # Public fixed slots avoid a bitmap but need a literal/type fallback for
    # failed slots. This is generous: one literal marker per K-atom slot.
    fixed_slot = (
        (q * delta_bits + (1.0 - q) * LITERAL_MARKER_BITS) / best_arity
        if best_arity
        else float("inf")
    )
    return BoundaryRow(
        block_bits=block_bits,
        max_arity=max_arity,
        delta_bits_per_record=delta_bits,
        best_arity=best_arity,
        arity_bits=best_arity_bits,
        lambda_options=best_lambda,
        option_probability=q,
        h2_bits_per_atom=h,
        h2_bits_per_rewritten_atom=h_per_rewrite,
        partial_h2_delta_per_atom=partial,
        fixed_slot_literal_delta_per_atom=fixed_slot,
        seed_width=best_seed_width,
    )


def rows() -> list[BoundaryRow]:
    return [
        best_boundary_row(block_bits, max_arity, delta)
        for block_bits in (4, 8, 12, 24)
        for max_arity in (5, 8, 16, 32, 64, 128, 512)
        for delta in (-4, -3, -2, -1, 0, 1, 2, 4)
    ]


def fmt(value: float) -> str:
    if value == float("inf"):
        return "inf"
    if abs(value) >= 1000.0 or (0.0 < abs(value) < 0.001):
        return f"{value:.3e}"
    return f"{value:.6f}"


def print_rows(items: list[BoundaryRow]) -> None:
    print("== Kraft boundary converse ==")
    print("delta is record bits minus raw span bits. Negative delta is per-record saving.")
    print("partial+H2 prices a content-selected ready/carry set; fixed-slot prices public slots with literal fallback.")
    print(
        f"{'B':>2} {'K':>4} {'d':>3} {'best k':>6} {'a bits':>6} {'seed w':>6} "
        f"{'lambda':>9} {'q':>9} {'H2/q':>9} {'partial+H2':>12} {'fixed-slot':>11}"
    )
    for row in items:
        if row.max_arity not in (5, 32, 128, 512) or row.delta_bits_per_record not in (-2, -1, 0, 1, 2):
            continue
        if row.block_bits not in (4, 8):
            continue
        print(
            f"{row.block_bits:2d} {row.max_arity:4d} {row.delta_bits_per_record:3d} "
            f"{row.best_arity:6d} {row.arity_bits:6d} {row.seed_width:6d} "
            f"{fmt(row.lambda_options):>9} {fmt(row.option_probability):>9} "
            f"{fmt(row.h2_bits_per_rewritten_atom):>9} "
            f"{fmt(row.partial_h2_delta_per_atom):>12} "
            f"{fmt(row.fixed_slot_literal_delta_per_atom):>11}"
        )
    print()


def print_thresholds(items: list[BoundaryRow]) -> None:
    print("== best rows by objective ==")
    candidates = [row for row in items if row.best_arity > 0]
    for block_bits, max_arity in ((4, 32), (4, 128), (8, 32), (8, 128)):
        subset = [row for row in candidates if row.block_bits == block_bits and row.max_arity == max_arity]
        best_partial = min(subset, key=lambda row: row.partial_h2_delta_per_atom)
        best_fixed = min(subset, key=lambda row: row.fixed_slot_literal_delta_per_atom)
        first_q90 = next((row for row in subset if row.option_probability >= 0.90), None)
        print(
            f"B{block_bits} K{max_arity}: "
            f"best partial d={best_partial.delta_bits_per_record} "
            f"net={best_partial.partial_h2_delta_per_atom:.6f}; "
            f"best fixed-slot d={best_fixed.delta_bits_per_record} "
            f"net={best_fixed.fixed_slot_literal_delta_per_atom:.6f}; "
            f"first q>=0.90 d={first_q90.delta_bits_per_record if first_q90 else 'none'}"
        )
    print()


def print_reading() -> None:
    print("== reading ==")
    print(
        "A seed-residue or self-delimiting boundary language cannot have the "
        "local-width oracle's full 2^w witnesses at every width. Kraft forces "
        "the width inventory to live under one unit of prefix mass."
    )
    print(
        "The best possible supply at a fixed record delta is therefore a public "
        "fixed seed width at the best arity. For power-of-two K this gives about "
        "lambda=2^delta: flat records produce q=1-e^-1, +2 bit records produce "
        "q~=0.982, and 1-bit saving records produce q~=0.393."
    )
    print(
        "Partial selection then pays H2(q), while public fixed slots avoid H2 "
        "but pay literal/type fallback on failures. In the tested rows neither "
        "path goes negative. The missing mechanism must beat Kraft, derive a "
        "near-total public layout, or supply real non-uniform fertility."
    )


def main() -> None:
    items = rows()
    print_rows(items)
    print_thresholds(items)
    print_reading()


if __name__ == "__main__":
    main()
