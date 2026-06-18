#!/usr/bin/env python3
"""H108 - exact prefix record grammar converse.

H106/H107 used floating kernels. H108 makes the same boundary exact for the
H94/H105 witness modes:

    S_a = sum_{symbols with arity a} 2^-L(symbol)
    Z_0 = 1
    Z_n = sum_a S_a Z_{n-a}

If sum_a S_a > 1, the record grammar is overfull/underpriced. If sum_a S_a <=
1, then Z_n <= 1 and a public grammar cannot provide positive source-free
whole-cover margin.
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model_analysis.proof_kernel.costs import (  # noqa: E402
    j3d1_cost_for_payload_width,
    record_cost_for_payload_width,
)


@dataclass(frozen=True)
class ConverseRow:
    mode: str
    max_arity: int
    depth_bits: int
    symbol_mass: Fraction
    log2_symbol_mass: float
    z_mass: Fraction
    log2_z: float
    valid_kraft: bool
    note: str


def fixed_arity_bits(max_arity: int) -> int:
    if max_arity <= 2:
        return 1
    return math.ceil(math.log2(max_arity))


def lotus_payload_width_from_rank(rank: int) -> int:
    if rank <= 1:
        return 1
    return max(1, (rank + 2).bit_length() - 1)


def pow2_neg(bits: int) -> Fraction:
    return Fraction(1, 1 << bits)


def rank_mass(depth_bits: int) -> Fraction:
    return sum(pow2_neg(lotus_payload_width_from_rank(rank)) for rank in range(1, (1 << depth_bits) + 1))


def arity_mass(max_arity: int) -> Fraction:
    return sum(pow2_neg(fixed_arity_bits(max_arity)) for _ in range(1, max_arity + 1))


def paid_lotus_cost(max_arity: int, arity: int, payload_width: int) -> int:
    if arity <= 5:
        return record_cost_for_payload_width(arity, payload_width)
    return fixed_arity_bits(max_arity) + j3d1_cost_for_payload_width(payload_width)


def arity_symbol_masses(mode: str, max_arity: int, depth_bits: int) -> list[Fraction]:
    ranks = [lotus_payload_width_from_rank(rank) for rank in range(1, (1 << depth_bits) + 1)]
    r_mass = rank_mass(depth_bits)
    a_weight = pow2_neg(fixed_arity_bits(max_arity))
    a_mass = arity_mass(max_arity)
    record_mass = a_mass * r_mass
    masses: list[Fraction] = []
    for arity in range(1, max_arity + 1):
        total = Fraction(0, 1)
        for payload_width in ranks:
            if mode == "h92_lower":
                if arity <= 5:
                    weight = pow2_neg(record_cost_for_payload_width(arity, payload_width))
                else:
                    weight = a_weight * pow2_neg(payload_width)
            elif mode == "custom_rank":
                weight = a_weight * pow2_neg(payload_width) / r_mass
            elif mode == "custom_record":
                weight = a_weight * pow2_neg(payload_width) / record_mass
            elif mode == "paid_lotus":
                weight = pow2_neg(paid_lotus_cost(max_arity, arity, payload_width))
            else:
                raise ValueError(mode)
            total += weight
        masses.append(total)
    return masses


def cover_mass(masses: list[Fraction], atoms: int) -> Fraction:
    dp = [Fraction(0, 1) for _ in range(atoms + 1)]
    dp[0] = Fraction(1, 1)
    for n in range(1, atoms + 1):
        total = Fraction(0, 1)
        for arity, mass in enumerate(masses, start=1):
            if arity <= n:
                total += mass * dp[n - arity]
        dp[n] = total
    return dp[atoms]


def log2_fraction(value: Fraction) -> float:
    if value <= 0:
        return float("-inf")
    return math.log2(value.numerator) - math.log2(value.denominator)


def row(mode: str, max_arity: int, depth_bits: int, atoms: int = 12) -> ConverseRow:
    masses = arity_symbol_masses(mode, max_arity, depth_bits)
    symbol_mass = sum(masses, Fraction(0, 1))
    z_mass = cover_mass(masses, atoms)
    valid = symbol_mass <= 1
    if not valid:
        note = "invalid/underpriced symbol mass"
    elif z_mass == 1:
        note = "complete for this N, zero margin"
    else:
        note = "valid subprobability"
    return ConverseRow(
        mode=mode,
        max_arity=max_arity,
        depth_bits=depth_bits,
        symbol_mass=symbol_mass,
        log2_symbol_mass=log2_fraction(symbol_mass),
        z_mass=z_mass,
        log2_z=log2_fraction(z_mass),
        valid_kraft=valid,
        note=note,
    )


def print_rows(rows: list[ConverseRow]) -> None:
    print("== exact prefix record grammar converse ==")
    print("Exact Fraction arithmetic for H94/H105 modes, N=12,B=1.")
    print(
        f"{'mode':<13} {'K':>3} {'D':>3} {'log2 sym':>10} "
        f"{'log2 Z_N':>10} {'valid':>7} {'note':<32}"
    )
    for item in rows:
        print(
            f"{item.mode:<13} {item.max_arity:3d} {item.depth_bits:3d} "
            f"{item.log2_symbol_mass:10.6f} {item.log2_z:10.6f} "
            f"{str(item.valid_kraft):>7} {item.note:<32}"
        )
    print()


def print_reading(rows: list[ConverseRow]) -> None:
    h92 = next(item for item in rows if item.mode == "h92_lower")
    custom = next(item for item in rows if item.mode == "custom_record")
    print("== reading ==")
    print(
        f"H92 lower crosses only because its exact symbol mass is overfull: "
        f"log2(sum symbols)={h92.log2_symbol_mass:.6f}, so it is not a valid "
        "prefix/uniquely-decodable record grammar."
    )
    print(
        f"The valid custom_record row has exact log2Z={custom.log2_z:.6f}, "
        "matching H105's nearest honest miss. Since its symbol mass is <=1, "
        "no grammar optimization inside this public record family can make "
        "source-free log2Z positive."
    )


def main() -> None:
    rows = [
        row("h92_lower", 8, 12),
        row("custom_rank", 8, 10),
        row("custom_record", 6, 12),
        row("paid_lotus", 12, 12),
    ]
    print_rows(rows)
    print_reading(rows)


if __name__ == "__main__":
    main()
