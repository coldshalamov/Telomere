#!/usr/bin/env python3
"""H63 - recursive fertility invariant threshold.

H62 gives the source class probability `c*` needed to cross a target. H63 asks
what the rewrite dynamics must preserve for recursive compression:

    c_{t+1} = c_t * p_FF + (1-c_t) * p_OF

where:

* F is a public high-fertility class;
* p_FF is the probability that an F input rewrites to an F output layer;
* p_OF is the background probability that a non-F input rewrites into F.

To maintain compression once `c_t >= c*`, the threshold must be forward
invariant:

    c* * p_FF + (1-c*) * p_OF >= c*

This is a toy dynamical ledger, not a compression test.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Scenario:
    target: str
    class_fraction: float
    q_lift_inside: float
    threshold_c: float
    background_inflow: float

    @property
    def min_p_ff(self) -> float:
        c = self.threshold_c
        p_of = self.background_inflow
        if c <= 0.0:
            return 0.0
        return max(0.0, min(1.0, (c - (1.0 - c) * p_of) / c))

    @property
    def canalization_gap(self) -> float:
        return self.min_p_ff - self.background_inflow

    @property
    def fixed_point_at_min(self) -> float:
        p_ff = self.min_p_ff
        p_of = self.background_inflow
        denominator = 1.0 - p_ff + p_of
        if denominator <= 0.0:
            return 1.0
        return p_of / denominator

    @property
    def odds_lift_at_min(self) -> float:
        p_ff = self.min_p_ff
        p_of = self.background_inflow
        if p_of <= 0.0:
            return float("inf")
        if p_ff >= 1.0:
            return float("inf")
        return (p_ff / (1.0 - p_ff)) / (p_of / (1.0 - p_of))


SCENARIOS = [
    # From H62 f=0.10,a=2 atom-level thresholds.
    Scenario("H59 atom", 0.10, 2.0, 0.1454, 0.10),
    Scenario("H58 atom", 0.10, 2.0, 0.1458, 0.10),
    Scenario("H7 atom", 0.10, 2.0, 0.1554, 0.10),
    # Stronger record-level thresholds from H62.
    Scenario("H12 witness", 0.10, 8.0, 0.5640, 0.10),
    Scenario("H7 witness", 0.10, 8.0, 0.6822, 0.10),
    Scenario("H7 witness rare", 0.01, 64.0, 0.3776, 0.01),
]


def variants() -> list[Scenario]:
    rows: list[Scenario] = []
    for scenario in SCENARIOS:
        for scale in (0.0, 0.5, 1.0, 2.0):
            p_of = min(0.99, scenario.class_fraction * scale)
            rows.append(
                Scenario(
                    scenario.target,
                    scenario.class_fraction,
                    scenario.q_lift_inside,
                    scenario.threshold_c,
                    p_of,
                )
            )
    return rows


def print_transition_thresholds() -> None:
    print("== recursive fertility transition threshold ==")
    print("p_OF is background inflow from non-F to F. min p_FF makes c* invariant.")
    print(
        f"{'target':<16} {'f':>6} {'a':>6} {'c*':>8} {'p_OF':>8} "
        f"{'min p_FF':>10} {'gap':>9} {'odds lift':>10} {'fixed pt':>9}"
    )
    for row in variants():
        if not (
            (row.background_inflow == row.class_fraction)
            or (row.target in {"H7 witness", "H7 witness rare"} and row.background_inflow == 0.0)
        ):
            continue
        odds = "inf" if math.isinf(row.odds_lift_at_min) else f"{row.odds_lift_at_min:.3f}"
        print(
            f"{row.target:<16} {row.class_fraction:6.2f} {row.q_lift_inside:6.1f} "
            f"{row.threshold_c:8.4f} {row.background_inflow:8.4f} "
            f"{row.min_p_ff:10.4f} {row.canalization_gap:9.4f} "
            f"{odds:>10} {row.fixed_point_at_min:9.4f}"
        )
    print()


def print_reading() -> None:
    print("== reading ==")
    print("Atom-level source alignment is dynamically plausible in this toy model:")
    print("with f=0.10,a=2 and background p_OF=0.10, the H59/H58 atom targets")
    print("need min p_FF about 0.41-0.42, not near-perfect self-renewal.")
    print()
    print("Record-level witness-gap targets are much stricter:")
    print("H7 witness with f=0.10,a=8 needs p_FF about 0.95 at background p_OF=0.10;")
    print("the rare f=0.01,a=64 version needs p_FF about 0.98 at background p_OF=0.01.")
    print()
    print("So the plausible breakthrough shape is:")
    print("  whole-cover/public-Q atom-level crossing first, then recursive fertility")
    print("  invariant; do not start by trying to pay the full local witness gap from")
    print("  source fertility alone.")


def main() -> None:
    print_transition_thresholds()
    print_reading()


if __name__ == "__main__":
    main()
