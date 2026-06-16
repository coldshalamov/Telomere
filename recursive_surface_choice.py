#!/usr/bin/env python3
"""Two-pass total-cover with surface-choice seed coherence.

For each interval, sample multiple candidate seed hits. The encoder greedily
chooses the candidate closest to the previous chosen seed index, so consecutive
seed indices tend to be near each other and delta-encode cheaply.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from statistics import mean


@dataclass(frozen=True)
class Record:
    arity: int
    seed_index: int  # 0-based
    payload_bits: int


def sample_hit_ranks(target_bits: int, k: int, rng: random.Random) -> list[int]:
    """Sample k i.i.d. geometrically-distributed first-hit ranks."""
    q = 2.0 ** (-target_bits)
    ranks: list[int] = []
    for _ in range(k):
        u = rng.random()
        if target_bits <= 48:
            rank = math.ceil(math.log1p(-u) / math.log1p(-q))
        else:
            rank = math.ceil(2.0 ** (target_bits + math.log2(rng.expovariate(1.0))))
        ranks.append(rank)
    return ranks


def encode_records(records: tuple[Record, ...], max_arity: int) -> tuple[list[int], int]:
    """Serialize records with delta-encoded seed indices."""
    abits = math.ceil(math.log2(max_arity))
    bits: list[int] = []
    prev_index = 0
    deltas: list[int] = []
    for i, record in enumerate(records):
        # Arity
        for j in range(abits - 1, -1, -1):
            bits.append((record.arity - 1) >> j & 1)
        # Seed index: first record absolute, rest delta from previous.
        if i == 0:
            delta = record.seed_index
        else:
            delta = record.seed_index - prev_index
        deltas.append(delta)
        # Encode delta with sign + magnitude.
        mag = abs(delta)
        # Simple Elias gamma-like code for magnitude, then sign bit.
        mag_bits = max(1, mag.bit_length())
        # Encode mag using mag_bits bits (unary length prefix + binary body).
        # Use length-prefixed: write mag_bits-1 zeros, then a 1, then mag bits.
        for _ in range(mag_bits - 1):
            bits.append(0)
        bits.append(1)
        for j in range(mag_bits - 1, -1, -1):
            bits.append((mag >> j) & 1)
        bits.append(0 if delta >= 0 else 1)
        prev_index = record.seed_index
    return bits, sum(len(bin(abs(d))) - 2 + 2 * max(0, abs(d).bit_length() - 1) + 1 for d in deltas)


def run_cover_coherent(
    bitstream: list[int],
    block_bits: int,
    max_arity: int,
    frontier: int,
    candidates: int,
    rng: random.Random,
) -> tuple[tuple[Record, ...], float] | None:
    atoms = len(bitstream) // block_bits
    if atoms * block_bits != len(bitstream):
        pad = atoms * block_bits + block_bits - len(bitstream)
        bitstream = bitstream + [0] * pad
        atoms += 1

    # Pre-sample candidate ranks for every interval.
    candidates_per_interval: list[list[int]] = []
    for start in range(atoms):
        row: list[list[int]] = []
        for arity in range(1, min(max_arity, atoms - start) + 1):
            span_bits = arity * block_bits
            ranks = sample_hit_ranks(span_bits, candidates, rng)
            row.append(sorted(ranks))
        candidates_per_interval.append(row)

    # DP minimizing payload width, with greedy coherence tie-breaking not possible in DP.
    # Instead, use plain width-minimizing DP first, then greedily re-choose candidates for coherence.
    dp = [float("inf")] * (atoms + 1)
    prev: list[tuple[int, int, int] | None] = [None] * (atoms + 1)
    dp[0] = 0.0
    for index in range(atoms):
        base = dp[index]
        if base == float("inf"):
            continue
        for offset, ranks in enumerate(candidates_per_interval[index], start=1):
            best_rank = min(ranks)
            payload_bits = max(1, best_rank.bit_length())
            if payload_bits > frontier:
                continue
            candidate = base + payload_bits
            end = index + offset
            if candidate < dp[end]:
                dp[end] = candidate
                prev[end] = (index, offset, best_rank)

    if dp[atoms] == float("inf"):
        return None

    cursor = atoms
    records: list[Record] = []
    while cursor > 0:
        entry = prev[cursor]
        if entry is None:
            return None
        start, arity, rank = entry
        records.append(Record(arity, rank - 1, max(1, rank.bit_length())))
        cursor = start
    records.reverse()

    # Greedy coherence re-selection: keep cover structure, choose closest seed index.
    coherent: list[Record] = []
    prev_index = 0
    for i, record in enumerate(records):
        start = sum(r.arity for r in coherent)
        arity = record.arity
        ranks = candidates_per_interval[start][arity - 1]
        if i == 0:
            chosen = min(ranks)
        else:
            chosen = min(ranks, key=lambda r: abs((r - 1) - prev_index))
        idx = chosen - 1
        coherent.append(Record(arity, idx, max(1, chosen.bit_length())))
        prev_index = idx

    selected = tuple(coherent)
    # Charged bits = arity codes + delta-encoded seed indices.
    _, charged = encode_records(selected, max_arity)
    return selected, charged


def main():
    input_bits = 256 * 24
    block_bits = 24
    max_arity = 8
    frontier = 72
    candidates = 16
    trials = 20
    seed = 20260615
    rng = random.Random(seed)

    deltas = []
    for _ in range(trials):
        input_stream = [rng.randint(0, 1) for _ in range(input_bits)]
        res = run_cover_coherent(input_stream, block_bits, max_arity, frontier, candidates, rng)
        if res is None:
            continue
        records, charged = res
        if len(records) > 1:
            deltas.extend(abs(records[i].seed_index - records[i - 1].seed_index) for i in range(1, len(records)))

    if deltas:
        print(f"Mean absolute delta: {mean(deltas):.2f}")
        print(f"Median delta: {sorted(deltas)[len(deltas)//2]:.2f}")
        print(f"Max delta: {max(deltas)}")
        print(f"Fraction <= 10: {sum(1 for d in deltas if d <= 10) / len(deltas):.4f}")


if __name__ == "__main__":
    main()
