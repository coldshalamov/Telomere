#!/usr/bin/env python3
"""H162 - full-cover item-stream DP.

H161 showed a local item-level opportunity: a source record can sometimes be
shorter than the self-delimiting item sequence it expands to. This kernel asks
the next question:

    if the current layer is already a public item stream, can a non-greedy
    full-cover DP choose matching records over 1..K items and get negative
    drift without carries?

It is a Monte Carlo over the exact analytic edge law, not a seed search. For
each sampled target interval, a source record either has no matching seed in the
first 2^D candidates or has a best matching record cost sampled from the exact
order statistic over J3D1 record costs.

By default, `--arity-code exact` uses the current V1/J3D1 arity costs and only
supports K<=5. H163 uses this same harness with explicitly labeled hypothetical
arity grammars (`fixed`, `escape5`) so higher-K tests pay a visible arity cost.

Failure means no complete record cover exists for that sampled item stream.
That is fatal for strict total-cover recursion unless another paid repair
channel is added.
"""

from __future__ import annotations

import argparse
import math
import random
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model_analysis.proof_kernel.costs import (  # noqa: E402
    MAX_PAYLOAD_WIDTH_BITS,
    LITERAL_MARKER_BITS,
    arity_cost,
    j3d1_cost_for_payload_width,
    payload_width_count_le,
)


@dataclass(frozen=True)
class Inventory:
    block_bits: int
    max_arity: int
    depth_bits: int
    arity_code: str
    literal_len: int
    literal_count: int
    item_lengths_by_count: dict[str, Counter[int]]
    source_costs_by_arity: dict[int, Counter[int]]


@dataclass
class Summary:
    block_bits: int
    max_arity: int
    depth_bits: int
    arity_code: str
    mode: str
    item_count: int
    trials: int
    successes: int = 0
    input_bits: float = 0.0
    output_bits: float = 0.0
    selected_records: float = 0.0
    selected_arity: float = 0.0
    sampled_edges: int = 0
    hit_edges: int = 0

    def add_success(self, input_len: int, output_len: int, arities: list[int]) -> None:
        self.successes += 1
        self.input_bits += input_len
        self.output_bits += output_len
        self.selected_records += len(arities)
        self.selected_arity += sum(arities)

    @property
    def support(self) -> float:
        return self.successes / self.trials if self.trials else 0.0

    @property
    def edge_hit_rate(self) -> float:
        return self.hit_edges / self.sampled_edges if self.sampled_edges else 0.0

    @property
    def avg_input_bits(self) -> float:
        return self.input_bits / self.successes if self.successes else 0.0

    @property
    def avg_output_bits(self) -> float:
        return self.output_bits / self.successes if self.successes else 0.0

    @property
    def gain_bits(self) -> float:
        return self.avg_input_bits - self.avg_output_bits

    @property
    def gain_per_item(self) -> float:
        return self.gain_bits / self.item_count if self.successes else 0.0

    @property
    def records_per_item(self) -> float:
        return self.selected_records / (self.successes * self.item_count) if self.successes else 0.0

    @property
    def avg_selected_arity(self) -> float:
        return self.selected_arity / self.selected_records if self.selected_records else 0.0


def exact_payload_counts_for_depth(depth_bits: int) -> Counter[int]:
    seed_count = 1 << depth_bits
    result: Counter[int] = Counter()
    prev = 0
    for width in range(1, MAX_PAYLOAD_WIDTH_BITS + 1):
        cur = min(payload_width_count_le(width), seed_count)
        count = cur - prev
        if count > 0:
            result[width] = count
        prev = cur
        if prev >= seed_count:
            break
    return result


def ceil_log2(value: int) -> int:
    if value <= 1:
        return 0
    return (value - 1).bit_length()


def record_arity_cost(arity: int, max_arity: int, arity_code: str) -> int:
    if arity_code == "exact":
        return arity_cost(arity)
    if arity_code == "fixed":
        return ceil_log2(max_arity)
    if arity_code == "escape5":
        if arity <= 5:
            return arity_cost(arity)
        return 3 + ceil_log2(max_arity - 5)
    raise ValueError(arity_code)


