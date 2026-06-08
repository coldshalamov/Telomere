"""Hit and gain distributions for content-agnostic Telomere seed search."""

from __future__ import annotations

import math
from functools import lru_cache

from costs import min_record_bits, seed_records_with_cost_le


LN2 = math.log(2.0)


def M(arity: int, record_budget_bits: int, depth_bits: int) -> int:
    """Required kernel formula: number of records with cost <= r under D."""

    return seed_records_with_cost_le(arity, record_budget_bits, depth_bits)


def _poissonized_at_least_one(log_expected: float) -> float:
    if log_expected > 36.0:
        return 1.0
    if log_expected < -36.0:
        return math.exp(log_expected)
    return -math.expm1(-math.exp(log_expected))


@lru_cache(maxsize=None)
def p_min_record_le(
    record_budget_bits: int,
    span_bits: int,
    arity: int,
    depth_bits: int,
    opportunity_multiplier: float = 1.0,
    exact_small: bool = False,
) -> float:
    """P(min record cost <= r | S, a, D), with optional variant multiplier."""

    if record_budget_bits < min_record_bits(min(arity, 5)) or span_bits <= 0:
        return 0.0
    seed_count = M(arity, record_budget_bits, depth_bits)
    if seed_count <= 0 or opportunity_multiplier <= 0:
        return 0.0

    trials = seed_count * opportunity_multiplier
    if exact_small and span_bits <= 24 and trials <= 1_000_000:
        q = 2.0 ** (-span_bits)
        return 1.0 - ((1.0 - q) ** trials)

    log_expected = math.log(trials) - span_bits * LN2
    return _poissonized_at_least_one(log_expected)


def gain_tail(
    span_bits: int,
    arity: int,
    depth_bits: int,
    opportunity_multiplier: float = 1.0,
    max_gain_bits: int | None = None,
) -> list[float]:
    """Return [P(gain >= 1), P(gain >= 2), ...]."""

    if max_gain_bits is None:
        max_gain_bits = max(0, span_bits - min_record_bits(min(arity, 5)))
    tail: list[float] = []
    for gain in range(1, max_gain_bits + 1):
        tail.append(
            p_min_record_le(
                span_bits - gain,
                span_bits,
                arity,
                depth_bits,
                opportunity_multiplier,
            )
        )
    return tail


def gain_exact_distribution(
    span_bits: int,
    arity: int,
    depth_bits: int,
    opportunity_multiplier: float = 1.0,
    cutoff: float = 1e-15,
) -> dict[int, float]:
    """Mass function over exact gain values, derived from the full tail."""

    tail = gain_tail(span_bits, arity, depth_bits, opportunity_multiplier)
    out: dict[int, float] = {}
    prev = 0.0
    for i in range(len(tail), 0, -1):
        ge_i = tail[i - 1]
        exact = max(0.0, ge_i - prev)
        if exact > cutoff:
            out[i] = exact
        prev = ge_i
    return out


def expected_gain_per_window(
    span_bits: int,
    arity: int,
    depth_bits: int,
    opportunity_multiplier: float = 1.0,
) -> float:
    return sum(gain_tail(span_bits, arity, depth_bits, opportunity_multiplier))


def expected_gain_given_hit(
    span_bits: int,
    arity: int,
    depth_bits: int,
    opportunity_multiplier: float = 1.0,
) -> float:
    hit = p_min_record_le(span_bits - 1, span_bits, arity, depth_bits, opportunity_multiplier)
    if hit <= 0:
        return 0.0
    return expected_gain_per_window(span_bits, arity, depth_bits, opportunity_multiplier) / hit


def exact_toy_hit_probability(span_bits: int, seed_outputs: int) -> float:
    """Exact finite probability for tiny independent seed-output universes."""

    if span_bits < 1 or seed_outputs < 0:
        raise ValueError("invalid toy universe")
    target_count = 1 << span_bits
    miss_assignments = (target_count - 1) ** seed_outputs
    total_assignments = target_count**seed_outputs
    return 1.0 - (miss_assignments / total_assignments)


def validate_toy_probabilities() -> list[dict[str, float | int]]:
    """Exact toy validation for S in {4,6,8} and arity 1..5."""

    rows: list[dict[str, float | int]] = []
    for span_bits in (4, 6, 8):
        for arity in range(1, 6):
            seed_outputs = arity + 1
            enumerated = exact_toy_hit_probability(span_bits, seed_outputs)
            analytic = 1.0 - (1.0 - 2.0 ** (-span_bits)) ** seed_outputs
            delta = abs(enumerated - analytic)
            if delta > 1e-15:
                raise AssertionError(
                    f"toy mismatch S={span_bits} arity={arity}: {enumerated} != {analytic}"
                )
            rows.append(
                {
                    "span_bits": span_bits,
                    "arity": arity,
                    "seed_outputs": seed_outputs,
                    "probability": analytic,
                    "abs_delta": delta,
                }
            )
    return rows


if __name__ == "__main__":
    for row in validate_toy_probabilities():
        print(row)
