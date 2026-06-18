#!/usr/bin/env python3
"""H50 - bounded repeated-pass reproduction sweep.

H49 made the right recursive score explicit:

    rho_t = paid_bits(layer_{t+1}) / padded_bits(layer_t)
    pass condition: held-out E[log rho_t] < 0

H50 runs a compact response-surface sweep around the closest Total-Cover paid
rows. It is intentionally small: this is not a large compression test, it is a
proof-kernel search for which knobs move the repeated-pass reproduction number.
"""

from __future__ import annotations

import argparse
import importlib.util
import math
import sys
from dataclasses import dataclass
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_h49():
    path = HERE / "H49-all_block_rg_kernel.py"
    spec = importlib.util.spec_from_file_location("h49_all_block_rg_kernel", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


H49 = load_h49()


@dataclass(frozen=True)
class SweepConfig:
    block_bits: int
    max_arity: int
    frontier: int
    atoms: int


@dataclass(frozen=True)
class SweepMode:
    mode: str
    h9_slack: int = 0

    @property
    def label(self) -> str:
        if self.mode == "h9_fixed_slack0":
            return f"h9_fixed_slack{self.h9_slack}"
        return self.mode


@dataclass(frozen=True)
class SweepRow:
    config: SweepConfig
    mode: SweepMode
    status: str
    mean_log2_rho: float
    geometric_rho: float
    final_bits_avg: float
    total_ratio_avg: float
    note: str


def parse_config(text: str) -> SweepConfig:
    parts = [int(part) for part in text.split(",")]
    if len(parts) not in {3, 4}:
        raise argparse.ArgumentTypeError("config must be B,K,D or B,K,D,atoms")
    block_bits, max_arity, frontier = parts[:3]
    atoms = parts[3] if len(parts) == 4 else 96
    return SweepConfig(block_bits, max_arity, frontier, atoms)


def default_configs() -> list[SweepConfig]:
    return [
        SweepConfig(4, 64, 256, 96),
        SweepConfig(4, 96, 384, 96),
        SweepConfig(4, 128, 512, 96),
        SweepConfig(8, 64, 512, 64),
    ]


def default_modes(slacks: list[int]) -> list[SweepMode]:
    modes = [SweepMode("oracle_free_boundary"), SweepMode("h7_raw_delta")]
    modes.extend(SweepMode("h9_fixed_slack0", slack) for slack in slacks)
    return modes


def namespace_for(args: argparse.Namespace, config: SweepConfig, mode: SweepMode) -> argparse.Namespace:
    return argparse.Namespace(
        block_bits=config.block_bits,
        max_arity=config.max_arity,
        frontier=config.frontier,
        atoms=config.atoms,
        passes=args.passes,
        trials=args.trials,
        train_trials=args.train_trials,
        iterations=args.iterations,
        alpha=args.alpha,
        h9_slack=mode.h9_slack,
        modes=[mode.mode],
        seed=args.seed + config.block_bits * 10007 + config.max_arity * 1009 + config.frontier * 17,
    )


def run_row(args: argparse.Namespace, config: SweepConfig, mode: SweepMode) -> SweepRow:
    h49_args = namespace_for(args, config, mode)
    try:
        summary, _pass_rows = H49.simulate_mode(h49_args, mode.mode)
    except Exception as exc:  # coverage failures are meaningful sweep output
        return SweepRow(
            config,
            mode,
            "failed",
            float("nan"),
            float("nan"),
            float("nan"),
            float("nan"),
            str(exc),
        )
    return SweepRow(
        config=config,
        mode=mode,
        status=summary.verdict,
        mean_log2_rho=summary.mean_log2_rho,
        geometric_rho=summary.geometric_rho,
        final_bits_avg=summary.final_bits_avg,
        total_ratio_avg=summary.total_ratio_avg,
        note="",
    )


def fmt(value: float) -> str:
    if math.isnan(value):
        return "nan"
    return f"{value:.6f}"


def render(rows: list[SweepRow], args: argparse.Namespace) -> str:
    lines = [
        "# Repeated-Pass Reproduction Sweep",
        "",
        f"`passes={args.passes}`, `trials={args.trials}`, "
        f"`train_trials={args.train_trials}`, `iterations={args.iterations}`.",
        "",
        "A row crosses only if `mean log2 rho < 0` in a parseable paid mode.",
        "The oracle row is a labeled lower bound.",
        "",
        "| B | K | D | atoms | mode | status | mean log2 rho | geometric rho | final bits avg | total ratio avg | note |",
        "| ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        note = row.note.replace("|", "/")
        lines.append(
            f"| {row.config.block_bits} | {row.config.max_arity} | "
            f"{row.config.frontier} | {row.config.atoms} | {row.mode.label} | "
            f"{row.status} | {fmt(row.mean_log2_rho)} | {fmt(row.geometric_rho)} | "
            f"{fmt(row.final_bits_avg)} | {fmt(row.total_ratio_avg)} | {note} |"
        )

    paid = [row for row in rows if row.mode.mode != "oracle_free_boundary" and row.status != "failed"]
    oracle = [row for row in rows if row.mode.mode == "oracle_free_boundary" and row.status != "failed"]
    best_paid = min(paid, key=lambda row: row.mean_log2_rho) if paid else None
    best_oracle = min(oracle, key=lambda row: row.mean_log2_rho) if oracle else None

    lines.extend(["", "## Reading", ""])
    if best_paid is None:
        lines.append("No paid row covered all tested passes.")
    else:
        lines.append(
            "Best paid row: "
            f"`B={best_paid.config.block_bits},K={best_paid.config.max_arity},"
            f"D={best_paid.config.frontier},{best_paid.mode.label}` with "
            f"`mean log2 rho={best_paid.mean_log2_rho:.6f}`."
        )
    if best_oracle is not None:
        lines.append(
            "Best oracle lower bound: "
            f"`B={best_oracle.config.block_bits},K={best_oracle.config.max_arity},"
            f"D={best_oracle.config.frontier}` with "
            f"`mean log2 rho={best_oracle.mean_log2_rho:.6f}`."
        )
    lines.append(
        "If oracle crosses but paid rows do not, the missing piece is still the "
        "paid witness boundary/selector, not pass freshness."
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", action="append", type=parse_config, dest="configs")
    parser.add_argument("--passes", type=int, default=3)
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--train-trials", type=int, default=4)
    parser.add_argument("--iterations", type=int, default=1)
    parser.add_argument("--alpha", type=float, default=0.02)
    parser.add_argument("--h9-slacks", type=int, nargs="+", default=[-8, -4, 0, 2])
    parser.add_argument("--seed", type=int, default=8101)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configs = args.configs if args.configs else default_configs()
    modes = default_modes(args.h9_slacks)
    rows = [run_row(args, config, mode) for config in configs for mode in modes]
    print(render(rows, args))


if __name__ == "__main__":
    main()
