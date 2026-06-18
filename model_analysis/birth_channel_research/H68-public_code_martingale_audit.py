#!/usr/bin/env python3
"""H68 - finite public-code martingale audit.

This is a tiny exact-domain version of the H57-H59 conservation check.

For a public normalized distribution Q over n-bit layers:

    L(x) = -log2 Q(x)
    W(x) = Q(x) / U(x) = 2^(n-L(x))

Under uniform X, E[W(X)] = 1 and:

    E[L(X)] = n + KL(U || Q) >= n

Thus "use the public code only on the strings where it helps" is a hidden
selector unless converted into a normalized public mixture. This kernel prints
the exact finite-domain numbers for a few toy Q profiles and their mixtures.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


def normalize(weights: list[float]) -> list[float]:
    total = sum(weights)
    if total <= 0.0:
        raise ValueError("weights must have positive mass")
    return [weight / total for weight in weights]


def spiky_distribution(size: int, heavy_count: int, lift: float) -> list[float]:
    weights = [1.0] * size
    for index in range(min(size, heavy_count)):
        weights[index] *= lift
    return normalize(weights)


def lane_distribution(size: int, modulus: int, residue: int, lift: float) -> list[float]:
    weights = [1.0] * size
    for index in range(size):
        if index % modulus == residue:
            weights[index] *= lift
    return normalize(weights)


def mixture(distributions: list[list[float]], alpha: float) -> list[float]:
    size = len(distributions[0])
    uniform = 1.0 / size
    lane_weight = alpha / len(distributions)
    return [
        (1.0 - alpha) * uniform
        + lane_weight * sum(distribution[index] for distribution in distributions)
        for index in range(size)
    ]


@dataclass(frozen=True)
class AuditRow:
    name: str
    n_bits: int
    excess_bits: float
    mean_log2_wealth: float
    mean_wealth: float
    fraction_saves_1: float
    fraction_saves_2: float
    hidden_selector_gain: float


def audit(name: str, distribution: list[float], hidden_profiles: list[list[float]] | None = None) -> AuditRow:
    size = len(distribution)
    n_bits = int(math.log2(size))
    if 2**n_bits != size:
        raise ValueError("domain size must be a power of two")
    uniform = 1.0 / size
    lengths = [-math.log2(probability) for probability in distribution]
    wealth = [probability / uniform for probability in distribution]
    expected_length = sum(lengths) / size
    mean_wealth = sum(wealth) / size
    fraction_saves_1 = sum(1 for length in lengths if length <= n_bits - 1) / size
    fraction_saves_2 = sum(1 for length in lengths if length <= n_bits - 2) / size

    hidden_gain = 0.0
    if hidden_profiles:
        best_lengths = [
            -math.log2(max(profile[index] for profile in hidden_profiles))
            for index in range(size)
        ]
        hidden_gain = expected_length - (sum(best_lengths) / size)

    return AuditRow(
        name=name,
        n_bits=n_bits,
        excess_bits=expected_length - n_bits,
        mean_log2_wealth=sum(math.log2(value) for value in wealth) / size,
        mean_wealth=mean_wealth,
        fraction_saves_1=fraction_saves_1,
        fraction_saves_2=fraction_saves_2,
        hidden_selector_gain=hidden_gain,
    )


def print_rows() -> None:
    n_bits = 8
    size = 2**n_bits
    profiles = [
        spiky_distribution(size, 16, 8.0),
        lane_distribution(size, 4, 1, 5.0),
        lane_distribution(size, 4, 2, 5.0),
        lane_distribution(size, 4, 3, 5.0),
    ]
    rows = [
        audit("uniform", [1.0 / size] * size),
        audit("spiky public Q", profiles[0]),
        audit("lane public Q", profiles[1]),
        audit("raw/Q mixture alpha=.25", mixture(profiles, 0.25)),
        audit("raw/Q mixture alpha=.75", mixture(profiles, 0.75)),
        audit("hidden best-of 4 profiles", mixture(profiles, 0.75), profiles),
    ]

    print("== finite public-code martingale audit ==")
    print(
        f"{'name':<26} {'excess':>10} {'E log2 W':>10} {'E W':>8} "
        f"{'Pr save>=1':>11} {'Pr save>=2':>11} {'hidden gain':>12}"
    )
    for row in rows:
        print(
            f"{row.name:<26} {row.excess_bits:10.6f} "
            f"{row.mean_log2_wealth:10.6f} {row.mean_wealth:8.6f} "
            f"{row.fraction_saves_1:11.6f} {row.fraction_saves_2:11.6f} "
            f"{row.hidden_selector_gain:12.6f}"
        )
    print()


def print_reading() -> None:
    print("== reading ==")
    print("For every normalized public Q, E[W]=1 and excess >= 0. Some strings")
    print("get short codes, but the winning fraction obeys the same betting bound.")
    print("The hidden best-of row shows why post-selecting the best profile looks")
    print("good: it reports a hidden selector gain. Turning that into a public")
    print("mixture restores the normalized excess >= 0 check.")


def main() -> None:
    print_rows()
    print_reading()


if __name__ == "__main__":
    main()
