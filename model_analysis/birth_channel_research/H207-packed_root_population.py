#!/usr/bin/env python3
"""H207 - packed root population / root-record language attack.

H206 showed that current V1/J3D1 root records miss arbitrary-uniform by the
root-record overhead.  The next attack removes that overhead: a public
visible-population mode packs the M root seeds as exactly M*G raw rank bits.

This kernel separates three ledgers:

1. generated-only packed mode: no raw fallback, supports only 2^(M*G) outputs;
2. packed mode with a mode/preset bill: arbitrary-uniform net is -mode_bits;
3. lossless all-data codec with raw fallback: leftover Kraft fallback expands
   the uniform source unless the generated mode consumes zero Kraft, i.e. does
   nothing.
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


@dataclass(frozen=True)
class Row:
    population_size: int
    root_bits: int
    atom_bits: int
    arity: int
    passes: int
    mode_bits: int
    out_bits: int
    support_bits: int
    packed_paid_bits: int
    generated_inside_gain: int
    membership_tax: int
    uniform_net_generated_only: int
    support_fraction_log2: int
    kraft_q: float
    fallback_len: float
    uniform_mean_delta_with_fallback: float


def row(
    *,
    population_size: int,
    root_bits: int,
    atom_bits: int,
    arity: int,
    passes: int,
    mode_bits: int,
) -> Row:
    out_bits = population_size * (arity**passes) * atom_bits
    support_bits = population_size * root_bits
    packed_paid_bits = support_bits + mode_bits
    generated_inside_gain = out_bits - packed_paid_bits
    membership_tax = out_bits - support_bits
    uniform_net_generated_only = generated_inside_gain - membership_tax
    support_fraction_log2 = support_bits - out_bits
    kraft_q = 2.0 ** (-mode_bits) if mode_bits >= 0 else math.inf
    if mode_bits <= 0:
        fallback_len = math.inf
        uniform_mean_delta = math.inf
    else:
        fallback_len = out_bits - math.log2(1.0 - kraft_q)
        f = 2.0 ** support_fraction_log2 if support_fraction_log2 > -1074 else 0.0
        uniform_mean = f * packed_paid_bits + (1.0 - f) * fallback_len
        uniform_mean_delta = uniform_mean - out_bits
    return Row(
        population_size=population_size,
        root_bits=root_bits,
        atom_bits=atom_bits,
        arity=arity,
        passes=passes,
        mode_bits=mode_bits,
        out_bits=out_bits,
        support_bits=support_bits,
        packed_paid_bits=packed_paid_bits,
        generated_inside_gain=generated_inside_gain,
        membership_tax=membership_tax,
        uniform_net_generated_only=uniform_net_generated_only,
        support_fraction_log2=support_fraction_log2,
        kraft_q=kraft_q,
        fallback_len=fallback_len,
        uniform_mean_delta_with_fallback=uniform_mean_delta,
    )


def print_rows(args: argparse.Namespace) -> None:
    populations = parse_int_list(args.population_size, [1, 2, 8, 32])
    roots = parse_int_list(args.root_bits, [1, 8, 16])
    modes = parse_int_list(args.mode_bits, [0, 1, 2, 4, 8])
    rows = [
        row(
            population_size=m,
            root_bits=g,
            atom_bits=args.atom_bits,
            arity=args.arity,
            passes=args.passes,
            mode_bits=mode,
        )
        for m in populations
        for g in roots
        for mode in modes
    ]
    rows.sort(key=lambda r: (r.uniform_net_generated_only, -r.mode_bits, -r.generated_inside_gain), reverse=True)
    print("== H207 packed root population / root language attack ==")
    print("Generated-only net subtracts reachable-set membership tax. Fallback rows use leftover Kraft.")
    print(
        f"{'M':>3} {'G':>3} {'A':>2} {'P':>2} {'mode':>4} {'out':>9} "
        f"{'support':>7} {'paid':>7} {'gainIn':>10} {'tax':>9} "
        f"{'uNetGen':>8} {'logFrac':>9} {'q':>8} {'fbDelta':>9}"
    )
    for item in rows[: args.limit]:
        print(
            f"{item.population_size:3d} {item.root_bits:3d} {item.arity:2d} "
            f"{item.passes:2d} {item.mode_bits:4d} {item.out_bits:9d} "
            f"{item.support_bits:7d} {item.packed_paid_bits:7d} "
            f"{item.generated_inside_gain:10d} {item.membership_tax:9d} "
            f"{item.uniform_net_generated_only:8d} {item.support_fraction_log2:9d} "
            f"{fmt(item.kraft_q):>8} {fmt(item.uniform_mean_delta_with_fallback):>9}"
        )


def print_theorem() -> None:
    print()
    print("== theorem ==")
    print("Packing root bits exactly removes V1 root-record overhead.  In a")
    print("generated-only preset with no mode/fallback, arbitrary-uniform net")
    print("ties at 0 after membership tax but covers only 2^(S-N) of inputs.")
    print("Any positive mode cost makes generated-only uniform net -mode_bits.")
    print("Adding raw fallback makes a full lossless codec, but leftover Kraft")
    print("lengthens the raw alphabet by -log2(1-2^-mode_bits), so the uniform")
    print("mean length is >= raw.  The witness effect vanishes only as q -> 0.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--population-size", action="append", default=[])
    parser.add_argument("--root-bits", action="append", default=[])
    parser.add_argument("--mode-bits", action="append", default=[])
    parser.add_argument("--atom-bits", type=int, default=32)
    parser.add_argument("--arity", type=int, default=5)
    parser.add_argument("--passes", type=int, default=6)
    parser.add_argument("--limit", type=int, default=30)
    args = parser.parse_args()

    print_rows(args)
    print_theorem()


if __name__ == "__main__":
    main()
