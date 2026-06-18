#!/usr/bin/env python3
"""H149 - decode-composition capacity.

This is the direct stateless-recursion audit:

    final stream --decode--> layer 1 --decode--> ... --decode--> bottom file

There is no stop depth, no branch selector, no birth tag, and no sidecar. The
only stored object is the final top-layer bitstream. If an intermediate layer
is larger, that is allowed, but it must itself be a valid record stream because
the next decode pass must parse it without search.

The kernel builds a tiny fixed public record language:

    [fixed arity bits][J3D1 seed witness]

with SHA-like seed expansion. It enumerates every valid record stream up to a
small bit cap, composes the decoder for P passes, and counts how many n-bit
bottom strings have at least one top stream of length <= n - saved_bits.

This is not a production codec and not a big search. It is a finite counting
sanity check for "larger intermediate then shrink" and non-greedy recursive
paths under a stateless fixed decoder.
"""

from __future__ import annotations

import argparse
import hashlib
import math
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model_analysis.proof_kernel.costs import (  # noqa: E402
    j3d1_cost_for_seed_index,
    lotus_width_for_value,
    payload_width_for_seed_index,
)


@dataclass(frozen=True)
class Record:
    arity: int
    seed: int
    bits: str
    out: str


@dataclass(frozen=True)
class StreamMap:
    streams: dict[str, str]
    record_count: int
    max_stream_bits: int
    max_output_bits: int


@dataclass(frozen=True)
class CapacityRow:
    atom_bits: int
    max_arity: int
    depth_bits: int
    stream_cap: int
    output_cap: int
    passes: int
    target_bits: int
    saved_bits: int
    valid_top_streams: int
    composed_streams: int
    reachable_outputs: int
    coverage: float
    prefix_bound: float
    best_top_bits: int | None
    mean_best_top_bits: float
    mean_saving_on_reached: float


def expand(seed: int, nbits: int) -> str:
    output = ""
    counter = 0
    while len(output) < nbits:
        digest = hashlib.sha256(f"H149:{seed}:{counter}".encode("ascii")).digest()
        output += "".join(f"{byte:08b}" for byte in digest)
        counter += 1
    return output[:nbits]


def j3d1_encode(seed_index: int) -> str:
    value = seed_index + 1
    payload_width = payload_width_for_seed_index(seed_index)
    tier_width = lotus_width_for_value(payload_width)
    bits = format(tier_width - 1, "03b")
    bits += format(payload_width - ((1 << tier_width) - 2), f"0{tier_width}b")
    bits += format(value - ((1 << payload_width) - 2), f"0{payload_width}b")
    if len(bits) != j3d1_cost_for_seed_index(seed_index):
        raise AssertionError("J3D1 width mismatch")
    return bits


def fixed_arity_encode(max_arity: int, arity: int) -> str:
    width = math.ceil(math.log2(max_arity))
    if width <= 0:
        return ""
    return format(arity - 1, f"0{width}b")


def build_records(atom_bits: int, max_arity: int, depth_bits: int) -> list[Record]:
    records: list[Record] = []
    for arity in range(1, max_arity + 1):
        arity_bits = fixed_arity_encode(max_arity, arity)
        for seed in range(1 << depth_bits):
            bits = arity_bits + j3d1_encode(seed)
            records.append(
                Record(
                    arity=arity,
                    seed=seed,
                    bits=bits,
                    out=expand(seed, arity * atom_bits),
                )
            )
    records.sort(key=lambda record: (len(record.bits), record.bits, record.arity, record.seed))
    return records


def enumerate_streams(
    records: list[Record],
    max_stream_bits: int,
    max_output_bits: int,
) -> StreamMap:
    streams: dict[str, str] = {}

    def rec(prefix_bits: str, output_bits: str) -> None:
        for record in records:
            next_len = len(prefix_bits) + len(record.bits)
            if next_len > max_stream_bits:
                continue
            next_output = output_bits + record.out
            if len(next_output) > max_output_bits:
                continue
            next_bits = prefix_bits + record.bits
            old = streams.get(next_bits)
            if old is not None and old != next_output:
                raise AssertionError("prefix-free stream collision with different output")
            streams[next_bits] = next_output
            rec(next_bits, next_output)

    rec("", "")
    return StreamMap(
        streams=streams,
        record_count=len(records),
        max_stream_bits=max_stream_bits,
        max_output_bits=max_output_bits,
    )


def compose(streams: dict[str, str], passes: int) -> dict[str, str]:
    if passes < 1:
        raise ValueError("passes must be >= 1")
    current = dict(streams)
    for _ in range(2, passes + 1):
        current = {
            top: current[mid]
            for top, mid in streams.items()
            if mid in current
        }
    return current


def prefix_coverage_bound(target_bits: int, saved_bits: int) -> float:
    max_top_bits = target_bits - saved_bits
    if max_top_bits < 0:
        return 0.0
    # Generous EOF-style <= length count, not prefix-code exact.
    return min(1.0, ((1 << (max_top_bits + 1)) - 1) / (1 << target_bits))


