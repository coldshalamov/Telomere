#!/usr/bin/env python3
"""H166 - visible-selected fertility conservation ledger.

H165 measured ordinary same-cost witness multiplicity and found it far below the
H164 bit target. H166 prices the remaining "visible selected witness" branch.

Under the uniform hash law, matching a current target interval is independent of
the future fertility of the visible witness string, except for public features
the decoder can see or derive: visible cost/length, arity class, payload width,
lane/class, or a predeclared seed class. Therefore:

* choosing the most fertile witness from a matched set is legitimate only for
  the witness that is actually emitted;
* same public-class matched witnesses have the same distribution as
  same-budget random witnesses, so expected lift over that control is zero;
* if the encoder restricts to a public high-fertility class with fraction f,
  the current hit supply pays a tax of -log2(f) bits/record.

This ledger does not close public fertility laws. It sets the gross future lift
they must measure before they can be combined with stateless lanes/salts.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class BaseMiss:
    label: str
    miss_bits_per_record: float
    observed_option_bits: float
    support: float

    @property
    def remaining_after_observed_option(self) -> float:
        return self.miss_bits_per_record - self.observed_option_bits

    @property
    def ideal_m_for_miss(self) -> float:
        return 2.0 ** self.miss_bits_per_record

    @property
    def ideal_m_for_observed_option(self) -> float:
        return 2.0 ** self.observed_option_bits


BASE_ROWS = [
    BaseMiss("H162 K5 D80 exact", 8.361777, 0.249277, 0.310),
    BaseMiss("H163 K5 D256 exact", 9.688172, 0.230719, 0.603),
    BaseMiss("H163 K5 D512 exact", 10.626718, 0.234505, 0.817),
    BaseMiss("H163 K16 D512 escape5", 11.143925, 0.217483, 0.833),
]

CLASS_FRACTIONS = [0.5, 0.25, 0.10, 0.03, 0.01]


def fmt(value: float) -> str:
    if abs(value) >= 1000.0 or (0.0 < abs(value) < 0.0001):
        return f"{value:.3e}"
    return f"{value:.6f}"


def print_exchangeability_rows() -> None:
    print("== same-class visible selection ==")
    print(
        "Under uniform hashes, selected matched witnesses and same-budget random "
        "witnesses have the same future-score distribution once public class/cost "
        "is fixed."
    )
    print(
        f"{'row':<27} {'support':>8} {'miss/rec':>9} {'obsOpt':>8} "
        f"{'remain':>9} {'M_miss':>10} {'M_obs':>8} {'lift-vs-rand':>13}"
    )
    for row in BASE_ROWS:
        print(
            f"{row.label:<27} {fmt(row.support):>8} "
            f"{fmt(row.miss_bits_per_record):>9} "
            f"{fmt(row.observed_option_bits):>8} "
            f"{fmt(row.remaining_after_observed_option):>9} "
            f"{fmt(row.ideal_m_for_miss):>10} "
            f"{fmt(row.ideal_m_for_observed_option):>8} "
            f"{fmt(0.0):>13}"
        )
    print()


def print_public_class_rows() -> None:
    print("== public fertility class cost ==")
    print(
        "If a public high-fertility witness class has fraction f, current hit "
        "supply thins by f. Gross future lift must cover miss/rec + -log2(f)."
    )
    print(
        f"{'row':<27} {'f':>7} {'supplyTax':>10} {'miss/rec':>9} "
        f"{'grossLiftNeeded':>15}"
    )
    for row in BASE_ROWS:
        for fraction in CLASS_FRACTIONS:
            supply_tax = -math.log2(fraction)
            gross = row.miss_bits_per_record + supply_tax
            print(
                f"{row.label:<27} {fmt(fraction):>7} {fmt(supply_tax):>10} "
                f"{fmt(row.miss_bits_per_record):>9} {fmt(gross):>15}"
            )
    print()


def print_reading() -> None:
    best_remaining = min(BASE_ROWS, key=lambda row: row.remaining_after_observed_option)
    print("== reading ==")
    print(
        f"Smallest post-H165 remaining strict gap: {best_remaining.label}; "
        f"{fmt(best_remaining.remaining_after_observed_option)} bits/record."
    )
    print(
        "Same-class visible selection has zero expected lift over a same-budget "
        "random control. A real positive H166+ result must therefore come from "
        "a public class/law whose measured future lift exceeds the supply tax, "
        "or from an emitted-stream recurrence that beats same-budget random."
    )


def main() -> None:
    print_exchangeability_rows()
    print_public_class_rows()
    print_reading()


if __name__ == "__main__":
    main()