def build_inventory(
    block_bits: int, max_arity: int, depth_bits: int, arity_code: str
) -> Inventory:
    if arity_code == "exact" and max_arity > 5:
        raise ValueError("exact V1/J3D1 arity coding only supports K<=5")
    payload_counts = exact_payload_counts_for_depth(depth_bits)
    source_costs_by_arity: dict[int, Counter[int]] = {}
    record_items_by_len: Counter[int] = Counter()
    for arity in range(1, max_arity + 1):
        costs: Counter[int] = Counter()
        for width, count in payload_counts.items():
            cost = record_arity_cost(arity, max_arity, arity_code) + j3d1_cost_for_payload_width(width)
            costs[cost] += count
            record_items_by_len[cost] += count
        source_costs_by_arity[arity] = costs

    literal_len = LITERAL_MARKER_BITS + block_bits
    literal_items = Counter({literal_len: 1 << block_bits})
    mixed_items = Counter(record_items_by_len)
    mixed_items[literal_len] += 1 << block_bits
    return Inventory(
        block_bits=block_bits,
        max_arity=max_arity,
        depth_bits=depth_bits,
        arity_code=arity_code,
        literal_len=literal_len,
        literal_count=1 << block_bits,
        item_lengths_by_count={
            "literal_only": literal_items,
            "seed_only": record_items_by_len,
            "mixed_all": mixed_items,
        },
        source_costs_by_arity=source_costs_by_arity,
    )


def no_hit_probability(source_count: int, target_len: int) -> float:
    if source_count <= 0:
        return 1.0
    log_no = source_count * math.log1p(-(2.0 ** -target_len))
    if log_no < -745.0:
        return 0.0
    return math.exp(log_no)


def draw_best_cost(rng: random.Random, source_costs: Counter[int], target_len: int) -> int | None:
    draw = rng.random()
    cumulative = 0.0
    no_lower = 1.0
    for cost in sorted(source_costs):
        no_this = no_hit_probability(source_costs[cost], target_len)
        best_here = no_lower * (1.0 - no_this)
        cumulative += best_here
        if draw < cumulative:
            return cost
        no_lower *= no_this
        if no_lower == 0.0:
            return None
    return None


def mass_distribution(length_counts: Counter[int]) -> list[tuple[int, float]]:
    kraft = sum(count * (2.0 ** -length) for length, count in length_counts.items())
    if kraft <= 0.0:
        raise ValueError("empty item grammar")
    cumulative = 0.0
    result: list[tuple[int, float]] = []
    for length in sorted(length_counts):
        cumulative += length_counts[length] * (2.0 ** -length) / kraft
        result.append((length, cumulative))
    result[-1] = (result[-1][0], 1.0)
    return result


def draw_length(rng: random.Random, cumulative: list[tuple[int, float]]) -> int:
    draw = rng.random()
    for length, threshold in cumulative:
        if draw <= threshold:
            return length
    return cumulative[-1][0]


def cover_once(
    rng: random.Random,
    inv: Inventory,
    mode: str,
    item_count: int,
    length_dist: list[tuple[int, float]],
) -> tuple[int, int | None, list[int], int, int]:
    lengths = [draw_length(rng, length_dist) for _ in range(item_count)]
    prefix = [0]
    for length in lengths:
        prefix.append(prefix[-1] + length)

    inf = 10**18
    dp = [inf] * (item_count + 1)
    prev: list[tuple[int, int] | None] = [None] * (item_count + 1)
    dp[0] = 0
    sampled_edges = 0
    hit_edges = 0

    for start in range(item_count):
        if dp[start] >= inf:
            continue
        for arity in range(1, inv.max_arity + 1):
            end = start + arity
            if end > item_count:
                break
            target_len = prefix[end] - prefix[start]
            sampled_edges += 1
            cost = draw_best_cost(rng, inv.source_costs_by_arity[arity], target_len)
            if cost is None:
                continue
            hit_edges += 1
            candidate = dp[start] + cost
            if candidate < dp[end]:
                dp[end] = candidate
                prev[end] = (start, arity)

    if dp[item_count] >= inf:
        return prefix[-1], None, [], sampled_edges, hit_edges

    arities: list[int] = []
    cursor = item_count
    while cursor > 0:
        step = prev[cursor]
        if step is None:
            raise RuntimeError("broken DP predecessor")
        start, arity = step
        arities.append(arity)
        cursor = start
    arities.reverse()
    return prefix[-1], dp[item_count], arities, sampled_edges, hit_edges


def run_row(
    rng: random.Random,
    block_bits: int,
    max_arity: int,
    depth_bits: int,
    arity_code: str,
    mode: str,
    item_count: int,
    trials: int,
) -> Summary:
    inv = build_inventory(block_bits, max_arity, depth_bits, arity_code)
    length_dist = mass_distribution(inv.item_lengths_by_count[mode])
    summary = Summary(block_bits, max_arity, depth_bits, arity_code, mode, item_count, trials)
    for _ in range(trials):
        input_len, output_len, arities, sampled_edges, hit_edges = cover_once(
            rng, inv, mode, item_count, length_dist
        )
        summary.sampled_edges += sampled_edges
        summary.hit_edges += hit_edges
        if output_len is not None:
            summary.add_success(input_len, output_len, arities)
    return summary


def fmt(value: float) -> str:
    if abs(value) >= 1000.0 or (0.0 < abs(value) < 0.0001):
        return f"{value:.3e}"
    return f"{value:.6f}"


