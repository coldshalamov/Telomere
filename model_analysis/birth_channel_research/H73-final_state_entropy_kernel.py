#!/usr/bin/env python3
"""H73 - final-board / decode-geometry entropy kernel.

This prices the final-position / egg-carton family directly.

Geometry can make stateless decode possible, but any content-selected fact it
conveys must appear as visible final-state entropy or as match-supply loss.
For R final survivors in coordinate space Q over P possible birth/open passes:

    occupancy coordinates:  log2 C(Q,R)
    ordered coordinates:    log2 (Q)_R = log2 C(Q,R) + log2 R!
    birth labels:           R log2 P, or multinomial if counts are fixed
    ready subset:           log2 C(N,R)
    orderless confluence:   log2 R! unless original order is public/irrelevant

The rows below compare hidden history demand with visible state capacity/cost.
Small counts are exact combinatorics; no hashing or compression search occurs.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


def log2_factorial(n: int) -> float:
    return math.lgamma(n + 1) / math.log(2.0)


def log2_comb(n: int, k: int) -> float:
    if k < 0 or k > n:
        return float("-inf")
    return log2_factorial(n) - log2_factorial(k) - log2_factorial(n - k)


def log2_perm(n: int, k: int) -> float:
    if k < 0 or k > n:
        return float("-inf")
    return log2_factorial(n) - log2_factorial(n - k)


def h2(p: float) -> float:
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -(p * math.log2(p) + (1.0 - p) * math.log2(1.0 - p))


def multinomial_bits(counts: tuple[int, ...]) -> float:
    return log2_factorial(sum(counts)) - sum(log2_factorial(count) for count in counts)


@dataclass(frozen=True)
class BoardRow:
    name: str
    n_items: int
    survivors: int
    q_space: int
    passes: int
    hidden_ready_bits: float
    hidden_birth_bits: float
    hidden_order_bits: float
    visible_occupancy_bits: float
    visible_ordered_bits: float
    exception_bits: float
    supply_loss_bits: float
    reading: str

    @property
    def hidden_total_bits(self) -> float:
        return self.hidden_ready_bits + self.hidden_birth_bits + self.hidden_order_bits

    @property
    def occupancy_margin_bits(self) -> float:
        return self.visible_occupancy_bits - self.hidden_total_bits

    @property
    def ordered_margin_bits(self) -> float:
        return self.visible_ordered_bits - self.hidden_total_bits


def sparse_ready_row(n_items: int, survivors: int, passes: int) -> BoardRow:
    ready = log2_comb(n_items, survivors)
    birth = survivors * math.log2(passes)
    order = 0.0
    return BoardRow(
        name="sparse ready + birth labels",
        n_items=n_items,
        survivors=survivors,
        q_space=n_items,
        passes=passes,
        hidden_ready_bits=ready,
        hidden_birth_bits=birth,
        hidden_order_bits=order,
        visible_occupancy_bits=log2_comb(n_items, survivors),
        visible_ordered_bits=log2_perm(n_items, survivors),
        exception_bits=0.0,
        supply_loss_bits=0.0,
        reading="occupancy can encode ready subset but not birth labels unless Q carries more state",
    )


def expanded_birth_board_row(n_items: int, survivors: int, passes: int) -> BoardRow:
    q_space = n_items * passes
    ready = log2_comb(n_items, survivors)
    birth = survivors * math.log2(passes)
    return BoardRow(
        name="expanded board encodes birth",
        n_items=n_items,
        survivors=survivors,
        q_space=q_space,
        passes=passes,
        hidden_ready_bits=ready,
        hidden_birth_bits=birth,
        hidden_order_bits=0.0,
        visible_occupancy_bits=log2_comb(q_space, survivors),
        visible_ordered_bits=log2_perm(q_space, survivors),
        exception_bits=0.0,
        supply_loss_bits=0.0,
        reading="visible coordinates have enough capacity, but that coordinate entropy is stored final state",
    )


def orderless_row(n_items: int, survivors: int, passes: int) -> BoardRow:
    order = log2_factorial(survivors)
    return BoardRow(
        name="orderless/confluent bag",
        n_items=n_items,
        survivors=survivors,
        q_space=survivors,
        passes=passes,
        hidden_ready_bits=0.0,
        hidden_birth_bits=0.0,
        hidden_order_bits=order,
        visible_occupancy_bits=0.0,
        visible_ordered_bits=order,
        exception_bits=0.0,
        supply_loss_bits=0.0,
        reading="bag decode is stateless only if original order is irrelevant or order bits are paid",
    )


def near_total_exception_row(n_items: int, exceptions: int, passes: int) -> BoardRow:
    survivors = n_items - exceptions
    exception_bits = log2_comb(n_items, exceptions) + exceptions * math.log2(max(1, passes - 1))
    return BoardRow(
        name="near-total exceptions",
        n_items=n_items,
        survivors=survivors,
        q_space=n_items,
        passes=passes,
        hidden_ready_bits=0.0,
        hidden_birth_bits=0.0,
        hidden_order_bits=0.0,
        visible_occupancy_bits=0.0,
        visible_ordered_bits=0.0,
        exception_bits=exception_bits,
        supply_loss_bits=0.0,
        reading="cheap only when exception count is tiny; otherwise subset/pass ledger returns",
    )


def public_lane_row(n_items: int, survivors: int, passes: int, active_fraction: float, choices: int) -> BoardRow:
    hit_fraction = 1.0 - (1.0 - active_fraction) ** choices
    supply_loss = -survivors * math.log2(hit_fraction)
    active_slots = max(survivors, int(round(n_items * active_fraction)))
    return BoardRow(
        name=f"public lane r={active_fraction},d={choices}",
        n_items=n_items,
        survivors=survivors,
        q_space=active_slots,
        passes=passes,
        hidden_ready_bits=0.0,
        hidden_birth_bits=0.0,
        hidden_order_bits=0.0,
        visible_occupancy_bits=log2_comb(active_slots, survivors),
        visible_ordered_bits=log2_perm(active_slots, survivors),
        exception_bits=0.0,
        supply_loss_bits=supply_loss,
        reading="decoder gets public placement; encoder pays in match supply",
    )


def rows() -> list[BoardRow]:
    n_items = 12
    survivors = 4
    passes = 8
    return [
        sparse_ready_row(n_items, survivors, passes),
        expanded_birth_board_row(n_items, survivors, passes),
        orderless_row(n_items, survivors, passes),
        near_total_exception_row(n_items, exceptions=1, passes=passes),
        near_total_exception_row(n_items, exceptions=2, passes=passes),
        public_lane_row(n_items, survivors, passes, active_fraction=0.25, choices=1),
        public_lane_row(n_items, survivors, passes, active_fraction=0.25, choices=4),
        public_lane_row(n_items, survivors, passes, active_fraction=0.50, choices=4),
    ]


def print_board_rows() -> None:
    print("== final-board entropy rows ==")
    print(
        f"{'mechanism':<30} {'hidden':>9} {'occ vis':>9} {'ord vis':>9} "
        f"{'exceptions':>11} {'supply':>9} {'occ margin':>10} {'ord margin':>10}"
    )
    for row in rows():
        print(
            f"{row.name:<30} {row.hidden_total_bits:9.3f} "
            f"{row.visible_occupancy_bits:9.3f} {row.visible_ordered_bits:9.3f} "
            f"{row.exception_bits:11.3f} {row.supply_loss_bits:9.3f} "
            f"{row.occupancy_margin_bits:10.3f} {row.ordered_margin_bits:10.3f}"
        )
    print()


def print_details() -> None:
    print("== row readings ==")
    for row in rows():
        print(f"{row.name}: {row.reading}")
    print()


def print_asymptotic_rules() -> None:
    print("== asymptotic rules ==")
    print("1. Sparse content-selected readiness costs log2 C(N,R) unless the")
    print("   selected set is public or physically represented in the output.")
    print("2. Birth labels cost R log2 P unless pass counts/lanes are fixed public")
    print("   invariants; fixed lanes then pay match-supply loss.")
    print("3. Orderless/confluent decode removes sequencing only for a bag source;")
    print("   arbitrary streams still owe order or linear-extension entropy.")
    print("4. Final boards are allowed. Their cost is log2(valid visible states).")
    print("   If valid states are numerous enough to encode arbitrary histories,")
    print("   that entropy is stored in the final board. If they are few, capacity")
    print("   is low and cannot carry arbitrary birth/open facts.")
    print("5. Total-cover remains special: hidden open/carry bits are zero because")
    print("   every record opens. The remaining gate is witness/public-Q economics.")


def main() -> None:
    print_board_rows()
    print_details()
    print_asymptotic_rules()


if __name__ == "__main__":
    main()
