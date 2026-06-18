#!/usr/bin/env python3
"""H106 - cover-sequence Kraft capacity.

H105's best honest target still needed 0.468557 bits/record. One possible
loophole is arity-weight allocation: maybe custom_record lost because it spent
record Kraft mass evenly over arities instead of putting mass where covers need
it.

This kernel separates the pure cover-sequence grammar from hash values.

Let W_a be the total Kraft mass of all record symbols with arity a. A whole
cover of N atoms is a sequence of arities summing to N, so its total mass is:

    F_0 = 1
    F_n = sum_{a=1..K} W_a F_{n-a}

For a uniquely parseable public record grammar, sum_a W_a <= 1. By induction,
F_n <= 1 for every n. Therefore arity reweighting can at best make the
collective whole-cover family complete (log2Z = 0), never positive. Positive
log2Z requires invalid extra Kraft mass, a source prior, or another visible
invariant.
"""

from __future__ import annotations

import math
import random


def cover_mass(weights: list[float], atoms: int) -> float:
    dp = [0.0] * (atoms + 1)
    dp[0] = 1.0
    for n in range(1, atoms + 1):
        total = 0.0
        for arity, weight in enumerate(weights, start=1):
            if arity <= n:
                total += weight * dp[n - arity]
        dp[n] = total
    return dp[atoms]


def log2_or_neg_inf(value: float) -> float:
    return math.log2(value) if value > 0.0 else float("-inf")


def equal_weights(max_arity: int) -> list[float]:
    return [1.0 / max_arity] * max_arity


def point_mass(max_arity: int, arity: int) -> list[float]:
    return [1.0 if index == arity else 0.0 for index in range(1, max_arity + 1)]


def random_simplex(max_arity: int, rng: random.Random) -> list[float]:
    xs = [rng.expovariate(1.0) for _ in range(max_arity)]
    total = sum(xs)
    return [x / total for x in xs]


def best_random(atoms: int, max_arity: int, trials: int, seed: int) -> tuple[float, list[float]]:
    rng = random.Random(seed)
    best = -1.0
    best_w: list[float] = []
    for _ in range(trials):
        weights = random_simplex(max_arity, rng)
        value = cover_mass(weights, atoms)
        if value > best:
            best = value
            best_w = weights
    return best, best_w


def print_capacity_table() -> None:
    print("== cover-sequence Kraft capacity ==")
    print("All rows obey sum_a W_a = 1. Valid public record grammars cannot exceed log2Z=0.")
    print(f"{'N':>4} {'K':>3} {'equal log2F':>12} {'best divisor':>12} {'random max':>12}")
    for atoms, max_arity in ((12, 6), (12, 8), (24, 6), (24, 12), (64, 16)):
        equal = cover_mass(equal_weights(max_arity), atoms)
        divisors = [
            (arity, cover_mass(point_mass(max_arity, arity), atoms))
            for arity in range(1, max_arity + 1)
            if atoms % arity == 0
        ]
        best_divisor = max(divisors, key=lambda row: row[1]) if divisors else (0, 0.0)
        sample_trials = 5000 if atoms <= 24 else 1000
        random_best, _ = best_random(atoms, max_arity, sample_trials, seed=106000 + atoms * 31 + max_arity)
        print(
            f"{atoms:4d} {max_arity:3d} {log2_or_neg_inf(equal):12.6f} "
            f"a={best_divisor[0]}, {log2_or_neg_inf(best_divisor[1]):.6f} "
            f"{log2_or_neg_inf(random_best):12.6f}"
        )
    print()


def print_invalid_mass_table() -> None:
    print("== how positive log2Z is bought ==")
    print("If total record mass M=sum W_a exceeds 1, log2Z can become positive, but M>1 violates Kraft.")
    atoms = 12
    max_arity = 6
    base = point_mass(max_arity, 6)
    print(f"{'M':>6} {'log2 F_N':>12} {'valid?':>8}")
    for mass in (0.5, 1.0, 1.1, 1.25, 1.5, 2.0):
        weights = [w * mass for w in base]
        value = cover_mass(weights, atoms)
        print(f"{mass:6.2f} {log2_or_neg_inf(value):12.6f} {str(mass <= 1.0):>8}")
    print()


def print_h105_interpretation() -> None:
    print("== H105 interpretation ==")
    print(
        "H105's 0.468557 bits/record target is not recoverable by merely "
        "reweighting arities inside a valid public record grammar. Reweighting "
        "can move a negative row up toward a complete whole-cover grammar "
        "(log2Z=0), but it cannot make log2Z_total > 0."
    )
    print(
        "A positive forced-rewrite collective row must therefore source real "
        "extra mass elsewhere: an invalid/underpriced code, a named non-uniform "
        "source law, a paid visible invariant, or a genuinely new syntax whose "
        "Kraft accounting is not equivalent to ordinary record sequences."
    )


def main() -> None:
    print_capacity_table()
    print_invalid_mass_table()
    print_h105_interpretation()


if __name__ == "__main__":
    main()
