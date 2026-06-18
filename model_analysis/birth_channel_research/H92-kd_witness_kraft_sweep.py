#!/usr/bin/env python3
"""H92 - K/D witness Kraft sweep.

H90-H91 show that the live target is honest witness Kraft mass. H92 tests the
obvious knob the user has emphasized: higher arity K and deeper search D.

This is an exact finite toy sweep over the same 12-bit H74/H89 word domain:

    B=1, N=12, K in {2,4,5,6,8,12}, D in {4,6,8,10,12}

Rows report the selected-best and all-description Kraft masses. For K>5 this
uses the existing H74 research extension:

    record_cost = ceil(log2(K)) + payload_width

not the current V1 arity alphabet. V1-exact rows are K<=5.

The question is not whether more search finds more local matches. It does. The
question is whether the fully paid witness family gets Z above 1.
"""

from __future__ import annotations

import importlib.util
import math
import sys
from dataclasses import dataclass
from pathlib import Path


H74_PATH = Path(__file__).resolve().with_name("H74-exact_latent_q_kernel.py")
_h74_spec = importlib.util.spec_from_file_location("h74_exact_latent_q_kernel", H74_PATH)
if _h74_spec is None or _h74_spec.loader is None:
    raise RuntimeError("could not load H74 exact latent Q kernel")
_h74 = importlib.util.module_from_spec(_h74_spec)
sys.modules[_h74_spec.name] = _h74
_h74_spec.loader.exec_module(_h74)


@dataclass(frozen=True)
class SweepRow:
    max_arity: int
    depth_bits: int
    selected_z: float
    collective_z: float
    selected_log2_z: float
    collective_log2_z: float
    selected_record_boost: float
    collective_record_boost: float
    v1_exact: bool


def masses_for(
    block_bits: int,
    atoms: int,
    max_arity: int,
    depth_bits: int,
    seed: int,
) -> tuple[float, float]:
    edge_weights, edge_maxes = _h74.build_edge_weights(block_bits, max_arity, depth_bits, seed)
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


def flat_to_record_boost(flat_gap: float, atoms: int, max_arity: int) -> float:
    """Rough lower-bound translation using the optimistic max-span record count."""

    min_records = math.ceil(atoms / max_arity)
    return flat_gap / min_records


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
            selected_log = math.log2(selected_z) if selected_z > 0.0 else float("-inf")
            collective_log = math.log2(collective_z) if collective_z > 0.0 else float("-inf")
            rows.append(
                SweepRow(
                    max_arity=max_arity,
                    depth_bits=depth_bits,
                    selected_z=selected_z,
                    collective_z=collective_z,
                    selected_log2_z=selected_log,
                    collective_log2_z=collective_log,
                    selected_record_boost=flat_to_record_boost(max(0.0, -selected_log), atoms, max_arity),
                    collective_record_boost=flat_to_record_boost(max(0.0, -collective_log), atoms, max_arity),
                    v1_exact=max_arity <= 5,
                )
            )
    return rows


def print_rows(rows: list[SweepRow]) -> None:
    print("== K/D witness Kraft sweep ==")
    print("B=1, N=12. K<=5 uses exact V1 arity costs; K>5 is H74 extended-arity toy cost.")
    print(
        f"{'K':>3} {'D':>3} {'mode':>8} {'Z_best':>11} {'log2 best':>10} "
        f"{'Z_total':>11} {'log2 total':>11} {'best rec':>9} {'total rec':>9}"
    )
    for row in rows:
        print(
            f"{row.max_arity:3d} {row.depth_bits:3d} "
            f"{'V1' if row.v1_exact else 'ext':>8} "
            f"{row.selected_z:11.6f} {row.selected_log2_z:10.6f} "
            f"{row.collective_z:11.6f} {row.collective_log2_z:11.6f} "
            f"{row.selected_record_boost:9.6f} {row.collective_record_boost:9.6f}"
        )
    print()


def print_frontier(rows: list[SweepRow]) -> None:
    best_selected = max(rows, key=lambda row: row.selected_log2_z)
    best_collective = max(rows, key=lambda row: row.collective_log2_z)
    crossings = [row for row in rows if row.selected_z >= 1.0 or row.collective_z >= 1.0]
    print("== frontier ==")
    print(
        f"best selected: K={best_selected.max_arity}, D={best_selected.depth_bits}, "
        f"log2 Z={best_selected.selected_log2_z:.6f}, "
        f"Z={best_selected.selected_z:.6f}, mode={'V1' if best_selected.v1_exact else 'ext'}"
    )
    print(
        f"best collective: K={best_collective.max_arity}, D={best_collective.depth_bits}, "
        f"log2 Z={best_collective.collective_log2_z:.6f}, "
        f"Z={best_collective.collective_z:.6f}, mode={'V1' if best_collective.v1_exact else 'ext'}"
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
        "Higher K and D can move the frontier, but the honest question is Z, not "
        "local option count. In this finite toy, any row with log2 Z < 0 still "
        "cannot be made positive by public source shaping over the same witness "
        "family. Rows with K>5 are research-extension rows, not current V1 wire "
        "format claims."
    )


def main() -> None:
    rows = run_sweep()
    print_rows(rows)
    print_frontier(rows)
    print_reading()


if __name__ == "__main__":
    main()
