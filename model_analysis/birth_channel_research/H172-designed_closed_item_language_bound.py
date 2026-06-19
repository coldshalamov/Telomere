#!/usr/bin/env python3
"""H172 - designed closed item-language bound.

This is the explicit grammar version of H171.

Suppose we design a fixed public total-cover record language G whose records
decode to item streams that are again valid inputs for G. Let W_a be the total
Kraft/match mass of all records that emit a items. For a uniform arbitrary item
stream, the total-cover partition function obeys:

    F_0 = 1
    F_n = sum_a W_a * F_{n-a}

A prefix-safe stateless grammar has:

    sum_a W_a <= 1.

The asymptotic growth rate lambda is defined by:

    sum_a W_a * lambda^-a = 1.

Positive recursive drift needs lambda > 1. But lambda > 1 implies
sum_a W_a > 1, so the grammar is overfull. This is the designed closed
item-language conservation law: closure can be public and stateless, but a
valid fixed grammar can at best break even under uniform all-data inputs.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class GrammarRow:
    name: str
    weights: tuple[float, ...]

    @property
    def max_arity(self) -> int:
        return len(self.weights)

    @property
    def kraft_mass(self) -> float:
        return sum(self.weights)


@dataclass(frozen=True)
class DriftRow:
    name: str
    max_arity: int
    kraft_mass: float
    lambda_rate: float
    log2_lambda: float
    valid_prefix: bool
    result: str


TARGET_GAPS = [
    ("H162 K5 D80 post-H165", 8.112500),
    ("H163 K16 D512 post-H165", 10.926442),
]


def fmt(value: float) -> str:
    if math.isinf(value):
        return "inf" if value > 0.0 else "-inf"
    if math.isnan(value):
        return "nan"
    if abs(value) >= 10_000.0 or (0.0 < abs(value) < 0.0001):
        return f"{value:.3e}"
    return f"{value:.6f}"


def characteristic(weights: tuple[float, ...], lambda_rate: float) -> float:
    return sum(weight * (lambda_rate ** (-(index + 1))) for index, weight in enumerate(weights))


def solve_lambda(weights: tuple[float, ...]) -> float:
    if not weights or sum(weights) <= 0.0:
        return 0.0
    low = 1e-12
    high = 1.0
    if characteristic(weights, high) < 1.0:
        while characteristic(weights, low) < 1.0:
            low *= 0.5
    else:
        while characteristic(weights, high) >= 1.0:
            high *= 2.0
    for _ in range(256):
        mid = (low + high) / 2.0
        value = characteristic(weights, mid)
        if value >= 1.0:
            low = mid
        else:
            high = mid
    return (low + high) / 2.0


def finite_log_z(weights: tuple[float, ...], n: int) -> float:
    f = [0.0] * (n + 1)
    f[0] = 1.0
    for length in range(1, n + 1):
        total = 0.0
        for arity, weight in enumerate(weights, start=1):
            if length >= arity:
                total += weight * f[length - arity]
        f[length] = total
    return math.log2(f[n]) if f[n] > 0.0 else float("-inf")


def grammar_rows() -> list[GrammarRow]:
    return [
        GrammarRow("singleton_valid", (1.0,)),
        GrammarRow("equal_valid_K5", (0.2, 0.2, 0.2, 0.2, 0.2)),
        GrammarRow("bundle_only_K5_valid_sparse", (0.0, 0.0, 0.0, 0.0, 1.0)),
        GrammarRow("front_loaded_valid_K5", (0.70, 0.20, 0.07, 0.02, 0.01)),
        GrammarRow("back_loaded_valid_K5", (0.01, 0.02, 0.07, 0.20, 0.70)),
        GrammarRow("underfull_K5", (0.05, 0.04, 0.03, 0.02, 0.01)),
        GrammarRow("overfull_all_ones_K5", (1.0, 1.0, 1.0, 1.0, 1.0)),
        GrammarRow("slightly_overfull_K5", (0.24, 0.24, 0.24, 0.24, 0.24)),
    ]


def drift_rows() -> list[DriftRow]:
    rows: list[DriftRow] = []
    for grammar in grammar_rows():
        lambda_rate = solve_lambda(grammar.weights)
        log_lambda = math.log2(lambda_rate) if lambda_rate > 0.0 else float("-inf")
        valid = grammar.kraft_mass <= 1.0 + 1e-12
        if valid and log_lambda > 1e-12:
            result = "BUG: valid positive drift"
        elif valid and abs(log_lambda) <= 1e-12:
            result = "valid break-even only"
        elif valid:
            result = "valid underfull negative drift"
        else:
            result = "overfull invalid positive mass"
        rows.append(
            DriftRow(
                name=grammar.name,
                max_arity=grammar.max_arity,
                kraft_mass=grammar.kraft_mass,
                lambda_rate=lambda_rate,
                log2_lambda=log_lambda,
                valid_prefix=valid,
                result=result,
            )
        )
    return rows


def minimum_overfull_for_item_margin(margin_bits_per_item: float, arity: int) -> float:
    """Kraft mass needed if one arity supplies the whole positive drift."""
    lambda_rate = 2.0**margin_bits_per_item
    return lambda_rate**arity


def print_drift_table() -> None:
    print("== designed closed item-language drift ==")
    print(
        f"{'grammar':<30} {'K':>4} {'sumW':>9} {'lambda':>9} "
        f"{'log2lam':>9} {'valid?':>7} {'logZ64':>9} {'result':<34}"
    )
    for row in drift_rows():
        log_z_64 = finite_log_z(grammar_by_name(row.name).weights, 64)
        print(
            f"{row.name:<30} {row.max_arity:4d} {fmt(row.kraft_mass):>9} "
            f"{fmt(row.lambda_rate):>9} {fmt(row.log2_lambda):>9} "
            f"{str(row.valid_prefix):>7} {fmt(log_z_64):>9} {row.result:<34}"
        )
    print()


def grammar_by_name(name: str) -> GrammarRow:
    for grammar in grammar_rows():
        if grammar.name == name:
            return grammar
    raise KeyError(name)


def print_overfull_targets() -> None:
    print("== overfull mass needed for target margins ==")
    print(
        "If an average arity-a record must supply r bits/record of missing margin, "
        "the per-item drift is r/a and the single-arity Kraft mass required is "
        "2^r. This is independent of arity."
    )
    print(
        f"{'target':<30} {'arity':>6} {'r/record':>10} "
        f"{'drift/item':>11} {'needed sumW':>12} {'overfull bits':>13}"
    )
    for label, gap in TARGET_GAPS:
        for arity in (1, 2, 5, 16, 64):
            drift = gap / arity
            required = minimum_overfull_for_item_margin(drift, arity)
            print(
                f"{label:<30} {arity:6d} {fmt(gap):>10} "
                f"{fmt(drift):>11} {fmt(required):>12} {fmt(math.log2(required)):>13}"
            )
    print()


def print_finite_rows() -> None:
    print("== finite-length exact F_n check ==")
    print(
        "Valid grammars have F_n <= 1 for every n. Overfull grammars can cross, "
        "which is exactly the invalid hidden-capacity case."
    )
    print(f"{'grammar':<30} {'logZ16':>9} {'logZ32':>9} {'logZ64':>9} {'logZ128':>9}")
    for grammar in grammar_rows():
        print(
            f"{grammar.name:<30} {fmt(finite_log_z(grammar.weights, 16)):>9} "
            f"{fmt(finite_log_z(grammar.weights, 32)):>9} "
            f"{fmt(finite_log_z(grammar.weights, 64)):>9} "
            f"{fmt(finite_log_z(grammar.weights, 128)):>9}"
        )
    print()


def print_reading() -> None:
    print("== reading ==")
    print(
        "This is the hand-designed closed item-language test in its most generous "
        "form. Closure is public and stateless by construction, but the total "
        "record mass still obeys the same recurrence. Positive all-data drift "
        "requires lambda>1, which requires sum W_a>1: an overfull code or hidden "
        "capacity. A valid designed grammar can break even only by spending the "
        "entire code mass on a lossless identity-like path."
    )


def main() -> None:
    print_drift_table()
    print_finite_rows()
    print_overfull_targets()
    print_reading()


if __name__ == "__main__":
    main()
