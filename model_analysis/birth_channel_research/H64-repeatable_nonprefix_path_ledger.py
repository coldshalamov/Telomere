#!/usr/bin/env python3
"""H64 - repeatable non-prefix shrink and the hidden length-path ledger.

EOF/non-prefix coding creates a tempting one-shot fact: for a known n-bit input
length, there are 2^n-1 shorter binary strings. So almost every n-bit string
can be assigned a shorter output if the decoder already knows that the previous
layer length was n.

This kernel separates three repeatable variants:

1. fixed exact shrink: every pass saves exactly s bits, so previous lengths are
   public; coverage is only 2^(-P*s) or 2^(1-P*s) depending on exact/EOF final
   output accounting;
2. variable shrink with a free length path: almost all strings can shrink for P
   passes, but the path of per-pass savings is a selector;
3. variable shrink with stateless global inverse: final output alone identifies
   the inverse chain, so the total winning set is bounded by the number of
   possible final strings of length <= n-P*s.

This is not a compressor. It is a counting ledger for the exact hidden channel
that makes non-prefix recursion look magical.
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass


def log2_comb(n: int, k: int) -> float:
    if k < 0 or k > n:
        return float("-inf")
    return (
        math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)
    ) / math.log(2.0)


def comb(n: int, k: int) -> int:
    if k < 0 or k > n:
        return 0
    return math.comb(n, k)


def path_count(total_saving: int, passes: int, min_step: int) -> int:
    """Number of positive saving paths with each pass saving at least min_step."""

    residual = total_saving - passes * min_step
    if residual < 0:
        return 0
    return comb(residual + passes - 1, passes - 1)


def path_available_fraction(n_bits: int, passes: int, min_step: int) -> float:
    """Fraction coverable if the per-pass length path is available for free."""

    minimum_total = passes * min_step
    if minimum_total > n_bits:
        return 0.0
    total = 0.0
    for saving in range(minimum_total, n_bits + 1):
        total += path_count(saving, passes, min_step) * (2.0 ** (-saving))
    return min(1.0, total)


def stateless_variable_fraction(n_bits: int, passes: int, min_step: int) -> float:
    """Upper bound when final output alone must identify the inverse chain."""

    minimum_total = passes * min_step
    if minimum_total > n_bits:
        return 0.0
    # All P-pass winners must end at length <= n-minimum_total.
    return min(1.0, (2.0 ** (1 - minimum_total)) - (2.0 ** (-n_bits)))


def fixed_exact_fraction(passes: int, min_step: int) -> float:
    return 2.0 ** (-(passes * min_step))


def path_entropy_stats(n_bits: int, passes: int, min_step: int) -> tuple[float, float, float]:
    """Return weighted average, max, and mass-weighted entropy of path choices."""

    minimum_total = passes * min_step
    if minimum_total > n_bits:
        return (0.0, 0.0, 0.0)

    weights: list[tuple[float, int]] = []
    for saving in range(minimum_total, n_bits + 1):
        count = path_count(saving, passes, min_step)
        if count <= 0:
            continue
        weights.append((count * (2.0 ** (-saving)), count))

    mass = sum(weight for weight, _ in weights)
    if mass <= 0.0:
        return (0.0, 0.0, 0.0)

    avg_log = sum(weight * math.log2(count) for weight, count in weights) / mass
    max_log = max(math.log2(count) for _, count in weights)
    # Entropy of the saving-total bucket; within each bucket log2(count) path
    # bits remain unless a canonical path is externally derived.
    bucket_entropy = 0.0
    for weight, _ in weights:
        p = weight / mass
        bucket_entropy -= p * math.log2(p)
    return (avg_log, max_log, bucket_entropy + avg_log)


@dataclass(frozen=True)
class Row:
    n_bits: int
    passes: int
    min_step: int
    fixed_exact: float
    stateless_variable: float
    path_available: float
    avg_path_bits: float
    max_path_bits: float
    path_entropy_bits: float

    @property
    def minimum_total_saving(self) -> int:
        return self.passes * self.min_step


def rows(n_values: list[int], pass_values: list[int], min_steps: list[int]) -> list[Row]:
    out: list[Row] = []
    for n_bits in n_values:
        for passes in pass_values:
            for min_step in min_steps:
                avg_path, max_path, entropy = path_entropy_stats(n_bits, passes, min_step)
                out.append(
                    Row(
                        n_bits=n_bits,
                        passes=passes,
                        min_step=min_step,
                        fixed_exact=fixed_exact_fraction(passes, min_step),
                        stateless_variable=stateless_variable_fraction(n_bits, passes, min_step),
                        path_available=path_available_fraction(n_bits, passes, min_step),
                        avg_path_bits=avg_path,
                        max_path_bits=max_path,
                        path_entropy_bits=entropy,
                    )
                )
    return out


def fmt_prob(value: float) -> str:
    if value == 0.0:
        return "0"
    if value >= 0.001:
        return f"{value:.6f}"
    return f"{value:.3e}"


def render(rows_: list[Row]) -> str:
    lines = [
        "# H64 - Repeatable Non-Prefix Path Ledger",
        "",
        "| n | P | min save/pass | min total S | exact fixed fraction | stateless variable fraction | path-free apparent fraction | avg path bits | max path bits | bucket+path entropy bits |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows_:
        lines.append(
            f"| {row.n_bits} | {row.passes} | {row.min_step} | {row.minimum_total_saving} | "
            f"{fmt_prob(row.fixed_exact)} | {fmt_prob(row.stateless_variable)} | "
            f"{fmt_prob(row.path_available)} | {row.avg_path_bits:.6f} | "
            f"{row.max_path_bits:.6f} | {row.path_entropy_bits:.6f} |"
        )

    lines.extend(
        [
            "",
            "## Reading",
            "",
            "`path-free apparent fraction` is the attractive but invalid row for",
            "stateless recursion: it assumes the decoder knows the per-pass length",
            "path. For `min save/pass = 1`, the infinite-n limit is 1 for every",
            "fixed `P`, which explains why EOF/final-length ideas feel powerful.",
            "",
            "`stateless variable fraction` is the honest row when the final bytes",
            "alone must identify the inverse chain. It is bounded by",
            "`2^(1-P*s)`, so it decays exponentially with pass count.",
            "",
            "A public invariant can choose one path and avoid path bits, but then",
            "coverage collapses to the fixed/exact or fixed-total final-slot row.",
            "Allowing many paths restores coverage only by restoring the hidden",
            "path selector.",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-bits", type=int, nargs="+", default=[16, 64, 128])
    parser.add_argument("--passes", type=int, nargs="+", default=[1, 2, 4, 8, 16, 64])
    parser.add_argument("--min-step", type=int, nargs="+", default=[1, 2])
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(render(rows(args.n_bits, args.passes, args.min_step)))


if __name__ == "__main__":
    main()
