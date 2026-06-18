#!/usr/bin/env python3
"""H144 - non-greedy lookahead value target.

The greedy "first/smallest current seed" rule can waste option value. If many
valid replacements exist, the encoder can choose a seed that is larger now but
more fertile on later passes. The decoder does not need to know the discarded
alternatives; it only decodes the selected seed. This is not automatically a
metadata hack.

H144 prices the target:

    how much public future-value signal per candidate is needed
    for non-greedy selection to offset the current slack/exception bill?

The model is deliberately optimistic. Candidate count M is Poisson(lambda) from
H143's exact J3D1 public-board supply. Future values are iid exponential with
mean mu bits/atom, so the expected best future value is:

    E[max V_i] = mu * E[H_M]

where H_M is the harmonic number and H_0 = 0. This gives the minimum mean value
scale mu needed to make a row break even. A real codec must then measure that
value in a recurrent transfer kernel with same-budget random controls.
"""

from __future__ import annotations

import importlib.util
import math
import sys
from dataclasses import dataclass
from pathlib import Path

H143_PATH = Path(__file__).with_name("H143-near_total_public_board_bound.py")
H143_SPEC = importlib.util.spec_from_file_location("h143_near_total", H143_PATH)
if H143_SPEC is None or H143_SPEC.loader is None:
    raise RuntimeError(f"could not load {H143_PATH}")
h143 = importlib.util.module_from_spec(H143_SPEC)
sys.modules[H143_SPEC.name] = h143
H143_SPEC.loader.exec_module(h143)


@dataclass(frozen=True)
class LookaheadRow:
    block_bits: int
    max_arity: int
    slack_bits: int
    passes: int
    open_probability: float
    lambda_options: float
    expected_harmonic: float
    current_total_delta: float
    mu_required: float
    value_needed_if_open: float
    value_needed_per_expected_option: float
    expected_delta_if_open: float


def harmonic(n: int) -> float:
    return sum(1.0 / k for k in range(1, n + 1))


def expected_harmonic_poisson(lam: float) -> float:
    if lam <= 0.0:
        return 0.0
    # Recurrence for Poisson probabilities avoids huge factorials.
    p = math.exp(-lam) if lam < 745.0 else 0.0
    total = 0.0
    cumulative = p
    prob = p
    h = 0.0
    max_m = max(64, int(lam + 12.0 * math.sqrt(max(1.0, lam)) + 64))
    for m in range(1, max_m + 1):
        prob = prob * lam / m if m > 1 else p * lam
        h += 1.0 / m
        total += prob * h
        cumulative += prob
        if m > lam and 1.0 - cumulative < 1e-14:
            break
    # For very large lambda, the omitted tail is negligible in our rows. If
    # cumulative underflowed because p=0, use the asymptotic E[H_M] ~= log(lam)+gamma.
    if p == 0.0:
        return math.log(lam) + 0.5772156649015329
    return total


def rows() -> list[LookaheadRow]:
    laws = h143.laws()
    result: list[LookaheadRow] = []
    for law in laws:
        if law.block_bits not in (4, 8):
            continue
        if law.max_arity not in (32, 128, 512):
            continue
        if law.slack_bits not in (-1, 0, 2, 4, 8):
            continue
        eh = expected_harmonic_poisson(law.lambda_total)
        for passes in (2, 64, 4096):
            net = h143.net_row(law, passes, 0.0)
            current = net.total_delta_per_atom
            mu = current / eh if current > 0.0 and eh > 0.0 else 0.0
            result.append(
                LookaheadRow(
                    block_bits=law.block_bits,
                    max_arity=law.max_arity,
                    slack_bits=law.slack_bits,
                    passes=passes,
                    open_probability=law.open_probability,
                    lambda_options=law.lambda_total,
                    expected_harmonic=eh,
                    current_total_delta=current,
                    mu_required=mu,
                    value_needed_if_open=(current / law.open_probability if current > 0.0 and law.open_probability > 0.0 else 0.0),
                    value_needed_per_expected_option=(current / law.lambda_total if current > 0.0 and law.lambda_total > 0.0 else 0.0),
                    expected_delta_if_open=law.expected_delta_if_open,
                )
            )
    return result


def fmt(value: float) -> str:
    if value == float("inf"):
        return "inf"
    if abs(value) >= 1000.0 or (0.0 < abs(value) < 0.0001):
        return f"{value:.3e}"
    return f"{value:.6f}"


def print_rows(items: list[LookaheadRow]) -> None:
    print("== non-greedy lookahead value target ==")
    print("mu_required is mean exponential future value in bits/atom per candidate needed to break even.")
    print(
        f"{'B':>2} {'K':>4} {'s':>3} {'P':>5} {'q':>9} {'lambda':>9} "
        f"{'E[H_M]':>9} {'current':>10} {'mu req':>9} "
        f"{'need/open':>10} {'need/opt':>9} {'d|open':>9}"
    )
    for row in items:
        if row.block_bits != 4:
            continue
        if row.passes not in (2, 4096):
            continue
        if row.slack_bits not in (0, 2, 4, 8):
            continue
        print(
            f"{row.block_bits:2d} {row.max_arity:4d} {row.slack_bits:3d} "
            f"{row.passes:5d} {fmt(row.open_probability):>9} "
            f"{fmt(row.lambda_options):>9} {fmt(row.expected_harmonic):>9} "
            f"{fmt(row.current_total_delta):>10} {fmt(row.mu_required):>9} "
            f"{fmt(row.value_needed_if_open):>10} "
            f"{fmt(row.value_needed_per_expected_option):>9} "
            f"{fmt(row.expected_delta_if_open):>9}"
        )
    print()


def print_best(items: list[LookaheadRow]) -> None:
    print("== easiest rows to rescue with lookahead value ==")
    print(
        f"{'B':>2} {'K':>4} {'s':>3} {'P':>5} {'q':>9} "
        f"{'current':>10} {'mu req':>9} {'E[H_M]':>9}"
    )
    candidates = [row for row in items if row.current_total_delta > 0.0]
    for row in sorted(candidates, key=lambda item: item.mu_required)[:12]:
        print(
            f"{row.block_bits:2d} {row.max_arity:4d} {row.slack_bits:3d} "
            f"{row.passes:5d} {fmt(row.open_probability):>9} "
            f"{fmt(row.current_total_delta):>10} {fmt(row.mu_required):>9} "
            f"{fmt(row.expected_harmonic):>9}"
        )
    print()


def print_reading() -> None:
    print("== reading ==")
    print(
        "Non-greedy choice is a real target: if selected seeds have a public, "
        "measurable future-value signal, the encoder can spend current slack "
        "to buy later compression without sending the discarded alternatives."
    )
    print(
        "The rows with tiny mu_required are the bloating/high-multiplicity rows. "
        "That means the next proof obligation is not another metadata ledger; "
        "it is a recurrent transfer measurement showing that same-budget chosen "
        "seeds have future value above random alternatives by the required scale."
    )
    print(
        "If future values are iid under the uniform law and no public fertility "
        "feature predicts them, the best-of value is just search over a random "
        "score and must be validated with held-out/same-budget controls."
    )


def main() -> None:
    items = rows()
    print_rows(items)
    print_best(items)
    print_reading()


if __name__ == "__main__":
    main()
