#!/usr/bin/env python3
"""H151 - closure Kraft ledger.

H149/H150 exposed the current bottleneck: after one decode pass, the visible
intermediate layer usually is not a valid record stream for the next pass.
This file prices the obvious repair:

    force generated intermediates to lie inside the public record language.

For a fixed public record grammar, a uniformly random t-bit intermediate lands
in the valid-stream language with probability:

    parse_density(t) = #valid_record_streams_of_length_t / 2^t

Forcing seed outputs into that subset costs:

    closure_tax(t) = -log2(parse_density(t))

bits of match supply. This is not metadata on the wire, but it is a real loss
of hash-match rate. A prefix-complete/literal fallback can make parse_density
near one, but then the final selected stream pays literal/raw length and cannot
create a content-blind average win.
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
    ARITY_BITS,
    j3d1_cost_for_payload_width,
    payload_width_count_exact,
)


@dataclass(frozen=True)
class Grammar:
    name: str
    block_bits: int
    max_arity: int
    depth_bits: int
    length_counts: Counter[int]
    arity_length_counts: dict[int, Counter[int]]

    @property
    def kraft_mass(self) -> float:
        return sum(count * (2.0 ** -length) for length, count in self.length_counts.items())


@dataclass(frozen=True)
class ClosureRow:
    name: str
    block_bits: int
    max_arity: int
    depth_bits: int
    max_code_len: int
    kraft_mass: float
    stream_bits: int
    valid_streams: int
    parse_density: float
    closure_tax: float
    tax_per_bit: float
    literal_tax_floor: int


def fixed_arity_bits(max_arity: int, arity: int) -> int:
    if max_arity <= 5:
        return ARITY_BITS[arity]
    return math.ceil(math.log2(max_arity))


def depth_limited_payload_count(payload_width: int, depth_bits: int) -> int:
    """Seed count at this payload width among the first 2^D seed indices."""

    if depth_bits <= 0:
        return 0
    total_depth = 1 << depth_bits
    count_before = 0 if payload_width == 1 else (1 << payload_width) - 3
    count_le = (1 << (payload_width + 1)) - 3
    return max(0, min(total_depth, count_le) - min(total_depth, count_before))


def build_grammar(
    block_bits: int,
    max_arity: int,
    depth_bits: int,
    max_record_len: int,
) -> Grammar:
    length_counts: Counter[int] = Counter()
    arity_length_counts: dict[int, Counter[int]] = {}
    for arity in range(1, max_arity + 1):
        arity_len = fixed_arity_bits(max_arity, arity)
        counter: Counter[int] = Counter()
        for payload_width in range(1, max_record_len + 1):
            seed_count = depth_limited_payload_count(payload_width, depth_bits)
            if seed_count == 0:
                continue
            length = arity_len + j3d1_cost_for_payload_width(payload_width)
            if length > max_record_len:
                continue
            counter[length] += seed_count
            length_counts[length] += seed_count
        arity_length_counts[arity] = counter
    return Grammar(
        name=f"B{block_bits}_K{max_arity}_D{depth_bits}",
        block_bits=block_bits,
        max_arity=max_arity,
        depth_bits=depth_bits,
        length_counts=length_counts,
        arity_length_counts=arity_length_counts,
    )


def valid_stream_counts(length_counts: Counter[int], max_stream_bits: int) -> list[int]:
    counts = [0] * (max_stream_bits + 1)
    counts[0] = 1
    for total in range(1, max_stream_bits + 1):
        value = 0
        for length, count in length_counts.items():
            if total >= length:
                value += counts[total - length] * count
        counts[total] = value
    return counts


def closure_rows(grammar: Grammar, stream_lengths: list[int], max_stream_bits: int) -> list[ClosureRow]:
    counts = valid_stream_counts(grammar.length_counts, max_stream_bits)
    max_code_len = max(grammar.length_counts) if grammar.length_counts else 0
    rows: list[ClosureRow] = []
    for stream_bits in stream_lengths:
        valid = counts[stream_bits] if stream_bits <= max_stream_bits else 0
        density = valid / (2.0 ** stream_bits) if stream_bits >= 0 else 0.0
        tax = -math.log2(density) if density > 0.0 else float("inf")
        rows.append(
            ClosureRow(
                name=grammar.name,
                block_bits=grammar.block_bits,
                max_arity=grammar.max_arity,
                depth_bits=grammar.depth_bits,
                max_code_len=max_code_len,
                kraft_mass=grammar.kraft_mass,
                stream_bits=stream_bits,
                valid_streams=valid,
                parse_density=density,
                closure_tax=tax,
                tax_per_bit=tax / stream_bits if math.isfinite(tax) and stream_bits > 0 else float("inf"),
                literal_tax_floor=stream_bits,
            )
        )
    return rows


def fmt(value: float) -> str:
    if value == float("inf"):
        return "inf"
    if value == float("-inf"):
        return "-inf"
    if abs(value) >= 1000.0 or (0.0 < abs(value) < 0.0001):
        return f"{value:.3e}"
    return f"{value:.6f}"


def print_grammar(grammar: Grammar) -> None:
    print(f"== grammar {grammar.name} ==")
    print(
        f"Kraft mass from seed records up to cap: {grammar.kraft_mass:.9f}; "
        f"missing mass to prefix-complete: {max(0.0, 1.0 - grammar.kraft_mass):.9f}"
    )
    print(f"record length histogram: {dict(sorted(grammar.length_counts.items()))}")
    print()


def print_rows(rows: list[ClosureRow]) -> None:
    print("== closure density ==")
    print(
        f"{'grammar':<14} {'K':>4} {'D':>4} {'L':>4} {'Kraft':>9} "
        f"{'t':>4} {'valid':>12} {'density':>11} {'tax':>9} {'tax/bit':>9}"
    )
    for row in rows:
        print(
            f"{row.name:<14} {row.max_arity:4d} {row.depth_bits:4d} "
            f"{row.max_code_len:4d} {row.kraft_mass:9.6f} "
            f"{row.stream_bits:4d} {row.valid_streams:12d} "
            f"{fmt(row.parse_density):>11} {fmt(row.closure_tax):>9} "
            f"{fmt(row.tax_per_bit):>9}"
        )
    print()


def print_reading(rows: list[ClosureRow]) -> None:
    print("== reading ==")
    finite = [row for row in rows if math.isfinite(row.closure_tax)]
    if finite:
        best = min(finite, key=lambda row: row.closure_tax)
        print(
            f"Cheapest finite closure tax here is {best.closure_tax:.6f} bits "
            f"at {best.name}, t={best.stream_bits}."
        )
    infinite = [row for row in rows if not math.isfinite(row.closure_tax)]
    if infinite:
        print(
            f"{len(infinite)} rows have zero valid streams at that exact length; "
            "forcing closure there would require changing the grammar or adding "
            "a visible repair/fallback."
        )
    print(
        "A closure constraint is not wire metadata, but it thins the seed search "
        "by exactly the tax above. A literal/prefix-complete repair can buy "
        "support, but then the final selected stream pays raw/literal length."
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-record-len", type=int, default=32)
    parser.add_argument("--max-stream-bits", type=int, default=64)
    parser.add_argument("--stream-bits", type=int, action="append", default=[])
    args = parser.parse_args()

    stream_lengths = args.stream_bits if args.stream_bits else [8, 9, 10, 11, 12, 16, 20, 24, 32, 48, 64]
    configs = [
        (1, 4, 7),
        (1, 5, 8),
        (1, 16, 4),
        (1, 32, 3),
        (4, 32, 16),
        (4, 128, 16),
    ]
    all_rows: list[ClosureRow] = []
    for block_bits, max_arity, depth_bits in configs:
        grammar = build_grammar(block_bits, max_arity, depth_bits, args.max_record_len)
        print_grammar(grammar)
        all_rows.extend(closure_rows(grammar, stream_lengths, args.max_stream_bits))
    print_rows(all_rows)
    print_reading(all_rows)


if __name__ == "__main__":
    main()
