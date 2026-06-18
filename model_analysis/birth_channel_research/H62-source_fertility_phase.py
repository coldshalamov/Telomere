#!/usr/bin/env python3
"""H62 - public source/fertility phase boundary.

This is the constructive side of the H61 split. It models a public fertility
class, not a learned per-file pattern:

* a public class F has uniform mass f;
* the public witness/code distribution Q gives every F state a per-state lift a
  over uniform and gives the complement the normalizing multiplier b;
* a source visits F with probability c.

The score is:

    score(x) = log2(Q(x) / U(x))

Uniform data has negative expected score because `E_U[-log2 Q] >= n`. A
source-shaped lane crosses a target only when:

    E_source[score] > target_bits

That makes the hidden premise explicit: recursive maintenance requires future
layers to keep `c` above the threshold, not merely to find a one-time match.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class FertilityModel:
    class_fraction: float
    q_lift_inside: float

    @property
    def q_lift_outside(self) -> float:
        f = self.class_fraction
        a = self.q_lift_inside
        if f * a >= 1.0:
            return 0.0
        return (1.0 - f * a) / (1.0 - f)

    @property
    def score_inside(self) -> float:
        return math.log2(self.q_lift_inside)

    @property
    def score_outside(self) -> float:
        b = self.q_lift_outside
        if b <= 0.0:
            return float("-inf")
        return math.log2(b)

    @property
    def uniform_excess_bits(self) -> float:
        f = self.class_fraction
        return -(f * self.score_inside + (1.0 - f) * self.score_outside)

    def source_score(self, source_class_probability: float) -> float:
        c = source_class_probability
        return c * self.score_inside + (1.0 - c) * self.score_outside

    def threshold_c(self, target_bits: float) -> float:
        low = self.score_outside
        high = self.score_inside
        if target_bits <= low:
            return 0.0
        if target_bits >= high:
            return float("inf")
        return (target_bits - low) / (high - low)


@dataclass(frozen=True)
class Target:
    name: str
    target_bits: float
    unit: str


@dataclass(frozen=True)
class Row:
    model: FertilityModel
    target: Target
    threshold_c: float
    threshold_lift: float
    uniform_excess_bits: float
    score_inside: float
    score_outside: float


TARGETS = [
    Target("H59 public mixture miss", 0.053411 / 384.0, "bits/atom"),
    Target("H58 public Q miss", 0.229195 / 384.0, "bits/atom"),
    Target("H12 atom miss", 0.008196, "bits/atom"),
    Target("H7 atom miss", 0.011929, "bits/atom"),
    Target("H12 witness miss", 0.746, "bits/record"),
    Target("H7 witness miss", 1.357, "bits/record"),
]


def candidate_models() -> list[FertilityModel]:
    models: list[FertilityModel] = []
    for f in (0.01, 0.03, 0.10, 0.25):
        for a in (1.25, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0):
            if f * a < 0.98:
                models.append(FertilityModel(f, a))
    return models


def rows_for(targets: list[Target]) -> list[Row]:
    rows: list[Row] = []
    for model in candidate_models():
        for target in targets:
            c = model.threshold_c(target.target_bits)
            if math.isinf(c) or c > 1.0:
                continue
            rows.append(
                Row(
                    model=model,
                    target=target,
                    threshold_c=c,
                    threshold_lift=c / model.class_fraction,
                    uniform_excess_bits=model.uniform_excess_bits,
                    score_inside=model.score_inside,
                    score_outside=model.score_outside,
                )
            )
    return rows


def print_public_q_atom_targets() -> None:
    print("== source enrichment needed for closest atom-level misses ==")
    print("c is source probability of public class F; c/f is enrichment over uniform.")
    print(
        f"{'target':<24} {'f':>6} {'a':>6} {'b':>8} "
        f"{'U excess':>9} {'c*':>8} {'c*/f':>9}"
    )
    wanted = {"H59 public mixture miss", "H58 public Q miss", "H7 atom miss"}
    for row in rows_for([target for target in TARGETS if target.name in wanted]):
        if row.model.class_fraction not in (0.01, 0.10, 0.25):
            continue
        if row.model.q_lift_inside not in (2.0, 4.0, 8.0, 32.0):
            continue
        print(
            f"{row.target.name:<24} {row.model.class_fraction:6.2f} "
            f"{row.model.q_lift_inside:6.2f} {row.model.q_lift_outside:8.4f} "
            f"{row.uniform_excess_bits:9.6f} {row.threshold_c:8.4f} "
            f"{row.threshold_lift:9.3f}"
        )
    print()


def print_record_gap_targets() -> None:
    print("== source enrichment needed for selected-record witness gaps ==")
    print("These are harder: the source must concentrate strongly in high-fertility")
    print("classes unless the witness language itself removes the record gap.")
    print(
        f"{'target':<20} {'f':>6} {'a':>6} {'b':>8} "
        f"{'score F':>8} {'score other':>11} {'c*':>8} {'c*/f':>9}"
    )
    wanted = {"H12 witness miss", "H7 witness miss"}
    for row in rows_for([target for target in TARGETS if target.name in wanted]):
        if row.model.class_fraction not in (0.01, 0.10):
            continue
        if row.model.q_lift_inside not in (8.0, 32.0, 64.0):
            continue
        print(
            f"{row.target.name:<20} {row.model.class_fraction:6.2f} "
            f"{row.model.q_lift_inside:6.2f} {row.model.q_lift_outside:8.4f} "
            f"{row.score_inside:8.3f} {row.score_outside:11.3f} "
            f"{row.threshold_c:8.4f} {row.threshold_lift:9.3f}"
        )
    print()


def print_recursive_condition() -> None:
    print("== recursive maintenance condition ==")
    print("A source-shaped crossing is maintained only if each rewrite layer keeps")
    print("the public fertility-class probability above c*. A one-time source bias")
    print("that maps back to uniform loses the gain on the next pass.")
    print()
    print("Required invariant:")
    print("  c_t >= c* and c_{t+1} = Pr[encoded layer in F | c_t] >= c*")
    print()
    print("Biology-shaped reading:")
    print("  A developmental/neutral network can be useful only if it is a public")
    print("  source law that repeatedly steers layers into high-fertility states.")
    print("  Uniform controls must stay negative; otherwise the lift is unpriced.")


def main() -> None:
    print_public_q_atom_targets()
    print_record_gap_targets()
    print_recursive_condition()


if __name__ == "__main__":
    main()
