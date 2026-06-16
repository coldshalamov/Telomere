#!/usr/bin/env python3
"""Measure conditional entropy of (arity, width) sequences from total-cover DP."""

from __future__ import annotations

import json
import math
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from total_cover_lotus_crossover import (
    EdgeSample,
    SelectedRecord,
    generate_samples,
    lotus_payload_width_from_log_rank,
    local_payload_bits_from_log_rank,
    sample_log2_first_rank,
)


def entropy_from_counts(counts: Counter) -> float:
    total = sum(counts.values())
    if total == 0:
        return 0.0
    h = 0.0
    for c in counts.values():
        if c > 0:
            p = c / total
            h -= p * math.log2(p)
    return h


def conditional_entropy(pairs: list[tuple[int, int]]) -> dict:
    # H(X)
    x_counts = Counter(p[0] for p in pairs)
    h_x = entropy_from_counts(x_counts)

    # H(Y)
    y_counts = Counter(p[1] for p in pairs)
    h_y = entropy_from_counts(y_counts)

    # H(X, Y)
    joint_counts = Counter(pairs)
    h_xy = entropy_from_counts(joint_counts)

    # H(Y | X) = H(X,Y) - H(X)
    h_y_given_x = h_xy - h_x

    # First-order Markov: H(X_i | X_{i-1})
    if len(pairs) >= 2:
        x_prev_counts = Counter(pairs[i][0] for i in range(len(pairs) - 1))
        cond_x_given_prev_counts: dict[int, Counter] = {}
        for i in range(len(pairs) - 1):
            prev = pairs[i][0]
            curr = pairs[i + 1][0]
            if prev not in cond_x_given_prev_counts:
                cond_x_given_prev_counts[prev] = Counter()
            cond_x_given_prev_counts[prev][curr] += 1
        h_x_given_prev = 0.0
        for prev, total in x_prev_counts.items():
            sub = cond_x_given_prev_counts[prev]
            sub_total = sum(sub.values())
            h_x_given_prev += (total / (len(pairs) - 1)) * entropy_from_counts(sub)
    else:
        h_x_given_prev = 0.0

    # H(Y_i | Y_{i-1})
    if len(pairs) >= 2:
        y_prev_counts = Counter(pairs[i][1] for i in range(len(pairs) - 1))
        cond_y_given_prev_counts: dict[int, Counter] = {}
        for i in range(len(pairs) - 1):
            prev = pairs[i][1]
            curr = pairs[i + 1][1]
            if prev not in cond_y_given_prev_counts:
                cond_y_given_prev_counts[prev] = Counter()
            cond_y_given_prev_counts[prev][curr] += 1
        h_y_given_prev = 0.0
        for prev, total in y_prev_counts.items():
            sub = cond_y_given_prev_counts[prev]
            h_y_given_prev += (total / (len(pairs) - 1)) * entropy_from_counts(sub)
    else:
        h_y_given_prev = 0.0

    # H((X_i,Y_i) | (X_{i-1},Y_{i-1}))
    if len(pairs) >= 2:
        prev_joint_counts = Counter(pairs[i] for i in range(len(pairs) - 1))
        cond_joint_given_prev_counts: dict[tuple, Counter] = {}
        for i in range(len(pairs) - 1):
            prev = pairs[i]
            curr = pairs[i + 1]
            if prev not in cond_joint_given_prev_counts:
                cond_joint_given_prev_counts[prev] = Counter()
            cond_joint_given_prev_counts[prev][curr] += 1
        h_joint_given_prev = 0.0
        for prev, total in prev_joint_counts.items():
            sub = cond_joint_given_prev_counts[prev]
            h_joint_given_prev += (total / (len(pairs) - 1)) * entropy_from_counts(sub)
    else:
        h_joint_given_prev = 0.0

    return {
        "H(arity)": h_x,
        "H(width)": h_y,
        "H(arity,width)": h_xy,
        "H(width|arity)": h_y_given_x,
        "H(arity_i|arity_i-1)": h_x_given_prev,
        "H(width_i|width_i-1)": h_y_given_prev,
        "H(arity_i,width_i|arity_i-1,width_i-1)": h_joint_given_prev,
    }


