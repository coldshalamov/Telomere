#!/usr/bin/env python3
"""Two-pass recursion test using Markov1-coded arity/width + raw rank bits.

Pass 1 produces records. The witness stream is serialized as:
- Markov1 entropy-coded (arity, width) stream
- raw seed rank bits (local_payload_bits per record)

Pass 2 runs the same total-cover DP on the serialized witness bits.
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
    rank: int
    payload_bits: int
    width: int


def sample_first_rank(target_bits: int, rng: random.Random) -> int:
    q = 2.0 ** (-target_bits)
    u = rng.random()
    if target_bits <= 48:
        return math.ceil(math.log1p(-u) / math.log1p(-q))
    return math.ceil(2.0 ** (target_bits + math.log2(rng.expovariate(1.0))))


def markov1_stream_bits(records: tuple[Record, ...], max_arity: int) -> float:
    """Lower-bound bits for Markov1-coded (arity, width) stream."""
    symbols = [(record.arity, record.width) for record in records]
    total = len(symbols)
    if total == 0:
        return 0.0
    counts = Counter(symbols)
    bits = -sum((c / total) * math.log2(c / total) for c in counts.values())
    if total >= 2:
        prev_counts = Counter(symbols[i] for i in range(total - 1))
        cond: dict[tuple, Counter] = {}
        for i in range(total - 1):
            prev = symbols[i]
            curr = symbols[i + 1]
            if prev not in cond:
                cond[prev] = Counter()
            cond[prev][curr] += 1
        cond_bits = 0.0
        for prev, cnt in prev_counts.items():
            sub = cond[prev]
            sub_total = sum(sub.values())
            p = cnt / (total - 1)
            h = -sum((c / sub_total) * math.log2(c / sub_total) for c in sub.values())
            cond_bits += p * h
        bits += (total - 1) * cond_bits / total
    return bits * total


def serialize_witness(records: tuple[Record, ...], max_arity: int) -> list[int]:
    """Serialize witness as raw arity + raw width + raw rank bits.
    This is the *raw* witness stream that might be fertile for pass 2."""
    abits = math.ceil(math.log2(max_arity))
    wbits = max(record.width.bit_length() for record in records) if records else 1
    bits: list[int] = []
    for record in records:
        # arity
        for i in range(abits - 1, -1, -1):
            bits.append((record.arity - 1) >> i & 1)
        # width
        for i in range(wbits - 1, -1, -1):
            bits.append(record.width >> i & 1)
        # rank
        for i in range(record.payload_bits - 1, -1, -1):
            bits.append(record.rank >> i & 1)
    return bits


def run_cover(
    bitstream: list[int],
    block_bits: int,
    max_arity: int,
    frontier: int,
    rng: random.Random,
) -> tuple[tuple[Record, ...], float] | None:
    atoms = len(bitstream) // block_bits
    if atoms * block_bits != len(bitstream):
        pad = atoms * block_bits + block_bits - len(bitstream)
        bitstream = bitstream + [0] * pad
        atoms += 1

    dp = [float("inf")] * (atoms + 1)
    prev: list[tuple[int, int, int] | None] = [None] * (atoms + 1)
    dp[0] = 0.0
    for index in range(atoms):
        base = dp[index]
        if base == float("inf"):
            continue
        for offset in range(1, min(max_arity, atoms - index) + 1):
            span_bits = offset * block_bits
            rank = sample_first_rank(span_bits, rng)
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
        records.append(Record(arity, rank, max(1, rank.bit_length()), max(1, rank.bit_length())))
        cursor = start
    records.reverse()
    return tuple(records), dp[atoms]


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
    pass1_records, _ = pass1

    # Pass 1 charged: Markov1 (arity,width) + raw rank bits
    pass1_charged = markov1_stream_bits(pass1_records, max_arity) + sum(r.payload_bits for r in pass1_records)
    pass1_stream = serialize_witness(pass1_records, max_arity)

    pass2 = run_cover(pass1_stream, block_bits, max_arity, frontier, rng)
    if pass2 is None:
        return {"pass1_charged": pass1_charged, "pass2_charged": float("inf")}
    pass2_records, _ = pass2
    pass2_charged = markov1_stream_bits(pass2_records, max_arity) + sum(r.payload_bits for r in pass2_records)

    return {
        "input_bits": input_bits,
        "pass1_charged": pass1_charged,
        "pass1_stream_bits": len(pass1_stream),
        "pass2_charged": pass2_charged,
        "pass2_stream_bits": len(serialize_witness(pass2_records, max_arity)),
    }


def main():
    input_bits = 256 * 24
    block_bits = 24
    max_arity = 8
    frontier = 72
    trials = 24
    seed = 20260615
    rng = random.Random(seed)

    results = []
    for _ in range(trials):
        res = run_two_passes(input_bits, block_bits, max_arity, frontier, rng)
        results.append(res)

    finite = [r for r in results if r["pass2_charged"] != float("inf")]
    print(f"Trials: {len(results)}, finite pass2: {len(finite)}")
    if finite:
        print(f"Pass1 charged mean: {mean(r['pass1_charged'] for r in finite):.2f}")
        print(f"Pass2 charged mean: {mean(r['pass2_charged'] for r in finite):.2f}")
        print(f"Recursive delta: {mean(r['pass2_charged'] - r['pass1_charged'] for r in finite):.4f} bits")


if __name__ == "__main__":
    main()
