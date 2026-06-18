#!/usr/bin/env python3
"""
H27 - orderless / confluent decode ledger.

This prices the tempting idea that decode order might not matter:

* records expand into a multiset and are sorted by a public key;
* children land through a commutative/confluent rewrite;
* seed-derived sort keys "implicitly" restore order.

The parser can be stateless, but arbitrary byte streams are ordered objects. If
the order is not public, it is either stored as a permutation or consumed as
match supply by requiring random seed keys to have the target order.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import lgamma, log, log2


def log2_factorial(n: int) -> float:
    return lgamma(n + 1) / log(2.0)


def log2_multinomial_uniform_counts(n: int, alphabet: int) -> float:
    """Approximate order entropy when only atom values matter.

    Uses the maximum-collision uniform-count case: counts are as even as possible
    across the alphabet. Random uniform data has nearly this entropy per atom for
    large n, up to lower-order count fluctuations.
    """
    base = n // alphabet
    extra = n % alphabet
    total = log2_factorial(n)
    total -= extra * log2_factorial(base + 1)
    total -= (alphabet - extra) * log2_factorial(base)
    return total


@dataclass(frozen=True)
class OrderRow:
    records: int
    permutation_bits_per_record: float
    uniform_b4_order_bits_per_atom: float
    uniform_b8_order_bits_per_atom: float
    seed_key_supply_loss: float


def order_rows() -> list[OrderRow]:
    rows: list[OrderRow] = []
    for records in (4, 8, 16, 64, 256, 4096, 1_000_000):
        perm_bits_per = log2_factorial(records) / records
        b4_bits = log2_multinomial_uniform_counts(records, 16) / records
        b8_bits = log2_multinomial_uniform_counts(records, 256) / records
        key_bits = log2(records)
        rows.append(
            OrderRow(
                records=records,
                permutation_bits_per_record=perm_bits_per,
                uniform_b4_order_bits_per_atom=b4_bits,
                uniform_b8_order_bits_per_atom=b8_bits,
                seed_key_supply_loss=key_bits,
            )
        )
    return rows


@dataclass(frozen=True)
class LaneSortRow:
    lane_fraction: float
    lane_supply_loss: float
    within_lane_order_bits_per_record: float
    total_no_value_lift: float
    value_lift_needed: float


def lane_sort_rows(total_records: int = 1_000_000, gross_bits: float = 2.0) -> list[LaneSortRow]:
    rows: list[LaneSortRow] = []
    for lane_fraction in (0.5, 0.25, 0.125, 0.10, 0.0625, 0.01):
        lane_records = max(1, int(round(total_records * lane_fraction)))
        lane_loss = log2(1.0 / lane_fraction)
        order_bits = log2_factorial(lane_records) / lane_records
        total_cost = lane_loss + order_bits
        rows.append(
            LaneSortRow(
                lane_fraction=lane_fraction,
                lane_supply_loss=lane_loss,
                within_lane_order_bits_per_record=order_bits,
                total_no_value_lift=gross_bits - total_cost,
                value_lift_needed=max(0.0, total_cost - gross_bits),
            )
        )
    return rows


def print_order_table() -> None:
    print("== orderless bag -> ordered stream bill ==")
    print(
        "If decoded records are a bag, arbitrary output order costs log2(m!). "
        "Requiring seed-derived keys to appear in target order spends the same "
        "amount as match-supply: probability 1/m!."
    )
    print(
        f"{'records':>9} {'log2(m!)/m':>14} {'B4 value-order/m':>17} "
        f"{'B8 value-order/m':>17} {'key bits/m':>11}"
    )
    for row in order_rows():
        print(
            f"{row.records:9d} {row.permutation_bits_per_record:14.6f} "
            f"{row.uniform_b4_order_bits_per_atom:17.6f} "
            f"{row.uniform_b8_order_bits_per_atom:17.6f} "
            f"{row.seed_key_supply_loss:11.6f}"
        )
    print()


def print_lane_sort_table() -> None:
    print("== public active lane plus orderless children ==")
    print(
        "Public lanes solve open/salt state, but if children inside the lane are "
        "only a bag, their order is another large channel."
    )
    print(
        f"{'lane r':>8} {'lane loss':>11} {'within-order':>14} "
        f"{'net no lift':>12} {'lift to >0':>11}"
    )
    for row in lane_sort_rows():
        print(
            f"{row.lane_fraction:8.4f} {row.lane_supply_loss:11.6f} "
            f"{row.within_lane_order_bits_per_record:14.6f} "
            f"{row.total_no_value_lift:12.3f} {row.value_lift_needed:11.3f}"
        )
    print()


def print_conclusion() -> None:
    print("CONCLUSION:")
    print(
        "Confluent/orderless decode is a valid parser only for an orderless "
        "target or a public canonical order. For arbitrary byte streams, "
        "canonical sorting adds one of three equivalent bills: store the "
        "permutation, match a seed/key order with probability 1/m!, or restrict "
        "the source to public-sorted strings. None refreshes match rate for "
        "roughly all data without a new value/count separation."
    )


def main() -> None:
    print_order_table()
    print_lane_sort_table()
    print_conclusion()


if __name__ == "__main__":
    main()
