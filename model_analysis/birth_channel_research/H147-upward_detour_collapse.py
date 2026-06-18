#!/usr/bin/env python3
"""H147 - upward detour collapse.

The user is right that the shortest final description of a file need not be
found by greedily shrinking at every intermediate pass. A seed can unfold to a
larger visible layer and only later shrink to the target.

This kernel prices the stateless limit:

* If decode depth/path is fixed and deterministic, the whole upward/downward
  route is just one final description string. Intermediate bloat does not add
  address capacity; only final description count matters.
* If one final description is allowed to try T possible intermediate branches
  and keep the branch that matches the desired file, the branch/stop/referee
  choice is a hidden channel of about log2(T) bits unless it is derivable from
  a public invariant.

No Shannon theorem is needed here. It is just counting final bit strings versus
target bit strings under a fixed decoder.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class CoverageRow:
    target_bits: int
    saved_bits: int
    exact_final_strings: int
    upto_final_strings: int
    exact_coverage_bound: float
    upto_coverage_bound: float


@dataclass(frozen=True)
class BranchRow:
    saved_bits: int
    target_coverage: float
    branches_exact_length: float
    branch_bits_exact_length: float
    net_exact_length: float
    branches_upto_length: float
    branch_bits_upto_length: float
    net_upto_length: float


def deterministic_rows(target_bits: int, saved_values: list[int]) -> list[CoverageRow]:
    rows: list[CoverageRow] = []
    target_count = 1 << target_bits
    for saved in saved_values:
        exact_len = max(0, target_bits - saved)
        exact_strings = 1 << exact_len
        upto_strings = (1 << (exact_len + 1)) - 1
        rows.append(
            CoverageRow(
                target_bits=target_bits,
                saved_bits=saved,
                exact_final_strings=exact_strings,
                upto_final_strings=upto_strings,
                exact_coverage_bound=min(1.0, exact_strings / target_count),
                upto_coverage_bound=min(1.0, upto_strings / target_count),
            )
        )
    return rows


def branch_rows(saved_values: list[int], coverages: list[float]) -> list[BranchRow]:
    rows: list[BranchRow] = []
    for saved in saved_values:
        exact_hit_rate_per_branch = 2.0 ** (-saved)
        upto_hit_rate_per_branch = min(1.0, 2.0 ** (1 - saved))
        for coverage in coverages:
            # Poissonized coupon model: coverage ~= 1 - exp(-T * hit_rate).
            branches_exact = -math.log1p(-coverage) / exact_hit_rate_per_branch
            branches_upto = -math.log1p(-coverage) / upto_hit_rate_per_branch
            bits_exact = math.log2(branches_exact)
            bits_upto = math.log2(branches_upto)
            rows.append(
                BranchRow(
                    saved_bits=saved,
                    target_coverage=coverage,
                    branches_exact_length=branches_exact,
                    branch_bits_exact_length=bits_exact,
                    net_exact_length=saved - bits_exact,
                    branches_upto_length=branches_upto,
                    branch_bits_upto_length=bits_upto,
                    net_upto_length=saved - bits_upto,
                )
            )
    return rows


def fmt(value: float) -> str:
    if abs(value) >= 1000.0 or (0.0 < abs(value) < 0.0001):
        return f"{value:.3e}"
    return f"{value:.6f}"


def print_deterministic(rows: list[CoverageRow]) -> None:
    print("== deterministic upward-detour coverage bound ==")
    print("Intermediate length is absent: a fixed stateless path collapses to final addresses.")
    print(
        f"{'n':>4} {'saved':>6} {'exact strings':>14} {'<= strings':>14} "
        f"{'exact cov':>10} {'<= cov':>10}"
    )
    for row in rows:
        print(
            f"{row.target_bits:4d} {row.saved_bits:6d} "
            f"{row.exact_final_strings:14d} {row.upto_final_strings:14d} "
            f"{fmt(row.exact_coverage_bound):>10} {fmt(row.upto_coverage_bound):>10}"
        )
    print()


def print_branch(rows: list[BranchRow]) -> None:
    print("== if a final seed gets hidden branches ==")
    print("Branch bits are the stop/referee bill unless a public invariant selects the branch.")
    print(
        f"{'saved':>6} {'q':>8} {'T exact':>12} {'bits exact':>11} "
        f"{'net exact':>10} {'T <=':>12} {'bits <=':>10} {'net <=':>9}"
    )
    for row in rows:
        print(
            f"{row.saved_bits:6d} {row.target_coverage:8.4f} "
            f"{fmt(row.branches_exact_length):>12} "
            f"{fmt(row.branch_bits_exact_length):>11} "
            f"{fmt(row.net_exact_length):>10} "
            f"{fmt(row.branches_upto_length):>12} "
            f"{fmt(row.branch_bits_upto_length):>10} "
            f"{fmt(row.net_upto_length):>9}"
        )
    print()


def print_reading() -> None:
    print("== reading ==")
    print(
        "Upward detours are legitimate search paths, but they are not extra "
        "decode capacity by themselves. With fixed depth/path, the final seed "
        "is simply a shorter program for the target."
    )
    print(
        "Letting a seed try many possible unfold depths or branches can raise "
        "coverage, but the selected branch is information. The table shows the "
        "log2(T) bill coming back almost exactly as the desired saving."
    )
    print(
        "So the live non-greedy target is narrower: find a public fertility "
        "invariant that makes the good branch derivable, or a recurrent selected "
        "record language whose visible strings carry the fertility without a "
        "separate stop/referee channel."
    )


def main() -> None:
    saved_values = [1, 2, 4, 8, 16]
    print_deterministic(deterministic_rows(32, saved_values))
    print_branch(branch_rows(saved_values, [0.5, 0.9, 0.999]))
    print_reading()


if __name__ == "__main__":
    main()
