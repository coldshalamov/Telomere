#!/usr/bin/env python3
"""H165 - fertility option DP.

H164 set the target for fertility-selected superposition: current strict rows
need at least 8.36 bits of future value per selected record. This kernel asks
whether the actual same-current-cost multiplicity in the matching seed bucket
can plausibly supply that value.

For each candidate interval, the first matching source-cost bucket is sampled
under the uniform hash law. The optimistic fertility credit for that edge is:

    E[log2(number of matching witnesses in the winning bucket) | bucket nonempty]

That is an upper bound on how much future value can be extracted by choosing
the most fertile witness inside the same visible current cost. The `value`
objective goes further and lets the cover DP select edges by raw_cost-credit,
while reporting the raw current cost separately.
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
class Edge:
    raw_cost: int
    option_bits: float
    arity: int


@dataclass
class Summary:
    label: str
    block_bits: int
    max_arity: int
    depth_bits: int
    arity_code: str
    mode: str
    item_count: int
    objective: str
    trials: int
    successes: int = 0
    input_bits: float = 0.0
    output_bits: float = 0.0
    option_bits: float = 0.0
    selected_records: float = 0.0
    selected_arity: float = 0.0
    sampled_edges: int = 0
    hit_edges: int = 0

    def add_success(self, input_len: int, raw_cost: int, option: float, arities: list[int]) -> None:
        self.successes += 1
        self.input_bits += input_len
        self.output_bits += raw_cost
        self.option_bits += option
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
    def current_gain_per_item(self) -> float:
        if not self.successes:
            return 0.0
        return (self.avg_input_bits - self.avg_output_bits) / self.item_count

    @property
    def option_per_item(self) -> float:
        if not self.successes:
            return 0.0
        return (self.option_bits / self.successes) / self.item_count

    @property
    def optimistic_gain_per_item(self) -> float:
        return self.current_gain_per_item + self.option_per_item

    @property
    def records_per_item(self) -> float:
        return self.selected_records / (self.successes * self.item_count) if self.successes else 0.0

    @property
    def option_per_record(self) -> float:
        return self.option_bits / self.selected_records if self.selected_records else 0.0

    @property
    def effective_alternatives(self) -> float:
        return 2.0 ** self.option_per_record if self.selected_records else 0.0

    @property
    def current_miss_per_record(self) -> float:
        miss_per_item = max(0.0, -self.current_gain_per_item)
        return miss_per_item / self.records_per_item if self.records_per_item else math.inf

    @property
    def avg_selected_arity(self) -> float:
        return self.selected_arity / self.selected_records if self.selected_records else 0.0


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


def source_costs_by_arity(max_arity: int, depth_bits: int, arity_code: str) -> dict[int, Counter[int]]:
    if arity_code == "exact" and max_arity > 5:
        raise ValueError("exact arity mode only supports K<=5")
    payload_counts = exact_payload_counts_for_depth(depth_bits)
    by_arity: dict[int, Counter[int]] = {}
    for arity in range(1, max_arity + 1):
        costs: Counter[int] = Counter()
        for width, count in payload_counts.items():
            cost = record_arity_cost(arity, max_arity, arity_code) + j3d1_cost_for_payload_width(width)
            costs[cost] += count
        by_arity[arity] = costs
    return by_arity


def item_counts(
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
        result = Counter(record_counts)
        result[literal_len] += 1 << block_bits
        return result
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
    draw = rng.random()
    for length, threshold in cumulative:
        if draw <= threshold:
            return length
    return cumulative[-1][0]


def no_hit_probability(source_count: int, target_len: int) -> float:
    if source_count <= 0:
        return 1.0
    log_no = source_count * math.log1p(-(2.0 ** -target_len))
    if log_no < -745.0:
        return 0.0
    return math.exp(log_no)


def expected_log2_positive_poisson(lam: float) -> float:
    if lam <= 0.0:
        return 0.0
    nonzero = 1.0 - math.exp(-lam) if lam < 745.0 else 1.0
    if nonzero <= 0.0:
        return 0.0
    if lam > 80.0:
        # Concavity correction is tiny for this diagnostic upper bound.
        return math.log2(lam)

    p = math.exp(-lam)
    total = 0.0
    # Start at k=1 from the k=0 probability.
    for k in range(1, 10000):
        p *= lam / k
        total += math.log2(k) * p
        if k > lam + 20.0 * math.sqrt(max(lam, 1.0)) and p < 1e-15:
            break
    return total / nonzero


def option_bits_for_bucket(source_count: int, target_len: int) -> float:
    # Poissonization is accurate in the sparse exact-match regime and gives an
    # optimistic neutral-multiplicity credit for enormous seed buckets.
    lam = math.ldexp(float(source_count), -target_len) if target_len < 1024 else 0.0
    return expected_log2_positive_poisson(lam)


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
            return Edge(
                raw_cost=cost,
                option_bits=option_bits_for_bucket(count, target_len),
                arity=arity,
            )
        no_lower *= no_this
        if no_lower == 0.0:
            return None
    return None


def cover_once(
    rng: random.Random,
    source_by_arity: dict[int, Counter[int]],
    max_arity: int,
    item_count: int,
    length_dist: list[tuple[int, float]],
    objective: str,
) -> tuple[int, int | None, float, list[int], int, int]:
    lengths = [draw_length(rng, length_dist) for _ in range(item_count)]
    prefix = [0]
    for length in lengths:
        prefix.append(prefix[-1] + length)

    inf = 10.0**100
    score = [inf] * (item_count + 1)
    raw = [0] * (item_count + 1)
    option = [0.0] * (item_count + 1)
    prev: list[tuple[int, Edge] | None] = [None] * (item_count + 1)
    score[0] = 0.0
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
            edge_score = edge.raw_cost
            if objective == "value":
                edge_score -= edge.option_bits
            elif objective != "raw":
                raise ValueError(objective)
            candidate = score[start] + edge_score
            if candidate < score[end]:
                score[end] = candidate
                raw[end] = raw[start] + edge.raw_cost
                option[end] = option[start] + edge.option_bits
                prev[end] = (start, edge)

    if score[item_count] >= inf:
        return prefix[-1], None, 0.0, [], sampled_edges, hit_edges

    arities: list[int] = []
    cursor = item_count
    while cursor > 0:
        step = prev[cursor]
        if step is None:
            raise RuntimeError("broken DP predecessor")
        start, edge = step
        arities.append(edge.arity)
        cursor = start
    arities.reverse()
    return prefix[-1], raw[item_count], option[item_count], arities, sampled_edges, hit_edges


def run_row(
    rng: random.Random,
    block_bits: int,
    max_arity: int,
    depth_bits: int,
    arity_code: str,
    mode: str,
    item_count: int,
    objective: str,
    trials: int,
) -> Summary:
    source_by_arity = source_costs_by_arity(max_arity, depth_bits, arity_code)
    lengths = item_counts(block_bits, max_arity, depth_bits, arity_code, mode)
    length_dist = mass_distribution(lengths)
    summary = Summary(
        label=f"K{max_arity} D{depth_bits} {arity_code} {objective}",
        block_bits=block_bits,
        max_arity=max_arity,
        depth_bits=depth_bits,
        arity_code=arity_code,
        mode=mode,
        item_count=item_count,
        objective=objective,
        trials=trials,
    )
    for _ in range(trials):
        input_len, raw_cost, option, arities, sampled, hits = cover_once(
            rng, source_by_arity, max_arity, item_count, length_dist, objective
        )
        summary.sampled_edges += sampled
        summary.hit_edges += hits
        if raw_cost is not None:
            summary.add_success(input_len, raw_cost, option, arities)
    return summary


def fmt(value: float) -> str:
    if value == math.inf:
        return "inf"
    if abs(value) >= 1000.0 or (0.0 < abs(value) < 0.0001):
        return f"{value:.3e}"
    return f"{value:.6f}"


def print_rows(rows: list[Summary]) -> None:
    print("== fertility option DP ==")
    print("option/rec is an optimistic same-cost witness multiplicity credit, not proven future compression.")
    print(
        f"{'B':>2} {'K':>2} {'D':>3} {'code':<7} {'mode':<9} {'obj':<5} "
        f"{'N':>4} {'trials':>6} {'support':>8} {'edgeHit':>8} "
        f"{'gain/item':>10} {'opt/item':>9} {'net/item':>9} "
        f"{'rec/item':>8} {'miss/rec':>9} {'opt/rec':>8} {'M_eq':>8} {'avgA':>7}"
    )
    for row in rows:
        print(
            f"{row.block_bits:2d} {row.max_arity:2d} {row.depth_bits:3d} "
            f"{row.arity_code:<7} {row.mode:<9} {row.objective:<5} "
            f"{row.item_count:4d} {row.trials:6d} {fmt(row.support):>8} "
            f"{fmt(row.edge_hit_rate):>8} {fmt(row.current_gain_per_item):>10} "
            f"{fmt(row.option_per_item):>9} {fmt(row.optimistic_gain_per_item):>9} "
            f"{fmt(row.records_per_item):>8} {fmt(row.current_miss_per_record):>9} "
            f"{fmt(row.option_per_record):>8} {fmt(row.effective_alternatives):>8} "
            f"{fmt(row.avg_selected_arity):>7}"
        )
    print()


def print_reading(rows: list[Summary]) -> None:
    print("== reading ==")
    successful = [row for row in rows if row.successes > 0]
    if not successful:
        print("No successful covers.")
        return
    best_net = max(successful, key=lambda row: row.optimistic_gain_per_item)
    best_option = max(successful, key=lambda row: row.option_per_record)
    print(
        f"Best optimistic net row: {best_net.label}; support={fmt(best_net.support)}, "
        f"net/item={fmt(best_net.optimistic_gain_per_item)}, "
        f"option/rec={fmt(best_net.option_per_record)}, "
        f"M_eq={fmt(best_net.effective_alternatives)}."
    )
    print(
        f"Largest option/record row: {best_option.label}; option/rec={fmt(best_option.option_per_record)}, "
        f"M_eq={fmt(best_option.effective_alternatives)}, "
        f"miss/rec={fmt(best_option.current_miss_per_record)}."
    )
    print(
        "If option/rec is far below miss/rec, same-cost neutral multiplicity cannot "
        "supply the H164 fertility value even under this optimistic credit."
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
    parser.add_argument("--objective", action="append", default=[])
    parser.add_argument("--trials", type=int, default=500)
    parser.add_argument("--seed", type=int, default=165)
    args = parser.parse_args()

    block_values = parse_int_list(args.block_bits, [8])
    depth_values = parse_int_list(args.depth, [80, 256, 512])
    item_values = parse_int_list(args.items, [32])
    objectives = args.objective or ["raw", "value"]
    rng = random.Random(args.seed)

    rows: list[Summary] = []
    for block_bits in block_values:
        for depth_bits in depth_values:
            for item_count in item_values:
                for objective in objectives:
                    rows.append(
                        run_row(
                            rng,
                            block_bits=block_bits,
                            max_arity=args.max_arity,
                            depth_bits=depth_bits,
                            arity_code=args.arity_code,
                            mode=args.mode,
                            item_count=item_count,
                            objective=objective,
                            trials=args.trials,
                        )
                    )
    print_rows(rows)
    print_reading(rows)


if __name__ == "__main__":
    main()
