#!/usr/bin/env python3
"""H46 - high-arity option-statistic bound.

This kernel focuses on the user's "15 options at K=5, many more at higher K"
point. The local option dividend is real:

    M(K) = 1 + 2 + ... + K = K(K+1)/2

An atom in the interior belongs to M possible intervals. If those were
independent first-hit races, the best rank improves by about log2 M bits.

The scientific question is not whether that dividend exists. It does. The
question is how much of it a paid, parseable, stateless witness language can
capture without moving the bill into arity/width/cover normalization.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


E_LOG2_EXP = -0.5772156649015329 / math.log(2.0)


def option_count(max_arity: int) -> int:
    return max_arity * (max_arity + 1) // 2


def ideal_best_rank_shift(max_arity: int) -> float:
    return math.log2(option_count(max_arity))


def expected_log2_min_rank(target_bits: int, choices: float) -> float:
    """Asymptotic E[log2 R_min] for M independent geometric races."""

    return target_bits + E_LOG2_EXP - math.log2(choices)


@dataclass(frozen=True)
class FrontierTarget:
    name: str
    gain_per_atom: float
    records_per_atom: float
    missing_bits_per_record: float
    avg_arity: float
    avg_rank_bits: float | None = None
    delta_bits_per_record: float | None = None

    @property
    def needed_choice_multiplier(self) -> float:
        return 2.0 ** self.missing_bits_per_record


TARGETS = (
    FrontierTarget(
        "H7 raw first-hit delta",
        gain_per_atom=-0.011929,
        records_per_atom=0.008789,
        missing_bits_per_record=1.357,
        avg_arity=113.78,
        avg_rank_bits=453.542,
        delta_bits_per_record=2.407,
    ),
    FrontierTarget(
        "H9 fixed slack 0",
        gain_per_atom=-0.012314,
        records_per_atom=0.009765,
        missing_bits_per_record=1.261,
        avg_arity=102.40,
    ),
    FrontierTarget(
        "H12 perfect-credit UB",
        gain_per_atom=-0.008196,
        records_per_atom=0.010987,
        missing_bits_per_record=0.746,
        avg_arity=91.02,
    ),
)


def print_local_option_table() -> None:
    print("== local interval-option dividend ==")
    print("This is the optimistic best-of-options shift before non-overlap and")
    print("before paying a public code for the selected cover distribution.")
    print(f"{'K':>5} {'M=K(K+1)/2':>13} {'log2 M':>10}")
    for max_arity in (5, 8, 16, 24, 32, 48, 64, 96, 128, 192, 256):
        m = option_count(max_arity)
        print(f"{max_arity:5d} {m:13d} {math.log2(m):10.3f}")
    print()


def print_current_gap_table() -> None:
    print("== current paid frontier: effective choices needed ==")
    print("If a better public selected-extreme law could save g bits/record,")
    print("it is equivalent to capturing an extra factor 2^g of effective choices.")
    print(
        f"{'target':<28} {'miss/rec':>9} {'2^miss':>9} "
        f"{'rec/atom':>10} {'avg arity':>10}"
    )
    for target in TARGETS:
        print(
            f"{target.name:<28} {target.missing_bits_per_record:9.3f} "
            f"{target.needed_choice_multiplier:9.3f} "
            f"{target.records_per_atom:10.6f} {target.avg_arity:10.2f}"
        )
    print()


def print_asymptotic_rank_table() -> None:
    print("== ideal min-rank shifts for representative spans ==")
    print("E[log2 R_min] ~= L - log2(M) - 0.833 for M independent races.")
    print(f"{'B':>4} {'arity':>6} {'K':>5} {'L=aB':>8} {'log2M':>8} {'E log2 Rmin':>14}")
    for block_bits, arity in ((4, 5), (4, 64), (4, 128), (8, 5), (8, 64), (8, 128), (24, 5)):
        for max_arity in (arity, 128) if arity < 128 else (arity,):
            choices = option_count(max_arity)
            target_bits = block_bits * arity
            print(
                f"{block_bits:4d} {arity:6d} {max_arity:5d} "
                f"{target_bits:8d} {math.log2(choices):8.3f} "
                f"{expected_log2_min_rank(target_bits, choices):14.3f}"
            )
    print()


def print_capture_budget_table() -> None:
    print("== how much of the ideal dividend is already implied? ==")
    print("For H7 B=4,K=128, avg arity is 113.78, so raw span bits are about")
    print("455.12. H7's avg rank bits are 453.542, meaning only a small part of")
    print("the 13-bit local ideal appears as rank-width reduction; the rest is")
    print("spent by non-overlap, arity language, frontier conditioning, and delta.")
    h7 = TARGETS[0]
    raw_span = h7.avg_arity * 4.0
    ideal_shift = ideal_best_rank_shift(128)
    observed_rank_shift = raw_span - (h7.avg_rank_bits or 0.0)
    missing = h7.missing_bits_per_record
    print(f"{'raw span bits':<28} {raw_span:10.3f}")
    print(f"{'ideal local log2 M':<28} {ideal_shift:10.3f}")
    print(f"{'observed rank shift':<28} {observed_rank_shift:10.3f}")
    print(f"{'remaining paid miss':<28} {missing:10.3f}")
    print(f"{'extra effective choices needed':<28} {2.0 ** missing:10.3f}")
    print()


def print_conservation_note() -> None:
    print("== conservation check ==")
    print("A public selected-extreme law may improve a selected-cover witness, but")
    print("if it creates a complete stateless code for uniform n-bit layers, then")
    print("the induced normalized layer distribution Q obeys:")
    print()
    print("  E_uniform[-log2 Q(X)] = n + KL(U || Q) >= n")
    print()
    print("So a positive uniform all-data average cannot come from better modeling")
    print("alone. A useful next law must either be a source/fertility prior with")
    print("negative uniform controls, or it will be balanced by normalization,")
    print("support loss, arity/width residuals, or a selector/referee channel.")


def main() -> None:
    print_local_option_table()
    print_current_gap_table()
    print_asymptotic_rank_table()
    print_capture_budget_table()
    print_conservation_note()


if __name__ == "__main__":
    main()
