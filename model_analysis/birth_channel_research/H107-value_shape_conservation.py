#!/usr/bin/env python3
"""H107 - value-shape conservation for fixed record mass.

H106 closes ordinary arity reweighting as a source of positive whole-cover
Kraft mass. Another tempting route is to bias the generator/seed grammar toward
"fertile" output values while keeping the same code lengths.

This kernel fixes the arity Kraft masses W_a and changes only how each arity's
mass is distributed over output values. The total description mass Z is
unchanged. The normalized public output law Q can become very non-uniform, but
uniform-source cross entropy cannot fall below raw.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass


@dataclass(frozen=True)
class ShapeRow:
    shape: str
    z_mass: float
    log2_z: float
    reachable_fraction: float
    cross_entropy_bits: float
    excess_bits: float
    best_alpha: float
    best_mixture_excess: float
    below_raw_fraction: float


def cover_mass(weights: list[float], atoms: int) -> float:
    dp = [0.0] * (atoms + 1)
    dp[0] = 1.0
    for n in range(1, atoms + 1):
        dp[n] = sum(weight * dp[n - arity] for arity, weight in enumerate(weights, start=1) if arity <= n)
    return dp[atoms]


def span_value(word: int, start_atom: int, arity: int, block_bits: int, atoms: int) -> int:
    shift_atoms = atoms - (start_atom + arity)
    shift = shift_atoms * block_bits
    mask = (1 << (arity * block_bits)) - 1
    return (word >> shift) & mask


def arity_value_weights(
    shape: str,
    arity_masses: list[float],
    block_bits: int,
    seed: int,
) -> list[list[float]]:
    rng = random.Random(seed)
    tables: list[list[float]] = [[]]
    for arity, mass in enumerate(arity_masses, start=1):
        values = 1 << (arity * block_bits)
        if shape == "uniform_values":
            table = [mass / values] * values
        elif shape == "zero_attractor":
            table = [0.0] * values
            table[0] = mass
        elif shape == "half_fertile":
            table = [0.0] * values
            fertile = max(1, values // 2)
            for value in range(fertile):
                table[value] = mass / fertile
        elif shape == "random_lumpy":
            draws = [rng.expovariate(1.0) for _ in range(values)]
            total = sum(draws)
            table = [mass * draw / total for draw in draws]
        else:
            raise ValueError(shape)
        tables.append(table)
    return tables


def q_raw_for_word(
    word: int,
    atoms: int,
    block_bits: int,
    max_arity: int,
    tables: list[list[float]],
) -> float:
    dp = [0.0] * (atoms + 1)
    dp[0] = 1.0
    for end in range(1, atoms + 1):
        total = 0.0
        for arity in range(1, min(max_arity, end) + 1):
            start = end - arity
            value = span_value(word, start, arity, block_bits, atoms)
            total += dp[start] * tables[arity][value]
        dp[end] = total
    return dp[atoms]


def cross_entropy_for_mixture(q_values: list[float], alpha: float) -> float:
    domain = len(q_values)
    u = 1.0 / domain
    total = 0.0
    for q in q_values:
        probability = (1.0 - alpha) * u + alpha * q
        if probability <= 0.0:
            return float("inf")
        total += math.log2(probability)
    return -total / domain


def evaluate_shape(
    shape: str,
    atoms: int,
    block_bits: int,
    max_arity: int,
    arity_masses: list[float],
    seed: int,
) -> ShapeRow:
    domain = 1 << (atoms * block_bits)
    tables = arity_value_weights(shape, arity_masses, block_bits, seed)
    q_raw = [q_raw_for_word(word, atoms, block_bits, max_arity, tables) for word in range(domain)]
    z_mass = sum(q_raw)
    q = [value / z_mass for value in q_raw]
    reachable = sum(1 for value in q if value > 0.0) / domain
    if any(value <= 0.0 for value in q):
        ce = float("inf")
        excess = float("inf")
    else:
        ce = -sum(math.log2(value) for value in q) / domain
        excess = ce - math.log2(domain)
    best_alpha = 0.0
    best_ce = math.log2(domain)
    for index in range(101):
        alpha = index / 100.0
        trial = cross_entropy_for_mixture(q, alpha)
        if trial < best_ce:
            best_ce = trial
            best_alpha = alpha
    u = 1.0 / domain
    return ShapeRow(
        shape=shape,
        z_mass=z_mass,
        log2_z=math.log2(z_mass),
        reachable_fraction=reachable,
        cross_entropy_bits=ce,
        excess_bits=excess,
        best_alpha=best_alpha,
        best_mixture_excess=best_ce - math.log2(domain),
        below_raw_fraction=sum(1 for value in q if value > u) / domain,
    )


def print_rows(rows: list[ShapeRow], expected_log2_z: float) -> None:
    print("== value-shape conservation ==")
    print(f"Expected log2Z from arity recurrence: {expected_log2_z:.6f}")
    print(
        f"{'shape':<15} {'log2Z':>10} {'reach':>8} {'CE excess':>10} "
        f"{'best alpha':>10} {'mix excess':>11} {'Q>U frac':>9}"
    )
    for row in rows:
        excess = "inf" if math.isinf(row.excess_bits) else f"{row.excess_bits:.6f}"
        print(
            f"{row.shape:<15} {row.log2_z:10.6f} {row.reachable_fraction:8.3f} "
            f"{excess:>10} {row.best_alpha:10.2f} "
            f"{row.best_mixture_excess:11.6f} {row.below_raw_fraction:9.3f}"
        )
    print()


def print_reading() -> None:
    print("== reading ==")
    print(
        "Changing the public value law reshapes which strings are favored, but "
        "does not change total description mass. Under a uniform roughly-all-data "
        "claim, normalized Q cannot beat raw on average; the best raw/Q mixture "
        "falls back to alpha=0 unless Q is exactly uniform."
    )
    print(
        "So biased seed grammars can be useful only as a named source-shaped or "
        "fertility-cycle mechanism with its entropy deficit paid. They do not "
        "supply the missing H105 witness margin for content-blind all-data."
    )


def main() -> None:
    atoms = 12
    block_bits = 1
    max_arity = 6
    arity_masses = [1.0 / max_arity] * max_arity
    expected = math.log2(cover_mass(arity_masses, atoms))
    rows = [
        evaluate_shape(shape, atoms, block_bits, max_arity, arity_masses, seed=107000)
        for shape in ("uniform_values", "zero_attractor", "half_fertile", "random_lumpy")
    ]
    print_rows(rows, expected)
    print_reading()


if __name__ == "__main__":
    main()
