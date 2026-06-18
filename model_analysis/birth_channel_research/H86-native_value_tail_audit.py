#!/usr/bin/env python3
"""H86 - native future-value tail audit.

H85 showed that high-entropy fertility is mathematically plausible under an
ideal value tail. H86 measures the same budget curve on the exact H80 finite
Telomere-like domain.

For a visible output law P over words and a future-value score V(x), charge:

    delta = D(P || U) = raw_bits - H(P)

and credit only:

    lift = E_P[V] - E_U[V]

The useful fertility investment is lift - delta. This is not a compressor: it
is a response-surface audit for whether a public native syntax has enough
future-value lift per visible non-uniformity bit to be worth trying.
"""

from __future__ import annotations

import importlib.util
import math
import sys
from dataclasses import dataclass
from pathlib import Path


H80_PATH = Path(__file__).resolve().with_name("H80-public_q_fertility_lane.py")
_h80_spec = importlib.util.spec_from_file_location("h80_public_q_fertility_lane", H80_PATH)
if _h80_spec is None or _h80_spec.loader is None:
    raise RuntimeError("could not load H80 public-Q fertility lane kernel")
_h80 = importlib.util.module_from_spec(_h80_spec)
sys.modules[_h80_spec.name] = _h80
_h80_spec.loader.exec_module(_h80)


H84_MARGIN = 0.216226
H58_MISS = 0.229195


def entropy(probabilities: list[float]) -> float:
    return -sum(p * math.log2(p) for p in probabilities if p > 0.0)


def entropy_deficit(probabilities: list[float]) -> float:
    return math.log2(len(probabilities)) - entropy(probabilities)


def expectation(probabilities: list[float], values: list[float]) -> float:
    return sum(p * value for p, value in zip(probabilities, values))


def tilted_law(values: list[float], theta: float) -> list[float]:
    exponents = [theta * value for value in values]
    max_exponent = max(exponents)
    weights = [2.0 ** (exponent - max_exponent) for exponent in exponents]
    total = sum(weights)
    return [weight / total for weight in weights]


def law_on_indices(domain_size: int, indices: list[int]) -> list[float]:
    probability = 1.0 / len(indices)
    index_set = set(indices)
    return [probability if index in index_set else 0.0 for index in range(domain_size)]


@dataclass(frozen=True)
class LawRow:
    name: str
    delta: float
    lift: float
    lift_minus_delta: float
    gamma: float
    top25_mass: float
    entropy_bits: float


def law_row(name: str, probabilities: list[float], values: list[float], top25: list[int]) -> LawRow:
    delta = entropy_deficit(probabilities)
    uniform_value = sum(values) / len(values)
    lift = expectation(probabilities, values) - uniform_value
    return LawRow(
        name=name,
        delta=delta,
        lift=lift,
        lift_minus_delta=lift - delta,
        gamma=lift / delta if delta > 0.0 else float("inf"),
        top25_mass=sum(probabilities[index] for index in top25),
        entropy_bits=entropy(probabilities),
    )


def row_for_theta(name: str, values: list[float], top25: list[int], theta: float) -> LawRow:
    return law_row(name, tilted_law(values, theta), values, top25)


def theta_for_delta(values: list[float], target_delta: float) -> float:
    if target_delta <= 0.0:
        return 0.0
    hi = 1.0
    while entropy_deficit(tilted_law(values, hi)) < target_delta:
        hi *= 2.0
        if hi > 256.0:
            raise RuntimeError("could not bracket target delta")
    lo = 0.0
    for _ in range(120):
        mid = (lo + hi) / 2.0
        if entropy_deficit(tilted_law(values, mid)) < target_delta:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def row_for_delta(values: list[float], top25: list[int], target_delta: float) -> LawRow:
    theta = theta_for_delta(values, target_delta)
    return row_for_theta(f"optimal delta {target_delta:.6f}", values, top25, theta)


def delta_for_margin(values: list[float], top25: list[int], margin: float) -> LawRow:
    hi = 0.001
    while row_for_theta(f"margin {margin:.6f}", values, top25, hi).lift_minus_delta < margin:
        hi *= 2.0
        if hi > 256.0:
            raise RuntimeError("margin exceeds finite-domain frontier")
    lo = 0.0
    for _ in range(100):
        mid = (lo + hi) / 2.0
        if row_for_theta(f"margin {margin:.6f}", values, top25, mid).lift_minus_delta < margin:
            lo = mid
        else:
            hi = mid
    return row_for_theta(f"margin {margin:.6f}", values, top25, (lo + hi) / 2.0)


