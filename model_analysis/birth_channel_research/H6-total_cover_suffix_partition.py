#!/usr/bin/env python3
"""Exact-suffix public witness model for high-arity Total-Cover.

This tests the most concrete surviving witness-language idea after H5:

    P(arity | exact remaining atoms)
    P(width delta | exact remaining atoms, exact arity)

The model is public/frozen: it is trained only on independent uniform-law
Total-Cover samples, then used on held-out samples. No per-file counts,
transition tables, layouts, or birth/open metadata are charged.

This is not a counting-law escape. It is a sharper entropy-rate probe for the
current nearest miss: can exact suffix normalization shave the last few
bits/selected record from the public factored arity+delta stream?
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
from total_cover_public_model_kernel import (  # noqa: E402
    Cover,
    selected_rank_bits,
)


@dataclass(frozen=True)
class SuffixModel:
    arity_counts: dict[int, Counter[int]]
    delta_counts: dict[tuple[int, int], Counter[int]]
    max_arity: int
    frontier: int
    alpha: float


@dataclass(frozen=True)
class SplitTotals:
    rank_bits: float
    arity_bits: float
    delta_bits: float
    flush_bits: float
    records: int
    atoms: int
    avg_arity: float
    avg_width: float

    @property
    def paid_bits(self) -> float:
        return self.rank_bits + self.arity_bits + self.delta_bits + self.flush_bits


def arity_cost(model: SuffixModel, remaining: int, arity: int) -> float:
    legal_max = min(model.max_arity, remaining)
    if not 1 <= arity <= legal_max:
        return float("inf")
    counts = model.arity_counts.get(remaining, Counter())
    denom_count = sum(counts.get(value, 0) for value in range(1, legal_max + 1))
    denom = denom_count + model.alpha * legal_max
    return -math.log2((counts.get(arity, 0) + model.alpha) / denom)


def delta_cost(model: SuffixModel, block_bits: int, remaining: int, arity: int, width: int) -> float:
    counts = model.delta_counts.get((remaining, arity), Counter())
    delta = arity * block_bits - width
    lo = arity * block_bits - model.frontier
    hi = arity * block_bits - 1
    denom_count = sum(count for value, count in counts.items() if lo <= value <= hi)
    denom = denom_count + model.alpha * model.frontier
    return -math.log2((counts.get(delta, 0) + model.alpha) / denom)


def code_cost(
    model: SuffixModel,
    block_bits: int,
    remaining: int,
    arity: int,
    width: int,
) -> float:
    return arity_cost(model, remaining, arity) + delta_cost(model, block_bits, remaining, arity, width)


def cover_with_suffix_model(
    trial: list[list[EdgeSample]],
    block_bits: int,
    max_arity: int,
    frontier: int,
    model: SuffixModel,
    flush_bits: float,
    rank_code: str,
) -> Cover:
    atoms = len(trial)
    dp = [float("inf")] * (atoms + 1)
    prev: list[tuple[int, int, EdgeSample] | None] = [None] * (atoms + 1)
    dp[0] = 0.0
    for index in range(atoms):
        base = dp[index]
        if base == float("inf"):
            continue
        remaining = atoms - index
        for arity, edge in enumerate(trial[index], start=1):
            if arity > max_arity or edge.lotus_payload_width > frontier:
                continue
            candidate = (
                base
                + selected_rank_bits(
                    SelectedRecord(
                        arity=arity,
                        rank=edge.rank,
                        target_bits=edge.target_bits,
                        lotus_payload_width=edge.lotus_payload_width,
                        local_payload_bits=edge.local_payload_bits,
                        cost_bits=0.0,
                    ),
                    rank_code,
                )
                + code_cost(model, block_bits, remaining, arity, edge.lotus_payload_width)
            )
            end = index + arity
            if candidate < dp[end]:
                dp[end] = candidate
                prev[end] = (index, arity, edge)
    if dp[atoms] == float("inf"):
        return Cover(False, float("inf"), ())
    cursor = atoms
    records: list[SelectedRecord] = []
    while cursor > 0:
        entry = prev[cursor]
        if entry is None:
            raise AssertionError("missing predecessor")
        prior, arity, edge = entry
        remaining = atoms - prior
        rank = selected_rank_bits(
            SelectedRecord(
                arity=arity,
                rank=edge.rank,
                target_bits=edge.target_bits,
                lotus_payload_width=edge.lotus_payload_width,
                local_payload_bits=edge.local_payload_bits,
                cost_bits=0.0,
            ),
            rank_code,
        )
        stream = code_cost(model, block_bits, remaining, arity, edge.lotus_payload_width)
        records.append(
            SelectedRecord(
                arity=arity,
                rank=edge.rank,
                target_bits=edge.target_bits,
                lotus_payload_width=edge.lotus_payload_width,
                local_payload_bits=edge.local_payload_bits,
                cost_bits=rank + stream,
            )
        )
        cursor = prior
    records.reverse()
    return Cover(True, dp[atoms] + flush_bits, tuple(records))


def fit_suffix_model(
    covers: list[Cover],
    block_bits: int,
    max_arity: int,
    frontier: int,
    alpha: float,
) -> SuffixModel:
    arity_counts: dict[int, Counter[int]] = {}
    delta_counts: dict[tuple[int, int], Counter[int]] = {}
    for cover in covers:
        if not cover.covered:
            continue
        atoms = sum(record.arity for record in cover.records)
        consumed = 0
        for record in cover.records:
            remaining = atoms - consumed
            arity_counts.setdefault(remaining, Counter())[record.arity] += 1
            delta = record.arity * block_bits - record.lotus_payload_width
            delta_counts.setdefault((remaining, record.arity), Counter())[delta] += 1
            consumed += record.arity
    return SuffixModel(arity_counts, delta_counts, max_arity, frontier, alpha)


def train_suffix_model(
    train_samples: list[list[list[EdgeSample]]],
    block_bits: int,
    max_arity: int,
    frontier: int,
    iterations: int,
    alpha: float,
    flush_bits: float,
    rank_code: str,
) -> SuffixModel:
    model = SuffixModel({}, {}, max_arity, frontier, alpha)
    for _ in range(iterations):
        covers = [
            cover_with_suffix_model(
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
        model = fit_suffix_model(covers, block_bits, max_arity, frontier, alpha)
    return model


def split_cover(
    cover: Cover,
    model: SuffixModel,
    block_bits: int,
    rank_code: str,
    flush_bits: float,
) -> SplitTotals:
    atoms = sum(record.arity for record in cover.records)
    consumed = 0
    rank_total = 0.0
    arity_total = 0.0
    delta_total = 0.0
    for record in cover.records:
        remaining = atoms - consumed
        rank_total += selected_rank_bits(record, rank_code)
        arity_total += arity_cost(model, remaining, record.arity)
        delta_total += delta_cost(
            model,
            block_bits,
            remaining,
            record.arity,
            record.lotus_payload_width,
        )
        consumed += record.arity
    return SplitTotals(
        rank_bits=rank_total,
        arity_bits=arity_total,
        delta_bits=delta_total,
        flush_bits=flush_bits,
        records=len(cover.records),
        atoms=atoms,
        avg_arity=mean(record.arity for record in cover.records) if cover.records else 0.0,
        avg_width=mean(record.lotus_payload_width for record in cover.records) if cover.records else 0.0,
    )


def render(
    totals: list[SplitTotals],
    block_bits: int,
    max_arity: int,
    frontier: int,
    rank_code: str,
) -> str:
    raw_bits = totals[0].atoms * block_bits
    records_per_atom = mean(total.records / total.atoms for total in totals)
    avg_arity = mean(total.avg_arity for total in totals)
    avg_width = mean(total.avg_width for total in totals)
    rank_per_record = mean(total.rank_bits / total.records for total in totals)
    arity_per_record = mean(total.arity_bits / total.records for total in totals)
    delta_per_record = mean(total.delta_bits / total.records for total in totals)
    paid_gains = [(raw_bits - total.paid_bits) / total.atoms for total in totals]
    paid_gain = mean(paid_gains)
    paid_missing = max(0.0, -paid_gain / records_per_atom)
    free_delta_gains = [
        (raw_bits - (total.rank_bits + total.arity_bits + total.flush_bits)) / total.atoms
        for total in totals
    ]
    free_delta_gain = mean(free_delta_gains)
    free_stream_gains = [
        (raw_bits - (total.rank_bits + total.flush_bits)) / total.atoms
        for total in totals
    ]
    free_stream_gain = mean(free_stream_gains)
    lines = [
        "# Exact-Suffix Total-Cover Witness Kernel",
        "",
        f"`B={block_bits}`, `K={max_arity}`, `D={frontier}`, rank code `{rank_code}`.",
        "",
        "Public model:",
        "",
        "```text",
        "P(arity | exact remaining atoms)",
        "P(delta | exact remaining atoms, exact arity)",
        "```",
        "",
        "| records/atom | avg arity | avg width | rank bits/rec | arity bits/rec | delta bits/rec | paid gain/atom | missing bits/rec |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        f"| {records_per_atom:.6f} | {avg_arity:.2f} | {avg_width:.2f} | "
        f"{rank_per_record:.3f} | {arity_per_record:.3f} | {delta_per_record:.3f} | "
        f"{paid_gain:.6f} | {paid_missing:.3f} |",
        "",
        "| diagnostic | gain/atom | meaning |",
        "| --- | ---: | --- |",
        f"| paid | {paid_gain:.6f} | honest public suffix model |",
        f"| free_delta | {free_delta_gain:.6f} | lower bound if width/slack were decoder-derived |",
        f"| free_stream | {free_stream_gain:.6f} | lower bound if arity+delta stream were decoder-derived |",
    ]
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--block-bits", type=int, default=4)
    parser.add_argument("--max-arity", type=int, default=128)
    parser.add_argument("--frontier", type=int, default=512)
    parser.add_argument("--atoms", type=int, default=256)
    parser.add_argument("--train-trials", type=int, default=32)
    parser.add_argument("--eval-trials", type=int, default=32)
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--alpha", type=float, default=0.25)
    parser.add_argument("--flush-bits", type=float, default=0.0)
    parser.add_argument("--rank-code", choices=["fixed", "truncated-geometric"], default="fixed")
    parser.add_argument("--seed", type=int, default=911)
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
    model = train_suffix_model(
        train_samples,
        args.block_bits,
        args.max_arity,
        args.frontier,
        args.iterations,
        args.alpha,
        args.flush_bits,
        args.rank_code,
    )
    covers = [
        cover_with_suffix_model(
            trial,
            args.block_bits,
            args.max_arity,
            args.frontier,
            model,
            args.flush_bits,
            args.rank_code,
        )
        for trial in eval_samples
    ]
    covered = [cover for cover in covers if cover.covered]
    if len(covered) != len(covers):
        print(f"coverage {len(covered)}/{len(covers)}; refusing summary on incomplete cover set")
        return
    totals = [split_cover(cover, model, args.block_bits, args.rank_code, args.flush_bits) for cover in covered]
    print(render(totals, args.block_bits, args.max_arity, args.frontier, args.rank_code))


if __name__ == "__main__":
    main()
