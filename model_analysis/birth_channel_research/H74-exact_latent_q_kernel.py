#!/usr/bin/env python3
"""H74 - exact tiny latent whole-cover Q kernel.

This tests the cleanest remaining Total-Cover witness language:

    Q_raw(x) = sum over all covers/descriptions that generate x of 2^-L(desc)
    Q(x)     = Q_raw(x) / sum_y Q_raw(y)

The selected cover is not transmitted. A decoder would arithmetic-decode the
previous layer under the frozen public Q. This preserves duplicate-cover and
order-statistic advantages without a selected-cover side channel.

The uniform-law check is exact over a tiny finite domain:

    E_U[-log2 Q(X)] = n + KL(U || Q) >= n

If some strings receive zero Q mass, H74 also tests the honest raw/Q mixture:

    Q_alpha = (1-alpha) U + alpha Q

and grid-searches alpha. Under uniform U the best alpha should be 0 unless Q is
exactly uniform; any positive crossing is a bug or finite accounting leak.
"""

from __future__ import annotations

import argparse
import math
import random
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model_analysis.proof_kernel.costs import record_cost_for_payload_width  # noqa: E402
from total_cover_lotus_crossover import lotus_payload_width_from_rank  # noqa: E402


@dataclass(frozen=True)
class KernelResult:
    block_bits: int
    atoms: int
    max_arity: int
    depth_bits: int
    domain_size: int
    z_mass: float
    reachable_fraction: float
    cross_entropy_bits: float
    excess_bits: float
    below_raw_fraction: float
    avg_duplicate_gain_bits: float
    best_alpha: float
    best_mixture_cross_entropy_bits: float
    best_mixture_excess_bits: float


def fixed_arity_bits(max_arity: int) -> int:
    if max_arity <= 2:
        return 1
    return math.ceil(math.log2(max_arity))


def record_cost(max_arity: int, arity: int, payload_width: int) -> int:
    if arity <= 5:
        return record_cost_for_payload_width(arity, payload_width)
    return fixed_arity_bits(max_arity) + payload_width


def span_value(word: int, start_atom: int, arity: int, block_bits: int, atoms: int) -> int:
    """Extract the integer value for atoms [start_atom, start_atom+arity)."""

    shift_atoms = atoms - (start_atom + arity)
    shift = shift_atoms * block_bits
    mask = (1 << (arity * block_bits)) - 1
    return (word >> shift) & mask


def build_edge_weights(
    block_bits: int,
    max_arity: int,
    depth_bits: int,
    seed: int,
) -> tuple[list[list[float]], list[list[float]]]:
    """Return total and max single-description weights by arity/value."""

    rng = random.Random(seed)
    total_weights: list[list[float]] = [[]]
    max_weights: list[list[float]] = [[]]
    seed_count = 1 << depth_bits
    for arity in range(1, max_arity + 1):
        value_count = 1 << (arity * block_bits)
        weights = [0.0] * value_count
        maxes = [0.0] * value_count
        for rank in range(1, seed_count + 1):
            width = lotus_payload_width_from_rank(rank)
            cost = record_cost(max_arity, arity, width)
            weight = 2.0 ** (-cost)
            value = rng.randrange(value_count)
            weights[value] += weight
            if weight > maxes[value]:
                maxes[value] = weight
        total_weights.append(weights)
        max_weights.append(maxes)
    return total_weights, max_weights


def dp_mass_for_word(
    word: int,
    atoms: int,
    block_bits: int,
    max_arity: int,
    edge_weights: list[list[float]],
    edge_maxes: list[list[float]],
) -> tuple[float, float]:
    total_dp = [0.0] * (atoms + 1)
    max_dp = [0.0] * (atoms + 1)
    total_dp[0] = 1.0
    max_dp[0] = 1.0
    for end in range(1, atoms + 1):
        total = 0.0
        best = 0.0
        for arity in range(1, min(max_arity, end) + 1):
            start = end - arity
            value = span_value(word, start, arity, block_bits, atoms)
            edge = edge_weights[arity][value]
            if edge > 0.0:
                total += total_dp[start] * edge
            edge_best = edge_maxes[arity][value]
            if edge_best > 0.0:
                best = max(best, max_dp[start] * edge_best)
        total_dp[end] = total
        max_dp[end] = best
    return total_dp[atoms], max_dp[atoms]


