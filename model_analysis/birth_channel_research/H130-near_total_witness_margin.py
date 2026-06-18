#!/usr/bin/env python3
"""H130 - near-total board versus witness-margin target.

H24 showed all-open public lanes solve decode status but preserve witness
economics. H128 showed a near-total board needs extremely small exception
fractions under current margins. This kernel combines those facts:

    net = (1-eps) * records_per_atom * (base_margin + boost)
          - exception_ledger(eps, P)
          - eps * fallback_overhead

For each target row and exception fraction, solve the extra paid witness boost
per selected record required to break even.

If adding near-total exceptions lowers the target, it is a path. If it raises
the target, all-open q=1 remains the cleanest public-board version.
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Target:
    name: str
    records_per_atom: float
    base_margin_per_record: float


@dataclass(frozen=True)
class Row:
    target_name: str
    passes: int
    eps: float
    coverage: float
    fallback_overhead: float
    records_per_atom: float
    base_margin_per_record: float
    exception_bits_per_atom: float
    required_boost_per_record: float
    extra_over_all_open: float
    required_gain_per_atom: float


def h2(p: float) -> float:
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -(p * math.log2(p) + (1.0 - p) * math.log2(1.0 - p))


def exception_bits(eps: float, passes: int) -> float:
    return h2(eps) + eps * math.log2(max(1, passes - 1))


def default_targets() -> list[Target]:
    return [
        # Current high-arity total-cover nearest misses from H43/H7/H9/H12.
        Target("H7 raw first-hit delta", 0.008789, -1.357),
        Target("H9 fixed slack 0", 0.009765, -1.261),
        Target("H12 perfect-credit UB", 0.010987, -0.746),
        # H105 exact tiny-domain collective target: log2Z miss per record.
        Target("H105 custom_record", (1.781751 / 0.468557) / 12.0, -0.468557),
    ]


def required_boost(target: Target, eps: float, passes: int, fallback_overhead: float) -> Row:
    q = 1.0 - eps
    ex_bits = exception_bits(eps, passes) + eps * fallback_overhead
    denom = max(1e-300, q * target.records_per_atom)
    boost = -target.base_margin_per_record + ex_bits / denom
    all_open = -target.base_margin_per_record
    return Row(
        target_name=target.name,
        passes=passes,
        eps=eps,
        coverage=q,
        fallback_overhead=fallback_overhead,
        records_per_atom=target.records_per_atom,
        base_margin_per_record=target.base_margin_per_record,
        exception_bits_per_atom=ex_bits,
        required_boost_per_record=boost,
        extra_over_all_open=boost - all_open,
        required_gain_per_atom=boost * target.records_per_atom,
    )


def fmt(value: float) -> str:
    if math.isinf(value):
        return "inf"
    return f"{value:.9f}"


def print_rows(rows: list[Row]) -> None:
    print(
        "target,passes,eps,coverage,F,rec/atom,base_margin/rec,"
        "exception_bits/atom,required_boost/rec,extra_vs_all_open/rec,"
        "required_gain/atom"
    )
    for row in rows:
        print(
            f"{row.target_name},{row.passes},{fmt(row.eps)},"
            f"{fmt(row.coverage)},{fmt(row.fallback_overhead)},"
            f"{fmt(row.records_per_atom)},"
            f"{fmt(row.base_margin_per_record)},"
            f"{fmt(row.exception_bits_per_atom)},"
            f"{fmt(row.required_boost_per_record)},"
            f"{fmt(row.extra_over_all_open)},"
            f"{fmt(row.required_gain_per_atom)}"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--passes", type=int, action="append", default=[])
    parser.add_argument("--eps", type=float, action="append", default=[])
    parser.add_argument("--fallback-overhead", type=float, action="append", default=[])
    args = parser.parse_args()

    passes_values = args.passes or [2, 64, 4096]
    eps_values = args.eps or [0.0, 0.0005, 0.001, 0.002, 0.005, 0.01]
    fallback_values = args.fallback_overhead or [0.0, 3.0]
    rows: list[Row] = []
    for target in default_targets():
        for passes in passes_values:
            for fallback in fallback_values:
                for eps in eps_values:
                    rows.append(required_boost(target, eps, passes, fallback))
    print_rows(rows)


if __name__ == "__main__":
    main()