def run_dp_and_collect_records(
    trial: list[list[EdgeSample]],
    block_bits: int,
    max_arity: int,
    frontier: int,
) -> tuple[SelectedRecord, ...]:
    # Simple local-cost DP matching arith_arity_width_lotus_payload
    atoms = len(trial)
    dp = [float("inf")] * (atoms + 1)
    prev = [None] * (atoms + 1)
    dp[0] = 0.0
    for index in range(atoms):
        base = dp[index]
        if base == float("inf"):
            continue
        for offset, edge in enumerate(trial[index], start=1):
            if offset > max_arity:
                break
            if edge.lotus_payload_width > frontier:
                continue
            cost = edge.lotus_payload_width
            candidate = base + cost
            end = index + offset
            if candidate < dp[end]:
                dp[end] = candidate
                prev[end] = (index, offset, edge)
    if dp[atoms] == float("inf"):
        return ()
    cursor = atoms
    records = []
    while cursor > 0:
        prior, arity, edge = prev[cursor]
        records.append(
            SelectedRecord(
                arity=arity,
                lotus_payload_width=edge.lotus_payload_width,
                local_payload_bits=edge.local_payload_bits,
                cost_bits=edge.lotus_payload_width,
            )
        )
        cursor = prior
    records.reverse()
    return tuple(records)


def main():
    block_bits = 24
    max_arity = 8
    frontier = 168
    atoms = 256
    trials = 48
    seed = 20260615

    samples = generate_samples(block_bits, max_arity, atoms, trials, seed)

    all_sequences = []
    for trial in samples:
        records = run_dp_and_collect_records(trial, block_bits, max_arity, frontier)
        if records:
            seq = [(r.arity, r.lotus_payload_width) for r in records]
            all_sequences.append(seq)

    print(f"Collected {len(all_sequences)} sequences, total records: {sum(len(s) for s in all_sequences)}")

    # Concatenate all sequences (with sentinel gaps to avoid cross-sequence conditioning)
    flat = []
    for seq in all_sequences:
        flat.extend(seq)
        flat.append((-1, -1))  # sentinel

    # Remove sentinels for some analyses
    clean = [p for p in flat if p[0] != -1]

    ent = conditional_entropy(clean)
    print("\nEmpirical entropies (bits/symbol):")
    for k, v in ent.items():
        print(f"  {k}: {v:.4f}")

    # Compare to multinomial lower bound used in arith mode
    symbols = Counter(clean)
    n = len(clean)
    from math import lgamma
    multinomial_bits = (lgamma(n + 1) - sum(lgamma(c + 1) for c in symbols.values())) / math.log(2)
    iid_bits_per_record = multinomial_bits / n
    print(f"\nIID joint entropy H(arity,width) per record: {iid_bits_per_record:.4f}")
    print(f"First-order Markov H(sym|prev) per record: {ent['H(arity_i,width_i|arity_i-1,width_i-1)']:.4f}")
    print(f"Potential savings from first-order Markov: {iid_bits_per_record - ent['H(arity_i,width_i|arity_i-1,width_i-1)']:.4f} bits/record")

    # Delta / second-order checks
    if len(clean) >= 2:
        deltas = [clean[i][1] - clean[i-1][1] for i in range(1, len(clean))]
        delta_counts = Counter(deltas)
        h_delta = entropy_from_counts(delta_counts)
        print(f"\nH(width_i - width_i-1): {h_delta:.4f} vs H(width): {ent['H(width)']:.4f}")

    if len(clean) >= 3:
        h_width_given_prev2 = 0.0
        prev2_counts = Counter((clean[i][1], clean[i+1][1]) for i in range(len(clean) - 2))
        cond: dict[tuple, Counter] = {}
        for i in range(len(clean) - 2):
            key = (clean[i][1], clean[i+1][1])
            val = clean[i+2][1]
            if key not in cond:
                cond[key] = Counter()
            cond[key][val] += 1
        for key, total in prev2_counts.items():
            sub = cond[key]
            h_width_given_prev2 += (total / (len(clean) - 2)) * entropy_from_counts(sub)
        print(f"H(width_i | width_i-1, width_i-2): {h_width_given_prev2:.4f}")

    # Position-based context: width | position mod M
    for M in [2, 4, 8, 16]:
        pos_counts = Counter(i % M for i, _ in enumerate(clean))
        cond_pos: dict[int, Counter] = {}
        for i, (a, w) in enumerate(clean):
            key = i % M
            if key not in cond_pos:
                cond_pos[key] = Counter()
            cond_pos[key][w] += 1
        h_width_given_pos = 0.0
        for key, total in pos_counts.items():
            sub = cond_pos[key]
            h_width_given_pos += (total / len(clean)) * entropy_from_counts(sub)
        print(f"H(width | position mod {M}): {h_width_given_pos:.4f}")


if __name__ == "__main__":
    main()