def capacity_row(
    atom_bits: int,
    max_arity: int,
    depth_bits: int,
    stream_cap: int,
    output_cap: int,
    passes: int,
    target_bits: int,
    saved_bits: int,
) -> CapacityRow:
    records = build_records(atom_bits, max_arity, depth_bits)
    stream_map = enumerate_streams(records, stream_cap, output_cap)
    composed = compose(stream_map.streams, passes)

    best_by_output: dict[str, int] = {}
    max_top_bits = target_bits - saved_bits
    for top, bottom in composed.items():
        if len(top) > max_top_bits or len(bottom) != target_bits:
            continue
        old = best_by_output.get(bottom)
        if old is None or len(top) < old:
            best_by_output[bottom] = len(top)

    best_lengths = list(best_by_output.values())
    return CapacityRow(
        atom_bits=atom_bits,
        max_arity=max_arity,
        depth_bits=depth_bits,
        stream_cap=stream_cap,
        output_cap=output_cap,
        passes=passes,
        target_bits=target_bits,
        saved_bits=saved_bits,
        valid_top_streams=len(stream_map.streams),
        composed_streams=len(composed),
        reachable_outputs=len(best_by_output),
        coverage=len(best_by_output) / (1 << target_bits),
        prefix_bound=prefix_coverage_bound(target_bits, saved_bits),
        best_top_bits=min(best_lengths) if best_lengths else None,
        mean_best_top_bits=(sum(best_lengths) / len(best_lengths) if best_lengths else float("inf")),
        mean_saving_on_reached=(
            sum(target_bits - length for length in best_lengths) / len(best_lengths)
            if best_lengths
            else float("-inf")
        ),
    )


def fmt(value: float) -> str:
    if value == float("inf"):
        return "inf"
    if value == float("-inf"):
        return "-inf"
    if abs(value) >= 1000.0 or (0.0 < abs(value) < 0.0001):
        return f"{value:.3e}"
    return f"{value:.6f}"


def print_rows(rows: list[CapacityRow]) -> None:
    print("== decode-composition capacity ==")
    print("Fixed public decoder; final top stream is the only stored object.")
    print(
        f"{'B':>2} {'K':>3} {'D':>2} {'cap':>4} {'out':>4} {'P':>2} "
        f"{'n':>3} {'save':>4} {'valid':>8} {'comp':>8} {'reach':>7} "
        f"{'cov':>10} {'bound':>10} {'best':>5} {'mean top':>9} {'mean save':>10}"
    )
    for row in rows:
        best = "-" if row.best_top_bits is None else str(row.best_top_bits)
        print(
            f"{row.atom_bits:2d} {row.max_arity:3d} {row.depth_bits:2d} "
            f"{row.stream_cap:4d} {row.output_cap:4d} {row.passes:2d} "
            f"{row.target_bits:3d} {row.saved_bits:4d} "
            f"{row.valid_top_streams:8d} {row.composed_streams:8d} "
            f"{row.reachable_outputs:7d} {fmt(row.coverage):>10} "
            f"{fmt(row.prefix_bound):>10} {best:>5} "
            f"{fmt(row.mean_best_top_bits):>9} {fmt(row.mean_saving_on_reached):>10}"
        )
    print()


def print_reading(rows: list[CapacityRow]) -> None:
    print("== reading ==")
    if not rows:
        print("No rows were generated.")
        return
    best = max(rows, key=lambda row: (row.coverage, -row.saved_bits, row.reachable_outputs))
    print(
        f"Best coverage row reaches {best.reachable_outputs} of 2^{best.target_bits} "
        f"targets ({best.coverage:.6g}) after P={best.passes} passes."
    )
    print(
        "Because the decoder path is fixed, every successful multi-pass detour "
        "is just one final top-layer address. Coverage stays below the ordinary "
        "<=length counting bound, and any missing branch/stop choice would have "
        "to be stored separately."
    )
    if all(row.coverage == 0.0 for row in rows):
        print(
            "The tested self-unfolding language has no shorter fixed-depth "
            "addresses for the requested targets. That is a support failure, "
            "not a broad impossibility proof."
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--atom-bits", type=int, default=1)
    parser.add_argument("--max-arity", type=int, default=16)
    parser.add_argument("--depth-bits", type=int, default=4)
    parser.add_argument("--stream-cap", type=int, default=18)
    parser.add_argument("--output-cap", type=int, default=24)
    parser.add_argument("--passes", type=int, action="append", default=[])
    parser.add_argument("--target-bits", type=int, action="append", default=[])
    parser.add_argument("--saved-bits", type=int, action="append", default=[])
    args = parser.parse_args()

    pass_values = args.passes if args.passes else [1, 2, 3]
    target_values = args.target_bits if args.target_bits else [8, 12, 16]
    saved_values = args.saved_bits if args.saved_bits else [1, 2, 4]
    rows = [
        capacity_row(
            args.atom_bits,
            args.max_arity,
            args.depth_bits,
            args.stream_cap,
            args.output_cap,
            passes,
            target_bits,
            saved_bits,
        )
        for passes in pass_values
        for target_bits in target_values
        for saved_bits in saved_values
    ]
    print_rows(rows)
    print_reading(rows)


if __name__ == "__main__":
    main()
