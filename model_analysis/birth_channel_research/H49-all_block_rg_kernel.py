#!/usr/bin/env python3
"""H49 - all-block renormalization / reproduction-number kernel.

This tests the user's total-cover recursion premise directly:

    every pass rewrites every atom
    every output unit is a record
    no birth/open/carry channel exists
    the next pass sees the serialized record stream as fresh target bits

Under the uniform hash law, freshness is automatic: a serialized seed-record
stream is just another fixed target string of its length. The question is
whether the paid one-pass reproduction number is below one:

    rho_t = paid_bits(layer_{t+1}) / padded_bits(layer_t)
    need E[log rho_t] < 0

The kernel compares a non-parseable free-boundary oracle against two paid
total-cover modes from the current worktree: H7 raw first-hit delta and H9
fixed slack 0.
"""

from __future__ import annotations

import argparse
import importlib.util
import math
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from types import ModuleType


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from total_cover_lotus_crossover import (  # noqa: E402
    EdgeSample,
    SelectedRecord,
    fixed_arity_bits,
    generate_samples,
)
from total_cover_public_model_kernel import Cover  # noqa: E402


HERE = Path(__file__).resolve().parent


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


H7 = load_module("h7_total_cover_parametric_delta", HERE / "H7-total_cover_parametric_delta.py")
H9 = load_module("h9_total_cover_fixed_slack", HERE / "H9-total_cover_fixed_slack.py")


@dataclass(frozen=True)
class PassRow:
    mode: str
    pass_index: int
    trials: int
    input_atoms_avg: float
    input_bits_avg: float
    output_bits_avg: float
    rho_avg: float
    log2_rho_avg: float
    records_per_atom_avg: float
    avg_arity: float
    avg_width: float


@dataclass(frozen=True)
class ModeSummary:
    mode: str
    passes: int
    trials: int
    mean_log2_rho: float
    geometric_rho: float
    final_bits_avg: float
    total_ratio_avg: float
    verdict: str


def cover_oracle_free(
    trial: list[list[EdgeSample]],
    max_arity: int,
    frontier: int,
) -> Cover:
    atoms = len(trial)
    dp = [float("inf")] * (atoms + 1)
    prev: list[tuple[int, int, EdgeSample, float] | None] = [None] * (atoms + 1)
    dp[0] = 0.0
    for index in range(atoms):
        base = dp[index]
        if base == float("inf"):
            continue
        for arity, edge in enumerate(trial[index], start=1):
            if arity > max_arity or edge.lotus_payload_width > frontier:
                continue
            cost = fixed_arity_bits(max_arity, arity) + edge.lotus_payload_width
            candidate = base + cost
            end = index + arity
            if candidate < dp[end]:
                dp[end] = candidate
                prev[end] = (index, arity, edge, float(cost))
    if dp[atoms] == float("inf"):
        return Cover(False, float("inf"), ())

    records: list[SelectedRecord] = []
    cursor = atoms
    while cursor > 0:
        entry = prev[cursor]
        if entry is None:
            raise AssertionError("missing predecessor")
        prior, arity, edge, cost = entry
        records.append(
            SelectedRecord(
                arity=arity,
                rank=edge.rank,
                target_bits=edge.target_bits,
                lotus_payload_width=edge.lotus_payload_width,
                local_payload_bits=edge.local_payload_bits,
                cost_bits=cost,
            )
        )
        cursor = prior
    records.reverse()
    return Cover(True, dp[atoms], tuple(records))


def train_h7_raw(
    block_bits: int,
    max_arity: int,
    frontier: int,
    atoms: int,
    train_trials: int,
    seed: int,
    iterations: int,
    alpha: float,
) -> object:
    samples = generate_samples(block_bits, max_arity, atoms, train_trials, seed)
    return H7.train_model("raw", samples, block_bits, max_arity, frontier, iterations, alpha, 0.0, "fixed")


def train_h9_slack(
    block_bits: int,
    max_arity: int,
    frontier: int,
    atoms: int,
    train_trials: int,
    seed: int,
    iterations: int,
    alpha: float,
    slack: int,
) -> object:
    samples = generate_samples(block_bits, max_arity, atoms, train_trials, seed)
    model, _covers = H9.train_model(samples, block_bits, max_arity, frontier, slack, iterations, alpha, 0.0)
    return model


