#!/usr/bin/env python3
"""H164 - fertility-selected superposition threshold.

H162/H163 give the non-greedy cover DP the best local source records and still
miss by several bits per item. A plausible remaining non-greedy knob is
fertility-selected superposition: when multiple matching witnesses produce the
same current interval, choose the witness whose visible record string is more
fertile for the next pass.

This ledger prices the minimum future value required. Under a uniform law, an
unpaid choice among M equally real alternatives can buy at most log2(M) bits of
future value per selected record unless a public fertility feature genuinely
changes the source law. Therefore:

    equivalent best-of-M choices = 2^(missing bits per selected record)

The table does not prove the mechanism impossible. It sets the target for the
next recurrent-transfer kernel and prevents "many alternatives" from being used
as an unpriced magic word.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Row:
    label: str
    mode: str
    support: float
    gain_per_item: float
    records_per_item: float
    strict: bool

    @property
    def missing_bits_per_item(self) -> float:
        return max(0.0, -self.gain_per_item)

    @property
    def missing_bits_per_record(self) -> float:
        if self.records_per_item <= 0.0:
            return math.inf
        return self.missing_bits_per_item / self.records_per_item

    @property
    def effective_alternatives(self) -> float:
        if self.missing_bits_per_record == math.inf:
            return math.inf
        return 2.0 ** self.missing_bits_per_record

    @property
    def support_tax(self) -> float:
        if self.support <= 0.0:
            return math.inf
        return -math.log2(self.support)


ROWS = [
    Row("H162 K5 D80 N32 exact", "seed_only", 0.310, -4.110081, 0.491532, True),
    Row("H162 K5 D80 N32 mixed", "mixed_all", 0.384, -3.472168, 0.426758, False),
    Row("H163 K5 D256 N32 exact", "seed_only", 0.603, -3.524344, 0.363778, True),
    Row("H163 K5 D512 N32 exact", "seed_only", 0.817, -3.476722, 0.327168, True),
    Row("H163 K16 D256 N32 escape5", "seed_only", 0.663, -3.546954, 0.359454, True),
    Row("H163 K16 D512 N32 escape5", "seed_only", 0.833, -3.266563, 0.293125, True),
]


def fmt(value: float) -> str:
    if value == math.inf:
        return "inf"
    if abs(value) >= 1000.0 or (0.0 < abs(value) < 0.0001):
        return f"{value:.3e}"
    return f"{value:.6f}"


def main() -> None:
    print("== fertility-selected superposition threshold ==")
    print("Primary target is miss/rec in bits. M_eq is the ideal best-of-M choice count with log2(M)=miss/rec.")
    print(
        f"{'row':<31} {'mode':<9} {'strict':>6} {'support':>8} "
        f"{'miss/item':>10} {'rec/item':>9} {'miss/rec':>9} "
        f"{'M_eq':>10} {'suppTax':>8}"
    )
    for row in ROWS:
        print(
            f"{row.label:<31} {row.mode:<9} {str(row.strict):>6} "
            f"{fmt(row.support):>8} {fmt(row.missing_bits_per_item):>10} "
            f"{fmt(row.records_per_item):>9} {fmt(row.missing_bits_per_record):>9} "
            f"{fmt(row.effective_alternatives):>10} {fmt(row.support_tax):>8}"
        )

    strict_rows = [row for row in ROWS if row.strict]
    best_item = min(strict_rows, key=lambda row: row.missing_bits_per_item)
    best_record = min(strict_rows, key=lambda row: row.missing_bits_per_record)
    print()
    print("== reading ==")
    print(
        f"Smallest strict miss per item: {best_item.label}; "
        f"{fmt(best_item.missing_bits_per_item)} bits/item, "
        f"{fmt(best_item.missing_bits_per_record)} bits/record, "
        f"M_eq={fmt(best_item.effective_alternatives)}."
    )
    print(
        f"Smallest strict miss per selected record: {best_record.label}; "
        f"{fmt(best_record.missing_bits_per_record)} bits/record, "
        f"M_eq={fmt(best_record.effective_alternatives)}."
    )
    print(
        "Fertility selection remains a live target only if a public, recurrent "
        "fertility score supplies this much value against same-budget random controls."
    )


if __name__ == "__main__":
    main()
