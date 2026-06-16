#!/usr/bin/env python3
"""Scheduled total-cover Telomere: arity/width are derived from public position salt.

The decoder knows the schedule, so the stream is only seed payload bits.
The encoder searches for seeds that match the scheduled spans.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from statistics import mean


@dataclass(frozen=True)
class ScheduleEntry:
    arity: int
    payload_width: int


def sample_first_hit_rank(target_bits: int, rng: random.Random) -> int:
    q = 2.0 ** (-target_bits)
    u = rng.random()
    if target_bits <= 48:
        return math.ceil(math.log1p(-u) / math.log1p(-q))
    return math.ceil(2.0 ** (target_bits + math.log2(rng.expovariate(1.0))))


def make_schedule(blocks: int, max_arity: int, widths: tuple[int, ...], rng: random.Random) -> list[ScheduleEntry]:
    """Create a public schedule of (arity, width) entries covering all blocks."""
    schedule: list[ScheduleEntry] = []
    pos = 0
    while pos < blocks:
        arity = rng.randint(1, max_arity)
        if pos + arity > blocks:
            arity = blocks - pos
        width = rng.choice(widths)
        schedule.append(ScheduleEntry(arity, width))
        pos += arity
    return schedule


def run_scheduled_pass(
    bitstream: list[int],
    block_bits: int,
    schedule: list[ScheduleEntry],
    rng: random.Random,
) -> tuple[int, bool]:
    """Try to cover the bitstream using the fixed schedule. Return charged bits and success."""
    pos = 0
    charged = 0
    for entry in schedule:
        if pos + entry.arity > len(bitstream) // block_bits:
            return 0, False
        span_bits = entry.arity * block_bits
        rank = sample_first_hit_rank(span_bits, rng)
        payload_bits = max(1, rank.bit_length())
        if payload_bits > entry.payload_width:
            return 0, False
        charged += entry.payload_width
        pos += entry.arity
    if pos != len(bitstream) // block_bits:
        return 0, False
    return charged, True


def run_scheduled_two_passes(
    input_bits: int,
    block_bits: int,
    max_arity: int,
    widths: tuple[int, ...],
    rng: random.Random,
) -> dict:
    input_blocks = input_bits // block_bits
    input_stream = [rng.randint(0, 1) for _ in range(input_bits)]

    # Pass 1 schedule.
    schedule1 = make_schedule(input_blocks, max_arity, widths, rng)
    pass1_charged, ok1 = run_scheduled_pass(input_stream, block_bits, schedule1, rng)
    if not ok1:
        return {"pass1_charged": float("inf"), "pass2_charged": float("inf")}

    # Pass 1 output is just seed payload bits; reinterpret as new bitstream.
    # For modeling, treat pass1_charged bits as the stream length and generate random bits.
    pass1_stream = [rng.randint(0, 1) for _ in range(pass1_charged)]
    pass1_blocks = pass1_charged // block_bits
    if pass1_blocks == 0:
        return {"pass1_charged": pass1_charged, "pass2_charged": 0.0}

    # Pad to whole blocks.
    pad = (pass1_blocks + 1) * block_bits - pass1_charged
    pass1_stream = pass1_stream + [0] * pad
    pass1_blocks += 1

    schedule2 = make_schedule(pass1_blocks, max_arity, widths, rng)
    pass2_charged, ok2 = run_scheduled_pass(pass1_stream, block_bits, schedule2, rng)
    if not ok2:
        return {"pass1_charged": pass1_charged, "pass2_charged": float("inf")}

    return {
        "input_bits": input_bits,
        "pass1_charged": pass1_charged,
        "pass1_stream_bits": len(pass1_stream),
        "pass2_charged": pass2_charged,
    }


def main():
    input_bits = 256 * 24
    block_bits = 24
    max_arity = 8
    widths = (24, 28, 32, 36, 40)
    trials = 48
    seed = 20260615
    rng = random.Random(seed)

    results = []
    for _ in range(trials):
        res = run_scheduled_two_passes(input_bits, block_bits, max_arity, widths, rng)
        results.append(res)

    finite = [r for r in results if r["pass2_charged"] != float("inf")]
    print(f"Trials: {len(results)}, finite pass2: {len(finite)}")
    if finite:
        print(f"Pass1 charged mean: {mean(r['pass1_charged'] for r in finite):.2f}")
        print(f"Pass2 charged mean: {mean(r['pass2_charged'] for r in finite):.2f}")
        print(f"Recursive delta: {mean(r['pass2_charged'] - r['pass1_charged'] for r in finite):.4f} bits")


if __name__ == "__main__":
    main()
