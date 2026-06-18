#!/usr/bin/env python3
"""
H33 - de Bruijn / universal tape address ledger.

Idea:

    A public cyclic tape contains every L-bit string exactly once.
    Encode a target span by its coordinate on the tape.

This guarantees matches, unlike raw hash search. The question is whether the
coordinate can be shorter than the span, or whether overlapping coordinates can
refresh recursive compression on roughly all data.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import log2


@dataclass(frozen=True)
class AddressRow:
    span_bits: int
    address_bits: int
    coverage_fraction_log2: int
    net_if_reachable: int
    all_data: bool


def address_rows() -> list[AddressRow]:
    rows: list[AddressRow] = []
    for span_bits in (8, 16, 32, 64, 128):
        for address_bits in (4, 8, 12, 16, 24, 32, 64, 128):
            if address_bits > span_bits + 8:
                continue
            cover_log = min(0, address_bits - span_bits)
            rows.append(
                AddressRow(
                    span_bits=span_bits,
                    address_bits=address_bits,
                    coverage_fraction_log2=cover_log,
                    net_if_reachable=span_bits - address_bits,
                    all_data=address_bits >= span_bits,
                )
            )
    return rows


@dataclass(frozen=True)
class OverlapRow:
    span_bits: int
    spans: int
    independent_raw_bits: int
    adjacent_tape_bits: int
    arbitrary_order_bits: float
    source_fraction_log2: int


def overlap_rows() -> list[OverlapRow]:
    rows: list[OverlapRow] = []
    for span_bits in (8, 16, 32):
        for spans in (2, 4, 16, 256):
            independent = spans * span_bits
            # One coordinate plus public adjacent run length/order. The adjacent
            # tape segment contains span_bits + spans - 1 bits if sliding by 1.
            adjacent = span_bits + max(0, spans - 1)
            source_fraction_log2 = adjacent - independent
            # If the spans are arbitrary and we sort/choose a path, order/choice
            # must be paid. A crude lower bound is the raw missing bits.
            arbitrary_order = max(0.0, float(independent - adjacent))
            rows.append(
                OverlapRow(
                    span_bits=span_bits,
                    spans=spans,
                    independent_raw_bits=independent,
                    adjacent_tape_bits=adjacent,
                    arbitrary_order_bits=arbitrary_order,
                    source_fraction_log2=source_fraction_log2,
                )
            )
    return rows


@dataclass(frozen=True)
class RecursiveRow:
    passes: int
    span_bits: int
    pass_selector_bits: float
    coordinate_bits_per_pass: int
    entropy_change: int


def recursive_rows() -> list[RecursiveRow]:
    rows: list[RecursiveRow] = []
    for passes in (1, 2, 4, 64, 4096):
        for span_bits in (16, 64):
            rows.append(
                RecursiveRow(
                    passes=passes,
                    span_bits=span_bits,
                    pass_selector_bits=0.0 if passes == 1 else log2(passes),
                    coordinate_bits_per_pass=span_bits,
                    entropy_change=0,
                )
            )
    return rows


def print_address_table() -> None:
    print("== universal tape coordinate cost ==")
    print(
        "A de Bruijn cycle of order L has 2^L positions. Naming every L-bit "
        "span needs L coordinate bits."
    )
    print(
        f"{'span L':>8} {'addr bits':>10} {'log2 coverage':>14} "
        f"{'net if hit':>11} {'all data?':>10}"
    )
    for row in address_rows():
        if row.span_bits in (16, 64, 128) and row.address_bits in (8, 16, 32, 64, 128):
            print(
                f"{row.span_bits:8d} {row.address_bits:10d} "
                f"{row.coverage_fraction_log2:14d} {row.net_if_reachable:11d} "
                f"{str(row.all_data):>10}"
            )
    print()


def print_overlap_table() -> None:
    print("== adjacent tape overlap ==")
    print(
        "Adjacent tape windows share bits and can be described cheaply, but only "
        "for sources constrained to adjacent tape paths."
    )
    print(
        f"{'span L':>8} {'spans':>8} {'raw bits':>9} {'adjacent bits':>14} "
        f"{'log2 source frac':>17} {'missing/order':>14}"
    )
    for row in overlap_rows():
        if row.span_bits in (8, 16) and row.spans in (4, 16, 256):
            print(
                f"{row.span_bits:8d} {row.spans:8d} "
                f"{row.independent_raw_bits:9d} {row.adjacent_tape_bits:14d} "
                f"{row.source_fraction_log2:17d} {row.arbitrary_order_bits:14.1f}"
            )
    print()


def print_recursive_table() -> None:
    print("== recursive pass refresh ==")
    print(
        "Changing the public tape phase/pass is a reversible relabeling. If the "
        "encoder chooses among phases, the phase selector is paid."
    )
    print(
        f"{'passes':>8} {'span L':>8} {'selector':>10} "
        f"{'coord/pass':>11} {'entropy change':>15}"
    )
    for row in recursive_rows():
        if row.passes in (1, 64, 4096):
            print(
                f"{row.passes:8d} {row.span_bits:8d} {row.pass_selector_bits:10.3f} "
                f"{row.coordinate_bits_per_pass:11d} {row.entropy_change:15d}"
            )
    print()


def main() -> None:
    print_address_table()
    print_overlap_table()
    print_recursive_table()
    print("CONCLUSION:")
    print(
        "A universal tape guarantees matches by making the address space as large "
        "as the span space. Short addresses cover only a matching fraction of "
        "all spans; adjacent overlap is a source constraint; phase changes are "
        "public reversible relabelings or paid selectors. This is a useful "
        "mental model for Telomere's seed universe, but not a new all-data "
        "recursive compression channel."
    )


if __name__ == "__main__":
    main()
