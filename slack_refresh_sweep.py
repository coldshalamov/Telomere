#!/usr/bin/env python3
"""Parameter sweep for slack-refresh sparse replacement recursion."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from statistics import mean


@dataclass(frozen=True)
class Block:
    bits: tuple[int, ...]
    pass_born: int


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
        best_span = len(blocks[i].bits)
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
                best_span = span_bits
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


def bbl_cost(arity, max_passes, e_a):
    if max_passes <= 1:
        return 0.0
    return math.log2(1.0 + (max_passes - 1) * 2.0 ** (-e_a))


def trial(num_blocks, block_bits, max_arity, frontier, slack, max_passes, e_a, header_bits, rng):
    blocks = [Block(tuple(rng.randint(0, 1) for _ in range(block_bits)), 0) for _ in range(num_blocks)]
    for pass_num in range(1, max_passes + 1):
        blocks = run_pass(blocks, pass_num, max_arity, frontier, slack, rng)
    ambiguity = sum(bbl_cost(1, max_passes, e_a) for b in blocks if b.pass_born > 0)
    final = stream_size(blocks) + ambiguity + header_bits
    return final - num_blocks * block_bits


def main():
    trials = 24
    seed = 20260615
    rng = random.Random(seed)
    header_bits = 32
    e_a = 12

    configs = []
    for block_bits in (16, 24, 32):
        for max_arity in (4, 6, 8):
            for frontier in (block_bits * 2, block_bits * 3, int(block_bits * 2.5)):
                configs.append((block_bits, max_arity, frontier))

    print("B | K | D | slack | delta")
    print("-" * 40)
    for block_bits, max_arity, frontier in configs:
        for slack in (0, 1):
            deltas = []
            for _ in range(trials):
                d = trial(256, block_bits, max_arity, frontier, slack, 8, e_a, header_bits, rng)
                deltas.append(d)
            print(f"{block_bits} | {max_arity} | {frontier} | {slack} | {mean(deltas):+.2f}")


if __name__ == "__main__":
    main()
