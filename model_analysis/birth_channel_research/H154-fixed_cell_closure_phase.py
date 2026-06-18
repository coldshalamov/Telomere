#!/usr/bin/env python3
"""H154 - fixed-cell closure phase.

This tests the cleanest way to make recursive parsing stateless:

    every output unit is one fixed-size cell;
    every cell is a record;
    the next pass sees the same cell grammar.

The decoder never needs open/carry/birth metadata and closure density is 1 for
streams whose length is a whole number of cells. The price is that a C-bit cell
must contain both arity and seed witness:

    [fixed arity bits][seed bits]

So the seed space per record is small. For a record that expands to `a` input
cells, exact-match probability under the uniform hash law is:

    p_a = 1 - (1 - 2^(-a*C))^(2^W)

where W=C-A and A=ceil(log2 K). H154 combines the analytic coverage pressure
with small adversarial simulations of the full-cover interval DP.
"""

from __future__ import annotations

import argparse
import math
import random
from dataclasses import dataclass
from statistics import mean


@dataclass(frozen=True)
class FixedCellRow:
    cell_bits: int
    max_arity: int
    arity_bits: int
    seed_bits: int
    lambda_cover: float
    approx_cell_touched: float
    expected_untouched_cells: float
    expected_edges_per_cell: float
    trials: int
    success_fraction: float
    mean_records_on_success: float
    mean_gain_bits_per_cell_on_success: float
    unconditional_gain_bits_per_cell: float


def fixed_arity_bits(max_arity: int) -> int:
    if max_arity <= 1:
        return 0
    return math.ceil(math.log2(max_arity))


def match_probability(cell_bits: int, seed_bits: int, arity: int) -> float:
    if seed_bits < 0:
        return 0.0
    target_bits = arity * cell_bits
    if target_bits > 1024:
        # In the tiny probabilities used here, this is exact enough and avoids
        # underflow in (1 - eps)^N.
        return min(1.0, 2.0 ** (seed_bits - target_bits))
    miss_one = 1.0 - 2.0 ** (-target_bits)
    seed_count = 1 << seed_bits
    return 1.0 - miss_one ** seed_count


def probabilities(cell_bits: int, max_arity: int, seed_bits: int) -> list[float]:
    return [
        0.0,
        *[
            match_probability(cell_bits, seed_bits, arity)
            for arity in range(1, max_arity + 1)
        ],
    ]


def simulated_trial(
    cells: int,
    max_arity: int,
    probs: list[float],
    rng: random.Random,
) -> int | None:
    inf = cells + 1
    dp = [inf] * (cells + 1)
    dp[0] = 0
    for start in range(cells):
        if dp[start] >= inf:
            continue
        for arity in range(1, min(max_arity, cells - start) + 1):
            if rng.random() < probs[arity]:
                end = start + arity
                if dp[start] + 1 < dp[end]:
                    dp[end] = dp[start] + 1
    return None if dp[cells] >= inf else dp[cells]


def row_for(
    cell_bits: int,
    max_arity: int,
    cells: int,
    trials: int,
    seed: int,
) -> FixedCellRow:
    arity_bits = fixed_arity_bits(max_arity)
    seed_bits = cell_bits - arity_bits
    probs = probabilities(cell_bits, max_arity, seed_bits)
    lambda_cover = sum(arity * probs[arity] for arity in range(1, max_arity + 1))
    approx_touched = 1.0 - math.exp(-lambda_cover)
    expected_edges = sum(probs[arity] for arity in range(1, max_arity + 1))

    rng = random.Random(seed + cell_bits * 1009 + max_arity * 9176)
    successes: list[int] = []
    for _ in range(trials):
        records = simulated_trial(cells, max_arity, probs, rng)
        if records is not None:
            successes.append(records)

    success_fraction = len(successes) / trials
    if successes:
        mean_records = mean(float(value) for value in successes)
        gain_bits = (cells - mean_records) * cell_bits / cells
    else:
        mean_records = float("inf")
        gain_bits = float("-inf")

    # Failed covers need a raw escape outside the fixed-cell grammar. The
    # unconditional line treats each failure as no compression, which is a
    # generous lower bill; a real escape marker would be worse.
    unconditional = success_fraction * max(gain_bits, 0.0)
    return FixedCellRow(
        cell_bits=cell_bits,
        max_arity=max_arity,
        arity_bits=arity_bits,
        seed_bits=seed_bits,
        lambda_cover=lambda_cover,
        approx_cell_touched=approx_touched,
        expected_untouched_cells=cells * (1.0 - approx_touched),
        expected_edges_per_cell=expected_edges,
        trials=trials,
        success_fraction=success_fraction,
        mean_records_on_success=mean_records,
        mean_gain_bits_per_cell_on_success=gain_bits,
        unconditional_gain_bits_per_cell=unconditional,
    )


