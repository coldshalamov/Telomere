#!/usr/bin/env python3
"""H93 - paid extended-arity Lotus K/D witness Kraft sweep.

H92 found collective/all-description crossings in K>5 rows, but those rows use
H74's cheap extended-arity toy cost:

    ceil(log2(K)) + payload_width

That omits the J3D1 Lotus width metadata. H93 reruns the same finite sweep with
the paid extended-arity cost used by `total_cover_lotus_crossover.py`:

    K<=5: exact V1 record_cost_for_payload_width(arity, width)
    K>5:  ceil(log2(K)) + j3d1_cost_for_payload_width(width)

This tests whether the higher-arity/deeper-search crossing survives honest
witness metadata.
"""

from __future__ import annotations

import importlib.util
import math
import random
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

H74_PATH = Path(__file__).resolve().with_name("H74-exact_latent_q_kernel.py")
_h74_spec = importlib.util.spec_from_file_location("h74_exact_latent_q_kernel", H74_PATH)
if _h74_spec is None or _h74_spec.loader is None:
    raise RuntimeError("could not load H74 exact latent Q kernel")
_h74 = importlib.util.module_from_spec(_h74_spec)
sys.modules[_h74_spec.name] = _h74
_h74_spec.loader.exec_module(_h74)

from model_analysis.proof_kernel.costs import (  # noqa: E402
    j3d1_cost_for_payload_width,
    record_cost_for_payload_width,
)
from total_cover_lotus_crossover import lotus_payload_width_from_rank  # noqa: E402


@dataclass(frozen=True)
class SweepRow:
    max_arity: int
    depth_bits: int
    selected_z: float
    collective_z: float
    selected_log2_z: float
    collective_log2_z: float
    v1_exact: bool


def fixed_arity_bits(max_arity: int) -> int:
    if max_arity <= 2:
        return 1
    return math.ceil(math.log2(max_arity))


def paid_record_cost(max_arity: int, arity: int, payload_width: int) -> int:
    if arity <= 5:
        return record_cost_for_payload_width(arity, payload_width)
    return fixed_arity_bits(max_arity) + j3d1_cost_for_payload_width(payload_width)


def build_paid_edge_weights(
    block_bits: int,
    max_arity: int,
    depth_bits: int,
    seed: int,
) -> tuple[list[list[float]], list[list[float]]]:
    rng = random.Random(seed)
    total_weights: list[list[float]] = [[]]
    max_weights: list[list[float]] = [[]]
    seed_count = 1 << depth_bits
    for arity in range(1, max_arity + 1):
        value_count = 1 << (arity * block_bits)
        weights = [0.0] * value_count
        maxes = [0.0] * value_count
        for rank in range(1, seed_count + 1):
            payload_width = lotus_payload_width_from_rank(rank)
            cost = paid_record_cost(max_arity, arity, payload_width)
            weight = 2.0 ** (-cost)
            value = rng.randrange(value_count)
            weights[value] += weight
            maxes[value] = max(maxes[value], weight)
        total_weights.append(weights)
        max_weights.append(maxes)
    return total_weights, max_weights


def masses_for(
    block_bits: int,
    atoms: int,
    max_arity: int,
    depth_bits: int,
    seed: int,
) -> tuple[float, float]:
    edge_weights, edge_maxes = build_paid_edge_weights(block_bits, max_arity, depth_bits, seed)
    total_mass = 0.0
    best_mass = 0.0
    for word in range(1 << (block_bits * atoms)):
        total, best = _h74.dp_mass_for_word(
            word,
            atoms,
            block_bits,
            max_arity,
            edge_weights,
            edge_maxes,
        )
        total_mass += total
        best_mass += best
    return best_mass, total_mass


def run_sweep() -> list[SweepRow]:
    block_bits = 1
    atoms = 12
    rows: list[SweepRow] = []
    for max_arity in (2, 4, 5, 6, 8, 12):
        for depth_bits in (4, 6, 8, 10, 12):
            selected_z, collective_z = masses_for(
                block_bits,
                atoms,
                max_arity,
                depth_bits,
                seed=92000 + max_arity * 100 + depth_bits,
            )
            rows.append(
                SweepRow(
                    max_arity=max_arity,
                    depth_bits=depth_bits,
                    selected_z=selected_z,
                    collective_z=collective_z,
                    selected_log2_z=math.log2(selected_z) if selected_z > 0.0 else float("-inf"),
                    collective_log2_z=math.log2(collective_z) if collective_z > 0.0 else float("-inf"),
                    v1_exact=max_arity <= 5,
                )
            )
    return rows


def print_rows(rows: list[SweepRow]) -> None:
    print("== paid extended-arity Lotus K/D sweep ==")
    print("B=1, N=12. K<=5 exact V1; K>5 fixed arity bits + J3D1 seed field.")
    print(f"{'K':>3} {'D':>3} {'mode':>8} {'Z_best':>11} {'log2 best':>10} {'Z_total':>11} {'log2 total':>11}")
    for row in rows:
        print(
            f"{row.max_arity:3d} {row.depth_bits:3d} "
            f"{'V1' if row.v1_exact else 'paid-ext':>8} "
            f"{row.selected_z:11.6f} {row.selected_log2_z:10.6f} "
            f"{row.collective_z:11.6f} {row.collective_log2_z:11.6f}"
        )
    print()


def print_frontier(rows: list[SweepRow]) -> None:
    best_selected = max(rows, key=lambda row: row.selected_log2_z)
    best_collective = max(rows, key=lambda row: row.collective_log2_z)
    crossings = [row for row in rows if row.selected_z >= 1.0 or row.collective_z >= 1.0]
    print("== frontier ==")
    print(
        f"best selected: K={best_selected.max_arity}, D={best_selected.depth_bits}, "
        f"log2 Z={best_selected.selected_log2_z:.6f}, Z={best_selected.selected_z:.6f}"
    )
    print(
        f"best collective: K={best_collective.max_arity}, D={best_collective.depth_bits}, "
        f"log2 Z={best_collective.collective_log2_z:.6f}, Z={best_collective.collective_z:.6f}"
    )
    if crossings:
        print("crossings:")
        for row in crossings:
            print(
                f"  K={row.max_arity}, D={row.depth_bits}, "
                f"selected log2Z={row.selected_log2_z:.6f}, "
                f"collective log2Z={row.collective_log2_z:.6f}"
            )
    else:
        print("crossings: none")
    print()


def print_reading() -> None:
    print("== reading ==")
    print(
        "If H92 crosses disappear here, they were witness-width/accounting "
        "artifacts. If paid-ext collective rows cross, the next obligation is "
        "to turn collective Q mass into a stateless parseable codec and show "
        "recursive retention with uniform controls."
    )


def main() -> None:
    rows = run_sweep()
    print_rows(rows)
    print_frontier(rows)
    print_reading()


if __name__ == "__main__":
    main()
