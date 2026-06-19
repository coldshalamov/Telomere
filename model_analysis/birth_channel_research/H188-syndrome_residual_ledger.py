#!/usr/bin/env python3
"""H188 - algebraic/syndrome residual ledger.

This kernel tests parity, syndrome, linear residual, and ECC-style proposals.

Given a seed expansion y and target x, the residual e = x xor y is uniform for
arbitrary content under the uniform hash law.  A c-bit syndrome partitions the
2^n possible residuals into 2^c bins; without a source restriction, each bin
has 2^(n-c) candidates.  Stateless unique decode therefore needs either the
full residual, a residual index/list, or a source-shaped low-volume residual
class whose membership tax is charged.
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


def parse_int_list(values: list[str], default: list[int]) -> list[int]:
    if not values:
        return default
    out: list[int] = []
    for value in values:
        out.extend(int(part) for part in value.split(",") if part)
    return out


def log2_binomial(n: int, k: int) -> float:
    if k < 0 or k > n:
        return float("-inf")
    return (
        math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)
    ) / math.log(2.0)


def log2_hamming_ball(n: int, radius: int) -> float:
    terms = [log2_binomial(n, k) for k in range(radius + 1)]
    largest = max(terms)
    return largest + math.log2(sum(2.0 ** (term - largest) for term in terms))


@dataclass(frozen=True)
class SyndromeRow:
    target_bits: int
    seed_bits: int
    syndrome_bits: int
    stored_bits: int
    ambiguity_bits: int
    paid_unique_bits: int
    direct_seed_bits: int
    net_vs_raw: int
    verdict: str


@dataclass(frozen=True)
class LowWeightRow:
    target_bits: int
    seed_bits: int
    radius: int
    log2_volume: float
    class_tax: float
    residual_index_bits: int
    inside_bits: int
    inside_gain: int
    uniform_net: float
    verdict: str


def syndrome_row(target_bits: int, seed_bits: int, syndrome_bits: int) -> SyndromeRow:
    stored = seed_bits + syndrome_bits
    ambiguity = max(0, target_bits - syndrome_bits)
    paid_unique = stored + ambiguity
    direct_seed = seed_bits + target_bits
    net_vs_raw = target_bits - paid_unique
    if ambiguity > 0:
        verdict = "ambiguous unless residual branch paid"
    elif net_vs_raw > 0:
        verdict = "BUG: unique syndrome beats raw residual"
    else:
        verdict = "full residual, no compression"
    return SyndromeRow(
        target_bits=target_bits,
        seed_bits=seed_bits,
        syndrome_bits=syndrome_bits,
        stored_bits=stored,
        ambiguity_bits=ambiguity,
        paid_unique_bits=paid_unique,
        direct_seed_bits=direct_seed,
        net_vs_raw=net_vs_raw,
        verdict=verdict,
    )


def low_weight_row(target_bits: int, seed_bits: int, radius: int) -> LowWeightRow:
    log_vol = log2_hamming_ball(target_bits, radius)
    class_tax = target_bits - log_vol
    residual_index_bits = math.ceil(log_vol)
    inside_bits = seed_bits + residual_index_bits
    inside_gain = target_bits - inside_bits
    uniform_net = inside_gain - class_tax
    if uniform_net > 1e-12:
        verdict = "BUG: low-weight class positive after tax"
    elif inside_gain > 0:
        verdict = "positive only inside residual class"
    else:
        verdict = "no inside compression"
    return LowWeightRow(
        target_bits=target_bits,
        seed_bits=seed_bits,
        radius=radius,
        log2_volume=log_vol,
        class_tax=class_tax,
        residual_index_bits=residual_index_bits,
        inside_bits=inside_bits,
        inside_gain=inside_gain,
        uniform_net=uniform_net,
        verdict=verdict,
    )


def print_syndrome_table(args: argparse.Namespace) -> None:
    n_values = parse_int_list(args.target_bits, [64, 256, 1024])
    seed_values = parse_int_list(args.seed_bits, [0, 8, 32])
    syndrome_values = parse_int_list(args.syndrome_bits, [8, 16, 32, 64, 128, 256])

    print("== H188 syndrome/residual ledger ==")
    print(
        "A c-bit syndrome leaves n-c residual bits ambiguous for arbitrary uniform residuals."
    )
    print(
        f"{'n':>6} {'seed':>5} {'c':>5} {'stored':>7} {'ambig':>7} "
        f"{'paidUniq':>9} {'rawSeed':>8} {'netRaw':>7} {'verdict':<40}"
    )
    for n in n_values:
        for seed_bits in seed_values:
            for c in syndrome_values:
                if c > n:
                    continue
                row = syndrome_row(n, seed_bits, c)
                print(
                    f"{row.target_bits:6d} {row.seed_bits:5d} {row.syndrome_bits:5d} "
                    f"{row.stored_bits:7d} {row.ambiguity_bits:7d} "
                    f"{row.paid_unique_bits:9d} {row.direct_seed_bits:8d} "
                    f"{row.net_vs_raw:7d} {row.verdict:<40}"
                )


def print_low_weight_table(args: argparse.Namespace) -> None:
    n_values = parse_int_list(args.target_bits, [64, 256, 1024])
    seed_values = parse_int_list(args.seed_bits, [0, 8, 32])
    radius_values = parse_int_list(args.radius, [0, 1, 2, 4, 8, 16])

    print()
    print("== low-volume residual class ledger ==")
    print(
        "Low-weight residuals can compress inside the class; arbitrary data pays the class tax."
    )
    print(
        f"{'n':>6} {'seed':>5} {'t':>4} {'logVol':>10} {'tax':>10} "
        f"{'idx':>7} {'inside':>8} {'gainIn':>7} {'uNet':>9} {'verdict':<38}"
    )
    for n in n_values:
        for seed_bits in seed_values:
            for radius in radius_values:
                if radius > n:
                    continue
                row = low_weight_row(n, seed_bits, radius)
                print(
                    f"{row.target_bits:6d} {row.seed_bits:5d} {row.radius:4d} "
                    f"{fmt(row.log2_volume):>10} {fmt(row.class_tax):>10} "
                    f"{row.residual_index_bits:7d} {row.inside_bits:8d} "
                    f"{row.inside_gain:7d} {fmt(row.uniform_net):>9} "
                    f"{row.verdict:<38}"
                )


def print_theorem() -> None:
    print()
    print("== theorem ==")
    print("For arbitrary content, x xor expand(seed) is uniform.")
    print("A syndrome with c bits leaves n-c residual bits; paying them")
    print("returns to the full residual. Low-volume residual classes are")
    print("source-shaped positives only after their membership tax is external.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-bits", action="append", default=[])
    parser.add_argument("--seed-bits", action="append", default=[])
    parser.add_argument("--syndrome-bits", action="append", default=[])
    parser.add_argument("--radius", action="append", default=[])
    args = parser.parse_args()

    print_syndrome_table(args)
    print_low_weight_table(args)
    print_theorem()


if __name__ == "__main__":
    main()
