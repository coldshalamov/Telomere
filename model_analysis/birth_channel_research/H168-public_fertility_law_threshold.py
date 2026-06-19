#!/usr/bin/env python3
"""H168 - public recurrent fertility-law threshold.

H167 closes the immediate selected-stream loophole: emitted witness identity has
no same-budget content lift under the uniform hash law. The remaining strict
target is therefore a public law for the emitted record language itself.

This file separates two ledgers that are easy to conflate:

1. Restriction ledger:
   The encoder only accepts witnesses in a public high-fertility class F of
   uniform fraction f. That can make the output closed in F, but hit supply pays
   -log2(f) bits/record. This is H166's public-class bill.

2. Population ledger:
   The current layer already has class fraction c_t, and F items are more
   compressible/fertile by a bits/record. No witness supply tax is charged here,
   but the source/output population must actually have c_t >= c* = gap/a and
   must maintain it under

       c_{t+1} = c_t p_FF + (1-c_t) p_OF.

If a proposal claims both "closed output class" and "no supply tax", H168 marks
that as the hidden-selector profile: closure came from restricting outputs but
the matching supply loss was not paid.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class GapRow:
    label: str
    gross_gap_bits_per_record: float
    observed_option_bits: float
    support: float

    @property
    def remaining_gap_bits_per_record(self) -> float:
        return self.gross_gap_bits_per_record - self.observed_option_bits


@dataclass(frozen=True)
class RestrictionRow:
    label: str
    gross_gap: float
    option: float
    remaining_gap: float
    fraction: float
    supply_tax: float
    lift_needed_post_h165: float
    lift_needed_conservative: float


@dataclass(frozen=True)
class PopulationRow:
    label: str
    gap: float
    conservative_gap: float
    fraction: float
    lift: float
    c_star: float
    starts_positive: bool
    min_p_ff_at_background: float
    closure_cross_pass: int | None
    closure_cumulative_positive_pass: int | None
    first_margin: float
    asymptotic_margin: float
    result: str


GAPS = [
    GapRow("H162 K5 D80 exact", 8.361777, 0.249277, 0.310),
    GapRow("H163 K5 D256 exact", 9.688172, 0.230719, 0.603),
    GapRow("H163 K5 D512 exact", 10.626718, 0.234505, 0.817),
    GapRow("H163 K16 D512 escape5", 11.143925, 0.217483, 0.833),
]

CLASS_FRACTIONS = [0.50, 0.25, 0.10, 0.03, 0.01]
FUTURE_LIFTS = [8.0, 12.0, 16.0, 32.0, 64.0, 128.0]


def fmt(value: float) -> str:
    if math.isinf(value):
        return "inf"
    if abs(value) >= 1000.0 or (0.0 < abs(value) < 0.0001):
        return f"{value:.3e}"
    return f"{value:.6f}"


def min_p_ff(c_star: float, p_of: float) -> float:
    if c_star <= 0.0:
        return 0.0
    if c_star > 1.0:
        return math.inf
    return max(0.0, min(1.0, (c_star - (1.0 - c_star) * p_of) / c_star))


def pass_count_until_threshold(
    *, c0: float, c_star: float, p_ff: float, p_of: float, max_passes: int = 4096
) -> int | None:
    c = c0
    for pass_index in range(max_passes + 1):
        if c >= c_star:
            return pass_index
        c = c * p_ff + (1.0 - c) * p_of
    return None


def pass_count_until_cumulative_positive(
    *,
    c0: float,
    gap: float,
    lift: float,
    p_ff: float,
    p_of: float,
    max_passes: int = 4096,
) -> int | None:
    c = c0
    cumulative = 0.0
    for pass_index in range(max_passes + 1):
        cumulative += c * lift - gap
        if cumulative > 0.0:
            return pass_index
        c = c * p_ff + (1.0 - c) * p_of
    return None


def restriction_rows() -> list[RestrictionRow]:
    rows: list[RestrictionRow] = []
    for gap in GAPS:
        for fraction in CLASS_FRACTIONS:
            supply_tax = -math.log2(fraction)
            rows.append(
                RestrictionRow(
                    label=gap.label,
                    gross_gap=gap.gross_gap_bits_per_record,
                    option=gap.observed_option_bits,
                    remaining_gap=gap.remaining_gap_bits_per_record,
                    fraction=fraction,
                    supply_tax=supply_tax,
                    lift_needed_post_h165=gap.remaining_gap_bits_per_record + supply_tax,
                    lift_needed_conservative=gap.gross_gap_bits_per_record + supply_tax,
                )
            )
    return rows


def population_row(gap: GapRow, fraction: float, lift: float) -> PopulationRow:
    remaining = gap.remaining_gap_bits_per_record
    c_star = remaining / lift if lift > 0.0 else math.inf
    starts_positive = fraction >= c_star
    p_of = fraction
    required_p_ff = min_p_ff(c_star, p_of)
    first_margin = fraction * lift - remaining
    asymptotic_margin = lift - remaining
    if c_star > 1.0:
        result = "lift too small even at c=1"
        cross_pass = None
        cumulative_pass = None
    else:
        cross_pass = pass_count_until_threshold(
            c0=fraction,
            c_star=c_star,
            p_ff=1.0,
            p_of=p_of,
        )
        cumulative_pass = pass_count_until_cumulative_positive(
            c0=fraction,
            gap=remaining,
            lift=lift,
            p_ff=1.0,
            p_of=p_of,
        )
        if starts_positive:
            result = "uniform start already above threshold"
        elif cross_pass is None:
            result = "cannot bootstrap even with closed F"
        elif cumulative_pass is None:
            result = "crosses threshold but startup loss not repaid"
        else:
            result = "requires closed/canalized F and startup bloat"
    return PopulationRow(
        label=gap.label,
        gap=remaining,
        conservative_gap=gap.gross_gap_bits_per_record,
        fraction=fraction,
        lift=lift,
        c_star=c_star,
        starts_positive=starts_positive,
        min_p_ff_at_background=required_p_ff,
        closure_cross_pass=cross_pass,
        closure_cumulative_positive_pass=cumulative_pass,
        first_margin=first_margin,
        asymptotic_margin=asymptotic_margin,
        result=result,
    )


def selected_population_rows() -> list[PopulationRow]:
    rows: list[PopulationRow] = []
    easiest = GAPS[0]
    hardest = GAPS[-1]
    for gap in (easiest, hardest):
        for fraction in CLASS_FRACTIONS:
            for lift in FUTURE_LIFTS:
                rows.append(population_row(gap, fraction, lift))
    return rows


def print_restriction_table() -> None:
    print("== public class restriction ledger ==")
    print(
        "If the encoder accepts only class-F witnesses, closure can be public, "
        "but hit supply thins by f."
    )
    print(
        f"{'row':<36} {'f':>7} {'g':>9} {'o':>8} {'r':>9} {'tax':>9} "
        f"{'need r+tax':>12} {'need g+tax':>12}"
    )
    for row in restriction_rows():
        if row.label != GAPS[0].label and row.fraction not in (0.10,):
            continue
        print(
            f"{row.label:<36} {fmt(row.fraction):>7} {fmt(row.gross_gap):>9} "
            f"{fmt(row.option):>8} {fmt(row.remaining_gap):>9} "
            f"{fmt(row.supply_tax):>9} {fmt(row.lift_needed_post_h165):>12} "
            f"{fmt(row.lift_needed_conservative):>12}"
        )
    print()


def print_population_table() -> None:
    print("== public population recurrence ledger ==")
    print(
        "No supply tax is charged here, so c_t must be an actual public source/output "
        "class fraction, not an enforced witness selector."
    )
    print(
        f"{'row':<36} {'f':>6} {'a':>7} {'c*':>8} {'start?':>7} "
        f"{'min pFF':>8} {'xPass':>7} {'cum+':>7} {'m0':>9} {'mInf':>9} {'result':<42}"
    )
    for row in selected_population_rows():
        if row.fraction not in (0.50, 0.10, 0.01):
            continue
        if row.lift not in (8.0, 16.0, 64.0, 128.0):
            continue
        cross = "-" if row.closure_cross_pass is None else str(row.closure_cross_pass)
        cumulative = (
            "-"
            if row.closure_cumulative_positive_pass is None
            else str(row.closure_cumulative_positive_pass)
        )
        print(
            f"{row.label:<36} {fmt(row.fraction):>6} {fmt(row.lift):>7} "
            f"{fmt(row.c_star):>8} {str(row.starts_positive):>7} "
            f"{fmt(row.min_p_ff_at_background):>8} {cross:>7} {cumulative:>7} "
            f"{fmt(row.first_margin):>9} {fmt(row.asymptotic_margin):>9} "
            f"{row.result:<42}"
        )
    print()


def print_measured_anchors() -> None:
    print("== measured anchors from prior exact toys ==")
    print(
        "H89 measured actual witness-cost fertility in the exact H80/H74 toy. "
        "The best oracle-saving law still had cycle=-2.397156 bits/word; "
        "the best word saved 4 bits but the average law did not cross."
    )
    print(
        "That is far below the H166 class-restriction requirements above "
        "(for example 11.434428 bits/record at f=0.10 after H165 option credit; "
        "11.683705 before that credit) and far below the uniform-start mixture "
        "requirement a >= gap/f (81.125 bits/record at f=0.10)."
    )
    print()


def print_reading() -> None:
    print("== reading ==")
    print(
        "There is still a mathematical target, but it is now very sharp. A public "
        "class can be used in one of two honest ways:"
    )
    print(
        "1. Restrict witnesses to F and pay -log2(f); then the fertile class must "
        "supply gap + tax bits/record immediately."
    )
    print(
        "2. Do not restrict witnesses; then c_t must be a real public source/output "
        "population fraction. Starting from uniform c0=f, it is positive on pass 0 "
        "only if a >= gap/f, or it needs a nearly closed attractor plus startup bloat."
    )
    print(
        "A claim that gets closed F without the supply tax is exactly the hidden "
        "selector/profile channel H168 is meant to catch."
    )


def main() -> None:
    print_restriction_table()
    print_population_table()
    print_measured_anchors()
    print_reading()


if __name__ == "__main__":
    main()
