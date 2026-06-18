#!/usr/bin/env python3
"""H94 - normalized rank/record witness coding sweep.

H92 crossed only when a seed rank of Lotus payload width w cost exactly w bits.
That is not a prefix-safe per-record witness code: each width class contributes
about one full Kraft unit, so the width-class multiplicity has to be paid.

H94 tests honest custom witness modes between H92 and H93:

* h92_lower:
    K<=5 exact V1; K>5 fixed_arity_bits + payload_width.
    Lower bound only; new high-arity seed-rank widths are not normalized.

* custom_rank:
    fixed_arity_bits + (-log2 p_rank)
    where p_rank is proportional to 2^-payload_width over the public frontier.

* custom_record:
    -log2 p(arity, rank)
    where p is proportional to 2^-fixed_arity_bits * 2^-payload_width over all
    legal arity/rank symbols. This also reuses unused arity code space.

* paid_lotus:
    K<=5 exact V1; K>5 fixed arity bits + J3D1(payload_width).

All rows are exact finite-domain Kraft masses over B=1,N=12. Positive log2 Z
is only a source-shaped public-law opening; roughly-all uniform recursion still
has to pass the H90/H60 gates.
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
class ModeRow:
    mode: str
    max_arity: int
    depth_bits: int
    selected_z: float
    collective_z: float
    selected_log2_z: float
    collective_log2_z: float
    rank_mass: float
    record_mass: float


def fixed_arity_bits(max_arity: int) -> int:
    if max_arity <= 2:
        return 1
    return math.ceil(math.log2(max_arity))


def rank_base_weights(depth_bits: int) -> list[tuple[int, int, float]]:
    rows: list[tuple[int, int, float]] = []
    for rank in range(1, (1 << depth_bits) + 1):
        payload_width = lotus_payload_width_from_rank(rank)
        rows.append((rank, payload_width, 2.0 ** (-payload_width)))
    return rows


def arity_base_mass(max_arity: int) -> float:
    return sum(2.0 ** (-fixed_arity_bits(max_arity)) for _ in range(1, max_arity + 1))


def paid_lotus_cost(max_arity: int, arity: int, payload_width: int) -> int:
    if arity <= 5:
        return record_cost_for_payload_width(arity, payload_width)
    return fixed_arity_bits(max_arity) + j3d1_cost_for_payload_width(payload_width)


def record_weight(
    mode: str,
    max_arity: int,
    arity: int,
    payload_width: int,
    rank_mass: float,
    record_mass: float,
) -> float:
    arity_weight = 2.0 ** (-fixed_arity_bits(max_arity))
    rank_weight = 2.0 ** (-payload_width)
    if mode == "h92_lower":
        if arity <= 5:
            return 2.0 ** (-record_cost_for_payload_width(arity, payload_width))
        return arity_weight * rank_weight
    if mode == "custom_rank":
        return arity_weight * rank_weight / rank_mass
    if mode == "custom_record":
        return arity_weight * rank_weight / record_mass
    if mode == "paid_lotus":
        return 2.0 ** (-paid_lotus_cost(max_arity, arity, payload_width))
    raise ValueError(mode)


def build_edge_weights(
    mode: str,
    block_bits: int,
    max_arity: int,
    depth_bits: int,
    seed: int,
) -> tuple[list[list[float]], list[list[float]], float, float]:
    rng = random.Random(seed)
    rank_rows = rank_base_weights(depth_bits)
    rank_mass = sum(weight for _, _, weight in rank_rows)
    record_mass = arity_base_mass(max_arity) * rank_mass
    total_weights: list[list[float]] = [[]]
    max_weights: list[list[float]] = [[]]
    for arity in range(1, max_arity + 1):
        value_count = 1 << (arity * block_bits)
        weights = [0.0] * value_count
        maxes = [0.0] * value_count
        for _, payload_width, _ in rank_rows:
            weight = record_weight(mode, max_arity, arity, payload_width, rank_mass, record_mass)
            value = rng.randrange(value_count)
            weights[value] += weight
            maxes[value] = max(maxes[value], weight)
        total_weights.append(weights)
        max_weights.append(maxes)
    return total_weights, max_weights, rank_mass, record_mass


def masses_for(
    mode: str,
    block_bits: int,
    atoms: int,
    max_arity: int,
    depth_bits: int,
    seed: int,
) -> ModeRow:
    edge_weights, edge_maxes, rank_mass, record_mass = build_edge_weights(
        mode,
        block_bits,
        max_arity,
        depth_bits,
        seed,
    )
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
    return ModeRow(
        mode=mode,
        max_arity=max_arity,
        depth_bits=depth_bits,
        selected_z=best_mass,
        collective_z=total_mass,
        selected_log2_z=math.log2(best_mass) if best_mass > 0.0 else float("-inf"),
        collective_log2_z=math.log2(total_mass) if total_mass > 0.0 else float("-inf"),
        rank_mass=rank_mass,
        record_mass=record_mass,
    )


def run_sweep() -> list[ModeRow]:
    rows: list[ModeRow] = []
    for mode in ("h92_lower", "custom_rank", "custom_record", "paid_lotus"):
        for max_arity in (6, 8, 12):
            for depth_bits in (8, 10, 12):
                rows.append(
                    masses_for(
                        mode,
                        block_bits=1,
                        atoms=12,
                        max_arity=max_arity,
                        depth_bits=depth_bits,
                        seed=92000 + max_arity * 100 + depth_bits,
                    )
                )
    return rows


def print_rows(rows: list[ModeRow]) -> None:
    print("== normalized rank/record witness sweep ==")
    print("B=1,N=12. h92_lower is H92-style lower bound; paid_lotus is H93-style accounting.")
    print(
        f"{'mode':<13} {'K':>3} {'D':>3} {'rankZ':>8} {'recordZ':>8} "
        f"{'log2 best':>10} {'log2 total':>11} {'Z_total':>10}"
    )
    for row in rows:
        print(
            f"{row.mode:<13} {row.max_arity:3d} {row.depth_bits:3d} "
            f"{row.rank_mass:8.3f} {row.record_mass:8.3f} "
            f"{row.selected_log2_z:10.6f} {row.collective_log2_z:11.6f} "
            f"{row.collective_z:10.6f}"
        )
    print()


def print_frontier(rows: list[ModeRow]) -> None:
    print("== frontier by mode ==")
    for mode in ("h92_lower", "custom_rank", "custom_record", "paid_lotus"):
        mode_rows = [row for row in rows if row.mode == mode]
        best = max(mode_rows, key=lambda row: row.collective_log2_z)
        crossings = [row for row in mode_rows if row.collective_z >= 1.0 or row.selected_z >= 1.0]
        print(
            f"{mode}: best collective K={best.max_arity},D={best.depth_bits}, "
            f"log2Z={best.collective_log2_z:.6f}, crossings={len(crossings)}"
        )
    print()


def print_reading() -> None:
    print("== reading ==")
    print(
        "The difference between h92_lower and custom_rank is the "
        "seed-width multiplicity bill for a custom rank code. custom_record also "
        "spends all unused arity code space on legal records. If crossings "
        "survive custom_record, a custom arithmetic record grammar is a real "
        "candidate. If only h92_lower "
        "crosses, the apparent win is a hidden width-class channel."
    )


def main() -> None:
    rows = run_sweep()
    print_rows(rows)
    print_frontier(rows)
    print_reading()


if __name__ == "__main__":
    main()
