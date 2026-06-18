#!/usr/bin/env python3
"""H156 - completion versus seed-mass tradeoff.

H151 priced closure by forcing generated intermediates to be valid record
streams. A natural escape is to complete the prefix grammar with filler/literal
records so that parsing is easy.

This kernel prices that escape:

* seed grammar: only real Telomere seed records;
* completed grammar: seed records plus enough filler records at a fixed length
  to use the remaining Kraft mass.

Completion can raise parse density, but the completed streams are often made of
filler records. If filler records are literals/raw repair, they do not refresh
hash opportunities. If the next layer must remain all seed-bearing records, the
conditional seed-only fraction is the paid bill.
"""

from __future__ import annotations

import argparse
import importlib.util
import math
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


HERE = Path(__file__).resolve().parent
H151_PATH = HERE / "H151-closure_kraft_ledger.py"
H151_SPEC = importlib.util.spec_from_file_location("h151_for_h156", H151_PATH)
if H151_SPEC is None or H151_SPEC.loader is None:
    raise RuntimeError(f"cannot load {H151_PATH}")
h151 = importlib.util.module_from_spec(H151_SPEC)
sys.modules[H151_SPEC.name] = h151
H151_SPEC.loader.exec_module(h151)


@dataclass(frozen=True)
class CompletionRow:
    name: str
    block_bits: int
    max_arity: int
    depth_bits: int
    stream_bits: int
    fill_len: int
    seed_kraft: float
    filler_count: int
    completed_kraft: float
    seed_valid: int
    completed_valid: int
    seed_density: float
    completed_density: float
    seed_closure_tax: float
    completed_closure_tax: float
    seed_only_given_completed: float
    seed_preservation_tax: float
    expected_seed_records: float
    expected_filler_records: float
    expected_filler_fraction: float


@dataclass(frozen=True)
class CountState:
    streams: int
    seed_records: int
    filler_records: int


def completion_count(grammar: h151.Grammar, fill_len: int) -> int:
    used_leaves = 0
    for length, count in grammar.length_counts.items():
        if length > fill_len:
            raise ValueError("fill_len must be at least the max seed code length")
        used_leaves += count << (fill_len - length)
    return (1 << fill_len) - used_leaves


def count_completed_streams(
    seed_counts: Counter[int],
    filler_len: int,
    filler_count: int,
    max_stream_bits: int,
) -> list[CountState]:
    states = [CountState(0, 0, 0) for _ in range(max_stream_bits + 1)]
    states[0] = CountState(1, 0, 0)
    for total in range(1, max_stream_bits + 1):
        streams = 0
        seed_records = 0
        filler_records = 0
        for length, count in seed_counts.items():
            if total >= length:
                prev = states[total - length]
                streams += prev.streams * count
                seed_records += (prev.seed_records + prev.streams) * count
                filler_records += prev.filler_records * count
        if filler_count and total >= filler_len:
            prev = states[total - filler_len]
            streams += prev.streams * filler_count
            seed_records += prev.seed_records * filler_count
            filler_records += (prev.filler_records + prev.streams) * filler_count
        states[total] = CountState(streams, seed_records, filler_records)
    return states


def safe_tax(probability: float) -> float:
    return -math.log2(probability) if probability > 0.0 else float("inf")


