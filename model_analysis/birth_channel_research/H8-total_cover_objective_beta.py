#!/usr/bin/env python3
"""Objective-tuned selected-delta temperature for Total-Cover.

H7 showed that an analytic raw first-hit delta law is the closest paid miss.
It also tested a beta-tilted law, but beta was fit by selected-delta
likelihood. H8 asks a sharper question: if beta is chosen by the actual
Total-Cover compression objective on independent public training samples, can a
one-parameter selected-delta residual law cross positive on held-out samples?

This remains stateless and public only because beta is selected from a fixed
grid using independent uniform-law samples. A beta chosen per file would be
metadata and is not modeled here.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from types import ModuleType


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from total_cover_lotus_crossover import generate_samples  # noqa: E402


H7_PATH = Path(__file__).with_name("H7-total_cover_parametric_delta.py")


def load_h7() -> ModuleType:
    spec = importlib.util.spec_from_file_location("h7_total_cover_parametric_delta", H7_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load H7 kernel from {H7_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


H7 = load_h7()


@dataclass(frozen=True)
class BetaRow:
    beta: float
    train_gain_per_atom: float
    eval_gain_per_atom: float
    eval_missing_bits_per_record: float
    eval_records_per_atom: float
    eval_avg_arity: float
    eval_rank_bits_per_record: float
    eval_arity_bits_per_record: float
    eval_delta_bits_per_record: float


def beta_grid(start: float, stop: float, step: float) -> list[float]:
    values: list[float] = []
    index = 0
    current = start
    while current <= stop + step / 2:
        values.append(round(current, 6))
        index += 1
        current = start + index * step
    if 0.0 not in values:
        values.append(0.0)
    return sorted(set(values))


def fit_arity_model(
    covers: list,
    max_arity: int,
    frontier: int,
    alpha: float,
    beta: float,
) -> object:
    arity_counts: dict[int, Counter[int]] = {}
    for cover in covers:
        if not cover.covered:
            continue
        atoms = sum(record.arity for record in cover.records)
        consumed = 0
        for record in cover.records:
            remaining = atoms - consumed
            arity_counts.setdefault(remaining, Counter())[record.arity] += 1
            consumed += record.arity
    return H7.DeltaModel(
        mode="tilted",
        arity_counts=arity_counts,
        suffix_delta_counts={},
        arity_delta_counts={},
        global_delta_counts=Counter(),
        max_arity=max_arity,
        frontier=frontier,
        alpha=alpha,
        beta=beta,
    )


def train_for_beta(
    beta: float,
    train_samples: list,
    block_bits: int,
    max_arity: int,
    frontier: int,
    iterations: int,
    alpha: float,
    flush_bits: float,
    rank_code: str,
) -> tuple[object, list]:
    model = H7.DeltaModel("tilted", {}, {}, {}, Counter(), max_arity, frontier, alpha, beta)
    covers = []
    for _ in range(iterations):
        covers = [
            H7.cover_with_model(
                trial,
                block_bits,
                max_arity,
                frontier,
                model,
                flush_bits,
                rank_code,
            )
            for trial in train_samples
        ]
        model = fit_arity_model(covers, max_arity, frontier, alpha, beta)
    return model, covers


def average_gain(covers: list, block_bits: int) -> float:
    covered = [cover for cover in covers if cover.covered]
    if not covered:
        return float("-inf")
    atoms = sum(record.arity for record in covered[0].records)
    raw_bits = atoms * block_bits
    return mean((raw_bits - cover.charged_bits) / atoms for cover in covered)


def evaluate_beta(
    beta: float,
    train_samples: list,
    eval_samples: list,
    block_bits: int,
    max_arity: int,
    frontier: int,
    iterations: int,
    alpha: float,
    flush_bits: float,
    rank_code: str,
) -> BetaRow:
    model, train_covers = train_for_beta(
        beta,
        train_samples,
        block_bits,
        max_arity,
        frontier,
        iterations,
        alpha,
        flush_bits,
        rank_code,
    )
    eval_covers = [
        H7.cover_with_model(
            trial,
            block_bits,
            max_arity,
            frontier,
            model,
            flush_bits,
            rank_code,
        )
        for trial in eval_samples
    ]
    summary = H7.summarize("tilted", model, eval_covers, block_bits, rank_code, flush_bits)
    return BetaRow(
        beta=beta,
        train_gain_per_atom=average_gain(train_covers, block_bits),
        eval_gain_per_atom=summary.gain_per_atom,
        eval_missing_bits_per_record=summary.missing_bits_per_record,
        eval_records_per_atom=summary.records_per_atom,
        eval_avg_arity=summary.avg_arity,
        eval_rank_bits_per_record=summary.rank_bits_per_record,
        eval_arity_bits_per_record=summary.arity_bits_per_record,
        eval_delta_bits_per_record=summary.delta_bits_per_record,
    )


def render(rows: list[BetaRow], selected: BetaRow, block_bits: int, max_arity: int, frontier: int) -> str:
    lines = [
        "# Objective-Tuned Delta Temperature",
        "",
        f"`B={block_bits}`, `K={max_arity}`, `D={frontier}`.",
        "",
        "Beta is chosen by train gain, then evaluated held-out. A per-file beta",
        "would be metadata; this kernel only models a public frozen profile beta.",
        "",
        "| beta | train gain/atom | eval gain/atom | missing bits/rec | rec/atom | avg arity | rank bits/rec | arity bits/rec | delta bits/rec |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        marker = "*" if row.beta == selected.beta else ""
        lines.append(
            f"| {row.beta:.3f}{marker} | {row.train_gain_per_atom:.6f} | "
            f"{row.eval_gain_per_atom:.6f} | {row.eval_missing_bits_per_record:.3f} | "
            f"{row.eval_records_per_atom:.6f} | {row.eval_avg_arity:.2f} | "
            f"{row.eval_rank_bits_per_record:.3f} | {row.eval_arity_bits_per_record:.3f} | "
            f"{row.eval_delta_bits_per_record:.3f} |"
        )
    best_eval = max(rows, key=lambda row: row.eval_gain_per_atom)
    lines.extend(
        [
            "",
            "## Reading",
            "",
            f"Train-selected beta: `{selected.beta:.3f}` with held-out gain "
            f"`{selected.eval_gain_per_atom:.6f}` bits/input atom.",
            f"Best held-out beta in this diagnostic grid: `{best_eval.beta:.3f}` with "
            f"`{best_eval.eval_gain_per_atom:.6f}` bits/input atom.",
            "Only the train-selected beta is a valid public-profile result; the",
            "best-held-out beta is reported as diagnostic overfit pressure.",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--block-bits", type=int, default=4)
    parser.add_argument("--max-arity", type=int, default=128)
    parser.add_argument("--frontier", type=int, default=512)
    parser.add_argument("--atoms", type=int, default=256)
    parser.add_argument("--train-trials", type=int, default=24)
    parser.add_argument("--eval-trials", type=int, default=16)
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--alpha", type=float, default=0.02)
    parser.add_argument("--flush-bits", type=float, default=0.0)
    parser.add_argument("--rank-code", choices=["fixed", "truncated-geometric"], default="fixed")
    parser.add_argument("--beta-start", type=float, default=-0.5)
    parser.add_argument("--beta-stop", type=float, default=0.8)
    parser.add_argument("--beta-step", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=1409)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    train_samples = generate_samples(
        args.block_bits,
        args.max_arity,
        args.atoms,
        args.train_trials,
        args.seed + args.block_bits * 1009 + args.max_arity * 9173 + args.frontier * 31,
    )
    eval_samples = generate_samples(
        args.block_bits,
        args.max_arity,
        args.atoms,
        args.eval_trials,
        args.seed + args.block_bits * 8081 + args.max_arity * 3571 + args.frontier * 43,
    )
    rows = [
        evaluate_beta(
            beta,
            train_samples,
            eval_samples,
            args.block_bits,
            args.max_arity,
            args.frontier,
            args.iterations,
            args.alpha,
            args.flush_bits,
            args.rank_code,
        )
        for beta in beta_grid(args.beta_start, args.beta_stop, args.beta_step)
    ]
    selected = max(rows, key=lambda row: row.train_gain_per_atom)
    print(render(rows, selected, args.block_bits, args.max_arity, args.frontier))


if __name__ == "__main__":
    main()
