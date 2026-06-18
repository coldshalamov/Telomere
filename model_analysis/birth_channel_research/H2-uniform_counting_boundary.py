#!/usr/bin/env python3
"""Uniform-source counting and finite birth-channel ledgers.

This is a math/checking kernel, not a compression experiment. It summarizes the
two conservation facts that bound the current search:

1. A fixed public lossless decoder can make at most a 2^-s fraction of n-bit
   uniform inputs save s bits.
2. A salted birth-pass channel with E free structural bits per record has an
   unpaid birth bill log2(1+(P-1)2^-E) bits/record after P candidate passes
   when wrong-pass survivors are independent with probability 2^-E.
"""

from __future__ import annotations

import argparse
import math


def max_fraction_saving(saving_bits: float) -> float:
    return 2.0 ** (-saving_bits)


def residual_birth_bits(passes: int, free_bits: float) -> float:
    if passes < 1:
        raise ValueError("passes must be >= 1")
    return math.log2(1.0 + (passes - 1) * (2.0 ** (-free_bits)))


def max_passes_for_residual(free_bits: float, residual_budget: float) -> int:
    return max(1, int(math.floor(1.0 + (2.0 ** residual_budget - 1.0) * (2.0 ** free_bits))))


def render(args: argparse.Namespace) -> str:
    lines: list[str] = [
        "# Uniform Counting Boundary",
        "",
        "For any fixed public uniquely-decodable lossless code on n-bit inputs,",
        "the number of strings with code length <= n-s is at most 2^(n-s).",
        "Therefore a uniformly random n-bit input saves s bits with probability",
        "at most 2^-s, before any Telomere-specific mechanism is considered.",
        "",
        "| requested saving s | max fraction of n-bit inputs | one-in |",
        "| ---: | ---: | ---: |",
    ]
    for saving in args.savings:
        frac = max_fraction_saving(saving)
        lines.append(f"| {saving:.3f} | {frac:.6g} | {1.0 / frac:.3g} |")

    lines.extend(
        [
            "",
            "# Birth-Pass Residual Ledger",
            "",
            "For a record with P live candidate birth passes and E free structural",
            "bits, the exact independent-survivor bill is",
            "log2(1+(P-1)2^-E) bits/record. If a match has only G gross bits",
            "of savings available, positive net requires that bill < G.",
            "",
            f"Gross match savings budget G = {args.gross_savings:.3f} bits/record.",
            "",
            "| channel | E free bits/record | knee P~=2^E | P with residual < G | residual at P=64 | residual at P=1024 | residual at P=1e6 |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    channels = [
        ("singles/no structural pruning", 0.0),
        ("old explosion-check folklore", 2.5),
        ("arity-2 bundle q=100/65536", 9.36),
        ("arity-3 bundle", 12.59),
        ("arity-4 bundle", 14.97),
        ("arity-5 bundle", 18.20),
    ]
    for name, free_bits in channels:
        knee = max(1, int(round(2.0 ** free_bits)))
        positive = max_passes_for_residual(free_bits, args.gross_savings)
        r64 = residual_birth_bits(64, free_bits)
        r1024 = residual_birth_bits(1024, free_bits)
        r1m = residual_birth_bits(1_000_000, free_bits)
        lines.append(
            f"| {name} | {free_bits:.3f} | {knee} | {positive} | {r64:.3f} | {r1024:.3f} | {r1m:.3f} |"
        )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--savings", type=float, nargs="+", default=[1, 8, 16, 32, 64, 128])
    parser.add_argument("--gross-savings", type=float, default=2.0)
    return parser.parse_args()


def main() -> None:
    print(render(parse_args()))


if __name__ == "__main__":
    main()
