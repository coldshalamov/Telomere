#!/usr/bin/env python3
"""H103 - class-local seed grammar Kraft check.

H102 says public lanes can remove the visible seed-parity tax if the witness is
a local rank inside the lane's public seed class. This file checks that claim in
the exact finite H74/H94 domain.

Three record families are compared:

* base_all:
    W-bit rank grammar over 2^W public seeds.

* visible_global_class:
    Same W-bit global grammar, but only one parity/class is accepted. This is
    the H99/H101 supply-loss model.

* local_class:
    The lane supplies the class, and W bits name 2^W local ranks inside that
    class. This should preserve the base Kraft mass; it does not add a hidden
    bit because the class is not selected by the file.
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
_h74_spec = importlib.util.spec_from_file_location("h74_exact_latent_q_kernel_for_h103", H74_PATH)
if _h74_spec is None or _h74_spec.loader is None:
    raise RuntimeError("could not load H74 exact latent Q kernel")
_h74 = importlib.util.module_from_spec(_h74_spec)
sys.modules[_h74_spec.name] = _h74
_h74_spec.loader.exec_module(_h74)

from total_cover_lotus_crossover import lotus_payload_width_from_rank  # noqa: E402


@dataclass(frozen=True)
class Row:
    family: str
    max_arity: int
    depth_bits: int
    rank_count: int
    rank_mass: float
    selected_log2_z: float
    collective_log2_z: float
    collective_delta_vs_base: float


def fixed_arity_bits(max_arity: int) -> int:
    if max_arity <= 2:
        return 1
    return math.ceil(math.log2(max_arity))


def rank_weight(rank: int) -> float:
    return 2.0 ** (-lotus_payload_width_from_rank(rank))


def arity_base_mass(max_arity: int) -> float:
    return sum(2.0 ** (-fixed_arity_bits(max_arity)) for _ in range(1, max_arity + 1))


def rank_rows(family: str, depth_bits: int, classes: int, class_id: int) -> tuple[list[tuple[int, float]], float]:
    if family == "base_all":
        rows = [(rank, rank_weight(rank)) for rank in range(1, (1 << depth_bits) + 1)]
    elif family == "visible_global_class":
        rows = [
            (rank, rank_weight(rank))
            for rank in range(1, (1 << depth_bits) + 1)
            if rank % classes == class_id
        ]
    elif family == "local_class":
        # These are local ranks inside the public class, so W bits still name
        # 2^W usable seeds. The global seed numbers would be interleaved, but
        # the witness cost and hash law are local-rank based.
        rows = [(rank, rank_weight(rank)) for rank in range(1, (1 << depth_bits) + 1)]
    else:
        raise ValueError(family)
    mass = sum(weight for _, weight in rows)
    return rows, mass


def build_weights(
    family: str,
    block_bits: int,
    max_arity: int,
    depth_bits: int,
    classes: int,
    class_id: int,
    seed: int,
) -> tuple[list[list[float]], list[list[float]], int, float]:
    rng = random.Random(seed)
    rows, mass = rank_rows(family, depth_bits, classes, class_id)
    normalizer = arity_base_mass(max_arity) * (
        sum(rank_weight(rank) for rank in range(1, (1 << depth_bits) + 1))
        if family == "visible_global_class"
        else mass
    )
    arity_weight = 2.0 ** (-fixed_arity_bits(max_arity))
    total_weights: list[list[float]] = [[]]
    max_weights: list[list[float]] = [[]]
    for arity in range(1, max_arity + 1):
        value_count = 1 << (arity * block_bits)
        totals = [0.0] * value_count
        maxes = [0.0] * value_count
        for _, weight in rows:
            record_weight = arity_weight * weight / normalizer
            value = rng.randrange(value_count)
            totals[value] += record_weight
            maxes[value] = max(maxes[value], record_weight)
        total_weights.append(totals)
        max_weights.append(maxes)
    return total_weights, max_weights, len(rows), mass


def mass_for_family(
    family: str,
    block_bits: int,
    atoms: int,
    max_arity: int,
    depth_bits: int,
    classes: int,
    class_id: int,
    seed: int,
) -> tuple[float, float, int, float]:
    edge_weights, edge_maxes, count, mass = build_weights(
        family,
        block_bits,
        max_arity,
        depth_bits,
        classes,
        class_id,
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
    return total_mass, best_mass, count, mass


def rows() -> list[Row]:
    result: list[Row] = []
    for max_arity, depth_bits in ((6, 8), (8, 10), (12, 10)):
        base_total, base_best, _, _ = mass_for_family(
            "base_all", 1, 12, max_arity, depth_bits, 2, 0, 103000 + max_arity * 100 + depth_bits
        )
        base_log = math.log2(base_total)
        for family in ("base_all", "visible_global_class", "local_class"):
            total, best, count, mass = mass_for_family(
                family,
                1,
                12,
                max_arity,
                depth_bits,
                2,
                0,
                103000 + max_arity * 100 + depth_bits,
            )
            result.append(
                Row(
                    family=family,
                    max_arity=max_arity,
                    depth_bits=depth_bits,
                    rank_count=count,
                    rank_mass=mass,
                    selected_log2_z=math.log2(best) if best > 0.0 else float("-inf"),
                    collective_log2_z=math.log2(total) if total > 0.0 else float("-inf"),
                    collective_delta_vs_base=(math.log2(total) - base_log) if total > 0.0 else float("-inf"),
                )
            )
    return result


def print_rows(result: list[Row]) -> None:
    print("== class-local Kraft check ==")
    print("Exact H74 domain: B=1,N=12. visible_global_class uses one class inside a global W-bit window.")
    print(
        f"{'family':<22} {'K':>3} {'D':>3} {'ranks':>7} {'rankZ':>9} "
        f"{'log2 best':>10} {'log2 total':>11} {'d total':>9}"
    )
    for row in result:
        print(
            f"{row.family:<22} {row.max_arity:3d} {row.depth_bits:3d} "
            f"{row.rank_count:7d} {row.rank_mass:9.3f} "
            f"{row.selected_log2_z:10.6f} {row.collective_log2_z:11.6f} "
            f"{row.collective_delta_vs_base:9.6f}"
        )
    print()


def print_reading(result: list[Row]) -> None:
    print("== reading ==")
    for max_arity, depth_bits in ((6, 8), (8, 10), (12, 10)):
        group = [row for row in result if row.max_arity == max_arity and row.depth_bits == depth_bits]
        base = next(row for row in group if row.family == "base_all")
        visible = next(row for row in group if row.family == "visible_global_class")
        local = next(row for row in group if row.family == "local_class")
        print(
            f"K={max_arity},D={depth_bits}: visible class shifts collective log2Z by "
            f"{visible.collective_delta_vs_base:.6f}; local class shifts it by "
            f"{local.collective_delta_vs_base:.6f}."
        )
    print(
        "The local-class result preserves the base Kraft mass because the public "
        "lane supplies the class and the witness indexes a full local seed "
        "window. The visible global class loses mass because the seed witness "
        "itself is doing the readiness signaling."
    )


def main() -> None:
    result = rows()
    print_rows(result)
    print_reading(result)


if __name__ == "__main__":
    main()
