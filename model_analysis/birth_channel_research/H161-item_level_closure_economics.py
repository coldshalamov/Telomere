#!/usr/bin/env python3
"""H161 - item-level closure economics.

H160 killed a bit-level H96 surrogate: source records emitted fewer raw bits
than they cost. SPEC_V1's decoder is item-level, though:

    a record of arity a expands to exactly a self-delimiting items

Those target items may be literals or records. This kernel prices that actual
shape analytically under the uniform hash law. It does not search seeds.

For each target grammar mode:

* literal_only: target items are literal-wrapped B-bit blocks;
* seed_only: target items are record items only;
* mixed_all: target items may be literals or records.

For every a-item target length L, and source arity a, it computes the expected
best matching source record cost from the public seed inventory:

    Pr(best cost = c) =
      Pr(no source with cost < c matches) * Pr(at least one cost-c source matches)

where each source seed matches that exact L-bit target with probability 2^-L.

This exposes the real item-level tradeoff:

    target item closure can make L much larger than the source record cost,
    but the match probability must still pay for the L-bit exact string.
"""

from __future__ import annotations

import argparse
import math
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
    literal_len: int
    literal_count: int
    record_items_by_len: Counter[int]
    record_costs_by_arity: dict[int, Counter[int]]


@dataclass(frozen=True)
class ModeRow:
    block_bits: int
    max_arity: int
    depth_bits: int
    mode: str
    target_arity: int
    item_kraft: float
    sequence_kraft: float
    sequence_closure_tax: float
    seed_item_mass_fraction: float
    total_target_sequences: int
    average_target_len_by_count: float
    average_target_len_by_mass: float
    hit_probability_by_count: float
    accepted_probability_by_count: float
    expected_saving_by_count: float
    expected_gain_if_hit: float
    expected_gain_if_accepted: float
    uniform_hit_mass: float
    uniform_accepted_mass: float
    uniform_saving_mass: float
    best_length_gain: float
    best_length: int
    best_hit_probability: float
    best_accepted_probability: float
    best_expected_saving: float
    best_source_cost_with_mass: int


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


def build_inventory(block_bits: int, max_arity: int, depth_bits: int) -> Inventory:
    payload_counts = exact_payload_counts_for_depth(depth_bits)
    record_items_by_len: Counter[int] = Counter()
    record_costs_by_arity: dict[int, Counter[int]] = {}
    for arity in range(1, max_arity + 1):
        costs: Counter[int] = Counter()
        for width, count in payload_counts.items():
            cost = arity_cost(arity) + j3d1_cost_for_payload_width(width)
            costs[cost] += count
            record_items_by_len[cost] += count
        record_costs_by_arity[arity] = costs
    literal_len = LITERAL_MARKER_BITS + block_bits
    return Inventory(
        block_bits=block_bits,
        max_arity=max_arity,
        depth_bits=depth_bits,
        literal_len=literal_len,
        literal_count=1 << block_bits,
        record_items_by_len=record_items_by_len,
        record_costs_by_arity=record_costs_by_arity,
    )


def convolve_counts(left: Counter[int], right: Counter[int]) -> Counter[int]:
    result: Counter[int] = Counter()
    for left_len, left_count in left.items():
        for right_len, right_count in right.items():
            result[left_len + right_len] += left_count * right_count
    return result


def sequence_counts(item_counts: Counter[int], arity: int) -> Counter[int]:
    result: Counter[int] = Counter({0: 1})
    for _ in range(arity):
        result = convolve_counts(result, item_counts)
    result.pop(0, None)
    return result


def item_counts_for_mode(inv: Inventory, mode: str) -> Counter[int]:
    if mode == "literal_only":
        return Counter({inv.literal_len: inv.literal_count})
    if mode == "seed_only":
        return Counter(inv.record_items_by_len)
    if mode == "mixed_all":
        counts = Counter(inv.record_items_by_len)
        counts[inv.literal_len] += inv.literal_count
        return counts
    raise ValueError(mode)


def seed_mass_fraction_for_mode(inv: Inventory, mode: str, item_kraft: float) -> float:
    if mode == "literal_only":
        return 0.0
    if mode == "seed_only":
        return 1.0
    record_mass = sum(count * (2.0 ** -length) for length, count in inv.record_items_by_len.items())
    return safe_div(record_mass, item_kraft)


def source_cost_distribution(inv: Inventory, arity: int) -> Counter[int]:
    return Counter(inv.record_costs_by_arity[arity])


def no_hit_probability(source_count: int, target_len: int) -> float:
    if source_count <= 0:
        return 1.0
    # Stable for tiny 2^-L and huge source_count.
    log_no = source_count * math.log1p(-(2.0 ** -target_len))
    if log_no < -745.0:
        return 0.0
    return math.exp(log_no)