def fmt(value: float) -> str:
    if value == float("inf"):
        return "inf"
    if value == float("-inf"):
        return "-inf"
    if abs(value) >= 1000.0 or (0.0 < abs(value) < 0.0001):
        return f"{value:.3e}"
    return f"{value:.6f}"


def print_rows(rows: list[FixedCellRow]) -> None:
    print("== fixed-cell closure phase ==")
    print("Every output cell is parseable; no birth/open/closure metadata is charged.")
    print(
        f"{'C':>3} {'K':>4} {'A':>3} {'W':>3} {'lambda':>10} "
        f"{'touch':>9} {'uncovered':>10} {'edges/cell':>10} "
        f"{'succ':>8} {'records':>9} {'gain|succ':>10} {'gain raw0':>10}"
    )
    for row in rows:
        print(
            f"{row.cell_bits:3d} {row.max_arity:4d} {row.arity_bits:3d} "
            f"{row.seed_bits:3d} {fmt(row.lambda_cover):>10} "
            f"{fmt(row.approx_cell_touched):>9} "
            f"{fmt(row.expected_untouched_cells):>10} "
            f"{fmt(row.expected_edges_per_cell):>10} "
            f"{fmt(row.success_fraction):>8} "
            f"{fmt(row.mean_records_on_success):>9} "
            f"{fmt(row.mean_gain_bits_per_cell_on_success):>10} "
            f"{fmt(row.unconditional_gain_bits_per_cell):>10}"
        )
    print()


def print_reading(rows: list[FixedCellRow]) -> None:
    print("== reading ==")
    viable = [row for row in rows if row.success_fraction > 0.0]
    if viable:
        best = max(viable, key=lambda row: row.unconditional_gain_bits_per_cell)
        print(
            f"Best simulated row has success {best.success_fraction:.6f} and "
            f"generous raw0 gain {fmt(best.unconditional_gain_bits_per_cell)} "
            f"bits/cell at C={best.cell_bits},K={best.max_arity}."
        )
    else:
        best = max(rows, key=lambda row: row.lambda_cover)
        print(
            "No full-cover successes appeared in the simulated rows. "
            f"Highest analytic lambda was {fmt(best.lambda_cover)} at "
            f"C={best.cell_bits},K={best.max_arity}."
        )
    print(
        "Closure can be made free by fixed cells, but then each record has only "
        "C-ceil(log2 K) seed bits. The per-cell coverage pressure is dominated "
        "by arity-1 probability about 2^-A, so high K makes closure parseable "
        "while starving the match rate."
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cells", type=int, default=128)
    parser.add_argument("--trials", type=int, default=256)
    parser.add_argument("--seed", type=int, default=154154)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows: list[FixedCellRow] = []
    for cell_bits in (4, 6, 8, 12, 24):
        for max_arity in (5, 8, 16, 32, 64, 128):
            if fixed_arity_bits(max_arity) <= cell_bits:
                rows.append(
                    row_for(
                        cell_bits=cell_bits,
                        max_arity=max_arity,
                        cells=args.cells,
                        trials=args.trials,
                        seed=args.seed,
                    )
                )
    print_rows(rows)
    print_reading(rows)


if __name__ == "__main__":
    main()
