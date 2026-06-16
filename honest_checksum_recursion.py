#!/usr/bin/env python3
"""Sparse-replacement recursion with honest end-to-end checksum accounting.

There are no "valid blocks" to prune wrong-pass openings. The decoder tries all
P^N birth-pass assignments and uses a C-bit checksum to select the correct one.
C must be at least N * log2(P) for unique decoding.
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


def run_pass(blocks, pass_num, max_arity, frontier, slack, rng):
    out = []
    i = 0
    while i < len(blocks):
        best_score = -1.0
        best_arity = 1
        best_rank = 0
        best_payload = 0
        for arity in range(1, min(max_arity, len(blocks) - i) + 1):
            span_bits = sum(len(blocks[i + j].bits) for j in range(arity))
            salt = make_salt(pass_num, i, arity)
            local_rng = random.Random(salt)
            rank = sample_first_rank(span_bits, local_rng)
            payload_bits = max(1, rank.bit_length())
            if payload_bits > frontier:
                continue
            cost = record_cost(arity, payload_bits, max_arity)
            score = span_bits - cost + slack
            if score > best_score:
                best_score = score
                best_arity = arity
                best_rank = rank
                best_payload = payload_bits
        if best_score >= 0:
            value = ((best_arity - 1) << best_payload) | (best_rank & ((1 << best_payload) - 1))
            bits = int_to_bits(value, record_cost(best_arity, best_payload, max_arity))
            out.append(Block(bits, pass_num))
            i += best_arity
        else:
            out.append(Block(blocks[i].bits, blocks[i].pass_born))
            i += 1
    return out


def stream_size(blocks):
    return sum(len(b.bits) for b in blocks)


def trial(num_blocks, block_bits, max_arity, frontier, slack, max_passes, rng):
    blocks = [Block(tuple(rng.randint(0, 1) for _ in range(block_bits)), 0) for _ in range(num_blocks)]
    sizes = [stream_size(blocks)]
    for pass_num in range(1, max_passes + 1):
        blocks = run_pass(blocks, pass_num, max_arity, frontier, slack, rng)
        sizes.append(stream_size(blocks))
    visible = sizes[-1]
    n_records = len(blocks)
    checksum_bits = n_records * math.log2(max_passes) if max_passes > 1 else 0
    header_bits = 32
    charged = visible + checksum_bits + header_bits
    return sizes, charged, n_records, checksum_bits


def main():
    num_blocks = 256
    block_bits = 24
    trials = 24
    seed = 20260615
    rng = random.Random(seed)

    print("B | K | D | slack | P | visible | records | checksum | charged | delta")
    print("-" * 80)
    for block_bits in (16, 24, 32):
        for max_arity in (4, 6, 8):
            for frontier in (block_bits * 2, int(block_bits * 2.5), block_bits * 3):
                for max_passes in (4, 8, 16, 32):
                    for slack in (0,):
                        charged_vals = []
                        visible_vals = []
                        rec_counts = []
                        checksum_vals = []
                        for _ in range(trials):
                            sizes, charged, n_records, checksum_bits = trial(
                                num_blocks, block_bits, max_arity, frontier, slack, max_passes, rng
                            )
                            charged_vals.append(charged)
                            visible_vals.append(sizes[-1])
                            rec_counts.append(n_records)
                            checksum_vals.append(checksum_bits)
                        delta = mean(charged_vals) - num_blocks * block_bits
                        print(
                            f"{block_bits} | {max_arity} | {frontier} | {slack} | {max_passes} | "
                            f"{mean(visible_vals):.0f} | {mean(rec_counts):.0f} | "
                            f"{mean(checksum_vals):.0f} | {mean(charged_vals):.0f} | {delta:+.0f}"
                        )


if __name__ == "__main__":
    main()
