#!/usr/bin/env python3
"""H71 - finite-pass coverage frontier for structure-free recursion.

This is the sharp "roughly all data" counting boundary. It ignores Telomere
implementation details on purpose and gives the best possible lossless
stateless map under a uniform source.

For any injective code from n-bit inputs to binary strings, the fraction of
inputs that can finish at least S bits shorter is bounded by:

    prefix / self-delimiting public stream:  2^-S
    EOF one-shot arbitrary strings:         2^(1-S) - 2^-n

The EOF row is the generous bound: it allows any output string shorter than
n-S and assumes the old length is known outside the code. It is not a recursive
Telomere record stream, but it is the strongest finite-pass loophole.

If a recursive scheme claims to save s bits/pass over P passes on coverage c
of uniform inputs, it needs total saving S=P*s on that coverage. The table
therefore gives max finite P before "roughly all data" becomes impossible.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


def prefix_coverage_bound(total_saving_bits: float) -> float:
    if total_saving_bits <= 0.0:
        return 1.0
    return 2.0 ** (-total_saving_bits)


def eof_coverage_bound(total_saving_bits: float) -> float:
    if total_saving_bits <= 0.0:
        return 1.0
    return min(1.0, 2.0 ** (1.0 - total_saving_bits))


def max_total_saving_bits(coverage: float, eof: bool) -> float:
    if not 0.0 < coverage <= 1.0:
        raise ValueError("coverage must be in (0,1]")
    if eof:
        return max(0.0, 1.0 - math.log2(coverage))
    return max(0.0, -math.log2(coverage))


def max_integer_passes(coverage: float, saving_per_pass_bits: int, eof: bool) -> int:
    if saving_per_pass_bits <= 0:
        raise ValueError("saving_per_pass_bits must be positive")
    return math.floor(max_total_saving_bits(coverage, eof) / saving_per_pass_bits)


def required_source_lift(coverage: float, total_saving_bits: float, eof: bool) -> float:
    bound = eof_coverage_bound(total_saving_bits) if eof else prefix_coverage_bound(total_saving_bits)
    if bound <= 0.0:
        return float("inf")
    if coverage <= bound:
        return 1.0
    return coverage / bound


def binary_kl(c: float, p: float) -> float:
    if c <= 0.0:
        return -math.log2(1.0 - p) if p < 1.0 else float("inf")
    if c >= 1.0:
        return -math.log2(p) if p > 0.0 else float("inf")
    if p <= 0.0 or p >= 1.0:
        return float("inf")
    return c * math.log2(c / p) + (1.0 - c) * math.log2((1.0 - c) / (1.0 - p))


def required_kl_deficit(coverage: float, uniform_bound: float) -> float:
    if coverage <= uniform_bound:
        return 0.0
    return binary_kl(coverage, uniform_bound)


@dataclass(frozen=True)
class CoverageRow:
    coverage: float
    prefix_max_total_bits: float
    eof_max_total_bits: float
    prefix_k_1b: int
    eof_k_1b: int
    prefix_k_2b: int
    eof_k_2b: int


@dataclass(frozen=True)
class PassRow:
    coverage: float
    passes: int
    prefix_max_bits_per_pass: float
    eof_max_bits_per_pass: float
    prefix_bound_for_1b_pass: float
    eof_bound_for_1b_pass: float


@dataclass(frozen=True)
class LiftRow:
    coverage: float
    passes: int
    saving_per_pass_bits: float
    total_saving_bits: float
    prefix_uniform_bound: float
    eof_uniform_bound: float
    prefix_lift_needed: float
    eof_lift_needed: float
    prefix_kl_deficit: float
    eof_kl_deficit: float


def coverage_rows() -> list[CoverageRow]:
    rows: list[CoverageRow] = []
    for coverage in (0.999, 0.99, 0.90, 0.75, 0.50, 0.10, 0.01):
        rows.append(
            CoverageRow(
                coverage=coverage,
                prefix_max_total_bits=max_total_saving_bits(coverage, eof=False),
                eof_max_total_bits=max_total_saving_bits(coverage, eof=True),
                prefix_k_1b=max_integer_passes(coverage, 1, eof=False),
                eof_k_1b=max_integer_passes(coverage, 1, eof=True),
                prefix_k_2b=max_integer_passes(coverage, 2, eof=False),
                eof_k_2b=max_integer_passes(coverage, 2, eof=True),
            )
        )
    return rows


def pass_rows() -> list[PassRow]:
    rows: list[PassRow] = []
    for coverage in (0.99, 0.90, 0.50, 0.10):
        for passes in (1, 2, 4, 8, 16, 64, 1024):
            rows.append(
                PassRow(
                    coverage=coverage,
                    passes=passes,
                    prefix_max_bits_per_pass=max_total_saving_bits(coverage, eof=False) / passes,
                    eof_max_bits_per_pass=max_total_saving_bits(coverage, eof=True) / passes,
                    prefix_bound_for_1b_pass=prefix_coverage_bound(passes),
                    eof_bound_for_1b_pass=eof_coverage_bound(passes),
                )
            )
    return rows


def lift_rows() -> list[LiftRow]:
    rows: list[LiftRow] = []
    for coverage in (0.90, 0.99):
        for passes in (4, 16, 64, 256):
            for saving_per_pass in (0.25, 1.0, 2.0):
                total = passes * saving_per_pass
                prefix_bound = prefix_coverage_bound(total)
                eof_bound = eof_coverage_bound(total)
                rows.append(
                    LiftRow(
                        coverage=coverage,
                        passes=passes,
                        saving_per_pass_bits=saving_per_pass,
                        total_saving_bits=total,
                        prefix_uniform_bound=prefix_bound,
                        eof_uniform_bound=eof_bound,
                        prefix_lift_needed=required_source_lift(coverage, total, eof=False),
                        eof_lift_needed=required_source_lift(coverage, total, eof=True),
                        prefix_kl_deficit=required_kl_deficit(coverage, prefix_bound),
                        eof_kl_deficit=required_kl_deficit(coverage, eof_bound),
                    )
                )
    return rows


def fmt_prob(value: float) -> str:
    if value == 0.0:
        return "0"
    if value >= 0.001:
        return f"{value:.6f}"
    return f"{value:.3e}"


def print_coverage_table() -> None:
    print("== max finite positive-saving passes by desired coverage ==")
    print("K columns assume every pass saves at least 1 or 2 full bits.")
    print(
        f"{'coverage':>9} {'prefix Smax':>12} {'EOF Smax':>10} "
        f"{'prefix K@1':>11} {'EOF K@1':>8} {'prefix K@2':>11} {'EOF K@2':>8}"
    )
    for row in coverage_rows():
        print(
            f"{row.coverage:9.3f} {row.prefix_max_total_bits:12.6f} "
            f"{row.eof_max_total_bits:10.6f} {row.prefix_k_1b:11d} "
            f"{row.eof_k_1b:8d} {row.prefix_k_2b:11d} {row.eof_k_2b:8d}"
        )
    print()


def print_pass_table() -> None:
    print("== max average bits/pass at fixed coverage ==")
    print("For arbitrary P, the allowed average saving per pass goes to zero.")
    print(
        f"{'coverage':>9} {'P':>6} {'prefix avg':>11} {'EOF avg':>10} "
        f"{'prefix cov if 1b/pass':>21} {'EOF cov if 1b/pass':>19}"
    )
    for row in pass_rows():
        if row.coverage in (0.90, 0.99) or row.passes in (1, 4, 16, 64):
            print(
                f"{row.coverage:9.3f} {row.passes:6d} "
                f"{row.prefix_max_bits_per_pass:11.6f} {row.eof_max_bits_per_pass:10.6f} "
                f"{fmt_prob(row.prefix_bound_for_1b_pass):>21} "
                f"{fmt_prob(row.eof_bound_for_1b_pass):>19}"
            )
    print()


def print_lift_table() -> None:
    print("== source lift required to make forbidden coverage true ==")
    print("These are not Telomere wins; they are the non-uniformity needed.")
    print(
        f"{'coverage':>9} {'P':>5} {'s/pass':>7} {'S':>8} "
        f"{'prefix lift':>13} {'EOF lift':>13} {'prefix KL':>11} {'EOF KL':>11}"
    )
    for row in lift_rows():
        if row.coverage == 0.90 and row.saving_per_pass_bits in (0.25, 1.0):
            print(
                f"{row.coverage:9.2f} {row.passes:5d} "
                f"{row.saving_per_pass_bits:7.2f} {row.total_saving_bits:8.2f} "
                f"{row.prefix_lift_needed:13.6g} {row.eof_lift_needed:13.6g} "
                f"{row.prefix_kl_deficit:11.6f} {row.eof_kl_deficit:11.6f}"
            )
    print()


def print_reading() -> None:
    print("== reading ==")
    print("For structure-free uniform inputs, the strongest possible finite-pass")
    print("loophole is EOF one-shot coding. It can cover almost all inputs for")
    print("one bit once, because any shorter string is allowed when old length is")
    print("external. But sustained positive saving over P passes needs total")
    print("saving S growing with P, and coverage then falls as 2^(1-S).")
    print()
    print("Therefore the max finite K for 90% coverage and >=1 bit/pass is:")
    print("  prefix/self-delimiting stream: K=0")
    print("  EOF one-shot generous bound:   K=1")
    print()
    print("For >=2 bits/pass at 90% coverage, even the EOF bound gives K=0.")
    print("Any claim above this must identify non-uniform source lift, a public")
    print("invariant outside this count, or a paid side channel.")


def main() -> None:
    print_coverage_table()
    print_pass_table()
    print_lift_table()
    print_reading()


if __name__ == "__main__":
    main()
