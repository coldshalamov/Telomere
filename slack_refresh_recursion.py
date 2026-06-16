#!/usr/bin/env python3
"""Sparse replacement with slack: replace compressive, equal, and slightly-bloating
matches to refresh blocks and maintain match rate across passes.

This is an optimistic model: it does NOT charge birth-pass ambiguity.
If the optimistic stream size still grows over passes, the idea cannot work.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from statistics import mean


@dataclass(frozen=True)
class Block:
    bits: tuple[int, ...]
    pass_born: int


@dataclass(frozen=True)
class Record:
    arity: int
    seed_rank: int
    payload_bits: int


def bits_to_int(bits: tuple[int, ...]) -> int:
    value = 0
    for b in bits:
        value = (value << 1) | b
    return value


def int_to_bits(value: int, width: int) -> tuple[int, ...]:
    return tuple((value >> i) & 1 for i in range(width - 1, -1, -1))


def sample_first_rank(target_bits: int, rng: random.Random) -> int:
    q = 2.0 ** (-target_bits)
    u = rng.random()
    if target_bits <= 48:
        return math.ceil(math.log1p(-u) / math.log1p(-q))
    return math.ceil(2.0 ** (target_bits + math.log2(rng.expovariate(1.0))))


def make_salt(pass_num: int, position: int, arity: int) -> int:
    """Public deterministic salt."""
    return (pass_num * 73856093) ^ (position * 19349663) ^ (arity * 83492791)


def record_cost(arity: int, payload_bits: int, max_arity: int) -> int:
    """Bits to store [arity][seed]."""
    return math.ceil(math.log2(max_arity)) + payload_bits


def run_pass(
    blocks: list[Block],
    pass_num: int,
    max_arity: int,
    frontier: int,
    slack: float,
    rng: random.Random,
) -> list[Block]:
    """One sparse-replacement pass. Returns new list of blocks."""
    out: list[Block] = []
    i = 0
    while i < len(blocks):
        best_score = -1.0
        best_arity = 1
        best_rank = 0
        best_payload = 0
        for arity in range(1, min(max_arity, len(blocks) - i) + 1):
            span_bits = sum(len(blocks[i + j].bits) for j in range(arity))
            # Deterministic salt from pass, position, arity.
            salt = make_salt(pass_num, i, arity)
            # Use salt to seed the rng for this interval.
            local_rng = random.Random(salt)
            rank = sample_first_rank(span_bits, local_rng)
            payload_bits = max(1, rank.bit_length())
            if payload_bits > frontier:
                continue
            cost = record_cost(arity, payload_bits, max_arity)
            # Score: how much we "gain" including slack.
            score = span_bits - cost + slack
            if score > best_score:
                best_score = score
                best_arity = arity
                best_rank = rank
                best_payload = payload_bits
        if best_score >= 0:
            # Replace with a record block.
            # The record block stores arity and seed bits.
            record_bits = record_cost(best_arity, best_payload, max_arity)
            # Represent the record as a block with the record bits (padded/truncated to block size for simplicity).
            # For size accounting, we just track the record cost.
            # Store as a synthetic block whose bits = serialized record.
            value = ((best_arity - 1) << best_payload) | (best_rank & ((1 << best_payload) - 1))
            bits = int_to_bits(value, record_bits)
            out.append(Block(bits, pass_num))
            i += best_arity
        else:
            # Carry single block.
            out.append(Block(blocks[i].bits, blocks[i].pass_born))
            i += 1
    return out


def stream_size_bits(blocks: list[Block]) -> int:
    return sum(len(b.bits) for b in blocks)


def bbl_ambiguity_cost(arity: int, max_passes: int, e_a: float) -> float:
    """Birth-pass ambiguity cost per record under BBL accounting."""
    if max_passes <= 1:
        return 0.0
    q_a = 2.0 ** (-e_a)
    return math.log2(1.0 + (max_passes - 1) * q_a)


def run_trial(
    num_blocks: int,
    block_bits: int,
    max_arity: int,
    frontier: int,
    slack: float,
    max_passes: int,
    e_a: float,
    header_bits: int,
    rng: random.Random,
) -> dict:
    blocks = [Block(tuple(rng.randint(0, 1) for _ in range(block_bits)), 0) for _ in range(num_blocks)]
    sizes = [stream_size_bits(blocks)]
    for pass_num in range(1, max_passes + 1):
        blocks = run_pass(blocks, pass_num, max_arity, frontier, slack, rng)
        sizes.append(stream_size_bits(blocks))
    # Add BBL ambiguity cost for all records born after pass 0.
    ambiguity = sum(bbl_ambiguity_cost(1, max_passes, e_a) for b in blocks if b.pass_born > 0)
    charged = sizes[-1] + ambiguity + header_bits
    return {
        "sizes": sizes,
        "final": sizes[-1],
        "charged": charged,
        "delta": charged - sizes[0],
        "ambiguity": ambiguity,
    }


def main():
    num_blocks = 256
    block_bits = 24
    max_arity = 8
    frontier = 72
    max_passes = 8
    trials = 48
    seed = 20260615
    rng = random.Random(seed)

    # Header: pass count + checksum/schedule; small fixed cost.
    header_bits = 32

    for e_a in (8, 10, 12, 16):
        print(f"\n=== E_a = {e_a} ===")
        for slack in (0, 1, 2):
            results = []
            for _ in range(trials):
                res = run_trial(num_blocks, block_bits, max_arity, frontier, slack, max_passes, e_a, header_bits, rng)
                results.append(res)
            finite = [r for r in results if r["final"] != float("inf")]
            print(f"\nSlack = {slack}")
            print(f"  Initial: {num_blocks * block_bits}")
            print(f"  Final visible: {mean(r['sizes'][-1] for r in finite):.2f}")
            print(f"  Ambiguity cost: {mean(r['ambiguity'] for r in finite):.2f}")
            print(f"  Charged final: {mean(r['charged'] for r in finite):.2f}")
            print(f"  Charged delta mean: {mean(r['delta'] for r in finite):.2f}")


if __name__ == "__main__":
    main()
