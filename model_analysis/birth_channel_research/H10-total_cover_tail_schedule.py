#!/usr/bin/env python3
"""Monotone fixed-width tail schedules for high-arity Total-Cover.

H9 tested one scalar fixed slack:

    width_bits = min(D, arity * B - slack)

H10 tests the smallest richer canonical-width family: use a stricter slack in
the body and relax it near the suffix tail where full-cover pressure is higher.
The schedule is public and decoder-derived from remaining atom count:

    slack(remaining) = tail_slack if remaining <= tail_atoms else body_slack

Width is still derived, so no delta stream is sent. A schedule chosen per file
would be metadata; this kernel reports the train-selected schedule as the
honest public-profile result and the best held-out schedule only as diagnostic
pressure.
"""

from __future__ import annotations

import argparse
import math
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from statistics import mean


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from total_cover_lotus_crossover import EdgeSample, SelectedRecord, generate_samples  # noqa: E402
from total_cover_public_model_kernel import Cover  # noqa: E402


@dataclass(frozen=True)
class Schedule:
    body_slack: int
    tail_slack: int
    tail_atoms: int

    def slack_for(self, remaining: int) -> int:
        return self.tail_slack if remaining <= self.tail_atoms else self.body_slack

    @property
    def label(self) -> str:
        return f"body{self.body_slack}_tail{self.tail_slack}_at{self.tail_atoms}"


@dataclass(frozen=True)
class ArityModel:
    counts: dict[int, Counter[int]]
    max_arity: int
    alpha: float


@dataclass(frozen=True)
class ScheduleRow:
    schedule: Schedule
    train_gain_per_atom: float
    eval_gain_per_atom: float
    missing_bits_per_record: float
    records_per_atom: float
    avg_arity: float
    avg_width_bits: float
    arity_bits_per_record: float
    coverage: float


def arity_cost(model: ArityModel, remaining: int, arity: int) -> float:
    legal_max = min(model.max_arity, remaining)
    if not 1 <= arity <= legal_max:
        return float("inf")
    counts = model.counts.get(remaining, Counter())
    denom_count = sum(counts.get(value, 0) for value in range(1, legal_max + 1))
    denom = denom_count + model.alpha * legal_max
    return -math.log2((counts.get(arity, 0) + model.alpha) / denom)


def width_bits_for(block_bits: int, frontier: int, arity: int, slack: int) -> int | None:
    width = min(frontier, arity * block_bits - slack)
    if width < 1:
        return None
    return width


def edge_fits_width(edge: EdgeSample, width_bits: int) -> bool:
    return edge.log2_rank <= width_bits


def cover_with_schedule(
    trial: list[list[EdgeSample]],
    block_bits: int,
    max_arity: int,
    frontier: int,
    model: ArityModel,
    schedule: Schedule,
    flush_bits: float,
) -> Cover:
    atoms = len(trial)
    dp = [float("inf")] * (atoms + 1)
    prev: list[tuple[int, int, EdgeSample, int, float] | None] = [None] * (atoms + 1)
    dp[0] = 0.0
    for index in range(atoms):
        base = dp[index]
        if base == float("inf"):
            continue
        remaining = atoms - index
        slack = schedule.slack_for(remaining)
        for arity, edge in enumerate(trial[index], start=1):
            if arity > max_arity:
                continue
            width_bits = width_bits_for(block_bits, frontier, arity, slack)
            if width_bits is None or not edge_fits_width(edge, width_bits):
                continue
            stream_bits = arity_cost(model, remaining, arity)
            candidate = base + width_bits + stream_bits
            end = index + arity
            if candidate < dp[end]:
                dp[end] = candidate
                prev[end] = (index, arity, edge, width_bits, stream_bits)
    if dp[atoms] == float("inf"):
        return Cover(False, float("inf"), ())
    records: list[SelectedRecord] = []
    cursor = atoms
    while cursor > 0:
        entry = prev[cursor]
        if entry is None:
            raise AssertionError("missing predecessor")
        prior, arity, edge, width_bits, stream_bits = entry
        records.append(
            SelectedRecord(
                arity=arity,
                rank=edge.rank,
                target_bits=edge.target_bits,
                lotus_payload_width=width_bits,
                local_payload_bits=width_bits,
                cost_bits=width_bits + stream_bits,
            )
        )
        cursor = prior
    records.reverse()
    return Cover(True, dp[atoms] + flush_bits, tuple(records))


def fit_arity_model(covers: list[Cover], max_arity: int, alpha: float) -> ArityModel:
    counts: dict[int, Counter[int]] = {}
    for cover in covers:
        if not cover.covered:
            continue
        atoms = sum(record.arity for record in cover.records)
        consumed = 0
        for record in cover.records:
            remaining = atoms - consumed
            counts.setdefault(remaining, Counter())[record.arity] += 1
            consumed += record.arity
    return ArityModel(counts, max_arity, alpha)


def train_model(
    train_samples: list[list[list[EdgeSample]]],
    block_bits: int,
    max_arity: int,
    frontier: int,
    schedule: Schedule,
    iterations: int,
    alpha: float,
    flush_bits: float,
) -> tuple[ArityModel, list[Cover]]:
    model = ArityModel({}, max_arity, alpha)
    covers: list[Cover] = []
    for _ in range(iterations):
        covers = [
            cover_with_schedule(trial, block_bits, max_arity, frontier, model, schedule, flush_bits)
            for trial in train_samples
        ]
        model = fit_arity_model(covers, max_arity, alpha)
    return model, covers


