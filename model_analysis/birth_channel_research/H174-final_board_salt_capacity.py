#!/usr/bin/env python3
"""H174 - final-board survivor shrink and position-salt capacity.

This reopens the final-position / egg-carton family in the user's intended
form: a large fixed or virtual board, records may move/bundle/wrap modulo, and
only final surviving records plus final positions are stored once.

The question is not whether that can decode. PCTB-style mechanics show it can.
The question is what end-state entropy is available after the final state is
priced optimally:

    unordered final occupancy:  log2 C(Q, R)
    ordered final positions:    log2 (Q)_R
    valid final arrangements:   log2 |E_valid|

If an adaptive salt/birth/open choice is hidden in the arrangement, its mutual
information with the decoder is at most log2 |E_valid|. If the arrangement is
stored, that many bits are in the compressed file. If it is public/deterministic,
the adaptive channel has zero entropy. Final boards can replace a more expensive
per-pass ledger, but they cannot create extra all-data capacity after the final
state itself is charged.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


def log2_factorial(n: int) -> float:
    return math.lgamma(n + 1) / math.log(2.0)


def log2_choose(n: int, k: int) -> float:
    if k < 0 or k > n:
        return float("-inf")
    if k == 0 or k == n:
        return 0.0
    return log2_factorial(n) - log2_factorial(k) - log2_factorial(n - k)


def log2_perm(n: int, k: int) -> float:
    if k < 0 or k > n:
        return float("-inf")
    if k == 0:
        return 0.0
    return log2_factorial(n) - log2_factorial(n - k)


def h2(p: float) -> float:
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -(p * math.log2(p) + (1.0 - p) * math.log2(1.0 - p))


def lane_supply_loss(active_fraction: float, choices: int) -> float:
    hit_fraction = 1.0 - (1.0 - active_fraction) ** choices
    if hit_fraction <= 0.0:
        return float("inf")
    return -math.log2(hit_fraction)


def yn(flag: bool) -> str:
    return "yes" if flag else "no"


@dataclass(frozen=True)
class ShrinkRow:
    q: int
    r: int
    p_passes: int

    @property
    def occ_bits(self) -> float:
        return log2_choose(self.q, self.r)

    @property
    def ordered_bits(self) -> float:
        return log2_perm(self.q, self.r)

    @property
    def occ_per_survivor(self) -> float:
        return self.occ_bits / self.r

    @property
    def ordered_per_survivor(self) -> float:
        return self.ordered_bits / self.r

    @property
    def pass_label_bits(self) -> float:
        return self.r * math.log2(self.p_passes)

    @property
    def pass_label_margin(self) -> float:
        return self.pass_label_bits - self.occ_bits


def print_sanity() -> None:
    q = 8
    r = 3
    comb = math.comb(q, r)
    perm = math.perm(q, r)
    print("== exact small-count sanity ==")
    print(f"Q={q}, R={r}")
    print(f"unordered states C(Q,R)={comb}, log2={log2_choose(q, r):.6f}")
    print(f"ordered states   (Q)_R={perm}, log2={log2_perm(q, r):.6f}")
    print()


def print_survivor_shrink_table() -> None:
    n = 1_000_000
    q = n
    p_passes = 256
    two_bit_budget = 2.0
    print("== final-position note vs survivor shrink ==")
    print(
        "Q=N=1,000,000, unordered final occupancy only. "
        "The 2-bit column is a per-survivor budget check, not a free-gain claim."
    )
    print(
        f"{'R/Q':>8} {'R':>9} {'pos/orig':>10} {'pos/R':>9} "
        f"{'2-pos/R':>9} {'<2b?':>6} {'<log2P?':>8} {'label margin':>13}"
    )
    for frac in (0.99, 0.95, 0.90, 0.75, 0.50, 0.25, 0.10, 0.03, 0.01, 0.003, 0.001):
        r = max(1, round(q * frac))
        row = ShrinkRow(q=q, r=r, p_passes=p_passes)
        print(
            f"{frac:8.3f} {r:9d} {row.occ_bits / n:10.6f} "
            f"{row.occ_per_survivor:9.3f} "
            f"{two_bit_budget - row.occ_per_survivor:9.3f} "
            f"{yn(row.occ_per_survivor < two_bit_budget):>6} "
            f"{yn(row.occ_per_survivor < math.log2(p_passes)):>8} "
            f"{row.pass_label_margin / n:13.6f}"
        )
    print()


def print_pass_label_capacity() -> None:
    n = 1_000_000
    q = n
    print("== final board as restricted birth/pass ledger ==")
    print(
        "Positive margin means C(Q,R) has fewer bits than arbitrary P-way labels, "
        "so the board is cheaper only by supporting a restricted history subset."
    )
    print(
        f"{'P':>6} {'R/Q':>7} {'pos/R':>9} {'log2P':>7} "
        f"{'can encode all?':>15} {'cheaper?':>9} {'margin/R':>9}"
    )
    for p_passes in (16, 64, 256, 4096):
        for frac in (0.50, 0.10, 0.03, 0.01, 0.003, 0.001):
            r = max(1, round(q * frac))
            row = ShrinkRow(q=q, r=r, p_passes=p_passes)
            label_per = math.log2(p_passes)
            print(
                f"{p_passes:6d} {frac:7.3f} {row.occ_per_survivor:9.3f} "
                f"{label_per:7.3f} {yn(row.occ_bits >= row.pass_label_bits):>15} "
                f"{yn(row.occ_bits < row.pass_label_bits):>9} "
                f"{row.pass_label_margin / r:9.3f}"
            )
        print()


def print_expanded_board_rows() -> None:
    n = 1_000_000
    print("== expanded Q=N*P board that directly encodes birth class ==")
    print(
        "An expanded board has enough coordinates for ready subset plus birth class, "
        "but the final coordinate note is essentially that same information."
    )
    print(
        f"{'P':>6} {'R/Q0':>7} {'C(NP,R)/R':>12} "
        f"{'ready+birth/R':>15} {'extra/R':>9}"
    )
    for p_passes in (16, 256, 4096):
        for frac in (0.50, 0.10, 0.03, 0.01):
            r = max(1, round(n * frac))
            expanded = log2_choose(n * p_passes, r)
            ready_plus_birth = log2_choose(n, r) + r * math.log2(p_passes)
            print(
                f"{p_passes:6d} {frac:7.3f} {expanded / r:12.3f} "
                f"{ready_plus_birth / r:15.3f} "
                f"{(expanded - ready_plus_birth) / r:9.3f}"
            )
        print()


def print_valid_arrangement_rows() -> None:
    q = 1_000_000
    r = 100_000
    print("== valid arrangement subset / public lane pricing ==")
    print(
        "If only a public fraction rho of cells is valid, the coordinate note uses "
        "C(rho Q,R). The match side also sees a public-lane supply loss."
    )
    print(
        f"{'rho':>6} {'valid cells':>11} {'log2 valid/R':>14} "
        f"{'d1 loss':>9} {'d4 loss':>9} {'d16 loss':>9}"
    )
    for rho in (1.0, 0.75, 0.50, 0.25, 0.10):
        valid = round(q * rho)
        if valid < r:
            cost_per = float("inf")
        else:
            cost_per = log2_choose(valid, r) / r
        print(
            f"{rho:6.2f} {valid:11d} {cost_per:14.3f} "
            f"{lane_supply_loss(rho, 1):9.3f} "
            f"{lane_supply_loss(rho, 4):9.3f} "
            f"{lane_supply_loss(rho, 16):9.3f}"
        )
    print()


def print_class_lane_rows() -> None:
    q = 1_000_000
    r = 100_000
    lanes = 8
    q_lane = q // lanes
    free_bits = log2_choose(q, r)
    cases = [
        ("free counts over all lanes", [r // lanes] * lanes, 1.0, True),
        ("balanced fixed lane counts", [r // lanes] * lanes, 1.0, False),
        ("two public active lanes", [r // 2, r // 2] + [0] * (lanes - 2), 2 / lanes, False),
        ("one public active lane", [r] + [0] * (lanes - 1), 1 / lanes, False),
    ]
    print("== public pass/lane class final-state counts ==")
    print(
        "For fixed lane counts r_p, H_final=sum_p log2 C(Q_p,r_p). "
        "If counts are not fixed, Vandermonde returns the free-count C(Q,R) row."
    )
    print(
        f"{'case':<28} {'state/R':>9} {'lost/R':>9} "
        f"{'d1 loss':>9} {'d4 loss':>9} {'reading':<32}"
    )
    for name, counts, active_fraction, is_free in cases:
        if is_free:
            state_bits = free_bits
            reading = "counts vary; same as C(Q,R)"
        else:
            state_bits = sum(log2_choose(q_lane, count) for count in counts)
            reading = "fixed public counts/classes"
        lost = (free_bits - state_bits) / r
        print(
            f"{name:<28} {state_bits / r:9.3f} {lost:9.3f} "
            f"{lane_supply_loss(active_fraction, 1):9.3f} "
            f"{lane_supply_loss(active_fraction, 4):9.3f} {reading:<32}"
        )
    print()


def print_hidden_channel_rows() -> None:
    q = 1_000_000
    salt_bits_per_survivor = 2.0
    print("== hidden-channel accounting for position-as-salt ==")
    print(
        "The maximum adaptive salt/birth information the decoder can observe from "
        "a stored final arrangement is its visible entropy. After charging the "
        "arrangement, net new capacity is never positive."
    )
    print(
        f"{'R/Q':>8} {'visible/R':>10} {'request/R':>10} "
        f"{'delivered/R':>12} {'net/R':>8} {'reading':<34}"
    )
    for frac in (0.90, 0.75, 0.50, 0.25, 0.10, 0.03, 0.01):
        r = max(1, round(q * frac))
        visible = log2_choose(q, r)
        request = r * salt_bits_per_survivor
        delivered = min(visible, request)
        net = delivered - visible
        if visible >= request:
            reading = "can carry request, costs more/equal"
        else:
            reading = "state-limited; not all salts fit"
        print(
            f"{frac:8.3f} {visible / r:10.3f} {salt_bits_per_survivor:10.3f} "
            f"{delivered / r:12.3f} {net / r:8.3f} {reading:<34}"
        )
    print()


def print_ordering_rows() -> None:
    q = 1_000_000
    print("== ordering cost if stream order is not otherwise public ==")
    print(
        f"{'R/Q':>8} {'occ/R':>9} {'log2 R!/R':>12} "
        f"{'ordered/R':>11} {'order share':>12}"
    )
    for frac in (0.50, 0.10, 0.03, 0.01, 0.003):
        r = max(1, round(q * frac))
        occ = log2_choose(q, r)
        order = log2_factorial(r)
        ordered = log2_perm(q, r)
        print(
            f"{frac:8.3f} {occ / r:9.3f} {order / r:12.3f} "
            f"{ordered / r:11.3f} {order / ordered:12.3f}"
        )
    print()


def print_verdict() -> None:
    print("== H174 verdict ==")
    print("1. Shrinking R can make the final-position note cheap per original atom.")
    print("2. Per survivor, the same note gets cheaper only when the board is dense;")
    print("   very small R is cheap per file but expensive per surviving record.")
    print("3. A final board can beat a naive R log2(P) or per-pass diary only by")
    print("   supporting a restricted set of histories, or by replacing placement")
    print("   bits that the board codec was already paying.")
    print("4. Position-as-salt is therefore a real stateless decode geometry, not a")
    print("   free capacity source: stored arrangements cost log2(valid states),")
    print("   while public deterministic arrangements have zero adaptive entropy.")
    print("5. The strongest surviving target is near-total/dense-board refresh:")
    print("   keep the state dense enough that occupancy costs <~2 bits per survivor,")
    print("   then prove the salted match gain exceeds that exact final-state bill.")


def main() -> None:
    print_sanity()
    print_survivor_shrink_table()
    print_pass_label_capacity()
    print_expanded_board_rows()
    print_valid_arrangement_rows()
    print_class_lane_rows()
    print_hidden_channel_rows()
    print_ordering_rows()
    print_verdict()


if __name__ == "__main__":
    main()
