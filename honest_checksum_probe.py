#!/usr/bin/env python3
"""Fast probe: measure per-record saving Δ and compare to log2(P).

In the sparse-replacement model with honest checksum, recursion is profitable iff

    average_bits_saved_per_record  >  log2(P)

because every final record forces the decoder to try P birth-pass assignments.
This probe runs one long pass over fresh random blocks and reports Δ.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass


@dataclass(frozen=True)
class Block:
    bits: tuple[int, ...]


def int_to_bits(value: int, width: int) -> tuple[int, ...]:
    return tuple((value >> i) & 1 for i in range(width - 1, -1, -1))


def sample_first_rank(target_bits: int, rng: random.Random) -> int:
    q = 2.0 ** (-target_bits)
    u = rng.random()
    if target_bits <= 48:
        return math.ceil(math.log1p(-u) / math.log1p(-q))
    return math.ceil(2.0 ** (target_bits + math.log2(rng.expovariate(1.0))))


def make_salt(pass_num: int, position: int, arity: int) -> int:
    return (pass_num * 73856093) ^ (position * 19349663) ^ (arity * 83492791)


def record_cost(arity: int, payload_bits: int, max_arity: int) -> int:
    return math.ceil(math.log2(max_arity)) + payload_bits


def greedy_cover(blocks, pass_num, max_arity, frontier):
    """Greedy left-to-right cover. Returns (out_blocks, total_span_bits, total_record_bits, n_records)."""
    out = []
    span_bits = 0
    record_bits = 0
    n_records = 0
    i = 0
    while i < len(blocks):
        best_score = -1.0
        best_arity = 1
        best_rank = 0
        best_payload = 0
        best_span = 0
        for arity in range(1, min(max_arity, len(blocks) - i) + 1):
            s = sum(len(blocks[i + j].bits) for j in range(arity))
            salt = make_salt(pass_num, i, arity)
            local_rng = random.Random(salt)
            rank = sample_first_rank(s, local_rng)
            payload_bits = max(1, rank.bit_length())
            if payload_bits > frontier:
                continue
            cost = record_cost(arity, payload_bits, max_arity)
            score = s - cost
            if score > best_score:
                best_score = score
                best_arity = arity
                best_rank = rank
                best_payload = payload_bits
                best_span = s
        if best_score >= 0:
            value = ((best_arity - 1) << best_payload) | (best_rank & ((1 << best_payload) - 1))
            bits = int_to_bits(value, record_cost(best_arity, best_payload, max_arity))
            out.append(Block(bits))
            span_bits += best_span
            record_bits += len(bits)
            n_records += 1
            i += best_arity
        else:
            out.append(blocks[i])
            i += 1
    return out, span_bits, record_bits, n_records


def probe(num_blocks, block_bits, max_arity, frontier, trials=12):
    rng = random.Random(20260616)
    savings = []
    records = []
    for _ in range(trials):
        blocks = [Block(tuple(rng.randint(0, 1) for _ in range(block_bits))) for _ in range(num_blocks)]
        out, span_bits, record_bits, n_records = greedy_cover(blocks, pass_num=1, max_arity=max_arity, frontier=frontier)
        total_in = num_blocks * block_bits
        total_out_visible = sum(len(b.bits) for b in out)
        # Average saving per actual record (excluding literals):
        saving_per_record = (span_bits - record_bits) / max(1, n_records)
        savings.append(saving_per_record)
        records.append(n_records)
    return sum(savings) / len(savings), sum(records) / len(records)


def main():
    configs = [
        # B, K, D
        (16, 4, 32),
        (16, 4, 40),
        (24, 4, 48),
        (24, 4, 60),
        (24, 4, 72),
        (24, 6, 60),
        (24, 6, 72),
        (24, 8, 64),
        (24, 8, 72),
        (32, 4, 64),
        (32, 4, 80),
        (32, 8, 80),
    ]
    print("B | K | D | delta bits/record | records | log2(P) thresholds")
    print("-" * 70)
    for block_bits, max_arity, frontier in configs:
        delta, nrec = probe(256, block_bits, max_arity, frontier, trials=24)
        # maximum P such that Δ > log2(P)
        max_p = 2.0 ** delta
        print(
            f"{block_bits} | {max_arity} | {frontier} | {delta:+.2f} | {nrec:.0f} | "
            f"P<={max_p:.1f} (P=4:{math.log2(4):.2f}, 8:{math.log2(8):.2f}, 16:{math.log2(16):.2f}, 32:{math.log2(32):.2f}, 64:{math.log2(64):.2f})"
        )


if __name__ == "__main__":
    main()
