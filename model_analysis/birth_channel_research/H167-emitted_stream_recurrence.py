#!/usr/bin/env python3
"""H167 - emitted-stream recurrence control.

H166 leaves one honest loophole: maybe the selected records actually emitted by
a total-cover pass form a visible stream that is unusually fertile on the next
pass. That would be legal: the decoder sees the records, and no discarded
alternatives are stored.

This kernel tests the loophole in the SPEC-style item-stream model used by
H162/H165:

* pass 1 draws a current record stream from the public item grammar;
* an optimal full-cover DP emits selected records, each with visible cost and
  arity;
* pass 2 tries to cover that emitted record-cost sequence using fresh uniform
  hash draws;
* controls keep the same visible costs but randomize content or order.

Under the uniform hash law, future exact-match probabilities depend on visible
target interval length, not on the unseen seed identity that happened to match
the previous layer. Therefore same-cost random content has exactly zero
expected lift over the selected stream. The only possible source-free recurrence
left in this model is a visible length/order effect, which the shuffled-length
control prices.
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
    LITERAL_MARKER_BITS,
    MAX_PAYLOAD_WIDTH_BITS,
    arity_cost,
    j3d1_cost_for_payload_width,
    payload_width_count_le,
)


@dataclass(frozen=True)
class Edge:
    cost: int
    arity: int


@dataclass(frozen=True)
class CoverResult:
    supported: bool
    input_bits: int
    output_bits: int | None
    costs: tuple[int, ...]
    arities: tuple[int, ...]
    sampled_edges: int
    hit_edges: int

    @property
    def record_count(self) -> int:
        return len(self.costs)

    @property
    def avg_arity(self) -> float:
        return sum(self.arities) / len(self.arities) if self.arities else 0.0


@dataclass
class RowSummary:
    block_bits: int
    max_arity: int
    depth_bits: int
    arity_code: str
    mode: str
    item_count: int
    trials: int
    pass1_successes: int = 0
    pass2_successes: int = 0
    shuffled_successes: int = 0
    pass1_input_bits: float = 0.0
    pass1_output_bits: float = 0.0
    pass2_base_input_bits: float = 0.0
    pass2_base_output_bits: float = 0.0
    pass2_base_records: float = 0.0
    pass2_output_bits: float = 0.0
    shuffled_base_input_bits: float = 0.0
    shuffled_output_bits: float = 0.0
    pass1_records: float = 0.0
    pass2_records: float = 0.0
    pass1_arity_sum: float = 0.0
    pass2_arity_sum: float = 0.0
    sampled_edges: int = 0
    hit_edges: int = 0
    shuffled_sampled_edges: int = 0
    shuffled_hit_edges: int = 0

    @property
    def pass1_support(self) -> float:
        return self.pass1_successes / self.trials if self.trials else 0.0

    @property
    def pass2_support_given_pass1(self) -> float:
        return self.pass2_successes / self.pass1_successes if self.pass1_successes else 0.0

    @property
    def shuffled_support_given_pass1(self) -> float:
        return self.shuffled_successes / self.pass1_successes if self.pass1_successes else 0.0

    @property
    def edge_hit_rate(self) -> float:
        return self.hit_edges / self.sampled_edges if self.sampled_edges else 0.0

    @property
    def shuffled_edge_hit_rate(self) -> float:
        return (
            self.shuffled_hit_edges / self.shuffled_sampled_edges
            if self.shuffled_sampled_edges
            else 0.0
        )

    @property
    def pass1_gain_per_item(self) -> float:
        if not self.pass1_successes:
            return 0.0
        return (
            (self.pass1_input_bits - self.pass1_output_bits)
            / self.pass1_successes
            / self.item_count
        )

    @property
    def pass2_delta_per_pass1_record(self) -> float:
        if not self.pass2_successes or not self.pass2_base_records:
            return 0.0
        mean_pass1_output = self.pass2_base_output_bits / self.pass2_successes
        mean_pass2_output = self.pass2_output_bits / self.pass2_successes
        mean_pass1_records = self.pass2_base_records / self.pass2_successes
        return (mean_pass1_output - mean_pass2_output) / mean_pass1_records

    @property
    def final_gain_per_item(self) -> float:
        if not self.pass2_successes:
            return 0.0
        mean_pass1_input = self.pass2_base_input_bits / self.pass2_successes
        mean_pass2_output = self.pass2_output_bits / self.pass2_successes
        return (mean_pass1_input - mean_pass2_output) / self.item_count

    @property
    def shuffled_final_gain_per_item(self) -> float:
        if not self.shuffled_successes:
            return 0.0
        mean_pass1_input = self.shuffled_base_input_bits / self.shuffled_successes
        mean_shuffled_output = self.shuffled_output_bits / self.shuffled_successes
        return (mean_pass1_input - mean_shuffled_output) / self.item_count

    @property
    def length_order_lift_per_item(self) -> float:
        if not self.pass2_successes or not self.shuffled_successes:
            return 0.0
        return self.final_gain_per_item - self.shuffled_final_gain_per_item

    @property
    def records_per_input_item(self) -> float:
        if not self.pass1_successes:
            return 0.0
        return self.pass1_records / self.pass1_successes / self.item_count

    @property
    def pass1_avg_arity(self) -> float:
        return self.pass1_arity_sum / self.pass1_records if self.pass1_records else 0.0

    @property
    def pass2_avg_arity(self) -> float:
        return self.pass2_arity_sum / self.pass2_records if self.pass2_records else 0.0


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


def source_costs_by_arity(
    max_arity: int, depth_bits: int, arity_code: str
) -> dict[int, Counter[int]]:
    if arity_code == "exact" and max_arity > 5:
        raise ValueError("exact V1/J3D1 arity coding only supports K<=5")
    payload_counts = exact_payload_counts_for_depth(depth_bits)
    result: dict[int, Counter[int]] = {}
    for arity in range(1, max_arity + 1):
        costs: Counter[int] = Counter()
        for width, count in payload_counts.items():
            cost = record_arity_cost(arity, max_arity, arity_code) + j3d1_cost_for_payload_width(width)
            costs[cost] += count
        result[arity] = costs
    return result


def item_length_counts(
    block_bits: int, max_arity: int, depth_bits: int, arity_code: str, mode: str
) -> Counter[int]:
    record_counts: Counter[int] = Counter()
    for costs in source_costs_by_arity(max_arity, depth_bits, arity_code).values():
        for cost, count in costs.items():
            record_counts[cost] += count

    literal_len = LITERAL_MARKER_BITS + block_bits
    if mode == "seed_only":
        return record_counts
    if mode == "literal_only":
        return Counter({literal_len: 1 << block_bits})
    if mode == "mixed_all":
        combined = Counter(record_counts)
        combined[literal_len] += 1 << block_bits
        return combined
    raise ValueError(mode)


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
    value = rng.random()
    for length, threshold in cumulative:
        if value <= threshold:
            return length
    return cumulative[-1][0]


def no_hit_probability(source_count: int, target_len: int) -> float:
    if source_count <= 0:
        return 1.0
    if target_len > 1200:
        return 1.0
    unit = 2.0 ** -target_len
    if unit == 0.0:
        return 1.0
    log_no = float(source_count) * math.log1p(-unit)
    if log_no < -745.0:
        return 0.0
    return math.exp(log_no)


def draw_edge(
    rng: random.Random, source_costs: Counter[int], target_len: int, arity: int
) -> Edge | None:
    draw = rng.random()
    cumulative = 0.0
    no_lower = 1.0
    for cost in sorted(source_costs):
        count = source_costs[cost]
        no_this = no_hit_probability(count, target_len)
        best_here = no_lower * (1.0 - no_this)
        cumulative += best_here
        if draw < cumulative:
            return Edge(cost=cost, arity=arity)
        no_lower *= no_this
        if no_lower == 0.0:
            return None
    return None


def cover_fixed_lengths(
    rng: random.Random,
    source_by_arity: dict[int, Counter[int]],
    max_arity: int,
    lengths: list[int],
) -> CoverResult:
    item_count = len(lengths)
    prefix = [0]
    for length in lengths:
        prefix.append(prefix[-1] + length)

    inf = 10**18
    score = [inf] * (item_count + 1)
    prev: list[tuple[int, Edge] | None] = [None] * (item_count + 1)
    score[0] = 0
    sampled_edges = 0
    hit_edges = 0

    for start in range(item_count):
        if score[start] >= inf:
            continue
        for arity in range(1, max_arity + 1):
            end = start + arity
            if end > item_count:
                break
            target_len = prefix[end] - prefix[start]
            sampled_edges += 1
            edge = draw_edge(rng, source_by_arity[arity], target_len, arity)
            if edge is None:
                continue
            hit_edges += 1
            candidate = score[start] + edge.cost
            if candidate < score[end]:
                score[end] = candidate
                prev[end] = (start, edge)

    if score[item_count] >= inf:
        return CoverResult(
            supported=False,
            input_bits=prefix[-1],
            output_bits=None,
            costs=(),
            arities=(),
            sampled_edges=sampled_edges,
            hit_edges=hit_edges,
        )

    costs: list[int] = []
    arities: list[int] = []
    cursor = item_count
    while cursor > 0:
        step = prev[cursor]
        if step is None:
            raise RuntimeError("broken DP predecessor")
        start, edge = step
        costs.append(edge.cost)
        arities.append(edge.arity)
        cursor = start
    costs.reverse()
    arities.reverse()
    return CoverResult(
        supported=True,
        input_bits=prefix[-1],
        output_bits=score[item_count],
        costs=tuple(costs),
        arities=tuple(arities),
        sampled_edges=sampled_edges,
        hit_edges=hit_edges,
    )


def run_row(
    rng: random.Random,
    *,
    block_bits: int,
    max_arity: int,
    depth_bits: int,
    arity_code: str,
    mode: str,
    item_count: int,
    trials: int,
) -> RowSummary:
    source_by_arity = source_costs_by_arity(max_arity, depth_bits, arity_code)
    current_lengths = mass_distribution(
        item_length_counts(block_bits, max_arity, depth_bits, arity_code, mode)
    )
    row = RowSummary(
        block_bits=block_bits,
        max_arity=max_arity,
        depth_bits=depth_bits,
        arity_code=arity_code,
        mode=mode,
        item_count=item_count,
        trials=trials,
    )

    for _ in range(trials):
        lengths = [draw_length(rng, current_lengths) for _ in range(item_count)]
        pass1 = cover_fixed_lengths(rng, source_by_arity, max_arity, lengths)
        row.sampled_edges += pass1.sampled_edges
        row.hit_edges += pass1.hit_edges
        if not pass1.supported or pass1.output_bits is None:
            continue

        row.pass1_successes += 1
        row.pass1_input_bits += pass1.input_bits
        row.pass1_output_bits += pass1.output_bits
        row.pass1_records += pass1.record_count
        row.pass1_arity_sum += sum(pass1.arities)

        emitted_lengths = list(pass1.costs)
        pass2 = cover_fixed_lengths(rng, source_by_arity, max_arity, emitted_lengths)
        row.sampled_edges += pass2.sampled_edges
        row.hit_edges += pass2.hit_edges
        if pass2.supported and pass2.output_bits is not None:
            row.pass2_successes += 1
            row.pass2_base_input_bits += pass1.input_bits
            row.pass2_base_output_bits += pass1.output_bits
            row.pass2_base_records += pass1.record_count
            row.pass2_output_bits += pass2.output_bits
            row.pass2_records += pass2.record_count
            row.pass2_arity_sum += sum(pass2.arities)

        shuffled = list(emitted_lengths)
        rng.shuffle(shuffled)
        shuffled_pass2 = cover_fixed_lengths(rng, source_by_arity, max_arity, shuffled)
        row.shuffled_sampled_edges += shuffled_pass2.sampled_edges
        row.shuffled_hit_edges += shuffled_pass2.hit_edges
        if shuffled_pass2.supported and shuffled_pass2.output_bits is not None:
            row.shuffled_successes += 1
            row.shuffled_base_input_bits += pass1.input_bits
            row.shuffled_output_bits += shuffled_pass2.output_bits

    return row


def fmt(value: float) -> str:
    if value == math.inf:
        return "inf"
    if abs(value) >= 1000.0 or (0.0 < abs(value) < 0.0001):
        return f"{value:.3e}"
    return f"{value:.6f}"


def print_rows(rows: list[RowSummary]) -> None:
    print("== emitted-stream recurrence control ==")
    print("contentLift is exactly 0 under the uniform hash law after visible costs are fixed.")
    print(
        f"{'B':>2} {'K':>2} {'D':>3} {'code':<7} {'mode':<9} {'N':>4} {'trials':>6} "
        f"{'p1sup':>7} {'p2|p1':>7} {'shuf|p1':>8} {'edgeHit':>8} {'shufHit':>8} "
        f"{'p1gain/i':>9} {'p2delta/r':>10} {'final/i':>9} {'shuf/i':>9} "
        f"{'orderLift/i':>11} {'contentLift':>11} {'rec/i':>7} {'a1':>6} {'a2':>6}"
    )
    for row in rows:
        print(
            f"{row.block_bits:2d} {row.max_arity:2d} {row.depth_bits:3d} "
            f"{row.arity_code:<7} {row.mode:<9} {row.item_count:4d} {row.trials:6d} "
            f"{fmt(row.pass1_support):>7} {fmt(row.pass2_support_given_pass1):>7} "
            f"{fmt(row.shuffled_support_given_pass1):>8} {fmt(row.edge_hit_rate):>8} "
            f"{fmt(row.shuffled_edge_hit_rate):>8} {fmt(row.pass1_gain_per_item):>9} "
            f"{fmt(row.pass2_delta_per_pass1_record):>10} {fmt(row.final_gain_per_item):>9} "
            f"{fmt(row.shuffled_final_gain_per_item):>9} "
            f"{fmt(row.length_order_lift_per_item):>11} {fmt(0.0):>11} "
            f"{fmt(row.records_per_input_item):>7} {fmt(row.pass1_avg_arity):>6} "
            f"{fmt(row.pass2_avg_arity):>6}"
        )
    print()


def print_reading(rows: list[RowSummary]) -> None:
    print("== reading ==")
    successful = [row for row in rows if row.pass1_successes]
    if not successful:
        print("No pass-1 full covers; emitted-stream recurrence cannot be evaluated.")
        return
    best_final = max(successful, key=lambda row: row.final_gain_per_item)
    best_order = max(successful, key=lambda row: row.length_order_lift_per_item)
    print(
        f"Best two-pass selected row: B={best_final.block_bits},K={best_final.max_arity},"
        f"D={best_final.depth_bits},{best_final.arity_code}; p2|p1="
        f"{fmt(best_final.pass2_support_given_pass1)}, final/i={fmt(best_final.final_gain_per_item)}."
    )
    print(
        f"Strongest visible order signal: B={best_order.block_bits},K={best_order.max_arity},"
        f"D={best_order.depth_bits},{best_order.arity_code}; orderLift/i="
        f"{fmt(best_order.length_order_lift_per_item)}."
    )
    print(
        "Same-cost random content has no independent fertility channel here: under "
        "uniform hashes, replacing selected seed identities with random identities "
        "of the same visible cost leaves the pass-2 distribution unchanged. A "
        "positive result must therefore show support near 1 and positive final/i "
        "from visible length/order alone, or name a public non-uniform law."
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
    parser.add_argument("--arity-code", choices=["exact", "fixed", "escape5"], default="exact")
    parser.add_argument("--mode", default="seed_only", choices=["seed_only", "mixed_all", "literal_only"])
    parser.add_argument("--items", action="append", default=[])
    parser.add_argument("--trials", type=int, default=60)
    parser.add_argument("--seed", type=int, default=167)
    args = parser.parse_args()

    block_values = parse_int_list(args.block_bits, [8])
    depth_values = parse_int_list(args.depth, [80, 256, 512])
    item_values = parse_int_list(args.items, [32])
    rng = random.Random(args.seed)

    rows: list[RowSummary] = []
    for block_bits in block_values:
        for depth_bits in depth_values:
            for item_count in item_values:
                rows.append(
                    run_row(
                        rng,
                        block_bits=block_bits,
                        max_arity=args.max_arity,
                        depth_bits=depth_bits,
                        arity_code=args.arity_code,
                        mode=args.mode,
                        item_count=item_count,
                        trials=args.trials,
                    )
                )
    print_rows(rows)
    print_reading(rows)


if __name__ == "__main__":
    main()