def best_cost_stats(
    source_costs: Counter[int], target_len: int
) -> tuple[float, float, float, float, float, int]:
    """Return P(hit), P(compressive hit), E(saving), gains, and first cost."""

    no_lower = 1.0
    hit_probability = 0.0
    accepted_probability = 0.0
    expected_saving = 0.0
    first_cost = 0
    for cost in sorted(source_costs):
        count = source_costs[cost]
        if first_cost == 0:
            first_cost = cost
        no_this = no_hit_probability(count, target_len)
        best_here = no_lower * (1.0 - no_this)
        hit_probability += best_here
        if cost < target_len:
            accepted_probability += best_here
            expected_saving += (target_len - cost) * best_here
        no_lower *= no_this
        if no_lower == 0.0:
            break
    gain_if_hit = expected_saving / hit_probability if hit_probability > 0.0 else 0.0
    gain_if_accepted = (
        expected_saving / accepted_probability if accepted_probability > 0.0 else 0.0
    )
    return (
        hit_probability,
        accepted_probability,
        expected_saving,
        gain_if_hit,
        gain_if_accepted,
        first_cost,
    )


def safe_div(num: float, den: float) -> float:
    return num / den if den else 0.0


def row_for(inv: Inventory, mode: str, target_arity: int) -> ModeRow:
    item_counts = item_counts_for_mode(inv, mode)
    seq_counts = sequence_counts(item_counts, target_arity)
    source_costs = source_cost_distribution(inv, target_arity)
    item_kraft = sum(count * (2.0 ** -length) for length, count in item_counts.items())
    seed_fraction = seed_mass_fraction_for_mode(inv, mode, item_kraft)
    sequence_kraft = sum(count * (2.0 ** -length) for length, count in seq_counts.items())
    total_sequences = sum(seq_counts.values())
    count_len_sum = sum(length * count for length, count in seq_counts.items())
    mass_len_sum = sum(length * count * (2.0 ** -length) for length, count in seq_counts.items())

    hit_by_count = 0.0
    accepted_by_count = 0.0
    saving_by_count = 0.0
    hit_mass = 0.0
    accepted_mass = 0.0
    saving_mass = 0.0
    best_length = 0
    best_hit = 0.0
    best_accepted = 0.0
    best_saving = float("-inf")
    best_gain = float("-inf")
    best_first_cost = 0

    for target_len, count in seq_counts.items():
        hit, accepted, saving, _gain_if_hit, gain_if_accepted, first_cost = best_cost_stats(
            source_costs, target_len
        )
        hit_by_count += count * hit
        accepted_by_count += count * accepted
        saving_by_count += count * saving
        mass = count * (2.0 ** -target_len)
        hit_mass += mass * hit
        accepted_mass += mass * accepted
        saving_mass += mass * saving
        if saving > best_saving:
            best_length = target_len
            best_hit = hit
            best_accepted = accepted
            best_saving = saving
            best_gain = gain_if_accepted
            best_first_cost = first_cost

    avg_hit = safe_div(hit_by_count, total_sequences)
    avg_accepted = safe_div(accepted_by_count, total_sequences)
    avg_saving = safe_div(saving_by_count, total_sequences)
    return ModeRow(
        block_bits=inv.block_bits,
        max_arity=inv.max_arity,
        depth_bits=inv.depth_bits,
        mode=mode,
        target_arity=target_arity,
        item_kraft=item_kraft,
        sequence_kraft=sequence_kraft,
        sequence_closure_tax=-math.log2(sequence_kraft) if sequence_kraft > 0.0 else math.inf,
        seed_item_mass_fraction=seed_fraction,
        total_target_sequences=total_sequences,
        average_target_len_by_count=safe_div(count_len_sum, total_sequences),
        average_target_len_by_mass=safe_div(mass_len_sum, sequence_kraft),
        hit_probability_by_count=avg_hit,
        accepted_probability_by_count=avg_accepted,
        expected_saving_by_count=avg_saving,
        expected_gain_if_hit=safe_div(avg_saving, avg_hit),
        expected_gain_if_accepted=safe_div(avg_saving, avg_accepted),
        uniform_hit_mass=hit_mass,
        uniform_accepted_mass=accepted_mass,
        uniform_saving_mass=saving_mass,
        best_length_gain=best_gain,
        best_length=best_length,
        best_hit_probability=best_hit,
        best_accepted_probability=best_accepted,
        best_expected_saving=max(0.0, best_saving),
        best_source_cost_with_mass=best_first_cost,
    )


def fmt(value: float) -> str:
    if value == float("inf"):
        return "inf"
    if value == float("-inf"):
        return "-inf"
    if abs(value) >= 1000.0 or (0.0 < abs(value) < 0.0001):
        return f"{value:.3e}"
    return f"{value:.6f}"


def compact_int(value: int) -> str:
    if value >= 1_000_000:
        return f"{value:.3e}"
    return str(value)