def cover_paid_mode(
    mode: str,
    trial: list[list[EdgeSample]],
    block_bits: int,
    max_arity: int,
    frontier: int,
    model: object,
    h9_slack: int,
) -> Cover:
    if mode == "h7_raw_delta":
        return H7.cover_with_model(trial, block_bits, max_arity, frontier, model, 0.0, "fixed")
    if mode == "h9_fixed_slack0":
        return H9.cover_with_slack(trial, block_bits, max_arity, frontier, model, h9_slack, 0.0)
    raise ValueError(mode)


def summarize_pass(
    mode: str,
    pass_index: int,
    input_atoms: list[int],
    input_bits: list[float],
    covers: list[Cover],
) -> PassRow:
    output_bits = [cover.charged_bits for cover in covers]
    rhos = [out / inp for out, inp in zip(output_bits, input_bits)]
    logs = [math.log2(rho) for rho in rhos]
    records_per_atom = [
        len(cover.records) / atoms for cover, atoms in zip(covers, input_atoms) if cover.covered
    ]
    records = [record for cover in covers for record in cover.records]
    return PassRow(
        mode=mode,
        pass_index=pass_index,
        trials=len(covers),
        input_atoms_avg=mean(input_atoms),
        input_bits_avg=mean(input_bits),
        output_bits_avg=mean(output_bits),
        rho_avg=mean(rhos),
        log2_rho_avg=mean(logs),
        records_per_atom_avg=mean(records_per_atom) if records_per_atom else 0.0,
        avg_arity=mean(record.arity for record in records) if records else 0.0,
        avg_width=mean(record.lotus_payload_width for record in records) if records else 0.0,
    )


def simulate_mode(args: argparse.Namespace, mode: str) -> tuple[ModeSummary, list[PassRow]]:
    label = f"h9_fixed_slack{args.h9_slack}" if mode == "h9_fixed_slack0" else mode
    current_bits = [float(args.atoms * args.block_bits) for _ in range(args.trials)]
    initial_bits = list(current_bits)
    pass_rows: list[PassRow] = []

    for pass_index in range(1, args.passes + 1):
        input_atoms = [max(1, math.ceil(bits / args.block_bits)) for bits in current_bits]
        padded_bits = [atoms * args.block_bits for atoms in input_atoms]
        covers_by_trial: list[Cover | None] = [None] * args.trials
        trial_groups: dict[int, list[int]] = defaultdict(list)
        for trial_index, atoms in enumerate(input_atoms):
            trial_groups[atoms].append(trial_index)

        for atoms, trial_indices in trial_groups.items():
            seed_base = (
                args.seed
                + pass_index * 1000003
                + atoms * 9173
                + len(trial_indices) * 101
            )
            samples = generate_samples(
                args.block_bits,
                args.max_arity,
                atoms,
                len(trial_indices),
                seed_base,
            )
            if mode == "oracle_free_boundary":
                covers = [
                    cover_oracle_free(sample, args.max_arity, args.frontier)
                    for sample in samples
                ]
            else:
                train_seed = seed_base + 424242
                if mode == "h7_raw_delta":
                    model = train_h7_raw(
                        args.block_bits,
                        args.max_arity,
                        args.frontier,
                        atoms,
                        args.train_trials,
                        train_seed,
                        args.iterations,
                        args.alpha,
                    )
                elif mode == "h9_fixed_slack0":
                    model = train_h9_slack(
                        args.block_bits,
                        args.max_arity,
                        args.frontier,
                        atoms,
                        args.train_trials,
                        train_seed,
                        args.iterations,
                        args.alpha,
                        args.h9_slack,
                    )
                else:
                    raise ValueError(mode)
                covers = [
                    cover_paid_mode(
                        mode,
                        sample,
                        args.block_bits,
                        args.max_arity,
                        args.frontier,
                        model,
                        args.h9_slack,
                    )
                    for sample in samples
                ]
            for trial_index, cover in zip(trial_indices, covers):
                if not cover.covered:
                    raise RuntimeError(f"{mode} failed to cover atoms={atoms}")
                covers_by_trial[trial_index] = cover

        ordered_covers = [cover for cover in covers_by_trial if cover is not None]
        pass_rows.append(summarize_pass(label, pass_index, input_atoms, padded_bits, ordered_covers))
        current_bits = [cover.charged_bits for cover in ordered_covers]

    all_logs = [row.log2_rho_avg for row in pass_rows]
    total_ratios = [final / start for final, start in zip(current_bits, initial_bits)]
    mean_log = mean(all_logs)
    summary = ModeSummary(
        mode=label,
        passes=args.passes,
        trials=args.trials,
        mean_log2_rho=mean_log,
        geometric_rho=2.0**mean_log,
        final_bits_avg=mean(current_bits),
        total_ratio_avg=mean(total_ratios),
        verdict="compressive" if mean_log < 0.0 else "expanding",
    )
    return summary, pass_rows


