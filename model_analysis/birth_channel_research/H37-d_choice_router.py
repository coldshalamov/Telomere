#!/usr/bin/env python3
"""
H37 - d-choice self-routing / cuckoo placement ledger.

Idea:

    Give each record d public candidate cells. Decode uses a canonical router
    (for example, lexicographically first matching) so placement is stateless.

This is a useful variant of public lanes: d choices can reduce the supply loss
for landing in a public active/fertile lane. It cannot make arbitrary final
order or content-selected placement free.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import lgamma, log2
import random


LN2 = 0.6931471805599453


def log2_factorial(n: int) -> float:
    return lgamma(n + 1) / LN2


def log2_choose(n: int, k: int) -> float:
    if k < 0 or k > n:
        return float("-inf")
    return log2_factorial(n) - log2_factorial(k) - log2_factorial(n - k)


def log2_permutation(n: int, k: int) -> float:
    if k < 0 or k > n:
        return float("-inf")
    return log2_factorial(n) - log2_factorial(n - k)


@dataclass(frozen=True)
class LaneRow:
    active_fraction: float
    choices: int
    hit_fraction: float
    supply_loss: float
    improvement_vs_one_choice: float
    gamma_threshold: float


def lane_rows() -> list[LaneRow]:
    rows: list[LaneRow] = []
    for active_fraction in (0.01, 0.05, 0.10, 0.25, 0.50):
        base_loss = -log2(active_fraction)
        for choices in (1, 2, 4, 8, 16):
            hit_fraction = 1.0 - ((1.0 - active_fraction) ** choices)
            supply_loss = -log2(hit_fraction)
            rows.append(
                LaneRow(
                    active_fraction=active_fraction,
                    choices=choices,
                    hit_fraction=hit_fraction,
                    supply_loss=supply_loss,
                    improvement_vs_one_choice=base_loss - supply_loss,
                    gamma_threshold=supply_loss,
                )
            )
    return rows


@dataclass(frozen=True)
class DestinationRow:
    board_cells: int
    choices: int
    destination_loss: float
    improvement_vs_coordinate: float


def destination_rows() -> list[DestinationRow]:
    rows: list[DestinationRow] = []
    for board_cells in (256, 4096, 1_000_000):
        coordinate = log2(board_cells)
        for choices in (1, 2, 4, 8, 16, 64):
            rows.append(
                DestinationRow(
                    board_cells=board_cells,
                    choices=choices,
                    destination_loss=max(0.0, log2(board_cells / choices)),
                    improvement_vs_coordinate=min(coordinate, log2(choices)),
                )
            )
    return rows


def count_matchings(candidates: list[tuple[int, ...]], board_cells: int) -> int:
    """Count injective assignments for a small candidate graph."""

    states: dict[int, int] = {0: 1}
    for options in candidates:
        next_states: dict[int, int] = {}
        for mask, count in states.items():
            for cell in options:
                bit = 1 << cell
                if mask & bit:
                    continue
                next_states[mask | bit] = next_states.get(mask | bit, 0) + count
        states = next_states
    return sum(states.values())


@dataclass(frozen=True)
class MatchingRow:
    board_cells: int
    records: int
    choices: int
    matching_count: int
    ambiguity_bits: float
    occupancy_bits: float
    ordered_slot_bits: float


def matching_rows() -> list[MatchingRow]:
    rows: list[MatchingRow] = []
    rng = random.Random(37037)
    for board_cells, records in ((10, 5), (12, 6), (16, 8)):
        for choices in (2, 3, 4):
            candidates: list[tuple[int, ...]] = []
            for _ in range(records):
                options = tuple(sorted(rng.sample(range(board_cells), choices)))
                candidates.append(options)
            count = count_matchings(candidates, board_cells)
            rows.append(
                MatchingRow(
                    board_cells=board_cells,
                    records=records,
                    choices=choices,
                    matching_count=count,
                    ambiguity_bits=log2(count) if count else float("-inf"),
                    occupancy_bits=log2_choose(board_cells, records),
                    ordered_slot_bits=log2_permutation(board_cells, records),
                )
            )
    return rows


@dataclass(frozen=True)
class StableCompactionRow:
    total_slots: int
    active_fraction: float
    opened_records: int
    boundary_bits_per_open: float
    hidden_subset_bits_per_open: float


def stable_compaction_rows() -> list[StableCompactionRow]:
    rows: list[StableCompactionRow] = []
    for total_slots in (256, 4096, 1_000_000):
        for active_fraction in (0.01, 0.10, 0.50):
            opened = max(1, round(total_slots * active_fraction))
            rows.append(
                StableCompactionRow(
                    total_slots=total_slots,
                    active_fraction=active_fraction,
                    opened_records=opened,
                    boundary_bits_per_open=log2(total_slots + 1) / opened,
                    hidden_subset_bits_per_open=log2_choose(total_slots, opened)
                    / opened,
                )
            )
    return rows


def print_lane_table() -> None:
    print("== d-choice active/fertile lane supply loss ==")
    print(
        "If a public active lane occupies fraction r, d candidate cells give "
        "hit fraction 1-(1-r)^d. This lowers, but does not remove, supply cost."
    )
    print(
        f"{'r':>7} {'d':>4} {'hit frac':>10} {'loss bits':>10} "
        f"{'improve':>9} {'needed lift':>12}"
    )
    for row in lane_rows():
        if row.active_fraction in (0.01, 0.10, 0.50):
            print(
                f"{row.active_fraction:7.2f} {row.choices:4d} "
                f"{row.hit_fraction:10.6f} {row.supply_loss:10.3f} "
                f"{row.improvement_vs_one_choice:9.3f} "
                f"{row.gamma_threshold:12.3f}"
            )
    print()


def print_destination_table() -> None:
    print("== exact destination / coordinate supply loss ==")
    print(
        "If placement must identify one cell among Q, d choices save only "
        "log2(d) bits; the remaining coordinate entropy is still paid as supply."
    )
    print(f"{'Q':>9} {'d':>4} {'loss bits':>10} {'saved':>8}")
    for row in destination_rows():
        if row.board_cells in (4096, 1_000_000) and row.choices in (1, 4, 16, 64):
            print(
                f"{row.board_cells:9d} {row.choices:4d} "
                f"{row.destination_loss:10.3f} {row.improvement_vs_coordinate:8.3f}"
            )
    print()


def print_matching_table() -> None:
    print("== small canonical router matching ambiguity ==")
    print(
        "A canonical matching is free but cannot be chosen for content. If the "
        "encoder selects among valid matchings, the ambiguity bits are metadata."
    )
    print(
        f"{'Q':>4} {'m':>3} {'d':>3} {'matchings':>10} {'amb bits':>9} "
        f"{'holes':>9} {'ordered':>9}"
    )
    for row in matching_rows():
        print(
            f"{row.board_cells:4d} {row.records:3d} {row.choices:3d} "
            f"{row.matching_count:10d} {row.ambiguity_bits:9.3f} "
            f"{row.occupancy_bits:9.3f} {row.ordered_slot_bits:9.3f}"
        )
    print()


def print_compaction_table() -> None:
    print("== stable compaction boundary vs hidden subset ==")
    print(
        "Boundary-only compaction is cheap only when active records are a public "
        "prefix. Content-selected readiness pays the subset entropy."
    )
    print(
        f"{'N':>9} {'r':>6} {'m':>8} {'boundary/open':>14} "
        f"{'subset/open':>13}"
    )
    for row in stable_compaction_rows():
        if row.total_slots in (4096, 1_000_000):
            print(
                f"{row.total_slots:9d} {row.active_fraction:6.2f} "
                f"{row.opened_records:8d} {row.boundary_bits_per_open:14.6f} "
                f"{row.hidden_subset_bits_per_open:13.3f}"
            )
    print()


def main() -> None:
    print_lane_table()
    print_destination_table()
    print_matching_table()
    print_compaction_table()
    print("CONCLUSION:")
    print(
        "d-choice routing is useful stateless machinery and can reduce the price "
        "of public active/fertile lanes. It does not make placement free: exact "
        "destinations still cost coordinate supply, selected matchings are "
        "metadata, and content-selected compaction pays subset entropy. Its best "
        "role is lowering the value-lift threshold for H28/H36 fertility lanes."
    )


if __name__ == "__main__":
    main()
