#!/usr/bin/env python3
"""Minimum non-uniform prior needed to escape the uniform counting wall.

H15 closes the uniform/content-blind recursive all-data branch. H16 quantifies
the price of the remaining escape hatch: a public non-uniform interpreter or
source-shaped seed universe.

If a code saves at least s bits on a set A of n-bit strings, Kraft/counting
allows |A| <= 2^(n-s). Under uniform data that set has mass <= 2^-s. Under a
non-uniform source Q, it can have larger mass only if Q concentrates probability
on A. That concentration is the source prior; it is not free all-data
compression.
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass


@dataclass(frozen=True)
class PriorRow:
    input_bits: int
    saving_bits: float
    coverage: float
    uniform_max_coverage: float
    concentration_factor: float
    min_entropy_deficit_bits: float
    max_entropy_bits: float
    lucky_set_log2_size: float
    avg_lucky_mass_bits: float


def h2(probability: float) -> float:
    if probability <= 0.0 or probability >= 1.0:
        return 0.0
    return -probability * math.log2(probability) - (1.0 - probability) * math.log2(1.0 - probability)


def binary_kl_to_uniform_short_set(coverage: float, saving_bits: float) -> float:
    """d2(coverage || 2^-saving_bits), computed stably in bits."""

    if coverage <= 0.0:
        return 0.0
    if coverage >= 1.0:
        return saving_bits
    base = coverage * saving_bits
    base += coverage * math.log2(coverage)
    base += (1.0 - coverage) * math.log2(1.0 - coverage)
    # Correction term: -(1-c) log2(1 - 2^-s). For large s this is negligible
    # and 2^-s may underflow, so skip it when it cannot affect the ledger.
    if saving_bits < 1023:
        alpha = 2.0 ** (-saving_bits)
        base -= (1.0 - coverage) * (math.log1p(-alpha) / math.log(2.0))
    return max(0.0, base)


def row(input_bits: int, saving_bits: float, coverage: float) -> PriorRow:
    uniform_max = 2.0 ** (-saving_bits) if saving_bits < 1024 else 0.0
    concentration = float("inf") if uniform_max == 0.0 else coverage / uniform_max
    lucky_log_size = max(0.0, input_bits - saving_bits)
    # If Q(A)=c and U(A)=alpha<=2^-s, the exact lower bound is
    # D(Q||U) >= d2(c||alpha). Using alpha=2^-s is conservative.
    deficit = binary_kl_to_uniform_short_set(coverage, saving_bits)
    max_entropy = input_bits - deficit
    # Average mass per lucky string is at least c / |A|. Report as
    # -log2 average mass, i.e. the implied ideal code length inside A.
    avg_mass_bits = lucky_log_size - math.log2(coverage) if coverage > 0.0 else float("inf")
    return PriorRow(
        input_bits=input_bits,
        saving_bits=saving_bits,
        coverage=coverage,
        uniform_max_coverage=uniform_max,
        concentration_factor=concentration,
        min_entropy_deficit_bits=deficit,
        max_entropy_bits=max_entropy,
        lucky_set_log2_size=lucky_log_size,
        avg_lucky_mass_bits=avg_mass_bits,
    )


def render(rows: list[PriorRow]) -> str:
    lines = [
        "# Prior Escape Ledger",
        "",
        "Rows quantify what a public non-uniform interpreter/source prior must",
        "buy to make `s`-bit savings cover source mass `c`.",
        "",
        "| n | saving s | source coverage c | uniform max c | avg likelihood-ratio lift | min entropy deficit | max source entropy | log2 lucky set size | avg lucky code bits |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in rows:
        concentration = "inf" if not math.isfinite(item.concentration_factor) else f"{item.concentration_factor:.6g}"
        lines.append(
            f"| {item.input_bits} | {item.saving_bits:.3f} | {item.coverage:.6g} | "
            f"{item.uniform_max_coverage:.6g} | {concentration} | "
            f"{item.min_entropy_deficit_bits:.3f} | {item.max_entropy_bits:.3f} | "
            f"{item.lucky_set_log2_size:.3f} | {item.avg_lucky_mass_bits:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Reading",
            "",
            "A public interpreter can beat the uniform wall only by making the",
            "source non-uniform: it assigns much more probability mass to a small",
            "set of strings than uniform does. That can be legitimate if the",
            "source really follows that prior, but it is a different claim from",
            "content-blind compression on roughly all arbitrary data.",
            "",
            "The entropy-deficit column is the exact binary-KL lower bound",
            "`d2(c || 2^-s)`. It is at least the looser approximation",
            "`max(0, c*s - h2(c))`.",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-bits", type=int, default=1024)
    parser.add_argument("--savings", type=float, nargs="+", default=[1.0, 8.0, 32.0, 128.0])
    parser.add_argument("--coverages", type=float, nargs="+", default=[0.5, 0.9, 0.99])
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = [
        row(args.input_bits, saving, coverage)
        for saving in args.savings
        for coverage in args.coverages
    ]
    print(render(rows))


if __name__ == "__main__":
    main()
