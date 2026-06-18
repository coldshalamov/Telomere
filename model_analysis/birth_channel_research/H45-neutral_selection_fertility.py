#!/usr/bin/env python3
"""H45 - neutral selection / recursive fertility response surface.

This is the genetics-shaped "missing piece" lane:

    many same-cost seeds decode to the same current span
    choose the seed whose descendants are easiest to compress next

The current layer remains stateless: the decoder reads the chosen seed witness
and gets the same current bytes. The question is whether selecting among M
neutral witnesses gives more than one future saved bit per neutral bit.

Under the uniform/content-blind law, future savings have a coding tail:

    Pr[V >= s] <= 2^-s

so max-of-M selection can convert neutral choice into future value at about
one-for-one, not superlinearly. H18 already showed one-for-one credit is still
short. H45 maps that boundary and shows where source-shaped heavier tails would
cross.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


def expected_max_from_survival(m: float, survival) -> float:
    """E[max(V_1..V_m)] for nonnegative integer V via survival summation."""

    total = 0.0
    for s in range(1, 512):
        p = min(1.0, max(0.0, survival(s)))
        if p <= 0.0:
            break
        term = 1.0 - ((1.0 - p) ** m)
        total += term
        if term < 1e-14 and s > 64:
            break
    return total


def uniform_tail(s: int) -> float:
    return 2.0 ** (-s)


def source_tail(multiplier: float):
    return lambda s: min(1.0, multiplier * (2.0 ** (-s)))


def bernoulli_max(m: float, probability: float, value_bits: float) -> float:
    return value_bits * (1.0 - ((1.0 - probability) ** m))


@dataclass(frozen=True)
class ExtremeRow:
    neutral_bits: float
    choices: float
    e_single: float
    e_best: float
    incremental: float
    gamma_incremental: float
    gamma_absolute: float


def extreme_rows(multiplier: float = 1.0) -> list[ExtremeRow]:
    rows: list[ExtremeRow] = []
    tail = uniform_tail if multiplier == 1.0 else source_tail(multiplier)
    e_single = expected_max_from_survival(1.0, tail)
    for neutral_bits in (0.5, 1.0, 2.0, 3.819, 4.0, 8.0, 12.0, 16.0):
        choices = 2.0 ** neutral_bits
        e_best = expected_max_from_survival(choices, tail)
        incremental = e_best - e_single
        rows.append(
            ExtremeRow(
                neutral_bits=neutral_bits,
                choices=choices,
                e_single=e_single,
                e_best=e_best,
                incremental=incremental,
                gamma_incremental=incremental / neutral_bits,
                gamma_absolute=e_best / neutral_bits,
            )
        )
    return rows


@dataclass(frozen=True)
class JackpotRow:
    value_bits: int
    neutral_bits: float
    probability: float
    e_single: float
    e_best: float
    incremental: float
    gamma_incremental: float
    law: str


def jackpot_rows() -> list[JackpotRow]:
    rows: list[JackpotRow] = []
    for value_bits in (4, 8, 12, 16):
        uniform_p = 2.0 ** (-value_bits)
        for neutral_bits in (value_bits / 2.0, float(value_bits), value_bits * 1.5):
            choices = 2.0 ** neutral_bits
            for law, probability in (
                ("uniform-tail", uniform_p),
                ("source-x4", min(1.0, 4.0 * uniform_p)),
                ("source-x16", min(1.0, 16.0 * uniform_p)),
            ):
                e_single = value_bits * probability
                e_best = bernoulli_max(choices, probability, value_bits)
                incremental = e_best - e_single
                rows.append(
                    JackpotRow(
                        value_bits=value_bits,
                        neutral_bits=neutral_bits,
                        probability=probability,
                        e_single=e_single,
                        e_best=e_best,
                        incremental=incremental,
                        gamma_incremental=incremental / neutral_bits if neutral_bits else 0.0,
                        law=law,
                    )
                )
    return rows


@dataclass(frozen=True)
class H18Target:
    slack: int
    missing_bits_per_record: float
    neutral_bits_per_record: float
    gamma_needed: float


H18_TARGETS = (
    H18Target(-8, 4.565, 3.819, 1.195),
    H18Target(-6, 4.171, 3.162, 1.319),
    H18Target(-4, 3.593, 2.574, 1.396),
    H18Target(-2, 2.393, 1.306, 1.832),
    H18Target(0, 2.316, 0.507, 4.568),
)


def print_uniform_extreme_table() -> None:
    print("== uniform-tail neutral selection ==")
    print("Future savings obey Pr[V>=s]=2^-s. Selection among M=2^b neutral")
    print("choices gives an extreme-value gain that approaches one-for-one.")
    print(
        f"{'neutral b':>10} {'M':>12} {'E[V]':>8} {'E[max]':>10} "
        f"{'increment':>10} {'gamma inc':>10} {'gamma abs':>10}"
    )
    for row in extreme_rows(1.0):
        print(
            f"{row.neutral_bits:10.3f} {row.choices:12.1f} "
            f"{row.e_single:8.3f} {row.e_best:10.3f} "
            f"{row.incremental:10.3f} {row.gamma_incremental:10.3f} "
            f"{row.gamma_absolute:10.3f}"
        )
    print()


def print_source_tail_table() -> None:
    print("== heavier-than-uniform source tails ==")
    print("A multiplier on Pr[V>=s] is a source prior / entropy deficit. A pure")
    print("multiplicative geometric tail adds baseline source value; it does not by")
    print("itself make the selection increment superlinear.")
    print(
        f"{'tail x':>7} {'neutral b':>10} {'E[V]':>8} {'E[max]':>10} "
        f"{'increment':>10} {'gamma inc':>10} {'gamma abs':>10}"
    )
    for multiplier in (2.0, 4.0, 16.0):
        for row in extreme_rows(multiplier):
            if row.neutral_bits in (3.819, 8.0, 16.0):
                print(
                    f"{multiplier:7.1f} {row.neutral_bits:10.3f} "
                    f"{row.e_single:8.3f} {row.e_best:10.3f} "
                    f"{row.incremental:10.3f} {row.gamma_incremental:10.3f} "
                    f"{row.gamma_absolute:10.3f}"
                )
    print()


def print_jackpot_table() -> None:
    print("== Bernoulli jackpot check ==")
    print("Uniform jackpot uses p=2^-w for a w-bit future saving. Source rows")
    print("multiply that probability and must be treated as a premise change.")
    print(
        f"{'law':>12} {'w':>4} {'neutral b':>10} {'p':>11} "
        f"{'E[max]':>10} {'increment':>10} {'gamma inc':>10}"
    )
    for row in jackpot_rows():
        if row.neutral_bits in (float(row.value_bits), row.value_bits / 2.0):
            print(
                f"{row.law:>12} {row.value_bits:4d} {row.neutral_bits:10.3f} "
                f"{row.probability:11.6f} {row.e_best:10.3f} "
                f"{row.incremental:10.3f} {row.gamma_incremental:10.3f}"
            )
    print()


def print_h18_target_table() -> None:
    print("== H18 neutral-fertility target vs uniform selection ==")
    print("H18 already asks how much future value per neutral bit is needed.")
    print("Uniform-tail selection increments are below those targets. Crossing needs")
    print("a measured source/developmental lift, not just more neutral sampling.")
    print(f"{'slack':>6} {'neutral':>9} {'needed gamma':>13} {'uniform gamma':>14} {'status':>10}")
    # Approximate the matching uniform-tail gamma by nearest neutral row.
    rows_by_b = {round(row.neutral_bits, 3): row for row in extreme_rows(1.0)}
    for target in H18_TARGETS:
        row = min(extreme_rows(1.0), key=lambda candidate: abs(candidate.neutral_bits - target.neutral_bits_per_record))
        status = "miss" if row.gamma_incremental < target.gamma_needed else "cross"
        print(
            f"{target.slack:6d} {target.neutral_bits_per_record:9.3f} "
            f"{target.gamma_needed:13.3f} {row.gamma_incremental:14.3f} "
            f"{status:>10}"
        )
    _ = rows_by_b
    print()


def print_verdict() -> None:
    print("== verdict ==")
    print("Neutral seed selection is the right genetics-like shape and is stateless")
    print("when all choices have the same current decode and same witness length.")
    print("Under the uniform saving tail, max-of-M selection does not give the")
    print("needed gamma > 1.195; it trends toward one-for-one from below and H12/H18")
    print("already show one-for-one is still short. Source-shaped rows can add")
    print("absolute future value, but that is a public source/fertility premise, not")
    print("a uniform neutral-selection amplifier.")
    print("So the next constructive target is not more neutral selection by itself;")
    print("it is a fixed developmental source where the heavier tail is measured")
    print("and uniform controls stay negative.")


def main() -> None:
    print_uniform_extreme_table()
    print_source_tail_table()
    print_jackpot_table()
    print_h18_target_table()
    print_verdict()


if __name__ == "__main__":
    main()
