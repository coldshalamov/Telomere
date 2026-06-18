#!/usr/bin/env python3
"""H138 - bounded-loss reset/ratchet ledger.

Loophole: maybe allow occasional reset/literalization events to bound rare
blowups, while the ordinary passes have negative drift.

A reset solves bounded loss, but it destroys accumulated recursive shrink. The
final saving after P passes is controlled by the good suffix since the last
reset. To maintain positive rate over arbitrary P on roughly all data, the
reset probability must shrink like O(1/P). If reset events are stored/visible in
the layer stack, their marker cost is another linear bill.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class ResetRow:
    passes: int
    eps_reset: float
    saving_per_good_pass: float
    marker_bits_per_reset: float
    expected_suffix_good: float
    expected_suffix_saving: float
    expected_marker_cost: float
    net_suffix_saving: float
    net_per_pass: float
    no_reset_probability: float
    half_rate_probability: float
    eps_needed_for_90_half_rate: float


def expected_trailing_good(passes: int, eps: float) -> float:
    q = 1.0 - eps
    if eps <= 0.0:
        return float(passes)
    return q * (1.0 - q**passes) / eps


def row(passes: int, eps: float, saving: float, marker: float) -> ResetRow:
    q = 1.0 - eps
    suffix = expected_trailing_good(passes, eps)
    suffix_saving = saving * suffix
    marker_cost = passes * eps * marker
    net = suffix_saving - marker_cost
    half_needed = math.ceil(0.5 * passes)
    half_prob = q**half_needed
    eps_needed = 1.0 - (0.90 ** (1.0 / half_needed))
    return ResetRow(
        passes=passes,
        eps_reset=eps,
        saving_per_good_pass=saving,
        marker_bits_per_reset=marker,
        expected_suffix_good=suffix,
        expected_suffix_saving=suffix_saving,
        expected_marker_cost=marker_cost,
        net_suffix_saving=net,
        net_per_pass=net / passes,
        no_reset_probability=q**passes,
        half_rate_probability=half_prob,
        eps_needed_for_90_half_rate=eps_needed,
    )


def rows() -> list[ResetRow]:
    out: list[ResetRow] = []
    for passes in (64, 256, 4096):
        for eps in (0.01, 0.001, 0.0001):
            for saving in (0.01, 0.10, 1.0):
                out.append(row(passes, eps, saving, marker=3.0))
    return out


def print_rows(result: list[ResetRow]) -> None:
    print("== bounded reset / ratchet ledger ==")
    print("Final saving comes from the good suffix since the last reset.")
    print(
        f"{'P':>5} {'eps':>8} {'s/good':>8} {'E suffix':>10} {'suffix save':>12} "
        f"{'marker':>9} {'net/pass':>10} {'no reset':>10} {'half-rate':>10}"
    )
    for item in result:
        if item.saving_per_good_pass not in (0.10, 1.0):
            continue
        if item.passes == 256 and item.eps_reset != 0.001:
            continue
        print(
            f"{item.passes:5d} {item.eps_reset:8.4g} {item.saving_per_good_pass:8.3f} "
            f"{item.expected_suffix_good:10.3f} {item.expected_suffix_saving:12.3f} "
            f"{item.expected_marker_cost:9.3f} {item.net_per_pass:10.6f} "
            f"{item.no_reset_probability:10.6f} {item.half_rate_probability:10.6f}"
        )
    print()


def print_thresholds() -> None:
    print("== reset probability needed for roughly-all linear savings ==")
    print("Require at least half the ideal all-good suffix with 90% probability.")
    print(f"{'P':>7} {'needed eps max':>16}")
    for passes in (64, 256, 4096, 1_000_000):
        half_needed = math.ceil(0.5 * passes)
        eps_needed = 1.0 - (0.90 ** (1.0 / half_needed))
        print(f"{passes:7d} {eps_needed:16.9g}")
    print()


def print_reading() -> None:
    print("== reading ==")
    print(
        "A reset ratchet can bound damage, but it cannot preserve arbitrary-pass "
        "linear compression unless resets become vanishingly rare. The final "
        "compressed length depends on the suffix after the last reset, not the "
        "entire history of good passes."
    )
    print(
        "For roughly-all positive rate over arbitrary P, eps must scale like "
        "O(1/P), and reset markers/literalization still have to be carried by "
        "the recursive layer stream. Otherwise the ratchet is bounded-loss "
        "engineering, not maintained compression."
    )


def main() -> None:
    result = rows()
    print_rows(result)
    print_thresholds()
    print_reading()


if __name__ == "__main__":
    main()
