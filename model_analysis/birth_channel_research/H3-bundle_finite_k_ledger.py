#!/usr/bin/env python3
"""Finite-K length-pinned bundle ledger.

This is a first-principles accounting kernel, not a compression benchmark.

It prices the best remaining constructive salted branch:

* fixed-arity bundles with fresh pass/position salts;
* no stored birth tags;
* a finite structural wrong-pass rejection budget E_a;
* exact V1/J3D1 record costs for arities 2..5;
* uniform-law hit density against literal item streams.

The key correction versus a tempting false positive is that a seed expansion
must reproduce the previous-layer *items*, not just raw payload bytes. For raw
literal atoms, that target includes literal markers. Those marker bits are the
same structure that makes wrong-pass parsing fail; they are not free hit supply.
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

from model_analysis.proof_kernel.costs import (  # noqa: E402
    MAX_PAYLOAD_WIDTH_BITS,
    payload_width_count_exact,
    record_cost_for_payload_width,
)


STRUCTURAL_BITS = {
    2: 9.36,
    3: 12.59,
    4: 14.97,
    5: 18.20,
}


@dataclass(frozen=True)
class SeedFrontier:
    seed_count: int
    avg_raw_savings: float
    max_payload_width: int


@dataclass(frozen=True)
class LedgerRow:
    arity: int
    passes: int
    structural_bits: float
    seed_count_log2: float
    target_bits: int
    hit_probability: float
    selected_records_per_atom: float
    coverage: float
    avg_raw_savings: float
    birth_residual: float
    net_per_selected: float
    optimistic_gain_per_atom: float
    literal_overhead_per_atom: float
    charged_gain_per_atom: float


def log2_count(value: int) -> float:
    if value <= 0:
        return float("-inf")
    return math.log2(value)


def hit_probability(seed_count: int, target_bits: int, passes: int) -> float:
    if seed_count <= 0:
        return 0.0
    per_pass = seed_count * (2.0 ** (-target_bits))
    if per_pass >= 1.0:
        return 1.0
    return -math.expm1(passes * math.log1p(-per_pass))


def selected_records_per_atom(hit_p: float, arity: int) -> float:
    # Mean-field greedy interval packing. It is optimistic enough for a ledger:
    # sparse p -> p records/start, p=1 -> the hard cap 1/arity.
    if hit_p <= 0.0:
        return 0.0
    return hit_p / (1.0 + (arity - 1) * hit_p)


def birth_residual_bits(passes: int, structural_bits: float) -> float:
    return math.log2(1.0 + (passes - 1) * (2.0 ** (-structural_bits)))


def profitable_frontier(block_bits: int, arity: int, min_raw_savings: float) -> SeedFrontier:
    raw_bits = arity * block_bits
    seed_count = 0
    weighted_savings = 0.0
    max_width = 0
    for payload_width in range(1, MAX_PAYLOAD_WIDTH_BITS + 1):
        record_bits = record_cost_for_payload_width(arity, payload_width)
        raw_savings = raw_bits - record_bits
        if raw_savings < min_raw_savings:
            if payload_width > raw_bits + 16:
                break
            continue
        count = payload_width_count_exact(payload_width)
        seed_count += count
        weighted_savings += count * raw_savings
        max_width = payload_width
    avg = weighted_savings / seed_count if seed_count else 0.0
    return SeedFrontier(seed_count, avg, max_width)


def evaluate(
    block_bits: int,
    literal_marker_bits: int,
    arity: int,
    passes: int,
    min_raw_savings: float,
) -> LedgerRow:
    frontier = profitable_frontier(block_bits, arity, min_raw_savings)
    target_bits = arity * (block_bits + literal_marker_bits)
    hit_p = hit_probability(frontier.seed_count, target_bits, passes)
    selected = selected_records_per_atom(hit_p, arity)
    structural = STRUCTURAL_BITS[arity]
    residual = birth_residual_bits(passes, structural)
    net = frontier.avg_raw_savings - residual
    coverage = min(1.0, arity * selected)
    literal_overhead = (1.0 - coverage) * literal_marker_bits
    optimistic_gain = selected * net
    return LedgerRow(
        arity=arity,
        passes=passes,
        structural_bits=structural,
        seed_count_log2=log2_count(frontier.seed_count),
        target_bits=target_bits,
        hit_probability=hit_p,
        selected_records_per_atom=selected,
        coverage=coverage,
        avg_raw_savings=frontier.avg_raw_savings,
        birth_residual=residual,
        net_per_selected=net,
        optimistic_gain_per_atom=optimistic_gain,
        literal_overhead_per_atom=literal_overhead,
        charged_gain_per_atom=optimistic_gain - literal_overhead,
    )


def default_passes() -> list[int]:
    values = {64, 1024, 100_000, 300_000, 1_000_000}
    for e in STRUCTURAL_BITS.values():
        values.add(max(1, round(2.0 ** e)))
    return sorted(values)


def render(rows: list[LedgerRow], block_bits: int, literal_marker_bits: int, min_raw_savings: float) -> str:
    lines = [
        "# Finite-K Bundle Ledger",
        "",
        f"`B={block_bits}`, literal marker bits per raw atom item = `{literal_marker_bits}`, "
        f"minimum raw savings per seed record = `{min_raw_savings}`.",
        "",
        "Hit probability is against literal item targets, so target bits are",
        "`arity * (B + literal_marker_bits)`. This prices the grammar bits that",
        "make wrong-pass openings fail structurally.",
        "",
        "| arity | passes | E | log2 seeds | target bits | hit p/window | selected rec/atom | coverage | avg raw save | birth residual | net/selected | optimistic gain/atom | literal overhead/atom | charged gain/atom |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row.arity} | {row.passes} | {row.structural_bits:.2f} | "
            f"{row.seed_count_log2:.2f} | {row.target_bits} | {row.hit_probability:.6g} | "
            f"{row.selected_records_per_atom:.6g} | {row.coverage:.6g} | "
            f"{row.avg_raw_savings:.3f} | {row.birth_residual:.3f} | "
            f"{row.net_per_selected:.3f} | {row.optimistic_gain_per_atom:.6g} | "
            f"{row.literal_overhead_per_atom:.6g} | {row.charged_gain_per_atom:.6g} |"
        )
    best = max(rows, key=lambda row: row.charged_gain_per_atom)
    lines.extend(
        [
            "",
            "## Best Charged Row",
            "",
            f"`arity={best.arity}, passes={best.passes}` gives "
            f"`{best.charged_gain_per_atom:.6g}` bits/input atom after charging "
            "literal markers on uncovered atoms, but before finite-file header "
            "and any extra open-map costs.",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--block-bits", type=int, default=8)
    parser.add_argument("--literal-marker-bits", type=int, default=3)
    parser.add_argument("--min-raw-savings", type=float, default=1.0)
    parser.add_argument("--arities", type=int, nargs="+", default=[2, 3, 4, 5])
    parser.add_argument("--passes", type=int, nargs="+", default=default_passes())
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = [
        evaluate(args.block_bits, args.literal_marker_bits, arity, passes, args.min_raw_savings)
        for arity in args.arities
        for passes in args.passes
    ]
    rows.sort(key=lambda row: (row.arity, row.passes))
    print(render(rows, args.block_bits, args.literal_marker_bits, args.min_raw_savings))


if __name__ == "__main__":
    main()