def print_summaries(rows: list[Summary]) -> None:
    print("== item-stream full-cover DP ==")
    print("Target item lengths are sampled from the normalized public item-grammar mass.")
    print("Rows are strict: failed cover means this pass cannot be decoded without a repair channel.")
    print(
        f"{'B':>2} {'K':>2} {'D':>3} {'mode':<12} {'N':>4} {'trials':>6} "
        f"{'code':<7} {'support':>8} {'edgeHit':>8} {'inBits':>8} {'outBits':>8} "
        f"{'gain':>9} {'gain/item':>9} {'rec/item':>8} {'avgA':>7}"
    )
    for row in rows:
        print(
            f"{row.block_bits:2d} {row.max_arity:2d} {row.depth_bits:3d} "
            f"{row.mode:<12} {row.item_count:4d} {row.trials:6d} "
            f"{row.arity_code:<7} "
            f"{fmt(row.support):>8} {fmt(row.edge_hit_rate):>8} "
            f"{fmt(row.avg_input_bits):>8} {fmt(row.avg_output_bits):>8} "
            f"{fmt(row.gain_bits):>9} {fmt(row.gain_per_item):>9} "
            f"{fmt(row.records_per_item):>8} {fmt(row.avg_selected_arity):>7}"
        )
    print()


def print_reading(rows: list[Summary]) -> None:
    print("== reading ==")
    successful = [row for row in rows if row.successes > 0]
    if successful:
        best_overall = max(successful, key=lambda row: row.gain_per_item)
        print(
            f"Best successful row: mode={best_overall.mode},B={best_overall.block_bits},"
            f"K={best_overall.max_arity},D={best_overall.depth_bits},"
            f"N={best_overall.item_count},code={best_overall.arity_code}; "
            f"support={fmt(best_overall.support)}, "
            f"gain/item={fmt(best_overall.gain_per_item)}."
        )
    strict = [row for row in rows if row.mode == "seed_only"]
    strict_success = [row for row in strict if row.successes > 0]
    if strict_success:
        best_gain = max(strict_success, key=lambda row: row.gain_per_item)
        best_support = max(strict, key=lambda row: row.support)
        print(
            f"Best strict gain row: B={best_gain.block_bits},K={best_gain.max_arity},"
            f"D={best_gain.depth_bits},N={best_gain.item_count},code={best_gain.arity_code}; "
            f"support={fmt(best_gain.support)}, gain/item={fmt(best_gain.gain_per_item)}."
        )
        print(
            f"Best strict support row: B={best_support.block_bits},K={best_support.max_arity},"
            f"D={best_support.depth_bits},N={best_support.item_count},code={best_support.arity_code}; "
            f"support={fmt(best_support.support)}, gain/item={fmt(best_support.gain_per_item)}."
        )
    elif strict:
        best_support = max(strict, key=lambda row: row.support)
        print(
            f"No strict seed-only row produced a successful full cover. Best support row: "
            f"B={best_support.block_bits},K={best_support.max_arity},"
            f"D={best_support.depth_bits},N={best_support.item_count},code={best_support.arity_code}; "
            f"support={fmt(best_support.support)}."
        )
    print(
        "A positive gain among successful covers is not enough: strict total-cover "
        "recursion also needs support near 1, or an explicitly paid repair/fallback channel."
    )


def parse_int_list(values: list[str], default: list[int]) -> list[int]:
    if not values:
        return default
    result: list[int] = []
    for raw in values:
        result.extend(int(part) for part in raw.split(",") if part)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--block-bits", action="append", default=[])
    parser.add_argument("--max-arity", type=int, default=5)
    parser.add_argument("--depth", action="append", default=[])
    parser.add_argument("--mode", action="append", default=[])
    parser.add_argument("--items", action="append", default=[])
    parser.add_argument("--arity-code", choices=["exact", "fixed", "escape5"], default="exact")
    parser.add_argument("--trials", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=162)
    args = parser.parse_args()

    block_values = parse_int_list(args.block_bits, [8])
    depth_values = parse_int_list(args.depth, [8, 16, 24, 32, 40])
    item_values = parse_int_list(args.items, [16, 32])
    modes = args.mode or ["seed_only", "mixed_all"]
    rng = random.Random(args.seed)

    rows: list[Summary] = []
    for block_bits in block_values:
        for depth_bits in depth_values:
            for mode in modes:
                for item_count in item_values:
                    rows.append(
                        run_row(
                            rng=rng,
                            block_bits=block_bits,
                            max_arity=args.max_arity,
                            depth_bits=depth_bits,
                            arity_code=args.arity_code,
                            mode=mode,
                            item_count=item_count,
                            trials=args.trials,
                        )
                    )
    print_summaries(rows)
    print_reading(rows)


if __name__ == "__main__":
    main()
