#!/usr/bin/env python3
"""H206 - visible-population arbitrary-uniform overhead bound.

H205 is strongly positive inside its generated lineage, but arbitrary uniform
data pays the reachable-set tax.  For any visible population of M root records:

    support_bits <= M*G
    paid_bits = mode_bits + M*record_cost_for_payload_width(A,G)
    uniform_net_upper = M*G - paid_bits

This kernel sweeps exact current V1/J3D1 record costs to find the nearest miss.
"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model_analysis.proof_kernel import costs


MODE_BITS = 1


def fmt(value: float) -> str:
    if value == 0.0:
        return "0"
    if abs(value) >= 10_000.0 or abs(value) < 0.0001:
        return f"{value:.3e}"
    return f"{value:.6f}"


def parse_int_list(values: list[str], default: list[int]) -> list[int]:
    if not values:
        return default
    out: list[int] = []
    for value in values:
        out.extend(int(part) for part in value.split(",") if part)
    return out


@dataclass(frozen=True)
class Row:
    population_size: int
    arity: int
    root_bits: int
    record_bits: int
    overhead_per_root: int
    paid_bits: int
    support_bits: int
    uniform_net_upper: int
    generated_out_bits: int
    generated_inside_gain: int


def row(
    *,
    population_size: int,
    arity: int,
    root_bits: int,
    atom_bits: int,
    passes: int,
) -> Row:
    record_bits = costs.record_cost_for_payload_width(arity, root_bits)
    paid_bits = MODE_BITS + population_size * record_bits
    support_bits = population_size * root_bits
    generated_out_bits = population_size * (arity**passes) * atom_bits
    return Row(
        population_size=population_size,
        arity=arity,
        root_bits=root_bits,
        record_bits=record_bits,
        overhead_per_root=record_bits - root_bits,
        paid_bits=paid_bits,
        support_bits=support_bits,
        uniform_net_upper=support_bits - paid_bits,
        generated_out_bits=generated_out_bits,
        generated_inside_gain=generated_out_bits - paid_bits,
    )


def print_best(args: argparse.Namespace) -> None:
    populations = parse_int_list(args.population_size, [1, 2, 4, 8, 32])
    arities = parse_int_list(args.arity, [1, 2, 3, 4, 5])
    roots = parse_int_list(args.root_bits, list(range(1, 33)) + [48, 64, 96, 128, 256, 508])
    rows = [
        row(
            population_size=m,
            arity=a,
            root_bits=g,
            atom_bits=args.atom_bits,
            passes=args.passes,
        )
        for m in populations
        for a in arities
        for g in roots
        if 1 <= g <= costs.MAX_PAYLOAD_WIDTH_BITS
    ]
    rows.sort(key=lambda r: (r.uniform_net_upper, r.generated_inside_gain), reverse=True)
    print("== H206 visible-population arbitrary-uniform overhead bound ==")
    print("uniform_net_upper = M*G - (1 + M*record_cost_for_payload_width(A,G))")
    print(
        f"{'M':>3} {'A':>2} {'G':>3} {'rec':>5} {'oh/root':>7} "
        f"{'paid':>6} {'support':>7} {'uNet':>7} {'out':>10} {'gainIn':>10}"
    )
    for item in rows[: args.limit]:
        print(
            f"{item.population_size:3d} {item.arity:2d} {item.root_bits:3d} "
            f"{item.record_bits:5d} {item.overhead_per_root:7d} "
            f"{item.paid_bits:6d} {item.support_bits:7d} "
            f"{item.uniform_net_upper:7d} {item.generated_out_bits:10d} "
            f"{item.generated_inside_gain:10d}"
        )
    print()
    print("== best nontrivial high-branch rows ==")
    print("Restricting to arity 5 keeps the H198/H205 high-growth branch.")
    arity5 = [item for item in rows if item.arity == 5]
    arity5.sort(key=lambda r: (r.uniform_net_upper, r.generated_inside_gain), reverse=True)
    for item in arity5[: args.limit]:
        print(
            f"M={item.population_size} A={item.arity} G={item.root_bits} "
            f"record={item.record_bits} overhead/root={item.overhead_per_root} "
            f"uniform_net={item.uniform_net_upper} out={item.generated_out_bits} "
            f"inside_gain={item.generated_inside_gain}"
        )


def print_theorem() -> None:
    print()
    print("== theorem ==")
    print("Because record_cost_for_payload_width(A,G) > G for every legal V1/J3D1")
    print("root record, uniform_net_upper is always negative:")
    print("  uniform_net <= -mode_bits - M*(record_bits-G).")
    print("Visible-population lineage can be a strong generated codec, but not an")
    print("arbitrary-uniform crossing without an external source membership law.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--population-size", action="append", default=[])
    parser.add_argument("--arity", action="append", default=[])
    parser.add_argument("--root-bits", action="append", default=[])
    parser.add_argument("--atom-bits", type=int, default=32)
    parser.add_argument("--passes", type=int, default=6)
    parser.add_argument("--limit", type=int, default=16)
    args = parser.parse_args()

    print_best(args)
    print_theorem()


if __name__ == "__main__":
    main()
