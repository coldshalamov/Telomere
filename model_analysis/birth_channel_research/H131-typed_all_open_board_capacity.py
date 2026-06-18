#!/usr/bin/env python3
"""H131 - typed all-open public board capacity.

Plato's strongest remaining geometry is a public typed all-open board:

    every slot opens
    arity/child count is public
    width/target class is public
    seed class and salt are public
    placement coordinates are public

Then decode is stateless and order-safe. The only stream left is the witness
payload. This kernel prices the finite capacity of such a board under the
uniform hash law.

If the previous layer has N bits and the public board carries W witness bits,
then at most 2^W distinct previous layers are reachable. With a random public
expander, the expected covered fraction is:

    p = 1 - exp(-2^(W - N)) = 1 - exp(-2^-G)

where G = N - W is the positive compression gain in bits. A positive-gain
all-open typed board therefore covers only a fraction of arbitrary layers. For
roughly-all data over many passes, p must be close to 1, which forces G <= 0.
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass


@dataclass(frozen=True)
class GainRow:
    gain_bits: float
    witness_bits_delta: float
    coverage_per_pass: float
    survive_2: float
    survive_64: float
    survive_4096: float


@dataclass(frozen=True)
class CoverageRow:
    target_coverage: float
    max_gain_bits: float
    required_bloat_bits: float
    witness_load: float


@dataclass(frozen=True)
class MultiPassRow:
    final_coverage: float
    passes: int
    per_pass_coverage: float
    max_gain_bits: float
    required_bloat_bits: float


def coverage_from_gain(gain_bits: float) -> float:
    load = 2.0 ** (-gain_bits)
    if load > 40.0:
        return 1.0
    if load < 1e-12:
        return load
    return 1.0 - math.exp(-load)


def max_gain_for_coverage(coverage: float) -> float:
    if coverage <= 0.0:
        return float("inf")
    if coverage >= 1.0:
        return float("-inf")
    return -math.log2(-math.log(1.0 - coverage))


def fmt(value: float) -> str:
    if math.isinf(value):
        return "inf" if value > 0 else "-inf"
    return f"{value:.9f}"


def gain_rows(gains: list[float]) -> list[GainRow]:
    rows: list[GainRow] = []
    for gain in gains:
        p = coverage_from_gain(gain)
        rows.append(
            GainRow(
                gain_bits=gain,
                witness_bits_delta=-gain,
                coverage_per_pass=p,
                survive_2=p**2,
                survive_64=p**64,
                survive_4096=p**4096,
            )
        )
    return rows


def coverage_rows(targets: list[float]) -> list[CoverageRow]:
    rows: list[CoverageRow] = []
    for target in targets:
        gain = max_gain_for_coverage(target)
        rows.append(
            CoverageRow(
                target_coverage=target,
                max_gain_bits=gain,
                required_bloat_bits=max(0.0, -gain),
                witness_load=-math.log(1.0 - target) if target < 1.0 else float("inf"),
            )
        )
    return rows


def multipass_rows(final_coverages: list[float], passes_values: list[int]) -> list[MultiPassRow]:
    rows: list[MultiPassRow] = []
    for final in final_coverages:
        for passes in passes_values:
            per_pass = final ** (1.0 / passes)
            gain = max_gain_for_coverage(per_pass)
            rows.append(
                MultiPassRow(
                    final_coverage=final,
                    passes=passes,
                    per_pass_coverage=per_pass,
                    max_gain_bits=gain,
                    required_bloat_bits=max(0.0, -gain),
                )
            )
    return rows


def print_gain_rows(rows: list[GainRow]) -> None:
    print("== positive gain coverage ==")
    print("gain_bits,witness_delta,coverage/pass,survive_2,survive_64,survive_4096")
    for row in rows:
        print(
            f"{fmt(row.gain_bits)},{fmt(row.witness_bits_delta)},"
            f"{fmt(row.coverage_per_pass)},{fmt(row.survive_2)},"
            f"{fmt(row.survive_64)},{fmt(row.survive_4096)}"
        )
    print()


def print_coverage_rows(rows: list[CoverageRow]) -> None:
    print("== max gain for per-pass coverage ==")
    print("target_coverage,max_gain_bits,required_bloat_bits,witness_load")
    for row in rows:
        print(
            f"{fmt(row.target_coverage)},{fmt(row.max_gain_bits)},"
            f"{fmt(row.required_bloat_bits)},{fmt(row.witness_load)}"
        )
    print()


def print_multipass_rows(rows: list[MultiPassRow]) -> None:
    print("== max gain for final survival over many passes ==")
    print("final_coverage,passes,per_pass_coverage,max_gain_bits,required_bloat_bits")
    for row in rows:
        print(
            f"{fmt(row.final_coverage)},{row.passes},"
            f"{fmt(row.per_pass_coverage)},{fmt(row.max_gain_bits)},"
            f"{fmt(row.required_bloat_bits)}"
        )
    print()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gain", type=float, action="append", default=[])
    parser.add_argument("--coverage", type=float, action="append", default=[])
    parser.add_argument("--final-coverage", type=float, action="append", default=[])
    parser.add_argument("--passes", type=int, action="append", default=[])
    args = parser.parse_args()

    gains = args.gain or [-8, -4, -2, -1, 0, 0.5, 1, 2, 4, 8]
    coverages = args.coverage or [0.50, 0.90, 0.99, 0.999, 0.9999, 0.999999]
    final_coverages = args.final_coverage or [0.50, 0.90, 0.99]
    passes = args.passes or [2, 64, 4096]
    print_gain_rows(gain_rows(gains))
    print_coverage_rows(coverage_rows(coverages))
    print_multipass_rows(multipass_rows(final_coverages, passes))


if __name__ == "__main__":
    main()
