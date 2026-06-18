#!/usr/bin/env python3
"""Phase-lane Total-Cover hybrid ledger.

H21 showed that a ready-prefix boundary is cheap, but a boundary-only sparse
stable partition hides a subset map. H22 prices the strongest public-lane
variant:

    - positions eligible to open are a public phase lane;
    - every slot in the active lane opens, so there is no hit bitmap inside it;
    - the only per-pass geometry metadata is a boundary/count;
    - the cost of restricting births to a lane is paid as match-supply loss.

This is an optimistic upper bound. It asks whether replacing sparse cover
layout entropy with deterministic lane supply loss can cross.
"""

from __future__ import annotations

import argparse
import importlib.util
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType


H4_PATH = Path(__file__).with_name("H4-cover_layout_entropy.py")


def load_h4() -> ModuleType:
    spec = importlib.util.spec_from_file_location("h4_cover_layout_entropy", H4_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load H4 kernel from {H4_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


H4 = load_h4()


@dataclass(frozen=True)
class PhaseLaneRow:
    arity: int
    passes: int
    hit_probability: float
    selected_records_per_atom: float
    optimistic_gain_per_atom: float
    cover_entropy_per_atom: float
    h4_layout_gain_per_atom: float
    lane_supply_bits_per_record: float
    lane_supply_bits_per_atom: float
    boundary_bits_per_atom: float
    phase_lane_gain_per_atom: float
    lane_minus_layout_per_atom: float


def lane_supply_loss(records_per_atom: float) -> float:
    if records_per_atom <= 0.0:
        return 0.0
    return math.log2(1.0 / records_per_atom)


def evaluate_row(
    block_bits: int,
    literal_marker_bits: int,
    arity: int,
    passes: int,
    min_raw_savings: float,
    atoms: int,
) -> PhaseLaneRow:
    h4 = H4.evaluate_cover(
        block_bits,
        literal_marker_bits,
        arity,
        passes,
        min_raw_savings,
        atoms,
    )
    base = h4.base
    q = base.selected_records_per_atom
    lane_per_record = lane_supply_loss(q)
    lane_per_atom = q * lane_per_record
    boundary_per_atom = math.log2(atoms + 1) / atoms
    phase_gain = base.optimistic_gain_per_atom - lane_per_atom - boundary_per_atom
    return PhaseLaneRow(
        arity=arity,
        passes=passes,
        hit_probability=base.hit_probability,
        selected_records_per_atom=q,
        optimistic_gain_per_atom=base.optimistic_gain_per_atom,
        cover_entropy_per_atom=h4.cover_entropy_per_atom,
        h4_layout_gain_per_atom=h4.layout_only_gain_per_atom,
        lane_supply_bits_per_record=lane_per_record,
        lane_supply_bits_per_atom=lane_per_atom,
        boundary_bits_per_atom=boundary_per_atom,
        phase_lane_gain_per_atom=phase_gain,
        lane_minus_layout_per_atom=lane_per_atom + boundary_per_atom - h4.cover_entropy_per_atom,
    )


def render(rows: list[PhaseLaneRow]) -> str:
    lines = [
        "# Phase-Lane Total-Cover Hybrid Ledger",
        "",
        "This is an optimistic positional-geometry ledger. It replaces sparse",
        "cover-layout entropy with a public active-lane restriction plus one",
        "boundary/count. It is valid only if every active lane slot opens, so",
        "the decoder never needs an intra-lane hit bitmap.",
        "",
        "| arity | passes | hit p/window | rec/atom q | optimistic gain/atom | H4 cover entropy/atom | H4 layout gain/atom | lane loss bits/rec | lane+boundary bits/atom | phase-lane gain/atom | lane minus layout/atom |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row.arity} | {row.passes} | {row.hit_probability:.6g} | "
            f"{row.selected_records_per_atom:.6g} | {row.optimistic_gain_per_atom:.6g} | "
            f"{row.cover_entropy_per_atom:.6g} | {row.h4_layout_gain_per_atom:.6g} | "
            f"{row.lane_supply_bits_per_record:.6g} | "
            f"{(row.lane_supply_bits_per_atom + row.boundary_bits_per_atom):.6g} | "
            f"{row.phase_lane_gain_per_atom:.6g} | {row.lane_minus_layout_per_atom:.6g} |"
        )

    best = max(rows, key=lambda row: row.phase_lane_gain_per_atom)
    lines.extend(
        [
            "",
            "## Best Phase-Lane Row",
            "",
            f"`arity={best.arity}, passes={best.passes}` gives "
            f"`{best.phase_lane_gain_per_atom:.9f}` bits/input atom in this",
            "optimistic public-lane ledger.",
            "",
            "## Reading",
            "",
            "A positive row is not yet a complete codec. It means a public lane",
            "could beat an arbitrary sparse layout charge if the encoder can fill",
            "the public lane without storing which lane positions hit. A real",
            "codec must therefore use Total-Cover/literal-witness fallback inside",
            "the lane, or prove another public all-open invariant.",
            "",
            "A negative row closes this positional rescue under the same H3/H4",
            "bundle economics because it already gives the lane the best possible",
            "boundary treatment.",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--block-bits", type=int, default=8)
    parser.add_argument("--literal-marker-bits", type=int, default=3)
    parser.add_argument("--min-raw-savings", type=float, default=2.0)
    parser.add_argument("--arities", type=int, nargs="+", default=[2, 3, 4, 5])
    parser.add_argument("--passes", type=int, nargs="+", default=H4.default_passes())
    parser.add_argument("--atoms", type=int, default=1_000_000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = [
        evaluate_row(
            args.block_bits,
            args.literal_marker_bits,
            arity,
            passes,
            args.min_raw_savings,
            args.atoms,
        )
        for arity in args.arities
        for passes in args.passes
    ]
    rows.sort(key=lambda row: (row.arity, row.passes))
    print(render(rows))


if __name__ == "__main__":
    main()
