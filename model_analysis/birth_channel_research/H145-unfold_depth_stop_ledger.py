#!/usr/bin/env python3
"""H145 - unfold-depth / stop-time ledger.

The user raised the "upward" version of Telomere search:

    a short seed may unfold through larger intermediate states and only later
    shrink to the target; maybe any seed can eventually create any file.

H145 prices that as a time/stop channel. A deterministic seed run for a fixed
public depth gives one output per seed, so extra time alone does not increase
coverage. If the decoder may stop at any of T intermediate states, the pair
(seed, stop_time) has T times as many descriptions. That can buy coverage, but
the stop time or an equivalent referee/checksum is an information channel.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class CoverageRow:
    target_bits: int
    seed_saving_bits: int
    stop_steps: float
    fixed_depth_coverage: float
    stop_time_coverage: float
    stop_bits: float
    net_saving_if_stop_stored: float


@dataclass(frozen=True)
class RequiredRow:
    seed_saving_bits: int
    target_coverage: float
    required_steps: float
    stop_bits: float
    net_saving_if_stop_stored: float


@dataclass(frozen=True)
class RefereeRow:
    checksum_bits: int
    safety_bits: int
    usable_stop_steps: float
    max_free_gain_bits: float


def coverage_with_stop(seed_saving_bits: int, stop_steps: float) -> float:
    load = stop_steps * (2.0 ** (-seed_saving_bits))
    if load > 40.0:
        return 1.0
    return 1.0 - math.exp(-load)


def required_steps(seed_saving_bits: int, coverage: float) -> float:
    if coverage <= 0.0:
        return 0.0
    if coverage >= 1.0:
        return float("inf")
    return -math.log(1.0 - coverage) * (2.0**seed_saving_bits)


def fmt(value: float) -> str:
    if value == float("inf"):
        return "inf"
    if value >= 1_000_000 or (0.0 < value < 0.0001):
        return f"{value:.3e}"
    return f"{value:.6f}"


def coverage_rows() -> list[CoverageRow]:
    rows: list[CoverageRow] = []
    target_bits = 1024
    for saving in (1, 2, 4, 8, 16, 32):
        for log_steps in (0, 1, 2, 4, 8, 16, 32):
            steps = 2.0**log_steps
            stop_bits = math.log2(steps)
            rows.append(
                CoverageRow(
                    target_bits=target_bits,
                    seed_saving_bits=saving,
                    stop_steps=steps,
                    fixed_depth_coverage=2.0 ** (-saving),
                    stop_time_coverage=coverage_with_stop(saving, steps),
                    stop_bits=stop_bits,
                    net_saving_if_stop_stored=saving - stop_bits,
                )
            )
    return rows


def required_rows() -> list[RequiredRow]:
    rows: list[RequiredRow] = []
    for saving in (1, 2, 4, 8, 16, 32):
        for coverage in (0.50, 0.90, 0.99, 0.999):
            steps = required_steps(saving, coverage)
            stop_bits = math.log2(steps) if steps > 0.0 else 0.0
            rows.append(
                RequiredRow(
                    seed_saving_bits=saving,
                    target_coverage=coverage,
                    required_steps=steps,
                    stop_bits=stop_bits,
                    net_saving_if_stop_stored=saving - stop_bits,
                )
            )
    return rows


def referee_rows() -> list[RefereeRow]:
    rows: list[RefereeRow] = []
    for checksum_bits in (16, 32, 64, 128):
        for safety_bits in (0, 16, 32):
            usable = 2.0 ** max(0, checksum_bits - safety_bits)
            rows.append(
                RefereeRow(
                    checksum_bits=checksum_bits,
                    safety_bits=safety_bits,
                    usable_stop_steps=usable,
                    max_free_gain_bits=max(0, math.log2(usable)),
                )
            )
    return rows


def print_required(rows: list[RequiredRow]) -> None:
    print("== stop-time required for coverage ==")
    print("If stop_time is stored, net saving is seed_saving - log2(steps).")
    print(f"{'G seed':>7} {'coverage':>9} {'steps':>12} {'stop bits':>10} {'net if stored':>13}")
    for row in rows:
        if row.target_coverage not in (0.90, 0.999):
            continue
        print(
            f"{row.seed_saving_bits:7d} {row.target_coverage:9.3f} "
            f"{fmt(row.required_steps):>12} {fmt(row.stop_bits):>10} "
            f"{fmt(row.net_saving_if_stop_stored):>13}"
        )
    print()


def print_coverage(rows: list[CoverageRow]) -> None:
    print("== fixed depth versus stop-time coverage ==")
    print(f"{'G seed':>7} {'log2 T':>7} {'fixed q':>10} {'stop q':>10} {'net if stored':>13}")
    for row in rows:
        if row.seed_saving_bits in (4, 8, 16, 32) and row.stop_bits in (0, 4, 8, 16, 32):
            print(
                f"{row.seed_saving_bits:7d} {row.stop_bits:7.0f} "
                f"{fmt(row.fixed_depth_coverage):>10} "
                f"{fmt(row.stop_time_coverage):>10} "
                f"{fmt(row.net_saving_if_stop_stored):>13}"
            )
    print()


def print_referee(rows: list[RefereeRow]) -> None:
    print("== checksum/referee stop budget ==")
    print(f"{'checksum':>8} {'safety':>7} {'usable steps':>14} {'max gain before stop bits':>26}")
    for row in rows:
        if row.safety_bits in (0, 32):
            print(
                f"{row.checksum_bits:8d} {row.safety_bits:7d} "
                f"{fmt(row.usable_stop_steps):>14} "
                f"{fmt(row.max_free_gain_bits):>26}"
            )
    print()


def print_reading() -> None:
    print("== reading ==")
    print(
        "Longer unfolding can trade decoder/search time for coverage only if "
        "the decoder is allowed to stop at one of many intermediate states. "
        "That stop choice is log2(T) bits unless a public invariant derives it."
    )
    print(
        "A fixed public depth has no stop-choice multiplier: one seed still "
        "names one output. A checksum/referee can hide a finite stop search, "
        "but the checksum bits are the same information budget and only cover "
        "a bounded T before ambiguity returns."
    )
    print(
        "So upward non-greedy unfolding is a valid compute-for-compression "
        "target, but roughly-all G-bit savings needs about 2^G stop candidates; "
        "storing or refereeing that stop time gives the bits back."
    )


def main() -> None:
    print_required(required_rows())
    print_coverage(coverage_rows())
    print_referee(referee_rows())
    print_reading()


if __name__ == "__main__":
    main()