def render(summaries: list[ModeSummary], rows: list[PassRow], args: argparse.Namespace) -> str:
    lines = [
        "# All-Block Renormalization Kernel",
        "",
        f"`B={args.block_bits}`, `K={args.max_arity}`, `D={args.frontier}`, "
        f"`passes={args.passes}`, `trials={args.trials}`.",
        "",
        "Every pass fully rewrites the current layer. The next pass sees the",
        "serialized paid record stream as fresh target bits of its charged",
        "length, re-atomized on the same `B` boundary. The pass criterion is",
        "`E[log2 rho] < 0`, where `rho = paid_output_bits / padded_input_bits`.",
        "",
        "## Summary",
        "",
        "| mode | verdict | mean log2 rho | geometric rho | avg final bits | avg total ratio |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for summary in summaries:
        lines.append(
            f"| {summary.mode} | {summary.verdict} | {summary.mean_log2_rho:.6f} | "
            f"{summary.geometric_rho:.6f} | {summary.final_bits_avg:.3f} | "
            f"{summary.total_ratio_avg:.6f} |"
        )

    lines.extend(
        [
            "",
            "## Pass Rows",
            "",
            "| mode | pass | atoms avg | in bits avg | out bits avg | rho avg | log2 rho avg | rec/atom | avg arity | avg width |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in rows:
        lines.append(
            f"| {row.mode} | {row.pass_index} | {row.input_atoms_avg:.2f} | "
            f"{row.input_bits_avg:.3f} | {row.output_bits_avg:.3f} | "
            f"{row.rho_avg:.6f} | {row.log2_rho_avg:.6f} | "
            f"{row.records_per_atom_avg:.6f} | {row.avg_arity:.2f} | "
            f"{row.avg_width:.2f} |"
        )

    lines.extend(
        [
            "",
            "## Reading",
            "",
            "A negative `mean log2 rho` is the constructive recursive target. A",
            "positive value means fresh dice are maintained but the paid codec",
            "still expands on average, so recursion compounds loss rather than",
            "compression. The oracle row is a labeled lower bound and not a",
            "parseable codec.",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--block-bits", type=int, default=4)
    parser.add_argument("--max-arity", type=int, default=128)
    parser.add_argument("--frontier", type=int, default=512)
    parser.add_argument("--atoms", type=int, default=96)
    parser.add_argument("--passes", type=int, default=5)
    parser.add_argument("--trials", type=int, default=6)
    parser.add_argument("--train-trials", type=int, default=8)
    parser.add_argument("--iterations", type=int, default=2)
    parser.add_argument("--alpha", type=float, default=0.02)
    parser.add_argument("--h9-slack", type=int, default=0)
    parser.add_argument(
        "--modes",
        nargs="+",
        choices=["oracle_free_boundary", "h7_raw_delta", "h9_fixed_slack0"],
        default=["oracle_free_boundary", "h7_raw_delta", "h9_fixed_slack0"],
    )
    parser.add_argument("--seed", type=int, default=7103)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summaries: list[ModeSummary] = []
    rows: list[PassRow] = []
    for mode in args.modes:
        summary, mode_rows = simulate_mode(args, mode)
        summaries.append(summary)
        rows.extend(mode_rows)
    print(render(summaries, rows, args))


if __name__ == "__main__":
    main()
