#!/usr/bin/env python3
"""Test higher pass counts under honest checksum accounting."""

from __future__ import annotations

import math
import random
from statistics import mean


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


def run_pass(blocks, pass_num, max_arity, frontier):
    out = []
    i = 0
    while i < len(blocks):
        best_score = -1.0
        best_arity = 1
        best_payload = 0
        for arity in range(1, min(max_arity, len(blocks) - i) + 1):
            span = sum(blocks[i + j] for j in range(arity))
            salt = make_salt(pass_num, i, arity)
            local_rng = random.Random(salt)
            rank = sample_first_rank(span, local_rng)
            payload_bits = max(1, rank.bit_length())
            if payload_bits > frontier:
                continue
            cost = record_cost(arity, payload_bits, max_arity)
            score = span - cost
            if score > best_score:
                best_score = score
                best_arity = arity
                best_payload = payload_bits
        if best_score >= 0:
            out.append(record_cost(best_arity, best_payload, max_arity))
            i += best_arity
        else:
            out.append(blocks[i])
            i += 1
    return out


def trial(num_blocks, block_bits, max_arity, frontier, max_passes, rng):
    blocks = [block_bits for _ in range(num_blocks)]
    for pass_num in range(1, max_passes + 1):
        blocks = run_pass(blocks, pass_num, max_arity, frontier)
    visible = sum(blocks)
    n_records = len(blocks)
    checksum_bits = n_records * math.log2(max_passes) if max_passes > 1 else 0
    header_bits = 32
    charged = visible + checksum_bits + header_bits
    return charged, visible, n_records, checksum_bits


def main():
    configs = [
        (256, 24, 4, 48, [64, 128, 256, 512, 1024]),
        (256, 24, 8, 72, [64, 128, 256]),
    ]
    trials = 12
    seed = 20260615
    rng = random.Random(seed)

    print("B | K | D | P | visible | records | checksum | charged | delta | pct")
    print("-" * 90)
    for num_blocks, block_bits, max_arity, frontier, pass_list in configs:
        for max_passes in pass_list:
            charged_vals = []
            visible_vals = []
            rec_counts = []
            checksum_vals = []
            for _ in range(trials):
                charged, visible, n_records, checksum_bits = trial(
                    num_blocks, block_bits, max_arity, frontier, max_passes, rng
                )
                charged_vals.append(charged)
                visible_vals.append(visible)
                rec_counts.append(n_records)
                checksum_vals.append(checksum_bits)
            raw = num_blocks * block_bits
            delta = mean(charged_vals) - raw
            pct = (mean(charged_vals) / raw - 1.0) * 100
            print(
                f"{block_bits} | {max_arity} | {frontier} | {max_passes} | "
                f"{mean(visible_vals):.0f} | {mean(rec_counts):.0f} | "
                f"{mean(checksum_vals):.0f} | {mean(charged_vals):.0f} | {delta:+.0f} | {pct:+.1f}%"
            )


if __name__ == "__main__":
    main()
