#!/usr/bin/env python3
"""Two-pass total-cover Telomere recursion test.

Pass 1 covers a random input bitstream with [arity][seed] records.
Pass 2 covers the serialized pass-1 witness stream with the same machinery.
The question is whether pass-2 output is smaller than pass-1 output.
"""

from __future__ import annotations

import math
import random
from collections import Counter
from dataclasses import dataclass
from statistics import mean


@dataclass(frozen=True)
class Record:
    arity: int
    seed_rank: int  # 1-based first-hit rank
    payload_bits: int  # ceil(log2(rank))


def sample_first_hit_rank(target_bits: int, rng: random.Random) -> int:
    """Sample the rank of the first hash hit for a target of target_bits bits."""
    q = 2.0 ** (-target_bits)
    u = rng.random()
    if target_bits <= 48:
        return math.ceil(math.log1p(-u) / math.log1p(-q))
    # Exponential approximation for large targets.
    return math.ceil(2.0 ** (target_bits + math.log2(rng.expovariate(1.0))))


def encode_fixed_width(value: int, width: int) -> int:
    """Return value as an integer bit pattern of width bits."""
    if value < 0 or value >= (1 << width):
        raise ValueError(f"value {value} does not fit in {width} bits")
    return value


def arity_code_bits(max_arity: int) -> int:
    return math.ceil(math.log2(max_arity))


def serialize_records(records: tuple[Record, ...], max_arity: int) -> list[int]:
    """Serialize records to a flat list of bits."""
    bits: list[int] = []
    abits = arity_code_bits(max_arity)
    for record in records:
        # Arity as fixed-width code (arity-1 stored).
        for i in range(abits - 1, -1, -1):
            bits.append((record.arity - 1) >> i & 1)
        # Seed payload bits, MSB first.
        for i in range(record.payload_bits - 1, -1, -1):
            bits.append(record.seed_rank >> i & 1)
    return bits


def run_cover(
    bitstream: list[int],
    block_bits: int,
    max_arity: int,
    frontier: int,
    rng: random.Random,
) -> tuple[tuple[Record, ...], float] | None:
    """Run total-cover DP on a bitstream, returning records and charged bits."""
    atoms = len(bitstream) // block_bits
    if atoms * block_bits != len(bitstream):
        # Pad to whole atoms for simplicity.
        pad = atoms * block_bits + block_bits - len(bitstream)
        bitstream = bitstream + [0] * pad
        atoms += 1

    # For each interval, sample the first-hit rank.
    interval_ranks: list[list[int]] = []
    for start in range(atoms):
        row: list[int] = []
        for arity in range(1, min(max_arity, atoms - start) + 1):
            span_bits = arity * block_bits
            rank = sample_first_hit_rank(span_bits, rng)
            row.append(rank)
        interval_ranks.append(row)

    # DP: find cheapest cover by raw payload width.
    dp = [float("inf")] * (atoms + 1)
    prev: list[tuple[int, int, int] | None] = [None] * (atoms + 1)
    dp[0] = 0.0
    for index in range(atoms):
        base = dp[index]
        if base == float("inf"):
            continue
        for offset, rank in enumerate(interval_ranks[index], start=1):
            payload_bits = max(1, rank.bit_length())
            if payload_bits > frontier:
                continue
            candidate = base + payload_bits
            end = index + offset
            if candidate < dp[end]:
                dp[end] = candidate
                prev[end] = (index, offset, rank)

    if dp[atoms] == float("inf"):
        return None

    cursor = atoms
    records: list[Record] = []
    while cursor > 0:
        entry = prev[cursor]
        if entry is None:
            return None
        start, arity, rank = entry
        records.append(Record(arity, rank, max(1, rank.bit_length())))
        cursor = start
    records.reverse()
    selected = tuple(records)

    # Charged bits = arity codes + payload bits.
    abits = arity_code_bits(max_arity)
    charged = sum(abits + record.payload_bits for record in selected)
    return selected, charged


def run_two_passes(
    input_bits: int,
    block_bits: int,
    max_arity: int,
    frontier: int,
    rng: random.Random,
) -> dict:
    input_stream = [rng.randint(0, 1) for _ in range(input_bits)]

    pass1 = run_cover(input_stream, block_bits, max_arity, frontier, rng)
    if pass1 is None:
        return {"pass1_charged": float("inf"), "pass2_charged": float("inf")}
    pass1_records, pass1_charged = pass1
    pass1_stream = serialize_records(pass1_records, max_arity)

    # For pass 2, use the same block size and arity, but the input is now the witness stream.
    pass2 = run_cover(pass1_stream, block_bits, max_arity, frontier, rng)
    if pass2 is None:
        return {"pass1_charged": pass1_charged, "pass2_charged": float("inf")}
    pass2_records, pass2_charged = pass2

    return {
        "input_bits": input_bits,
        "pass1_charged": pass1_charged,
        "pass1_records": len(pass1_records),
        "pass1_stream_bits": len(pass1_stream),
        "pass2_charged": pass2_charged,
        "pass2_records": len(pass2_records),
        "pass2_stream_bits": len(serialize_records(pass2_records, max_arity)),
    }


def main():
    input_bits = 256 * 24  # same scale as refined runs
    block_bits = 24
    max_arity = 8
    frontier = 72  # near the Markov1 optimum
    trials = 48
    seed = 20260615
    rng = random.Random(seed)

    results = []
    for _ in range(trials):
        res = run_two_passes(input_bits, block_bits, max_arity, frontier, rng)
        results.append(res)

    finite = [r for r in results if r["pass2_charged"] != float("inf")]
    print(f"Trials: {len(results)}, finite pass2: {len(finite)}")
    if finite:
        print(f"Input bits: {input_bits}")
        print(f"Pass1 charged mean: {mean(r['pass1_charged'] for r in finite):.2f}")
        print(f"Pass2 charged mean: {mean(r['pass2_charged'] for r in finite):.2f}")
        print(f"Pass1 bits/atom: {mean(r['pass1_charged'] / (input_bits / block_bits) for r in finite):.4f}")
        print(f"Pass2 bits/atom (of pass1 atoms): {mean(r['pass2_charged'] / (r['pass1_stream_bits'] / block_bits) for r in finite):.4f}")
        print(f"Pass1 stream bits mean: {mean(r['pass1_stream_bits'] for r in finite):.2f}")
        print(f"Pass2 stream bits mean: {mean(r['pass2_stream_bits'] for r in finite):.2f}")
        print(f"Recursive delta (pass2 - pass1): {mean(r['pass2_charged'] - r['pass1_charged'] for r in finite):.4f} bits")


if __name__ == "__main__":
    main()
