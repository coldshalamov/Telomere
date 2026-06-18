#!/usr/bin/env python3
"""Active-lane Total-Cover ledger.

H22 tested public lanes as a sparse-bundle replacement for cover layout. H24
tests the stronger all-open invariant:

    - a public phase selects an active lane;
    - every atom in that lane is rewritten by a Total-Cover record stream;
    - inactive lanes carry in public order;
    - the decoder parses the active stream until arities sum to the known lane
      atom count, so no boundary/count is needed in the idealized model.

This solves the open/carry/birth problem for the active lane, but it should not
change the per-active-atom witness economics. The kernel quantifies that.
"""

from __future__ import annotations

import argparse
import importlib.util
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TCLC_PATH = ROOT / "total_cover_lotus_crossover.py"


def load_tclc() -> ModuleType:
    spec = importlib.util.spec_from_file_location("total_cover_lotus_crossover_runtime", TCLC_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load total-cover kernel from {TCLC_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


TCLC = load_tclc()


@dataclass(frozen=True)
class ActiveLaneRow:
    mode: str
    block_bits: int
    max_arity: int
    frontier: int
    lane_count: int
    active_atoms: int
    cover_rate: float
    active_gain_per_atom: float
    full_stream_gain_per_pass_atom: float
    full_cycle_gain_per_atom: float
    pass_count_bits_per_atom: float
    net_cycle_gain_per_atom: float
    records_per_active_atom: float
    avg_arity: float
    missing_bits_per_record: float


def find_mode(name: str):
    modes = {mode.name: mode for mode in TCLC.make_modes()}
    if name not in modes:
        raise SystemExit(f"unknown mode {name!r}; options: {', '.join(sorted(modes))}")
    return modes[name]


def evaluate_lane(
    block_bits: int,
    max_arity: int,
    frontier: int,
    lane_count: int,
    atoms: int,
    trials: int,
    seed: int,
    mode_name: str,
    pass_count: int,
) -> ActiveLaneRow:
    active_atoms = max(1, atoms // lane_count)
    mode = find_mode(mode_name)
    samples = TCLC.generate_samples(
        block_bits,
        max_arity,
        active_atoms,
        trials,
        seed + block_bits * 1009 + max_arity * 9173 + lane_count * 7919,
    )
    summary = TCLC.evaluate(samples, block_bits, max_arity, frontier, mode)
    # One pass touches one public lane. A full cycle touches each lane once, so
    # the sign per full-stream atom is the same as the active-lane sign, aside
    # from any pass-count/header amortization.
    full_pass_gain = summary.gain_per_atom / lane_count
    full_cycle_gain = summary.gain_per_atom
    pass_bits = math.log2(pass_count + 1) / max(1, atoms)
    net_cycle = full_cycle_gain - pass_bits
    return ActiveLaneRow(
        mode=mode_name,
        block_bits=block_bits,
        max_arity=max_arity,
        frontier=frontier,
        lane_count=lane_count,
        active_atoms=active_atoms,
        cover_rate=summary.cover_rate,
        active_gain_per_atom=summary.gain_per_atom,
        full_stream_gain_per_pass_atom=full_pass_gain,
        full_cycle_gain_per_atom=full_cycle_gain,
        pass_count_bits_per_atom=pass_bits,
        net_cycle_gain_per_atom=net_cycle,
        records_per_active_atom=summary.records_per_atom,
        avg_arity=summary.avg_selected_arity,
        missing_bits_per_record=summary.missing_bits_per_record,
    )


def render(rows: list[ActiveLaneRow]) -> str:
    lines = [
        "# Active-Lane Total-Cover Ledger",
        "",
        "The active lane is public and all-open. The decoder parses active",
        "records until arities sum to the known lane atom count, then carries",
        "inactive lanes in public order. This idealized lane has no open/carry",
        "bitmap and no boundary count.",
        "",
        "| mode | B | K | D | lanes | active atoms | cover | active gain/atom | full-pass gain/atom | full-cycle gain/atom | pass-count bits/atom | net cycle gain/atom | rec/active atom | avg arity | missing bits/rec |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row.mode} | {row.block_bits} | {row.max_arity} | {row.frontier} | "
            f"{row.lane_count} | {row.active_atoms} | {row.cover_rate:.3f} | "
            f"{row.active_gain_per_atom:.6f} | {row.full_stream_gain_per_pass_atom:.6f} | "
            f"{row.full_cycle_gain_per_atom:.6f} | {row.pass_count_bits_per_atom:.9f} | "
            f"{row.net_cycle_gain_per_atom:.6f} | {row.records_per_active_atom:.6f} | "
            f"{row.avg_arity:.2f} | {row.missing_bits_per_record:.3f} |"
        )

    best = max(rows, key=lambda row: row.net_cycle_gain_per_atom)
    lines.extend(
        [
            "",
            "## Best Row",
            "",
            f"`{best.mode}`, `B={best.block_bits}`, `K={best.max_arity}`, "
            f"`D={best.frontier}`, `lanes={best.lane_count}` gives "
            f"`{best.net_cycle_gain_per_atom:.6f}` bits/input atom per full",
            "lane cycle after pass-count amortization.",
            "",
            "## Reading",
            "",
            "All-open phase lanes solve stateless open/carry for the active lane.",
            "They do not improve the paid witness margin: per full cycle, every",
            "atom eventually pays the same Total-Cover record economics it would",
            "pay if rewritten all at once. Lane scheduling can organize salts and",
            "decode order, but it is not by itself a compression source.",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--atoms", type=int, default=1024)
    parser.add_argument("--trials", type=int, default=16)
    parser.add_argument("--seed", type=int, default=20260617)
    parser.add_argument("--pass-count", type=int, default=1024)
    parser.add_argument("--block-bits", type=int, nargs="+", default=[4, 8, 24])
    parser.add_argument("--max-arity", type=int, nargs="+", default=[8, 64, 128])
    parser.add_argument("--frontiers", type=int, nargs="+", default=[64, 120, 512])
    parser.add_argument("--lanes", type=int, nargs="+", default=[1, 2, 4, 8, 16])
    parser.add_argument(
        "--modes",
        nargs="+",
        default=["arith_arity_width_lotus_payload", "free_boundary_oracle"],
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows: list[ActiveLaneRow] = []
    for block_bits in args.block_bits:
        for max_arity in args.max_arity:
            for frontier in args.frontiers:
                if frontier > max_arity * block_bits:
                    continue
                for lane_count in args.lanes:
                    for mode_name in args.modes:
                        rows.append(
                            evaluate_lane(
                                block_bits,
                                max_arity,
                                frontier,
                                lane_count,
                                args.atoms,
                                args.trials,
                                args.seed,
                                mode_name,
                                args.pass_count,
                            )
                        )
    rows.sort(key=lambda row: (row.mode, row.block_bits, row.max_arity, row.frontier, row.lane_count))
    print(render(rows))


if __name__ == "__main__":
    main()
