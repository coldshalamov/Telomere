#!/usr/bin/env python3
"""H85 - entropy-budget fertility frontier.

H84 says repeatability needs a high-entropy fertile law: future compression
value must separate from mere source entropy deficit.

H85 models the cleanest possible frontier. Under a uniform/content-blind future
value tail:

    Pr_U[V >= s] = 2^-s

the value distribution is geometric. For a public source P with entropy deficit
delta = D(P||U), the maximum E_P[V] is achieved by exponential tilting. This
kernel reports the best possible value lift under that KL/entropy budget.

If measured mechanisms beat these rows, the value tail is not the uniform hash
tail; it is a real public source/developmental law. If they merely match these
rows, the source entropy budget is doing the work and must be charged.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


BASE_MEAN = 1.0


def tilted_stats(theta: float) -> tuple[float, float]:
    """Return (mean_value, kl_bits) for geometric base tilted by 2^(theta*v)."""

    if not 0.0 <= theta < 1.0:
        raise ValueError("theta must be in [0,1)")
    a = 2.0 ** (theta - 1.0)
    mean_value = a / (1.0 - a)
    log_z = -1.0 - math.log2(1.0 - a)
    kl_bits = theta * mean_value - log_z
    return mean_value, kl_bits


def theta_for_delta(delta_bits: float) -> float:
    if delta_bits <= 0.0:
        return 0.0
    lo = 0.0
    hi = 1.0 - 1e-12
    for _ in range(200):
        mid = (lo + hi) / 2.0
        _, kl_bits = tilted_stats(mid)
        if kl_bits < delta_bits:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


@dataclass(frozen=True)
class BudgetRow:
    delta_bits: float
    theta: float
    mean_value: float
    value_lift: float
    lift_minus_delta: float
    gamma: float


def budget_row(delta_bits: float) -> BudgetRow:
    theta = theta_for_delta(delta_bits)
    mean_value, _ = tilted_stats(theta)
    lift = mean_value - BASE_MEAN
    return BudgetRow(
        delta_bits=delta_bits,
        theta=theta,
        mean_value=mean_value,
        value_lift=lift,
        lift_minus_delta=lift - delta_bits,
        gamma=lift / delta_bits if delta_bits > 0.0 else float("inf"),
    )


def rows() -> list[BudgetRow]:
    return [
        budget_row(delta)
        for delta in (0.001, 0.01, 0.03, 0.05, 0.10, 0.216226, 0.25, 0.50, 1.0, 1.365022, 2.0, 4.0)
    ]


def delta_for_margin(required_margin: float) -> BudgetRow:
    lo = 0.0
    hi = 1.0
    while budget_row(hi).lift_minus_delta < required_margin:
        hi *= 2.0
    for _ in range(120):
        mid = (lo + hi) / 2.0
        if budget_row(mid).lift_minus_delta < required_margin:
            lo = mid
        else:
            hi = mid
    return budget_row((lo + hi) / 2.0)


def print_rows() -> None:
    print("== entropy-budget fertility frontier ==")
    print(
        "delta is source entropy deficit D(P||U). Value lift is the maximum "
        "extra future bits under the uniform tail Pr[V>=s]=2^-s."
    )
    print(
        f"{'delta':>9} {'theta':>8} {'E[V]':>10} {'lift':>10} "
        f"{'lift-delta':>12} {'gamma':>9}"
    )
    for row in rows():
        print(
            f"{row.delta_bits:9.6f} {row.theta:8.5f} {row.mean_value:10.4f} "
            f"{row.value_lift:10.4f} {row.lift_minus_delta:12.4f} "
            f"{row.gamma:9.3f}"
        )
    print()


def print_margin_targets() -> None:
    print("== entropy budget needed for finite margins ==")
    print(
        "These are ideal upper-bound rows. A real Telomere mechanism still has "
        "to realize the value law with a stateless parse and uniform controls."
    )
    print(f"{'margin':>9} {'delta needed':>13} {'E[V]':>10} {'lift':>10} {'theta':>8}")
    for margin in (0.05, 0.216226, 0.50, 1.0, 2.0):
        row = delta_for_margin(margin)
        print(
            f"{margin:9.6f} {row.delta_bits:13.6f} {row.mean_value:10.4f} "
            f"{row.value_lift:10.4f} {row.theta:8.5f}"
        )
    print()


def print_reading() -> None:
    print("== reading ==")
    print(
        "A high-entropy fertile law is mathematically plausible in this ideal "
        "tail model: small entropy deficits can create value lift larger than "
        "the deficit. But that is a source-law statement, not a free all-data "
        "result. A Telomere breakthrough needs a public native syntax whose "
        "measured future-value tail follows such a law while arbitrary uniform "
        "inputs remain negative after the same accounting."
    )


def main() -> None:
    print_rows()
    print_margin_targets()
    print_reading()


if __name__ == "__main__":
    main()