def row_for(
    grammar: h151.Grammar,
    stream_bits: int,
    fill_len: int,
) -> CompletionRow:
    filler_count = completion_count(grammar, fill_len)
    max_stream_bits = stream_bits
    seed_states = count_completed_streams(grammar.length_counts, fill_len, 0, max_stream_bits)
    completed_states = count_completed_streams(
        grammar.length_counts,
        fill_len,
        filler_count,
        max_stream_bits,
    )
    seed_state = seed_states[stream_bits]
    completed_state = completed_states[stream_bits]
    denom = 2.0 ** stream_bits
    seed_density = seed_state.streams / denom
    completed_density = completed_state.streams / denom
    completed_kraft = grammar.kraft_mass + filler_count * (2.0 ** -fill_len)
    seed_only = (
        seed_state.streams / completed_state.streams
        if completed_state.streams
        else 0.0
    )
    expected_seed = (
        completed_state.seed_records / completed_state.streams
        if completed_state.streams
        else 0.0
    )
    expected_filler = (
        completed_state.filler_records / completed_state.streams
        if completed_state.streams
        else 0.0
    )
    expected_total_records = expected_seed + expected_filler
    filler_fraction = (
        expected_filler / expected_total_records
        if expected_total_records > 0.0
        else 0.0
    )
    return CompletionRow(
        name=grammar.name,
        block_bits=grammar.block_bits,
        max_arity=grammar.max_arity,
        depth_bits=grammar.depth_bits,
        stream_bits=stream_bits,
        fill_len=fill_len,
        seed_kraft=grammar.kraft_mass,
        filler_count=filler_count,
        completed_kraft=completed_kraft,
        seed_valid=seed_state.streams,
        completed_valid=completed_state.streams,
        seed_density=seed_density,
        completed_density=completed_density,
        seed_closure_tax=safe_tax(seed_density),
        completed_closure_tax=safe_tax(completed_density),
        seed_only_given_completed=seed_only,
        seed_preservation_tax=safe_tax(seed_only),
        expected_seed_records=expected_seed,
        expected_filler_records=expected_filler,
        expected_filler_fraction=filler_fraction,
    )


def rows() -> list[CompletionRow]:
    configs = [
        (1, 4, 7),
        (1, 5, 8),
        (1, 16, 4),
        (4, 32, 16),
        (4, 128, 16),
    ]
    result: list[CompletionRow] = []
    for block_bits, max_arity, depth_bits in configs:
        grammar = h151.build_grammar(block_bits, max_arity, depth_bits, 32)
        fill_len = max(grammar.length_counts)
        for stream_bits in (fill_len, max(32, fill_len * 2), 64):
            result.append(row_for(grammar, stream_bits, fill_len))
    return result


def fmt(value: float) -> str:
    if value == float("inf"):
        return "inf"
    if value == float("-inf"):
        return "-inf"
    if abs(value) >= 1000.0 or (0.0 < abs(value) < 0.0001):
        return f"{value:.3e}"
    return f"{value:.6f}"


def print_rows(items: list[CompletionRow]) -> None:
    print("== completion versus seed-mass tradeoff ==")
    print("Completion uses all remaining Kraft leaves at fill_len.")
    print(
        f"{'grammar':<13} {'t':>4} {'F':>3} {'seedK':>8} {'fill#':>10} "
        f"{'seedTax':>8} {'compTax':>8} {'seed|comp':>10} "
        f"{'presTax':>8} {'Eseed':>8} {'Efill':>8} {'fillFrac':>8}"
    )
    for row in items:
        print(
            f"{row.name:<13} {row.stream_bits:4d} {row.fill_len:3d} "
            f"{fmt(row.seed_kraft):>8} {row.filler_count:10d} "
            f"{fmt(row.seed_closure_tax):>8} "
            f"{fmt(row.completed_closure_tax):>8} "
            f"{fmt(row.seed_only_given_completed):>10} "
            f"{fmt(row.seed_preservation_tax):>8} "
            f"{fmt(row.expected_seed_records):>8} "
            f"{fmt(row.expected_filler_records):>8} "
            f"{fmt(row.expected_filler_fraction):>8}"
        )
    print()


def print_reading(items: list[CompletionRow]) -> None:
    print("== reading ==")
    best_parse = min(items, key=lambda row: row.completed_closure_tax)
    best_seed = min(items, key=lambda row: row.seed_closure_tax)
    print(
        f"Best completed parse tax is {fmt(best_parse.completed_closure_tax)} bits "
        f"at {best_parse.name}, t={best_parse.stream_bits}; filler fraction is "
        f"{fmt(best_parse.expected_filler_fraction)}."
    )
    print(
        f"Best seed-only closure tax is still {fmt(best_seed.seed_closure_tax)} bits "
        f"at {best_seed.name}, t={best_seed.stream_bits}."
    )
    print(
        "Completion makes streams parse, but most parse mass can be filler. "
        "If filler is literal/raw repair it loses freshness; if every record "
        "must stay seed-bearing, the seed preservation tax restores the H151 "
        "seed-only closure bill."
    )


def main() -> None:
    result = rows()
    print_rows(result)
    print_reading(result)


if __name__ == "__main__":
    main()
