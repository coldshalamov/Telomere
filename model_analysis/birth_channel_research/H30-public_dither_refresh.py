#!/usr/bin/env python3
"""
H30 - public reversible dither / transform refresh ledger.

Idea: instead of per-record salting, apply a fixed public reversible transform
T_p to the whole layer before each pass:

    target_p = T_p(current_layer)
    encode target_p with Total-Cover/Telomere
    decoder reconstructs target_p, then applies T_p^-1

This can refresh the visible bytes without birth/open metadata if pass p is
public or stored once. Because T_p is a bijection, it preserves uniform entropy;
the ledger separates "fresh dice" from "net compression".
"""

from __future__ import annotations

from dataclasses import dataclass
from math import log2


@dataclass(frozen=True)
class DitherRow:
    saving_bits_if_hit: float
    passes: int
    cheap_fraction_per_pass: float
    free_best_hit_probability: float
    selector_bits: float
    paid_saving_per_hit: float
    hidden_selector_if_free: float


def dither_rows() -> list[DitherRow]:
    rows: list[DitherRow] = []
    for saving_bits in (2, 4, 8, 12):
        cheap_fraction = 2.0 ** (-saving_bits)
        for passes in (1, 2, 4, 16, 64, 256, 4096):
            free_hit = 1.0 - (1.0 - cheap_fraction) ** passes
            selector = 0.0 if passes == 1 else log2(passes)
            rows.append(
                DitherRow(
                    saving_bits_if_hit=float(saving_bits),
                    passes=passes,
                    cheap_fraction_per_pass=cheap_fraction,
                    free_best_hit_probability=free_hit,
                    selector_bits=selector,
                    paid_saving_per_hit=float(saving_bits) - selector,
                    hidden_selector_if_free=selector,
                )
            )
    return rows


@dataclass(frozen=True)
class FixedScheduleRow:
    pass_count: int
    per_pass_match_rate: float
    metadata_bits_total: float
    entropy_change_bits: float


def fixed_schedule_rows() -> list[FixedScheduleRow]:
    rows: list[FixedScheduleRow] = []
    for pass_count in (1, 2, 4, 16, 64, 256, 4096):
        rows.append(
            FixedScheduleRow(
                pass_count=pass_count,
                per_pass_match_rate=1.0,
                metadata_bits_total=0.0 if pass_count == 1 else log2(pass_count),
                entropy_change_bits=0.0,
            )
        )
    return rows


def print_fixed_schedule_table() -> None:
    print("== fixed public reversible dither schedule ==")
    print(
        "A fixed T_p can refresh the visible layer with no per-record state. "
        "Only the total pass count/profile is needed. Since T_p is bijective, "
        "uniform entropy change is zero."
    )
    print(
        f"{'passes':>8} {'freshness':>10} {'header bits':>12} "
        f"{'entropy change':>15}"
    )
    for row in fixed_schedule_rows():
        print(
            f"{row.pass_count:8d} {row.per_pass_match_rate:10.3f} "
            f"{row.metadata_bits_total:12.3f} {row.entropy_change_bits:15.3f}"
        )
    print()


def print_best_of_pass_table() -> None:
    print("== choosing the best public dither among P passes ==")
    print(
        "Free best-of-P is an unpaid selector. Paying log2(P) restores the "
        "ordinary counting bound."
    )
    print(
        f"{'save s':>7} {'P':>6} {'per-pass f':>12} {'free hit p':>12} "
        f"{'selector':>9} {'paid save/hit':>14}"
    )
    for row in dither_rows():
        if row.passes not in (1, 4, 64, 4096):
            continue
        print(
            f"{row.saving_bits_if_hit:7.1f} {row.passes:6d} "
            f"{row.cheap_fraction_per_pass:12.6g} "
            f"{row.free_best_hit_probability:12.6f} "
            f"{row.selector_bits:9.3f} {row.paid_saving_per_hit:14.3f}"
        )
    print()


def main() -> None:
    print_fixed_schedule_table()
    print_best_of_pass_table()
    print("CONCLUSION:")
    print(
        "Public reversible dither is a good stateless freshness scaffold: it can "
        "avoid per-record birth/salt metadata when every pass uses the public "
        "schedule. It cannot be the compression source for roughly all uniform "
        "data, because bijections preserve entropy and best-of-pass selection "
        "costs log2(P) bits when the decoder must know which transformed layer "
        "was used."
    )


if __name__ == "__main__":
    main()