def print_domain(domain) -> None:
    print("== native value domain ==")
    print(
        f"B={domain.block_bits}, N={domain.atoms}, K={domain.max_arity}, "
        f"D={domain.depth_bits}, domain={len(domain.q)}"
    )
    print(f"raw visible word bits: {domain.raw_bits:.6f}")
    print(f"E_U score:             {domain.uniform_mean_score:.6f}")
    print(f"E_Q score:             {domain.q_mean_score:.6f}")
    print(f"D(Q||U):               {entropy_deficit(domain.q):.6f}")
    print()


def print_hard_support_rows(domain, values: list[float], top25: list[int]) -> None:
    print("== hard public support classes ==")
    print(f"{'class':<10} {'delta':>9} {'lift':>9} {'lift-delta':>12} {'Q(F)':>9}")
    for fraction in (0.01, 0.05, 0.10, 0.25):
        indices = _h80.top_class_indices(values, fraction)
        probabilities = law_on_indices(len(values), indices)
        row = law_row(f"top{fraction:.0%}", probabilities, values, top25)
        q_mass = sum(domain.q[index] for index in indices)
        print(
            f"{row.name:<10} {row.delta:9.6f} {row.lift:9.6f} "
            f"{row.lift_minus_delta:12.6f} {q_mass:9.6f}"
        )
    print()


def print_soft_frontier(values: list[float], top25: list[int]) -> None:
    print("== soft entropy/value frontier on H80 score ==")
    print(f"{'delta':>9} {'theta':>8} {'lift':>9} {'lift-delta':>12} {'gamma':>9} {'top25':>9}")
    for delta in (0.001, 0.01, 0.017703, 0.05, 0.10, H84_MARGIN, H58_MISS, 0.50, 1.0, 1.365022, 2.0):
        theta = theta_for_delta(values, delta)
        row = row_for_delta(values, top25, delta)
        print(
            f"{row.delta:9.6f} {theta:8.5f} {row.lift:9.6f} "
            f"{row.lift_minus_delta:12.6f} {row.gamma:9.3f} {row.top25_mass:9.6f}"
        )
    print()


def print_candidate_laws(domain, values: list[float], top25: list[int]) -> None:
    print("== named candidate laws ==")
    print(f"{'law':<15} {'delta':>9} {'lift':>9} {'lift-delta':>12} {'top25':>9} {'H(P)':>9}")
    candidates = [
        ("uniform", [1.0 / len(values)] * len(values)),
        ("H84 R0.90", tilted_law(values, 0.90)),
        ("Q/native", domain.q),
        ("hard top25", law_on_indices(len(values), top25)),
    ]
    for name, probabilities in candidates:
        row = law_row(name, probabilities, values, top25)
        print(
            f"{row.name:<15} {row.delta:9.6f} {row.lift:9.6f} "
            f"{row.lift_minus_delta:12.6f} {row.top25_mass:9.6f} {row.entropy_bits:9.6f}"
        )
    print()


def print_margin_targets(values: list[float], top25: list[int]) -> None:
    print("== entropy budget needed on measured H80 score ==")
    print(f"{'margin':>9} {'delta needed':>13} {'lift':>9} {'theta':>8} {'top25':>9}")
    for margin in (H84_MARGIN, H58_MISS, 0.50, 1.0, 1.50):
        row = delta_for_margin(values, top25, margin)
        theta = theta_for_delta(values, row.delta)
        print(
            f"{margin:9.6f} {row.delta:13.6f} {row.lift:9.6f} "
            f"{theta:8.5f} {row.top25_mass:9.6f}"
        )
    print()


def print_reading() -> None:
    print("== reading ==")
    print(
        "The measured H80 score tail has strong fertility ROI under soft tilts: "
        "future-value lift can exceed the visible entropy deficit. That keeps "
        "the source/fertility route alive, but it is not an all-data result. "
        "A recursive Telomere mechanism still has to make this law the native "
        "parseable output without hiding a selector, profile, or reshaping "
        "ledger. The next useful test is a real record-language candidate "
        "whose emitted bytes follow one of these high-ROI laws under its own "
        "fixed grammar."
    )


def main() -> None:
    domain = _h80.exact_domain()
    values = domain.scores
    top25 = _h80.top_class_indices(values, 0.25)
    print_domain(domain)
    print_hard_support_rows(domain, values, top25)
    print_soft_frontier(values, top25)
    print_candidate_laws(domain, values, top25)
    print_margin_targets(values, top25)
    print_reading()


if __name__ == "__main__":
    main()