def gain_for(covers: list[Cover], block_bits: int, atoms: int) -> float:
    covered = [cover for cover in covers if cover.covered]
    if not covered:
        return float("-inf")
    raw_bits = atoms * block_bits
    return mean((raw_bits - cover.charged_bits) / atoms for cover in covered)


def summarize(
    schedule: Schedule,
    train_covers: list[Cover],
    eval_covers: list[Cover],
    block_bits: int,
    atoms: int,
) -> ScheduleRow:
    covered_eval = [cover for cover in eval_covers if cover.covered]
    coverage = len(covered_eval) / len(eval_covers) if eval_covers else 0.0
    if not covered_eval:
        return ScheduleRow(schedule, float("-inf"), float("-inf"), float("inf"), 0.0, 0.0, 0.0, 0.0, coverage)
    eval_gain = gain_for(covered_eval, block_bits, atoms)
    all_records = [record for cover in covered_eval for record in cover.records]
    records_per_atom = mean(len(cover.records) / atoms for cover in covered_eval)
    missing = max(0.0, -eval_gain / records_per_atom) if records_per_atom else float("inf")
    arity_bits = [record.cost_bits - record.local_payload_bits for record in all_records]
    return ScheduleRow(
        schedule=schedule,
        train_gain_per_atom=gain_for(train_covers, block_bits, atoms),
        eval_gain_per_atom=eval_gain,
        missing_bits_per_record=missing,
        records_per_atom=records_per_atom,
        avg_arity=mean(record.arity for record in all_records),
        avg_width_bits=mean(record.local_payload_bits for record in all_records),
        arity_bits_per_record=mean(arity_bits),
        coverage=coverage,
    )


def schedule_grid(body_slacks: list[int], tail_slacks: list[int], tail_atoms_values: list[int]) -> list[Schedule]:
    schedules: list[Schedule] = []
    for tail_atoms in tail_atoms_values:
        for body in body_slacks:
            for tail in tail_slacks:
                if tail > body:
                    continue
                schedules.append(Schedule(body, tail, tail_atoms))
    return schedules


def render(rows: list[ScheduleRow], selected: ScheduleRow, block_bits: int, max_arity: int, frontier: int) -> str:
    lines = [
        "# Monotone Fixed-Width Tail Schedule",
        "",
        f"`B={block_bits}`, `K={max_arity}`, `D={frontier}`.",
        "",
        "Schedule: `tail_slack` when `remaining <= tail_atoms`, otherwise",
        "`body_slack`. The train-selected row is the honest public-profile",
        "candidate; best held-out is diagnostic only.",
        "",
        "| schedule | cover | train gain/atom | eval gain/atom | missing bits/rec | rec/atom | avg arity | avg width | arity bits/rec |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        marker = "*" if row.schedule == selected.schedule else ""
        lines.append(
            f"| {row.schedule.label}{marker} | {row.coverage:.3f} | "
            f"{row.train_gain_per_atom:.6f} | {row.eval_gain_per_atom:.6f} | "
            f"{row.missing_bits_per_record:.3f} | {row.records_per_atom:.6f} | "
            f"{row.avg_arity:.2f} | {row.avg_width_bits:.2f} | "
            f"{row.arity_bits_per_record:.3f} |"
        )
    best_eval = max(rows, key=lambda row: row.eval_gain_per_atom)
    lines.extend(
        [
            "",
            "## Reading",
            "",
            f"Train-selected schedule: `{selected.schedule.label}` with held-out gain "
            f"`{selected.eval_gain_per_atom:.6f}` bits/input atom.",
            f"Best held-out diagnostic schedule: `{best_eval.schedule.label}` with "
            f"`{best_eval.eval_gain_per_atom:.6f}` bits/input atom.",
            "Only the train-selected schedule is a valid public-profile result.",
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
    parser.add_argument("--body-slacks", type=int, nargs="+", default=[0, 1, 2])
    parser.add_argument("--tail-slacks", type=int, nargs="+", default=[0, 1])
    parser.add_argument("--tail-atoms", type=int, nargs="+", default=[32, 64, 128])
    parser.add_argument("--seed", type=int, default=1801)
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
    rows: list[ScheduleRow] = []
    for schedule in schedule_grid(args.body_slacks, args.tail_slacks, args.tail_atoms):
        model, train_covers = train_model(
            train_samples,
            args.block_bits,
            args.max_arity,
            args.frontier,
            schedule,
            args.iterations,
            args.alpha,
            args.flush_bits,
        )
        eval_covers = [
            cover_with_schedule(
                trial,
                args.block_bits,
                args.max_arity,
                args.frontier,
                model,
                schedule,
                args.flush_bits,
            )
            for trial in eval_samples
        ]
        rows.append(summarize(schedule, train_covers, eval_covers, args.block_bits, args.atoms))
    selected = max(rows, key=lambda row: row.train_gain_per_atom)
    print(render(rows, selected, args.block_bits, args.max_arity, args.frontier))


if __name__ == "__main__":
    main()