def print_rows(rows: list[ModeRow]) -> None:
    print("== item-level closure economics ==")
    print("Conditioned columns are over valid target item sequences; mass columns are under uniform bits.")
    print(
        f"{'B':>2} {'K':>2} {'D':>3} {'mode':<12} {'a':>2} "
        f"{'itemK':>8} {'seqK':>8} {'seqTax':>8} {'seedF':>7} {'seq#':>9} "
        f"{'Lcnt':>8} {'Lmass':>8} {'hit|seq':>9} {'acc|seq':>9} "
        f"{'save|seq':>9} {'gain|acc':>9} {'hitMass':>9} "
        f"{'accMass':>9} {'saveMass':>9} {'bestL':>5} "
        f"{'bestAcc':>8} {'bestSave':>9} {'firstC':>6}"
    )
    for row in rows:
        print(
            f"{row.block_bits:2d} {row.max_arity:2d} {row.depth_bits:3d} "
            f"{row.mode:<12} {row.target_arity:2d} "
            f"{fmt(row.item_kraft):>8} {fmt(row.sequence_kraft):>8} "
            f"{fmt(row.sequence_closure_tax):>8} "
            f"{fmt(row.seed_item_mass_fraction):>7} "
            f"{compact_int(row.total_target_sequences):>9} "
            f"{fmt(row.average_target_len_by_count):>8} "
            f"{fmt(row.average_target_len_by_mass):>8} "
            f"{fmt(row.hit_probability_by_count):>9} "
            f"{fmt(row.accepted_probability_by_count):>9} "
            f"{fmt(row.expected_saving_by_count):>9} "
            f"{fmt(row.expected_gain_if_accepted):>9} "
            f"{fmt(row.uniform_hit_mass):>9} "
            f"{fmt(row.uniform_accepted_mass):>9} "
            f"{fmt(row.uniform_saving_mass):>9} "
            f"{row.best_length:5d} {fmt(row.best_accepted_probability):>8} "
            f"{fmt(row.best_expected_saving):>9} "
            f"{row.best_source_cost_with_mass:6d}"
        )
    print()


def print_reading(rows: list[ModeRow]) -> None:
    print("== reading ==")
    seed_rows = [row for row in rows if row.mode == "seed_only"]
    mixed_rows = [row for row in rows if row.mode == "mixed_all"]
    best_seed = max(seed_rows, key=lambda row: row.expected_saving_by_count) if seed_rows else None
    best_seed_mass = max(seed_rows, key=lambda row: row.uniform_saving_mass) if seed_rows else None
    best_mixed = max(mixed_rows, key=lambda row: row.expected_saving_by_count) if mixed_rows else None
    if best_seed is not None:
        print(
            f"Best seed-only conditioned row: B={best_seed.block_bits},K={best_seed.max_arity},"
            f"D={best_seed.depth_bits},a={best_seed.target_arity}; "
            f"hit|seq={fmt(best_seed.hit_probability_by_count)}, "
            f"acc|seq={fmt(best_seed.accepted_probability_by_count)}, "
            f"save|seq={fmt(best_seed.expected_saving_by_count)}, "
            f"seqK={fmt(best_seed.sequence_kraft)}."
        )
    if best_seed_mass is not None:
        print(
            f"Best seed-only uniform-mass row: B={best_seed_mass.block_bits},"
            f"K={best_seed_mass.max_arity},D={best_seed_mass.depth_bits},"
            f"a={best_seed_mass.target_arity}; hitMass={fmt(best_seed_mass.uniform_hit_mass)}, "
            f"accMass={fmt(best_seed_mass.uniform_accepted_mass)}, "
            f"saveMass={fmt(best_seed_mass.uniform_saving_mass)}, "
            f"seqK={fmt(best_seed_mass.sequence_kraft)}."
        )
    if best_mixed is not None:
        print(
            f"Best mixed conditioned row: B={best_mixed.block_bits},K={best_mixed.max_arity},"
            f"D={best_mixed.depth_bits},a={best_mixed.target_arity}; "
            f"hit|seq={fmt(best_mixed.hit_probability_by_count)}, "
            f"acc|seq={fmt(best_mixed.accepted_probability_by_count)}, "
            f"save|seq={fmt(best_mixed.expected_saving_by_count)}, "
            f"seed mass fraction={fmt(best_mixed.seed_item_mass_fraction)}."
        )
    print(
        "A positive conditioned save|seq is not a universal compression proof: it is "
        "conditioned on the stream already being valid item syntax. The uniform "
        "mass columns price how much of arbitrary bitspace those targets occupy."
    )
    print(
        "For maintained recursion, seed_only is the strict row. mixed_all can "
        "look better by spending literals, but literals do not refresh future "
        "seed-match opportunities."
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
    parser.add_argument("--target-arity", action="append", default=[])
    args = parser.parse_args()

    block_values = parse_int_list(args.block_bits, [8])
    depth_values = parse_int_list(args.depth, [8, 16, 24, 32, 40])
    target_arities = parse_int_list(args.target_arity, [2, 3, 5])
    modes = args.mode or ["literal_only", "mixed_all", "seed_only"]
    rows: list[ModeRow] = []
    for block_bits in block_values:
        for depth_bits in depth_values:
            inv = build_inventory(block_bits, args.max_arity, depth_bits)
            for mode in modes:
                for target_arity in target_arities:
                    rows.append(row_for(inv, mode, target_arity))
    print_rows(rows)
    print_reading(rows)


if __name__ == "__main__":
    main()
