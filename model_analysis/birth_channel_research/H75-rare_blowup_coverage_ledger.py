#!/usr/bin/env python3
"""H75 - rare-blowup coverage ledger.

This attacks the loophole:

    "Maybe shrink roughly all inputs every pass and let rare inputs expand."

Rare blowups can balance average length, but they do not create more short
outputs. Coverage is still limited by the number of descriptions with length
<= n-S.

For prefix/self-delimiting codes with non-winners bounded to length n+E, Kraft
gives the optimistic bound:

    c * 2^S + (1-c) * 2^-E <= 1
    c <= (1 - 2^-E) / (2^S - 2^-E)

As E grows this approaches 2^-S. For EOF/non-prefix one-shot injective maps,
the generous winner bound remains:

    c <= 2^(1-S)

independent of how large the losing outputs are. Blowups can pay the mean, not
the winner inventory.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


def prefix_max_coverage(saving_bits: float, max_loser_expansion_bits: float) -> float:
    if saving_bits <= 0.0:
        return 1.0
    if max_loser_expansion_bits < 0.0:
        return 0.0
    loser_kraft = 2.0 ** (-max_loser_expansion_bits)
    denominator = (2.0**saving_bits) - loser_kraft
    if denominator <= 0.0:
        return 0.0
    return max(0.0, min(1.0, (1.0 - loser_kraft) / denominator))


def eof_max_coverage(saving_bits: float) -> float:
    if saving_bits <= 0.0:
        return 1.0
    return min(1.0, 2.0 ** (1.0 - saving_bits))


def mean_balance_loser_expansion(coverage: float, saving_bits: float) -> float:
    """Expansion per losing input needed to make mean delta nonnegative."""

    if coverage >= 1.0:
        return float("inf")
    return coverage * saving_bits / (1.0 - coverage)


def max_passes_for_coverage(coverage: float, saving_per_pass: float, eof: bool) -> int:
    if saving_per_pass <= 0.0:
        return math.inf  # type: ignore[return-value]
    if eof:
        total = max(0.0, 1.0 - math.log2(coverage))
    else:
        total = max(0.0, -math.log2(coverage))
    return math.floor(total / saving_per_pass)


def max_bad_probability_for_survival(coverage: float, passes: int) -> float:
    if passes <= 0:
        return 0.0
    return 1.0 - (coverage ** (1.0 / passes))


@dataclass(frozen=True)
class CoverageRow:
    saving_bits: int
    max_expansion_bits: int
    prefix_coverage: float
    eof_coverage: float


@dataclass(frozen=True)
class BlowupRow:
    coverage: float
    passes: int
    saving_per_pass_bits: float
    total_saving_bits: float
    loser_expansion_for_mean_bits: float
    prefix_coverage_bound: float
    eof_coverage_bound: float
    max_bad_probability: float


def coverage_rows() -> list[CoverageRow]:
    rows: list[CoverageRow] = []
    for saving in (1, 2, 4, 8, 16, 64):
        for expansion in (0, 1, 4, 16, 64, 1024):
            rows.append(
                CoverageRow(
                    saving_bits=saving,
                    max_expansion_bits=expansion,
                    prefix_coverage=prefix_max_coverage(saving, expansion),
                    eof_coverage=eof_max_coverage(saving),
                )
            )
    return rows


def blowup_rows() -> list[BlowupRow]:
    rows: list[BlowupRow] = []
    for coverage in (0.50, 0.90, 0.99):
        for passes in (1, 4, 16, 64, 256):
            for saving_per_pass in (0.25, 1.0, 2.0):
                total = passes * saving_per_pass
                rows.append(
                    BlowupRow(
                        coverage=coverage,
                        passes=passes,
                        saving_per_pass_bits=saving_per_pass,
                        total_saving_bits=total,
                        loser_expansion_for_mean_bits=mean_balance_loser_expansion(coverage, total),
                        prefix_coverage_bound=prefix_max_coverage(total, 1024),
                        eof_coverage_bound=eof_max_coverage(total),
                        max_bad_probability=max_bad_probability_for_survival(coverage, passes),
                    )
                )
    return rows


def fmt_prob(value: float) -> str:
    if value == 0.0:
        return "0"
    if value >= 0.001:
        return f"{value:.6f}"
    return f"{value:.3e}"


def print_coverage_rows() -> None:
    print("== coverage bound with bounded loser expansion ==")
    print("Prefix rows assume losers may expand by at most E bits.")
    print(f"{'S':>5} {'E':>6} {'prefix max c':>14} {'EOF max c':>12}")
    for row in coverage_rows():
        if row.saving_bits in (1, 4, 16, 64) and row.max_expansion_bits in (0, 4, 64, 1024):
            print(
                f"{row.saving_bits:5d} {row.max_expansion_bits:6d} "
                f"{fmt_prob(row.prefix_coverage):>14} {fmt_prob(row.eof_coverage):>12}"
            )
    print()


def print_blowup_rows() -> None:
    print("== mean-balancing blowup needed for claimed typical shrink ==")
    print("Mean balance does not remove the short-output coverage bound.")
    print(
        f"{'c claim':>7} {'P':>5} {'s/pass':>7} {'S':>8} "
        f"{'loser E mean':>14} {'eps max':>10} {'prefix c max':>13} {'EOF c max':>11}"
    )
    for row in blowup_rows():
        if row.coverage == 0.90 and row.saving_per_pass_bits in (1.0, 2.0):
            print(
                f"{row.coverage:7.2f} {row.passes:5d} "
                f"{row.saving_per_pass_bits:7.2f} {row.total_saving_bits:8.2f} "
                f"{row.loser_expansion_for_mean_bits:14.3f} "
                f"{row.max_bad_probability:10.6f} "
                f"{fmt_prob(row.prefix_coverage_bound):>13} "
                f"{fmt_prob(row.eof_coverage_bound):>11}"
            )
    print()


def print_max_k() -> None:
    print("== max K at target coverage despite rare blowups ==")
    print(f"{'coverage':>9} {'s/pass':>8} {'prefix K':>9} {'EOF K':>7}")
    for coverage in (0.90, 0.99):
        for saving_per_pass in (0.25, 1.0, 2.0):
            print(
                f"{coverage:9.2f} {saving_per_pass:8.2f} "
                f"{max_passes_for_coverage(coverage, saving_per_pass, eof=False):9d} "
                f"{max_passes_for_coverage(coverage, saving_per_pass, eof=True):7d}"
            )
    print()


def print_reading() -> None:
    print("== reading ==")
    print("Rare blowups are not a hidden source of short codewords. They can make")
    print("the average length ledger balance after a typical shrink claim, but the")
    print("winning fraction is still bounded by the short-output inventory.")
    print()
    print("For Telomere's bounded-loss contract, large rare blowups are not allowed")
    print("anyway. With bounded losers, prefix coverage stays near 2^-S; with the")
    print("generous EOF one-shot loophole it stays near 2^(1-S). Neither supports")
    print("maintained positive-rate recursion on roughly all uniform inputs.")


def main() -> None:
    print_coverage_rows()
    print_blowup_rows()
    print_max_k()
    print_reading()


if __name__ == "__main__":
    main()
