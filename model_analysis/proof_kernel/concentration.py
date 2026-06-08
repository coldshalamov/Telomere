"""Concentration bounds for large-file Telomere expectation statements."""

from __future__ import annotations

import math
from dataclasses import dataclass

from costs import literal_entry_bits, record_cost_for_payload_width


@dataclass(frozen=True)
class ConcentrationBound:
    epsilon_ratio: float
    alpha: float
    per_block_swing_bits: float
    statement: str


def per_block_swing(block_bits: int, arity_cap: int, payload_width_bits: int = 160) -> float:
    literal = literal_entry_bits(block_bits)
    record_share = max(
        record_cost_for_payload_width(arity, min(payload_width_bits, arity * block_bits)) / arity
        for arity in range(1, arity_cap + 1)
    )
    return literal + record_share


def deviation_probability(entry_count: int, block_bits: int, arity_cap: int, epsilon_ratio: float) -> float:
    if entry_count <= 0:
        return 1.0
    c = per_block_swing(block_bits, arity_cap)
    t = epsilon_ratio * entry_count * block_bits
    exponent = -2.0 * t * t / (entry_count * c * c)
    if exponent < -700:
        return 0.0
    return min(1.0, 2.0 * math.exp(exponent))


def epsilon_for_confidence(
    entry_count: int,
    block_bits: int,
    arity_cap: int,
    alpha: float = 1e-9,
) -> ConcentrationBound:
    c = per_block_swing(block_bits, arity_cap)
    eps = c * math.sqrt(math.log(2.0 / alpha) / (2.0 * entry_count)) / block_bits
    return ConcentrationBound(
        epsilon_ratio=eps,
        alpha=alpha,
        per_block_swing_bits=c,
        statement=(
            "P(|final/raw - E| > epsilon) <= alpha by a bounded-differences "
            "bound using the stated per-block swing."
        ),
    )


if __name__ == "__main__":
    for n in (10**6, 10**9, 10**12):
        bound = epsilon_for_confidence(n, 24, 5)
        print(n, bound)
