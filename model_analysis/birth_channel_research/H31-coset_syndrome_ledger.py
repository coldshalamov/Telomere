#!/usr/bin/env python3
"""
H31 - coset / syndrome / ECC-style witness ledger.

Idea:

    target x = seed_codeword(s) XOR residual e
    record = [seed][syndrome_or_error_residual]

This can look like Telomere plus a repair channel. The question is whether the
repair channel can be smaller than the bytes it replaces, or become a recursive
fertility source, without relying on ordinary structure.

This is a counting ledger, not a compression search.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import comb, log2


def log2_choose(n: int, k: int) -> float:
    if k < 0 or k > n:
        return float("-inf")
    k = min(k, n - k)
    if k == 0:
        return 0.0
    return sum(log2(n - i) - log2(i + 1) for i in range(k))


def log2_hamming_ball(n: int, radius: int) -> float:
    return log2(sum(comb(n, i) for i in range(radius + 1)))


@dataclass(frozen=True)
class FullSyndromeRow:
    n_bits: int
    seed_bits: int
    full_syndrome_bits: int
    total_bits: int
    net_vs_raw: int


def full_syndrome_rows() -> list[FullSyndromeRow]:
    rows: list[FullSyndromeRow] = []
    for n_bits in (32, 64, 128, 1024):
        for seed_bits in (4, 8, 16, 32):
            if seed_bits <= n_bits:
                syndrome_bits = n_bits - seed_bits
                total = seed_bits + syndrome_bits
                rows.append(
                    FullSyndromeRow(
                        n_bits=n_bits,
                        seed_bits=seed_bits,
                        full_syndrome_bits=syndrome_bits,
                        total_bits=total,
                        net_vs_raw=n_bits - total,
                    )
                )
    return rows


@dataclass(frozen=True)
class LowWeightRow:
    n_bits: int
    seed_bits: int
    radius: int
    coverage_log2_fraction: float
    error_map_bits: float
    total_bits: float
    net_if_reachable: float
    expected_trials_log2: float


def low_weight_rows() -> list[LowWeightRow]:
    rows: list[LowWeightRow] = []
    for n_bits in (64, 128, 1024):
        for seed_bits in (8, 16, 32):
            if seed_bits > n_bits:
                continue
            for radius in (1, 2, 4, 8):
                if radius > n_bits:
                    continue
                ball_bits = log2_hamming_ball(n_bits, radius)
                coverage_log2_fraction = seed_bits + ball_bits - n_bits
                total_bits = seed_bits + ball_bits
                rows.append(
                    LowWeightRow(
                        n_bits=n_bits,
                        seed_bits=seed_bits,
                        radius=radius,
                        coverage_log2_fraction=coverage_log2_fraction,
                        error_map_bits=ball_bits,
                        total_bits=total_bits,
                        net_if_reachable=n_bits - total_bits,
                        expected_trials_log2=max(0.0, -coverage_log2_fraction),
                    )
                )
    return rows


@dataclass(frozen=True)
class RefereeRow:
    candidates_log2: float
    checksum_bits: int
    false_accept_log2: float
    deterministic: bool


def referee_rows() -> list[RefereeRow]:
    rows: list[RefereeRow] = []
    for candidates_log2 in (8, 16, 32, 64, 128, 1024):
        for checksum_bits in (32, 64, 128, 256):
            false_accept_log2 = candidates_log2 - checksum_bits
            rows.append(
                RefereeRow(
                    candidates_log2=candidates_log2,
                    checksum_bits=checksum_bits,
                    false_accept_log2=false_accept_log2,
                    deterministic=false_accept_log2 < -32,
                )
            )
    return rows


@dataclass(frozen=True)
class FertilityResidualRow:
    residual_bits: float
    gamma: float
    future_value: float
    net_after_residual: float
    crosses: bool


def fertility_residual_rows() -> list[FertilityResidualRow]:
    rows: list[FertilityResidualRow] = []
    for residual_bits in (1, 2, 4, 8, 16, 64):
        for gamma in (0.0, 0.5, 1.0, 1.2):
            future = gamma * residual_bits
            net = future - residual_bits
            rows.append(
                FertilityResidualRow(
                    residual_bits=float(residual_bits),
                    gamma=gamma,
                    future_value=future,
                    net_after_residual=net,
                    crosses=net > 0.0,
                )
            )
    return rows


def print_full_syndrome_table() -> None:
    print("== full syndrome/coset residual ==")
    print(
        "A k-bit seed/codeword plus an (n-k)-bit syndrome is exactly n bits "
        "before record overhead."
    )
    print(f"{'n':>6} {'seed k':>8} {'syndrome':>10} {'total':>8} {'net':>6}")
    for row in full_syndrome_rows():
        if row.n_bits in (64, 1024) and row.seed_bits in (8, 16, 32):
            print(
                f"{row.n_bits:6d} {row.seed_bits:8d} "
                f"{row.full_syndrome_bits:10d} {row.total_bits:8d} "
                f"{row.net_vs_raw:6d}"
            )
    print()


def print_low_weight_table() -> None:
    print("== low-weight error residual ==")
    print(
        "Low-weight residuals are short only on a small subset. The missing "
        "coverage appears as search/trials or as a fallback/raw escape."
    )
    print(
        f"{'n':>6} {'seed k':>8} {'r':>4} {'log2 cover frac':>16} "
        f"{'err bits':>10} {'net if hit':>11} {'log2 trials':>12}"
    )
    for row in low_weight_rows():
        if (row.n_bits, row.seed_bits, row.radius) in {
            (64, 16, 2),
            (64, 32, 4),
            (128, 32, 4),
            (1024, 32, 8),
        }:
            print(
                f"{row.n_bits:6d} {row.seed_bits:8d} {row.radius:4d} "
                f"{row.coverage_log2_fraction:16.3f} "
                f"{row.error_map_bits:10.3f} {row.net_if_reachable:11.3f} "
                f"{row.expected_trials_log2:12.3f}"
            )
    print()


def print_referee_table() -> None:
    print("== omitted syndrome with checksum/referee ==")
    print(
        "If the syndrome is omitted, the decoder has a candidate set. A checksum "
        "must scale with log2(candidate_count)."
    )
    print(
        f"{'log2 candidates':>16} {'checksum':>9} {'log2 false accepts':>19} {'ok?':>5}"
    )
    for row in referee_rows():
        if row.candidates_log2 in (64, 128, 1024) and row.checksum_bits in (64, 128, 256):
            print(
                f"{row.candidates_log2:16.1f} {row.checksum_bits:9d} "
                f"{row.false_accept_log2:19.1f} {str(row.deterministic):>5}"
            )
    print()


def print_fertility_table() -> None:
    print("== residual as future fertility channel ==")
    print(
        "A residual can become useful only if it saves more future bits than it "
        "costs now. gamma<=1 is conserved."
    )
    print(
        f"{'residual bits':>13} {'gamma':>7} {'future':>10} {'net':>10} {'crosses':>8}"
    )
    for row in fertility_residual_rows():
        if row.residual_bits in (2, 8, 64):
            print(
                f"{row.residual_bits:13.1f} {row.gamma:7.3f} "
                f"{row.future_value:10.3f} {row.net_after_residual:10.3f} "
                f"{('yes' if row.crosses else 'no'):>8}"
            )
    print()


def main() -> None:
    print_full_syndrome_table()
    print_low_weight_table()
    print_referee_table()
    print_fertility_table()
    print("CONCLUSION:")
    print(
        "Coset/syndrome witnesses are stateless and decode cleanly, but full "
        "syndromes return to raw length, low-weight residuals cover only a tiny "
        "subset, and omitted syndromes require a scaling referee. The only "
        "surviving use is H26/H28-shaped: residual bits must have future "
        "fertility gamma>1, with uniform controls staying negative."
    )


if __name__ == "__main__":
    main()
