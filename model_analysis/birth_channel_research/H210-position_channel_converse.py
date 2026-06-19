#!/usr/bin/env python3
"""H210 - position/final-board channel converse.

Position, egg-carton, lane, and modular-board ideas are useful decode geometry:
they can make a salt/phase/order visible to a stateless decoder.  This kernel
prices that visibility as final-state arrangement entropy or as match-supply
thinning.

The model is deliberately content-blind.  It does not charge sparse open/carry
inside total-cover.  It asks the narrower question: if final positions tell the
decoder pass/salt labels for R surviving records on a board of Q positions, how
many bits did the final arrangement make visible, and can that be below the
per-match savings budget?
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass


def fmt(value: float) -> str:
    if math.isinf(value):
        return "inf" if value > 0.0 else "-inf"
    if math.isnan(value):
        return "nan"
    if value == 0.0:
        return "0"
    if abs(value) >= 10_000.0 or abs(value) < 0.0001:
        return f"{value:.3e}"
    return f"{value:.6f}"


def log2_factorial(n: int) -> float:
    if n < 0:
        raise ValueError("factorial input must be non-negative")
    return math.lgamma(n + 1) / math.log(2.0)


def log2_choose(n: int, k: int) -> float:
    if k < 0 or k > n:
        return -math.inf
    return log2_factorial(n) - log2_factorial(k) - log2_factorial(n - k)


def log2_falling(n: int, k: int) -> float:
    if k < 0 or k > n:
        return -math.inf
    return log2_factorial(n) - log2_factorial(n - k)


def log2_sum(values: list[float]) -> float:
    finite = [value for value in values if not math.isinf(value)]
    if not finite:
        return -math.inf
    m = max(finite)
    return m + math.log2(sum(2.0 ** (value - m) for value in finite))


def equal_counts(total: int, bins: int) -> list[int]:
    base, rem = divmod(total, bins)
    return [base + (1 if i < rem else 0) for i in range(bins)]


def equal_lane_capacity(total: int, bins: int) -> list[int]:
    return equal_counts(total, bins)


def fixed_lane_arrangements(records: int, positions: int, passes: int) -> float:
    q_counts = equal_lane_capacity(positions, passes)
    r_counts = equal_counts(records, passes)
    if any(r > q for r, q in zip(r_counts, q_counts)):
        return -math.inf
    return sum(log2_choose(q, r) for q, r in zip(q_counts, r_counts))


def variable_lane_arrangements(records: int, positions: int, passes: int) -> float:
    """Exact log2 sum over pass-lane counts.

    Vandermonde collapses this to log2 C(Q,R) when lanes partition Q and counts
    vary freely.  That identity is the point: variable lane counts do not add a
    free birth ledger; they are just ordinary occupancy arrangements.
    """

    _ = passes
    return log2_choose(positions, records)


def birth_label_bits(records: int, passes: int) -> float:
    return records * math.log2(passes)


def fixed_count_birth_bits(records: int, passes: int) -> float:
    counts = equal_counts(records, passes)
    return log2_factorial(records) - sum(log2_factorial(count) for count in counts)


def max_public_passes_for_budget(records: int, positions: int, budget_per_record: float) -> int:
    """Largest P whose uniform birth labels fit inside charged occupancy bits.

    This is not a free construction: the occupancy bits are still paid.  It is a
    finite-capacity diagnostic for dense final boards.
    """

    occ_bits = log2_choose(positions, records)
    if records <= 0:
        return 1
    visible_budget = min(occ_bits, records * budget_per_record)
    return max(1, int(2.0 ** (visible_budget / records)))


@dataclass(frozen=True)
class Row:
    records: int
    positions: int
    passes: int
    density: float
    occ_bits: float
    ordered_bits: float
    fixed_lane_bits: float
    variable_lane_bits: float
    birth_bits: float
    fixed_birth_bits: float
    occ_per_record: float
    ordered_per_record: float
    fixed_lane_per_record: float
    birth_per_record: float
    residual_after_occ: float
    lane_supply_per_record: float
    net_if_occ_pays_budget: float
    net_if_lane_thins_budget: float
    max_p_under_budget: int


def row(records: int, positions: int, passes: int, savings_budget: float) -> Row:
    if records <= 0 or positions <= 0 or passes <= 0:
        raise ValueError("records, positions, passes must be positive")
    if records > positions:
        raise ValueError("records cannot exceed positions")
    occ = log2_choose(positions, records)
    ordered = log2_falling(positions, records)
    fixed_lane = fixed_lane_arrangements(records, positions, passes)
    variable_lane = variable_lane_arrangements(records, positions, passes)
    birth = birth_label_bits(records, passes)
    fixed_birth = fixed_count_birth_bits(records, passes)
    residual = max(0.0, birth - occ)
    lane_supply = math.log2(passes)
    return Row(
        records=records,
        positions=positions,
        passes=passes,
        density=records / positions,
        occ_bits=occ,
        ordered_bits=ordered,
        fixed_lane_bits=fixed_lane,
        variable_lane_bits=variable_lane,
        birth_bits=birth,
        fixed_birth_bits=fixed_birth,
        occ_per_record=occ / records,
        ordered_per_record=ordered / records,
        fixed_lane_per_record=fixed_lane / records if math.isfinite(fixed_lane) else math.inf,
        birth_per_record=birth / records,
        residual_after_occ=residual,
        lane_supply_per_record=lane_supply,
        net_if_occ_pays_budget=savings_budget - (occ / records),
        net_if_lane_thins_budget=savings_budget - lane_supply,
        max_p_under_budget=max_public_passes_for_budget(records, positions, savings_budget),
    )


def print_rows(args: argparse.Namespace) -> None:
    densities = [float(value) for value in args.density.split(",")]
    passes_list = [int(value) for value in args.passes_list.split(",")]
    print("== H210 position / final-board channel converse ==")
    print("Arrangement bits are visible to the decoder, but they are paid end-state entropy.")
    print(
        f"{'R':>5} {'Q':>6} {'rho':>7} {'P':>5} {'occ/R':>9} {'ord/R':>9} "
        f"{'lane/R':>9} {'birth/R':>9} {'resid':>9} {'netOcc':>9} "
        f"{'netLane':>9} {'maxP@bud':>9}"
    )
    rows: list[Row] = []
    for density in densities:
        positions = max(args.records, int(round(args.records / density)))
        for passes in passes_list:
            rows.append(row(args.records, positions, passes, args.savings_budget))
    rows.sort(key=lambda item: (item.density, item.passes))
    for item in rows:
        print(
            f"{item.records:5d} {item.positions:6d} {fmt(item.density):>7} "
            f"{item.passes:5d} {fmt(item.occ_per_record):>9} "
            f"{fmt(item.ordered_per_record):>9} {fmt(item.fixed_lane_per_record):>9} "
            f"{fmt(item.birth_per_record):>9} {fmt(item.residual_after_occ):>9} "
            f"{fmt(item.net_if_occ_pays_budget):>9} {fmt(item.net_if_lane_thins_budget):>9} "
            f"{item.max_p_under_budget:9d}"
        )


def print_exact_case(args: argparse.Namespace) -> None:
    item = row(args.records, args.positions, args.pass_count, args.savings_budget)
    print()
    print("== exact selected case ==")
    print(f"R={item.records} Q={item.positions} P={item.passes} rho={fmt(item.density)}")
    print(f"unordered occupancy bits     log2 C(Q,R)   = {fmt(item.occ_bits)}")
    print(f"ordered positions bits       log2 (Q)_R    = {fmt(item.ordered_bits)}")
    print(f"fixed equal pass lanes       sum log C     = {fmt(item.fixed_lane_bits)}")
    print(f"variable lane counts         log sum       = {fmt(item.variable_lane_bits)}")
    print(f"independent birth labels     R log2 P      = {fmt(item.birth_bits)}")
    print(f"balanced birth labels        log multinom  = {fmt(item.fixed_birth_bits)}")
    print(f"residual birth after occ cap                = {fmt(item.residual_after_occ)}")


def print_theorem() -> None:
    print()
    print("== theorem ==")
    print("If pass/salt/order is derived only from public state and final positions,")
    print("then either it is public deterministic and carries no adaptive bits, it")
    print("is enforced by restricting eligible matches and pays supply loss, or it")
    print("is encoded in the final arrangement.  The arrangement capacity is at most")
    print("log2 of the valid final states, so dense boards can amortize a finite")
    print("boundary but cannot create a free many-pass birth channel.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", type=int, default=1000)
    parser.add_argument("--positions", type=int, default=2000)
    parser.add_argument("--pass-count", type=int, default=16)
    parser.add_argument("--passes-list", default="2,4,16,64")
    parser.add_argument("--density", default="0.9,0.5,0.1")
    parser.add_argument("--savings-budget", type=float, default=2.0)
    args = parser.parse_args()

    print_rows(args)
    print_exact_case(args)
    print_theorem()


if __name__ == "__main__":
    main()
