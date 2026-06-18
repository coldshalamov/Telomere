#!/usr/bin/env python3
"""H66 - all-block high-arity option dividend vs cover entropy.

This kernel addresses the user's all-block intuition directly:

    with max arity K, each interior atom belongs to 1+2+...+K intervals;
    choosing the best bundle should improve the next pass.

The local option dividend is real, but a total-cover encoder must also identify
which non-overlapping cover was chosen. For a line of N atoms and parts
1..K, the number of public cover shapes is:

    C(N,K) = sum_{a=1..K} C(N-a,K)

with entropy rate log2(lambda_K), where lambda_K solves:

    sum_{a=1..K} lambda_K^(-a) = 1

As K grows, this cover-shape entropy approaches 1 bit/atom. That is the
selector bill hidden inside "pick the best bundle." Normalized collective-Q
can encode the whole cover as a public prior, but under the uniform law the
layer code still pays KL conservation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


def option_count(max_arity: int) -> int:
    return max_arity * (max_arity + 1) // 2


def cover_count(max_atoms: int, max_arity: int) -> int:
    dp = [0] * (max_atoms + 1)
    dp[0] = 1
    for n in range(1, max_atoms + 1):
        dp[n] = sum(dp[n - a] for a in range(1, min(max_arity, n) + 1))
    return dp[max_atoms]


def lambda_k(max_arity: int) -> float:
    lo, hi = 1.0, 2.0
    for _ in range(100):
        mid = (lo + hi) / 2.0
        value = sum(mid ** (-a) for a in range(1, max_arity + 1))
        if value > 1.0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


@dataclass(frozen=True)
class CoverEntropyRow:
    max_arity: int
    local_options: int
    local_log2_options: float
    entropy_rate_bits_per_atom: float
    cover_bits_n128: float
    cover_count_n32_log2: float


@dataclass(frozen=True)
class GapRow:
    name: str
    missing_bits_per_record: float
    records_per_atom: float
    avg_arity: float

    @property
    def missing_bits_per_atom(self) -> float:
        return self.missing_bits_per_record * self.records_per_atom


GAPS = [
    GapRow("H12 perfect-credit UB", 0.746, 0.010987, 91.02),
    GapRow("H7 raw first-hit", 1.357, 0.008789, 113.78),
    GapRow("H9 fixed slack 0", 1.261, 0.009765, 102.40),
    GapRow("H58 bucket Q layer", 0.229195, 1.0 / 384.0, 384.0),
    GapRow("H59 raw/Q T1 layer", 0.053411, 1.0 / 384.0, 384.0),
]


def cover_rows() -> list[CoverEntropyRow]:
    rows: list[CoverEntropyRow] = []
    for max_arity in (2, 3, 4, 5, 8, 16, 32, 64, 128, 256, 512):
        lam = lambda_k(max_arity)
        rate = math.log2(lam)
        rows.append(
            CoverEntropyRow(
                max_arity=max_arity,
                local_options=option_count(max_arity),
                local_log2_options=math.log2(option_count(max_arity)),
                entropy_rate_bits_per_atom=rate,
                cover_bits_n128=128.0 * rate,
                cover_count_n32_log2=math.log2(cover_count(32, max_arity)),
            )
        )
    return rows


def print_cover_entropy() -> None:
    print("== cover-shape entropy vs local interval options ==")
    print(
        f"{'K':>5} {'local M':>10} {'log2 M':>9} "
        f"{'entropy/atom':>13} {'N128 cover bits':>16} {'log2 C(32,K)':>14}"
    )
    for row in cover_rows():
        print(
            f"{row.max_arity:5d} {row.local_options:10d} "
            f"{row.local_log2_options:9.3f} {row.entropy_rate_bits_per_atom:13.6f} "
            f"{row.cover_bits_n128:16.3f} {row.cover_count_n32_log2:14.3f}"
        )
    print()


def print_gap_comparison() -> None:
    print("== current gaps vs hidden cover-selector scale ==")
    print("The paid misses are tiny per atom, but the unpriced cover-choice budget")
    print("available from high K is O(1) bit/atom. It cannot be counted as free.")
    print(
        f"{'target':<24} {'miss/rec':>9} {'rec/atom':>10} "
        f"{'miss/atom':>10} {'avg arity':>10} {'K~arity hK':>11}"
    )
    for gap in GAPS:
        k = max(2, int(round(gap.avg_arity)))
        h_k = math.log2(lambda_k(k))
        print(
            f"{gap.name:<24} {gap.missing_bits_per_record:9.3f} "
            f"{gap.records_per_atom:10.6f} {gap.missing_bits_per_atom:10.6f} "
            f"{gap.avg_arity:10.2f} {h_k:11.6f}"
        )
    print()


def print_asymptotic_reading() -> None:
    print("== asymptotic reading ==")
    print("1. Local option count grows as K^2/2, so the ideal local best-rank")
    print("   dividend grows like 2 log2 K - 1.")
    print("2. Legal non-overlapping cover shapes grow only exponentially in N,")
    print("   with entropy rate h_K < 1 bit/atom and h_K -> 1.")
    print("3. If the encoder chooses a cover after seeing content, those h_K bits")
    print("   per atom are a selector unless the cover is encoded by a normalized")
    print("   public Q. Under uniform data, normalized Q pays KL conservation:")
    print()
    print("     E_U[-log2 Q(X)] = n + KL(U || Q) >= n")
    print()
    print("4. Therefore high arity can move constants and create near-boundary")
    print("   rows, but the all-data uniform crossing still needs either a public")
    print("   invariant not represented by cover choice, or a source/fertility law.")


def main() -> None:
    print_cover_entropy()
    print_gap_comparison()
    print_asymptotic_reading()


if __name__ == "__main__":
    main()
