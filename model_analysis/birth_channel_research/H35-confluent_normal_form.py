#!/usr/bin/env python3
"""
H35 - confluent normal-form / order-independent decode ledger.

Idea:

    Records may open in any order. Public local moves commute or sort the
    opened pieces into a canonical final arrangement, so decoding is confluent.

This is the algebraic version of "order does not matter; everything ends up in
the right place." The question is whether the lost order/placement information
is free, public, or paid elsewhere.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import lgamma, log2


LN2 = 0.6931471805599453


def log2_factorial(n: int) -> float:
    return lgamma(n + 1) / LN2


def log2_choose(n: int, k: int) -> float:
    if k < 0 or k > n:
        return float("-inf")
    return log2_factorial(n) - log2_factorial(k) - log2_factorial(n - k)


@dataclass(frozen=True)
class ReadyBoundaryRow:
    total_slots: int
    ready_slots: int
    boundary_bits: float
    hidden_subset_bits: float
    hidden_bits_per_ready: float


def ready_boundary_rows() -> list[ReadyBoundaryRow]:
    rows: list[ReadyBoundaryRow] = []
    for total_slots in (64, 256, 4096, 1_000_000):
        for fraction in (0.01, 0.10, 0.50):
            ready_slots = max(1, round(total_slots * fraction))
            boundary_bits = log2(total_slots + 1)
            hidden_subset_bits = log2_choose(total_slots, ready_slots)
            rows.append(
                ReadyBoundaryRow(
                    total_slots=total_slots,
                    ready_slots=ready_slots,
                    boundary_bits=boundary_bits,
                    hidden_subset_bits=hidden_subset_bits,
                    hidden_bits_per_ready=hidden_subset_bits / ready_slots,
                )
            )
    return rows


@dataclass(frozen=True)
class LinearExtensionRow:
    items: int
    chains: tuple[int, ...]
    extension_bits: float
    extension_bits_per_item: float


def linear_extension_rows() -> list[LinearExtensionRow]:
    rows: list[LinearExtensionRow] = []
    for chains in (
        (16,),
        (8, 8),
        (4, 4, 4, 4),
        (1,) * 16,
        (64,),
        (8,) * 8,
        (1,) * 64,
        (128,),
        (16,) * 8,
        (1,) * 128,
    ):
        items = sum(chains)
        extension_bits = log2_factorial(items) - sum(log2_factorial(c) for c in chains)
        rows.append(
            LinearExtensionRow(
                items=items,
                chains=chains,
                extension_bits=extension_bits,
                extension_bits_per_item=extension_bits / items,
            )
        )
    return rows


@dataclass(frozen=True)
class MultisetOrderRow:
    items: int
    value_counts: tuple[int, ...]
    order_bits: float
    order_bits_per_item: float


def multiset_order_rows() -> list[MultisetOrderRow]:
    rows: list[MultisetOrderRow] = []
    for counts in (
        (1,) * 16,
        (2,) * 8,
        (4,) * 4,
        (8, 8),
        (1,) * 64,
        (4,) * 16,
        (16,) * 4,
    ):
        items = sum(counts)
        order_bits = log2_factorial(items) - sum(log2_factorial(c) for c in counts)
        rows.append(
            MultisetOrderRow(
                items=items,
                value_counts=counts,
                order_bits=order_bits,
                order_bits_per_item=order_bits / items,
            )
        )
    return rows


@dataclass(frozen=True)
class SeedPlacementRow:
    payload_bits: int
    placement_bits: int
    searched_seeds_log2: int
    expected_hits_log2: int
    hit_supply_loss: int


def seed_placement_rows() -> list[SeedPlacementRow]:
    rows: list[SeedPlacementRow] = []
    for payload_bits in (16, 32, 64):
        for placement_bits in (0, 4, 8, 16):
            for searched in (32, 48, 80):
                rows.append(
                    SeedPlacementRow(
                        payload_bits=payload_bits,
                        placement_bits=placement_bits,
                        searched_seeds_log2=searched,
                        expected_hits_log2=searched
                        - payload_bits
                        - placement_bits,
                        hit_supply_loss=placement_bits,
                    )
                )
    return rows


def print_ready_boundary_table() -> None:
    print("== ready-prefix boundary vs arbitrary ready subset ==")
    print(
        "A single boundary is cheap only if readiness is already a public prefix. "
        "If the encoder chose which slots are ready, the subset must be paid."
    )
    print(
        f"{'N':>9} {'m':>8} {'boundary':>10} {'subset bits':>13} "
        f"{'bits/ready':>11}"
    )
    for row in ready_boundary_rows():
        if row.total_slots in (256, 4096, 1_000_000):
            print(
                f"{row.total_slots:9d} {row.ready_slots:8d} "
                f"{row.boundary_bits:10.3f} {row.hidden_subset_bits:13.3f} "
                f"{row.hidden_bits_per_ready:11.3f}"
            )
    print()


def print_linear_extension_table() -> None:
    print("== confluent linear-extension cost ==")
    print(
        "Canonicalization is free for the normal form, but lossless recovery of "
        "an arbitrary original order needs the linear-extension index."
    )
    print(f"{'items':>6} {'chains':>18} {'ext bits':>11} {'bits/item':>10}")
    for row in linear_extension_rows():
        chains = "x".join(str(c) for c in row.chains[:4])
        if len(row.chains) > 4:
            chains += f"...({len(row.chains)})"
        print(
            f"{row.items:6d} {chains:>18} {row.extension_bits:11.3f} "
            f"{row.extension_bits_per_item:10.3f}"
        )
    print()


def print_multiset_order_table() -> None:
    print("== unordered multiset to ordered stream ==")
    print(
        "Repeated values reduce permutation entropy, but arbitrary byte streams "
        "still need the order index unless the source is actually a multiset."
    )
    print(f"{'items':>6} {'groups':>8} {'max count':>9} {'order bits':>12} {'bits/item':>10}")
    for row in multiset_order_rows():
        print(
            f"{row.items:6d} {len(row.value_counts):8d} "
            f"{max(row.value_counts):9d} {row.order_bits:12.3f} "
            f"{row.order_bits_per_item:10.3f}"
        )
    print()


def print_seed_placement_table() -> None:
    print("== seed-derived placement as match-supply loss ==")
    print(
        "If the seed must also self-describe a destination/phase, the equality "
        "predicate gains placement_bits and expected hits drop by that amount."
    )
    print(
        f"{'payload':>8} {'place':>7} {'search':>7} "
        f"{'log2 E_hits':>12} {'supply loss':>12}"
    )
    for row in seed_placement_rows():
        if row.payload_bits in (32, 64) and row.searched_seeds_log2 in (48, 80):
            print(
                f"{row.payload_bits:8d} {row.placement_bits:7d} "
                f"{row.searched_seeds_log2:7d} {row.expected_hits_log2:12d} "
                f"{row.hit_supply_loss:12d}"
            )
    print()


def main() -> None:
    print_ready_boundary_table()
    print_linear_extension_table()
    print_multiset_order_table()
    print_seed_placement_table()
    print("CONCLUSION:")
    print(
        "Confluent decode is excellent machinery: records can open out of order "
        "and settle into a public normal form. But the normal form discards the "
        "original linear extension. For arbitrary streams the decoder must be "
        "given that extension, or the seed predicate must include placement and "
        "lose the same bits of match supply. Public placement is free only when "
        "it is not a content-dependent signal."
    )


if __name__ == "__main__":
    main()
