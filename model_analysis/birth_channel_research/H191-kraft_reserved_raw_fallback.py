#!/usr/bin/env python3
"""H191 - Kraft-reserved raw fallback / implicit mode channel.

H190 charged a full one-bit raw-vs-witness mode.  This kernel tests the sharper
paid version: let witness codewords consume Kraft mass q, and encode raw fallback
inside the remaining prefix/arithmetic interval with length

    raw_L = N - log2(1 - q)

for an N-bit layer.  That is the optimal implicit mode channel for a uniform raw
fallback; it is strictly better than a one-bit mode when q is small.

Two variants are reported:

* all_syntax: every public witness codeword up to Wmax is syntactically valid and
  consumes Kraft mass, even if the encoder would never choose a non-shortest
  alias.
* canonical: a generous public-canonical fantasy keeps only the shortest witness
  per output and reclaims alias mass.  This needs a real syntax/canonicality
  story to be implementable, so it is a lower-bound stress test.

For uniform targets, both should stay non-positive.  If either crosses, the next
step is to inspect whether canonicality hid a target-derived selector, a
backtracking parser, or a source restriction.
"""

from __future__ import annotations

import argparse
import hashlib
import math
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model_analysis.proof_kernel import costs


INF = 10**9


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


def layer_from_witness(payload_width: int, rank: int, target_bits: int) -> int:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(b"H191-layer\0")
    digest.update(payload_width.to_bytes(2, "big"))
    digest.update(rank.to_bytes((rank.bit_length() + 7) // 8 or 1, "big"))
    digest.update(target_bits.to_bytes(2, "big"))
    return int.from_bytes(digest.digest(), "big") & ((1 << target_bits) - 1)


@dataclass(frozen=True)
class Row:
    target_bits: int
    max_payload_width: int
    strategy: str
    descriptions: int
    support: int
    kraft_mass: float
    raw_len_frac: float
    raw_len_ceil: int
    avg_frac: float
    avg_ceil: float
    gain_frac: float
    gain_ceil: float
    kl_gap: float
    verdict: str


def witness_inventory(target_bits: int, max_payload_width: int) -> tuple[list[int], int, float]:
    output_count = 1 << target_bits
    best = [INF] * output_count
    descriptions = 0
    all_mass = 0.0
    for payload_width in range(1, max_payload_width + 1):
        count = costs.payload_width_count_exact(payload_width)
        record_bits = costs.record_cost_for_payload_width(1, payload_width)
        descriptions += count
        all_mass += count * (2.0 ** (-record_bits))
        for rank in range(count):
            out = layer_from_witness(payload_width, rank, target_bits)
            if record_bits < best[out]:
                best[out] = record_bits
    return best, descriptions, all_mass


def raw_len_for_mass(target_bits: int, mass: float) -> float:
    if not 0.0 <= mass < 1.0:
        return float("inf")
    return target_bits - math.log2(1.0 - mass)


def row_all_syntax(target_bits: int, max_payload_width: int) -> Row:
    best, descriptions, all_mass = witness_inventory(target_bits, max_payload_width)
    raw_frac = raw_len_for_mass(target_bits, all_mass)
    raw_ceil = math.ceil(raw_frac)
    avg_frac = sum(min(length, raw_frac) for length in best) / len(best)
    avg_ceil = sum(min(length, raw_ceil) for length in best) / len(best)
    support = sum(1 for length in best if length < raw_frac)
    gain_frac = target_bits - avg_frac
    gain_ceil = target_bits - avg_ceil
    # Gibbs/source-coding gap for uniform data under the chosen effective lengths.
    kl_gap = avg_frac - target_bits
    verdict = (
        "BUG: implicit all-syntax mode crosses"
        if gain_frac > 1e-12
        else "paid implicit mode remains negative"
    )
    return Row(
        target_bits,
        max_payload_width,
        "all_syntax",
        descriptions,
        support,
        all_mass,
        raw_frac,
        raw_ceil,
        avg_frac,
        avg_ceil,
        gain_frac,
        gain_ceil,
        kl_gap,
        verdict,
    )


def canonical_fixed_point(target_bits: int, best: list[int]) -> tuple[float, float, int]:
    active = [length for length in best if length < INF]
    while True:
        mass = sum(2.0 ** (-length) for length in active)
        raw_frac = raw_len_for_mass(target_bits, mass)
        next_active = [length for length in active if length < raw_frac]
        if len(next_active) == len(active):
            return mass, raw_frac, len(active)
        active = next_active


def row_canonical(target_bits: int, max_payload_width: int) -> Row:
    best, descriptions, _all_mass = witness_inventory(target_bits, max_payload_width)
    mass, raw_frac, support = canonical_fixed_point(target_bits, best)
    raw_ceil = math.ceil(raw_frac)
    avg_frac = sum(min(length, raw_frac) for length in best) / len(best)
    avg_ceil = sum(min(length, raw_ceil) for length in best) / len(best)
    gain_frac = target_bits - avg_frac
    gain_ceil = target_bits - avg_ceil
    kl_gap = avg_frac - target_bits
    verdict = (
        "BUG: canonical implicit mode crosses"
        if gain_frac > 1e-12
        else "canonical lower bound remains negative"
    )
    return Row(
        target_bits,
        max_payload_width,
        "canonical",
        descriptions,
        support,
        mass,
        raw_frac,
        raw_ceil,
        avg_frac,
        avg_ceil,
        gain_frac,
        gain_ceil,
        kl_gap,
        verdict,
    )


def print_table(args: argparse.Namespace) -> None:
    target_bits_values = parse_int_list(args.target_bits, [8, 10, 12, 16])
    max_width_values = parse_int_list(args.max_payload_width, [4, 6, 8, 10, 12, 16])
    print("== H191 Kraft-reserved raw fallback / implicit mode channel ==")
    print(
        "rawFrac = N - log2(1-q), where q is witness Kraft mass. gainFrac > 0 would be a real crossing."
    )
    print(
        f"{'N':>4} {'Wmax':>5} {'strategy':<11} {'desc':>8} {'sup':>7} "
        f"{'q':>9} {'rawF':>9} {'rawI':>5} {'avgF':>9} {'gainF':>9} "
        f"{'gainI':>9} {'gap':>9} {'verdict'}"
    )
    worst_gain = -float("inf")
    worst_nontrivial_gain = -float("inf")
    worst_nontrivial_label = "none"
    for target_bits in target_bits_values:
        for max_width in max_width_values:
            if max_width > args.max_exact_width:
                continue
            for row in (
                row_all_syntax(target_bits, max_width),
                row_canonical(target_bits, max_width),
            ):
                worst_gain = max(worst_gain, row.gain_frac)
                if row.support > 0 and row.gain_frac > worst_nontrivial_gain:
                    worst_nontrivial_gain = row.gain_frac
                    worst_nontrivial_label = (
                        f"N={row.target_bits},Wmax={row.max_payload_width},"
                        f"{row.strategy}"
                    )
                if row.gain_frac > 1e-9:
                    raise AssertionError(f"{row.strategy} crossed on uniform data")
                print(
                    f"{row.target_bits:4d} {row.max_payload_width:5d} "
                    f"{row.strategy:<11} {row.descriptions:8d} {row.support:7d} "
                    f"{fmt(row.kraft_mass):>9} {fmt(row.raw_len_frac):>9} "
                    f"{row.raw_len_ceil:5d} {fmt(row.avg_frac):>9} "
                    f"{fmt(row.gain_frac):>9} {fmt(row.gain_ceil):>9} "
                    f"{fmt(row.kl_gap):>9} {row.verdict}"
                )
    print(f"\nnearest fractional gain: {fmt(worst_gain)} bits/layer")
    print(
        "nearest nontrivial fractional gain: "
        f"{fmt(worst_nontrivial_gain)} bits/layer at {worst_nontrivial_label}"
    )


def print_theorem() -> None:
    print()
    print("== theorem ==")
    print("Replacing a one-bit mode with leftover Kraft mass is the right paid")
    print("attack on H190. For uniform N-bit targets, the remaining raw interval")
    print("cost is N-log2(1-q). Any short witness mass q raises fallback length")
    print("for the rest of the alphabet. The expected length is H(U)+D(U||Q)")
    print("for the induced code distribution, so a negative uniform drift would")
    print("indicate hidden invalid-code reclamation, a non-UD parser, or a source")
    print("restriction. The canonical row is a generous lower bound, not a wire")
    print("format until canonicality is prefix-derivable without backtracking.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-bits", action="append", default=[])
    parser.add_argument("--max-payload-width", action="append", default=[])
    parser.add_argument("--max-exact-width", type=int, default=16)
    args = parser.parse_args()

    print_table(args)
    print_theorem()


if __name__ == "__main__":
    main()
