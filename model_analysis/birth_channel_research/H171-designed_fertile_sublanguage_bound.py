#!/usr/bin/env python3
"""H171 - designed fertile sublanguage Kraft bound.

H169/H170 asked whether existing visible classes are fertile. The next escape
would be to design the record language so a public class F is fertile by
construction.

This file prices that idea directly. If F has public fraction f and its members
get a future paid-saving boost a bits/record, that boost consumes at least

    f * 2^a

Kraft mass. Therefore restriction mode cannot beat its own class tax:

    tax(F) = -log2(f)
    a < tax(F)  for a valid code with any complement left
    a - tax(F) <= 0

But H168 needs positive margin after that tax:

    a - tax(F) > r

where r is the remaining current miss in bits/selected-record. The F class
alone would then require Kraft mass:

    f * 2^(r + tax(F)) = 2^r,

before encoding any other outputs. That is the exact overfull bill.

Population mode can still be a live target only if the stream is already
concentrated in F by a real public recurrence. This kernel prints how rare F
must be for pure-F population mode to have enough boost under Kraft, and how
large c* is for finite boosts.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Target:
    label: str
    remaining_gap_bits_per_record: float
    conservative_gap_bits_per_record: float


@dataclass(frozen=True)
class RestrictionBoundRow:
    target: str
    fraction: float
    tax: float
    need_boost_post: float
    need_boost_conservative: float
    max_valid_boost: float
    best_restriction_net: float
    best_post_margin: float
    overfull_bits_post: float
    overfull_bits_conservative: float


@dataclass(frozen=True)
class KraftBalancedRow:
    target: str
    fraction: float
    alpha: float
    tax: float
    boost_f: float
    complement_penalty: float
    uniform_mean_saving: float
    pure_f_margin: float
    c_star: float
    min_p_ff_at_background: float


TARGETS = [
    Target("H162 K5 D80 exact post-H165", 8.112500, 8.361777),
    Target("H163 K5 D256 exact post-H165", 9.457453, 9.688172),
    Target("H163 K5 D512 exact post-H165", 10.392213, 10.626718),
    Target("H163 K16 D512 escape5 post-H165", 10.926442, 11.143925),
]

FRACTIONS = [0.50, 0.25, 0.10, 0.03, 0.01, 0.003, 0.001]
ALPHAS = [0.25, 0.50, 0.75, 0.90, 0.99]


def fmt(value: float) -> str:
    if math.isinf(value):
        return "inf" if value > 0 else "-inf"
    if math.isnan(value):
        return "nan"
    if abs(value) >= 10_000.0 or (0.0 < abs(value) < 0.0001):
        return f"{value:.3e}"
    return f"{value:.6f}"


def tax(fraction: float) -> float:
    return -math.log2(fraction)


def complement_penalty_for_kraft(fraction: float, boost: float) -> float:
    """Return b such that f*2^boost + (1-f)*2^b == 1."""
    remaining = 1.0 - fraction * (2.0**boost)
    if remaining <= 0.0:
        return float("-inf")
    return math.log2(remaining / (1.0 - fraction))


def min_p_ff(c_star: float, p_of: float) -> float:
    if c_star <= 0.0:
        return 0.0
    if c_star > 1.0:
        return math.inf
    return max(0.0, min(1.0, (c_star - (1.0 - c_star) * p_of) / c_star))


def restriction_rows() -> list[RestrictionBoundRow]:
    rows: list[RestrictionBoundRow] = []
    for target in TARGETS:
        for fraction in FRACTIONS:
            t = tax(fraction)
            need_post = target.remaining_gap_bits_per_record + t
            need_conservative = target.conservative_gap_bits_per_record + t
            rows.append(
                RestrictionBoundRow(
                    target=target.label,
                    fraction=fraction,
                    tax=t,
                    need_boost_post=need_post,
                    need_boost_conservative=need_conservative,
                    max_valid_boost=t,
                    best_restriction_net=0.0,
                    best_post_margin=-target.remaining_gap_bits_per_record,
                    overfull_bits_post=target.remaining_gap_bits_per_record,
                    overfull_bits_conservative=target.conservative_gap_bits_per_record,
                )
            )
    return rows


def c_star_for_population(gap: float, boost_f: float, complement_penalty: float) -> float:
    if boost_f <= complement_penalty:
        return math.inf
    return (gap - complement_penalty) / (boost_f - complement_penalty)


def balanced_rows() -> list[KraftBalancedRow]:
    rows: list[KraftBalancedRow] = []
    for target in (TARGETS[0], TARGETS[-1]):
        for fraction in FRACTIONS:
            t = tax(fraction)
            for alpha in ALPHAS:
                boost = alpha * t
                penalty = complement_penalty_for_kraft(fraction, boost)
                uniform_mean = fraction * boost + (1.0 - fraction) * penalty
                c_star = c_star_for_population(
                    target.remaining_gap_bits_per_record,
                    boost,
                    penalty,
                )
                rows.append(
                    KraftBalancedRow(
                        target=target.label,
                        fraction=fraction,
                        alpha=alpha,
                        tax=t,
                        boost_f=boost,
                        complement_penalty=penalty,
                        uniform_mean_saving=uniform_mean,
                        pure_f_margin=boost - target.remaining_gap_bits_per_record,
                        c_star=c_star,
                        min_p_ff_at_background=min_p_ff(c_star, fraction),
                    )
                )
    return rows


def print_restriction_table() -> None:
    print("== designed fertile sublanguage restriction bound ==")
    print(
        "A public class F with fraction f and future boost a consumes Kraft mass f*2^a. "
        "To beat restriction tax plus gap r, F alone is overfull by exactly r bits."
    )
    print(
        f"{'target':<38} {'f':>7} {'tax':>9} {'need a':>10} "
        f"{'max a':>9} {'best net':>9} {'post margin':>12} {'overfull':>10}"
    )
    for row in restriction_rows():
        if row.target != TARGETS[0].label and row.fraction not in (0.10,):
            continue
        print(
            f"{row.target:<38} {fmt(row.fraction):>7} {fmt(row.tax):>9} "
            f"{fmt(row.need_boost_post):>10} {fmt(row.max_valid_boost):>9} "
            f"{fmt(row.best_restriction_net):>9} {fmt(row.best_post_margin):>12} "
            f"{fmt(row.overfull_bits_post):>10}"
        )
    print()


def print_population_table() -> None:
    print("== Kraft-balanced population recurrence ledger ==")
    print(
        "Rows set boost a = alpha*tax(F) and choose the complement penalty b so "
        "f*2^a + (1-f)*2^b = 1. Uniform mean saving stays <= 0; only real "
        "population concentration in F can help."
    )
    print(
        f"{'target':<38} {'f':>7} {'alpha':>6} {'a':>9} {'b':>9} "
        f"{'E_U':>9} {'pureF-r':>9} {'c*':>9} {'min pFF':>9}"
    )
    for row in balanced_rows():
        if row.fraction not in (0.10, 0.01, 0.003, 0.001):
            continue
        if row.alpha not in (0.50, 0.90, 0.99):
            continue
        print(
            f"{row.target:<38} {fmt(row.fraction):>7} {fmt(row.alpha):>6} "
            f"{fmt(row.boost_f):>9} {fmt(row.complement_penalty):>9} "
            f"{fmt(row.uniform_mean_saving):>9} {fmt(row.pure_f_margin):>9} "
            f"{fmt(row.c_star):>9} {fmt(row.min_p_ff_at_background):>9}"
        )
    print()


def print_pure_f_thresholds() -> None:
    print("== pure-F population threshold under Kraft ==")
    print(
        "If the stream were already entirely inside F and the designed boost could "
        "approach tax(F), pure-F positivity needs tax(F) > r, i.e. f < 2^-r."
    )
    print(f"{'target':<38} {'r':>9} {'max f for pure-F':>18} {'tax at f':>10}")
    for target in TARGETS:
        max_fraction = 2.0 ** (-target.remaining_gap_bits_per_record)
        print(
            f"{target.label:<38} {fmt(target.remaining_gap_bits_per_record):>9} "
            f"{fmt(max_fraction):>18} {fmt(tax(max_fraction)):>10}"
        )
    print()


def print_catalyst_bits() -> None:
    print("== catalyst-bit corollary ==")
    print(
        "Forcing c public catalyst bits is just f=2^-c. A valid designed grammar "
        "can give at most c future bits to that class, so restriction net is at "
        "most zero before the current gap is paid."
    )
    print(f"{'c bits':>6} {'f':>10} {'max boost':>10} {'best net':>10} {'margin r=8.1125':>16}")
    for c_bits in (1, 2, 4, 8, 12, 16):
        fraction = 2.0 ** (-c_bits)
        print(
            f"{c_bits:6d} {fmt(fraction):>10} {fmt(float(c_bits)):>10} "
            f"{fmt(0.0):>10} {fmt(-TARGETS[0].remaining_gap_bits_per_record):>16}"
        )
    print()


def print_reading() -> None:
    print("== reading ==")
    print(
        "A designed public fertile sublanguage is not free fuel under the uniform "
        "hash law. Any boost assigned to F spends the same exponential budget as "
        "ordinary prefix-code/Kraft mass. Restricting witnesses to F can at best "
        "break even with the class tax, so it cannot pay the positive H168 gap."
    )
    print(
        "The only remaining use for such a language is population mode: a real "
        "decoder-visible recurrence must drive c_t far above the background f, "
        "and startup bloat must be repaid. That is a different claim from "
        "restricting the encoder's witness supply."
    )


def main() -> None:
    print_restriction_table()
    print_population_table()
    print_pure_f_thresholds()
    print_catalyst_bits()
    print_reading()


if __name__ == "__main__":
    main()
