#!/usr/bin/env python3
"""H200 - nearest generated-cover residual ledger.

H199 enumerates tiny H198 root + residual balls.  H200 takes the large-N limit:
if M generated phenotypes each get a residual family of volume V, then expected
coverage is

    f ~= 1 - exp(-M*V/2^N).

This lets us price the strongest nearest-codeword story directly at 90%, 99%,
or 99.9% coverage.  The residual volume needed for coverage f is

    log2(V) ~= N - log2(M) + log2(-ln(1-f)).

Best-of-M roots buy log2(M) residual bits, but the selected root channel costs
log2(M) plus native record overhead.  Fallback holes add more.
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass


def fmt(value: float) -> str:
    if math.isinf(value):
        return "inf" if value > 0.0 else "-inf"
    if math.isnan(value):
        return "nan"
    if value == 0.0:
        return "0"
    if abs(value) >= 10_000.0 or abs(value) < 0.0001:
        return f"{value:.3e}"
    return f"{value:.6f}"


def parse_float_list(values: list[str], default: list[float]) -> list[float]:
    if not values:
        return default
    out: list[float] = []
    for value in values:
        out.extend(float(part) for part in value.split(",") if part)
    return out


def parse_int_list(values: list[str], default: list[int]) -> list[int]:
    if not values:
        return default
    out: list[int] = []
    for value in values:
        out.extend(int(part) for part in value.split(",") if part)
    return out


def slack_for_coverage(coverage: float) -> float:
    if not 0.0 < coverage < 1.0:
        raise ValueError("coverage must be between 0 and 1")
    return math.log2(-math.log1p(-coverage))


def coverage_for_slack(slack: float) -> float:
    return 1.0 - math.exp(-(2.0**slack))


def kraft_implicit_delta(raw_bits: int, coverage: float, short_delta: float) -> tuple[float, str]:
    """Expected delta under implicit leftover-Kraft raw fallback.

    short length is N + short_delta.  If covered aliases consume Kraft mass >=1,
    the row is overfull/non-UD and the numeric delta is not valid.
    """

    q = coverage * (2.0 ** (-short_delta))
    if q >= 1.0:
        return math.inf, "overfull"
    raw_len = raw_bits - math.log2(1.0 - q)
    short_len = raw_bits + short_delta
    expected = coverage * short_len + (1.0 - coverage) * raw_len
    return expected - raw_bits, "ok"


@dataclass(frozen=True)
class Row:
    raw_bits: int
    m_bits: int
    root_mode: str
    root_bits: float
    slack: float
    coverage: float
    residual_log2: float
    short_delta: float
    hard_delta: float
    kraft_delta: float
    kraft_status: str


def row_for(raw_bits: int, m_bits: int, root_mode: str, root_bits: float, slack: float) -> Row:
    coverage = coverage_for_slack(slack)
    residual_log2 = raw_bits - m_bits + slack
    short_delta = root_bits + residual_log2 - raw_bits
    short_len = raw_bits + short_delta
    hard_expected = coverage * (1.0 + short_len) + (1.0 - coverage) * (1.0 + raw_bits)
    hard_delta = hard_expected - raw_bits
    kraft_delta, status = kraft_implicit_delta(raw_bits, coverage, short_delta)
    return Row(
        raw_bits=raw_bits,
        m_bits=m_bits,
        root_mode=root_mode,
        root_bits=root_bits,
        slack=slack,
        coverage=coverage,
        residual_log2=residual_log2,
        short_delta=short_delta,
        hard_delta=hard_delta,
        kraft_delta=kraft_delta,
        kraft_status=status,
    )


def print_table(args: argparse.Namespace) -> None:
    m_values = parse_int_list(args.m_bits, [8, 12, 16])
    slacks = parse_float_list(args.slack, [-4.0, -2.0, 0.0, 1.0, 2.203, 3.0, 4.0, 8.0])
    print("== H200 nearest generated-cover residual ledger ==")
    print("Large-N analytic version of H199. Slack s means coverage ~= 1-exp(-2^s).")
    print(
        f"{'N':>8} {'m':>4} {'mode':<12} {'root':>9} {'s':>8} {'cov':>9} "
        f"{'logV':>12} {'shortD':>10} {'hardD':>10} {'kraftD':>10} {'status'}"
    )
    modes = [
        ("free_index", 0.0),
        ("paid_index", None),
        ("native_fixed", float(args.native_fixed_root_bits)),
        ("native_stored", float(args.native_stored_root_bits)),
    ]
    best_paid: Row | None = None
    for m_bits in m_values:
        for mode, root_override in modes:
            root_bits = float(m_bits if root_override is None else root_override)
            for slack in slacks:
                row = row_for(args.raw_bits, m_bits, mode, root_bits, slack)
                if mode != "free_index" and row.kraft_status == "ok":
                    if best_paid is None or row.kraft_delta < best_paid.kraft_delta:
                        best_paid = row
                print(
                    f"{row.raw_bits:8d} {row.m_bits:4d} {row.root_mode:<12} "
                    f"{fmt(row.root_bits):>9} {fmt(row.slack):>8} "
                    f"{fmt(row.coverage):>9} {fmt(row.residual_log2):>12} "
                    f"{fmt(row.short_delta):>10} {fmt(row.hard_delta):>10} "
                    f"{fmt(row.kraft_delta):>10} {row.kraft_status}"
                )
    if best_paid is not None:
        print()
        print(
            "best valid paid Kraft-fallback delta: "
            f"{fmt(best_paid.kraft_delta)} at mode={best_paid.root_mode},"
            f"m={best_paid.m_bits},s={fmt(best_paid.slack)},coverage={fmt(best_paid.coverage)}"
        )


def print_coverage_table(args: argparse.Namespace) -> None:
    coverages = parse_float_list(args.coverage, [0.5, 0.9, 0.99, 0.999])
    print()
    print("== requested coverage rows for native H198 best case ==")
    print(f"{'coverage':>9} {'slack':>10} {'shortD_fixed':>13} {'shortD_stored':>13}")
    for coverage in coverages:
        slack = slack_for_coverage(coverage)
        fixed_delta = args.native_fixed_root_bits - args.bound_m_bits + slack
        stored_delta = args.native_stored_root_bits - args.bound_m_bits + slack
        print(
            f"{fmt(coverage):>9} {fmt(slack):>10} "
            f"{fmt(fixed_delta):>13} {fmt(stored_delta):>13}"
        )


def print_theorem() -> None:
    print()
    print("== theorem ==")
    print("For coverage f, residual_log2 ~= N-m+log2(-ln(1-f)).")
    print("A paid selected-root index costs at least m; native H198 costs m plus")
    print("record overhead. Therefore high-coverage residual coding is N plus")
    print("coverage slack and overhead, before fallback/bin syntax.")
    print("Rows where a free index appears to win are exactly the hidden root")
    print("selector channel.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-bits", type=int, default=500_000)
    parser.add_argument("--m-bits", action="append", default=[])
    parser.add_argument("--bound-m-bits", type=int, default=16)
    parser.add_argument("--native-fixed-root-bits", type=int, default=27)
    parser.add_argument("--native-stored-root-bits", type=int, default=35)
    parser.add_argument("--slack", action="append", default=[])
    parser.add_argument("--coverage", action="append", default=[])
    args = parser.parse_args()

    print_table(args)
    print_coverage_table(args)
    print_theorem()


if __name__ == "__main__":
    main()