def cross_entropy_for_mixture(q_values: list[float], alpha: float) -> float:
    domain = len(q_values)
    u = 1.0 / domain
    return -sum(math.log2((1.0 - alpha) * u + alpha * q) for q in q_values) / domain


def run_kernel(block_bits: int, atoms: int, max_arity: int, depth_bits: int, seed: int) -> KernelResult:
    domain = 1 << (block_bits * atoms)
    edge_weights, edge_maxes = build_edge_weights(block_bits, max_arity, depth_bits, seed)

    q_raw: list[float] = []
    best_raw: list[float] = []
    for word in range(domain):
        total, best = dp_mass_for_word(word, atoms, block_bits, max_arity, edge_weights, edge_maxes)
        q_raw.append(total)
        best_raw.append(best)

    z = sum(q_raw)
    if z <= 0.0:
        raise RuntimeError("Q has zero total mass; increase depth_bits or lower atom count")

    q = [value / z for value in q_raw]
    u = 1.0 / domain
    reachable = sum(1 for value in q_raw if value > 0.0) / domain

    if any(value == 0.0 for value in q):
        cross_entropy = float("inf")
        excess = float("inf")
    else:
        cross_entropy = -sum(math.log2(value) for value in q) / domain
        excess = cross_entropy - math.log2(domain)

    below_raw = sum(1 for value in q if value > u) / domain
    duplicate_gains = [
        math.log2(total / best)
        for total, best in zip(q_raw, best_raw)
        if total > 0.0 and best > 0.0
    ]
    avg_dup = sum(duplicate_gains) / len(duplicate_gains) if duplicate_gains else 0.0

    best_alpha = 0.0
    best_ce = math.log2(domain)
    for i in range(0, 101):
        alpha = i / 100.0
        ce = cross_entropy_for_mixture(q, alpha)
        if ce < best_ce:
            best_ce = ce
            best_alpha = alpha

    return KernelResult(
        block_bits=block_bits,
        atoms=atoms,
        max_arity=max_arity,
        depth_bits=depth_bits,
        domain_size=domain,
        z_mass=z,
        reachable_fraction=reachable,
        cross_entropy_bits=cross_entropy,
        excess_bits=excess,
        below_raw_fraction=below_raw,
        avg_duplicate_gain_bits=avg_dup,
        best_alpha=best_alpha,
        best_mixture_cross_entropy_bits=best_ce,
        best_mixture_excess_bits=best_ce - math.log2(domain),
    )


def print_result(result: KernelResult) -> None:
    print("== exact latent whole-cover Q ==")
    print(
        f"B={result.block_bits}, N={result.atoms}, K={result.max_arity}, "
        f"D={result.depth_bits}, domain={result.domain_size}"
    )
    print(f"raw bits:                     {math.log2(result.domain_size):.6f}")
    print(f"Q raw Kraft mass Z:           {result.z_mass:.12e}")
    print(f"reachable fraction:           {result.reachable_fraction:.6f}")
    if math.isinf(result.cross_entropy_bits):
        print("Q cross entropy:              inf (zero-mass strings)")
        print("Q excess over raw:            inf")
    else:
        print(f"Q cross entropy:              {result.cross_entropy_bits:.6f}")
        print(f"Q excess over raw:            {result.excess_bits:.6f}")
    print(f"fraction with Q(x)>U(x):      {result.below_raw_fraction:.6f}")
    print(f"avg duplicate-cover gain:     {result.avg_duplicate_gain_bits:.6f}")
    print(f"best raw/Q alpha grid:        {result.best_alpha:.2f}")
    print(f"best mixture cross entropy:   {result.best_mixture_cross_entropy_bits:.6f}")
    print(f"best mixture excess:          {result.best_mixture_excess_bits:.6f}")
    print()
    print("Reading: duplicate covers can create winners, but the normalized public")
    print("Q does not beat uniform average. The honest raw/Q mixture chooses alpha")
    print("0 unless the public Q is exactly uniform or a non-uniform source is named.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--block-bits", type=int, default=2)
    parser.add_argument("--atoms", type=int, default=8)
    parser.add_argument("--max-arity", type=int, default=4)
    parser.add_argument("--depth-bits", type=int, default=8)
    parser.add_argument("--seed", type=int, default=74)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_kernel(args.block_bits, args.atoms, args.max_arity, args.depth_bits, args.seed)
    print_result(result)


if __name__ == "__main__":
    main()
