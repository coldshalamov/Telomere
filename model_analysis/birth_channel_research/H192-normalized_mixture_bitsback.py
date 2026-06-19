#!/usr/bin/env python3
"""H192 - normalized arithmetic/bits-back mixture ledger.

H191 priced a prefix-style implicit mode using leftover Kraft mass.  This kernel
prices the arithmetic/ANS/bits-back version suggested by the same loophole:

    Q_lambda(x) = (1-lambda) * U(x) + lambda * R(x)

where U is the uniform raw layer distribution and R is the normalized witness
distribution induced by exact V1/J3D1 seed records up to Wmax.

For arbitrary uniform inputs,

    E_U[-log2 Q_lambda(X)] = N + D(U || Q_lambda) >= N.

So a normalized mixture can make selected files shorter, but it cannot create a
negative mean drift on roughly-all uniform data.  The useful output is the exact
winner fraction, mean gap, and tail for finite witness inventories.
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


def parse_float_list(values: list[str], default: list[float]) -> list[float]:
    if not values:
        return default
    out: list[float] = []
    for value in values:
        out.extend(float(part) for part in value.split(",") if part)
    return out


def layer_from_witness(payload_width: int, rank: int, target_bits: int) -> int:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(b"H192-layer\0")
    digest.update(payload_width.to_bytes(2, "big"))
    digest.update(rank.to_bytes((rank.bit_length() + 7) // 8 or 1, "big"))
    digest.update(target_bits.to_bytes(2, "big"))
    return int.from_bytes(digest.digest(), "big") & ((1 << target_bits) - 1)


@dataclass(frozen=True)
class Row:
    target_bits: int
    max_payload_width: int
    lam: float
    witness_mass: float
    support: int
    winner_fraction: float
    mean_len: float
    mean_gain: float
    p95_len: float
    max_len: float
    divergence: float
    verdict: str


def witness_mass_by_output(target_bits: int, max_payload_width: int) -> tuple[list[float], float]:
    masses = [0.0] * (1 << target_bits)
    total = 0.0
    for payload_width in range(1, max_payload_width + 1):
        count = costs.payload_width_count_exact(payload_width)
        record_bits = costs.record_cost_for_payload_width(1, payload_width)
        mass = 2.0 ** (-record_bits)
        for rank in range(count):
            out = layer_from_witness(payload_width, rank, target_bits)
            masses[out] += mass
            total += mass
    return masses, total


def percentile(values: list[float], pct: float) -> float:
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, math.ceil(len(ordered) * pct) - 1))
    return ordered[idx]


def run_row_from_masses(
    target_bits: int,
    max_payload_width: int,
    lam: float,
    masses: list[float],
    total_mass: float,
) -> Row:
    raw_p = 2.0 ** (-target_bits)
    if total_mass <= 0.0:
        raise ValueError("empty witness inventory")
    lengths: list[float] = []
    winners = 0
    for mass in masses:
        r_p = mass / total_mass
        q_p = (1.0 - lam) * raw_p + lam * r_p
        length = -math.log2(q_p) if q_p > 0.0 else float("inf")
        lengths.append(length)
        if length < target_bits:
            winners += 1
    mean_len = sum(lengths) / len(lengths)
    mean_gain = target_bits - mean_len
    divergence = mean_len - target_bits
    verdict = (
        "BUG: normalized mixture crosses uniform entropy"
        if mean_gain > 1e-12
        else "normalized mixture conserved"
    )
    return Row(
        target_bits=target_bits,
        max_payload_width=max_payload_width,
        lam=lam,
        witness_mass=total_mass,
        support=sum(1 for mass in masses if mass > 0.0),
        winner_fraction=winners / len(lengths),
        mean_len=mean_len,
        mean_gain=mean_gain,
        p95_len=percentile(lengths, 0.95),
        max_len=max(lengths),
        divergence=divergence,
        verdict=verdict,
    )


def run_row(target_bits: int, max_payload_width: int, lam: float) -> Row:
    masses, total_mass = witness_mass_by_output(target_bits, max_payload_width)
    return run_row_from_masses(target_bits, max_payload_width, lam, masses, total_mass)


def print_table(args: argparse.Namespace) -> None:
    target_bits_values = parse_int_list(args.target_bits, [8, 12, 16])
    max_width_values = parse_int_list(args.max_payload_width, [4, 8, 16])
    lambdas = parse_float_list(args.lam, [0.0, 0.01, 0.05, 0.1, 0.25, 0.5, 0.9, 1.0])
    print("== H192 normalized arithmetic/bits-back mixture ledger ==")
    print("Q=(1-lambda)U+lambda R. gain>0 would violate the uniform source-code bound.")
    print(
        f"{'N':>4} {'Wmax':>5} {'lam':>7} {'massR':>9} {'support':>8} "
        f"{'winFrac':>9} {'meanLen':>9} {'gain':>9} {'p95':>9} "
        f"{'maxLen':>9} {'D':>9} {'verdict'}"
    )
    best_nonzero = -float("inf")
    best_label = "none"
    for target_bits in target_bits_values:
        for max_width in max_width_values:
            masses, total_mass = witness_mass_by_output(target_bits, max_width)
            row_lambdas = sorted(
                set(lambdas + ([total_mass] if 0.0 <= total_mass <= 1.0 else []))
            )
            for lam in row_lambdas:
                row = run_row_from_masses(target_bits, max_width, lam, masses, total_mass)
                if lam > 0.0 and row.mean_gain > best_nonzero:
                    best_nonzero = row.mean_gain
                    best_label = f"N={target_bits},Wmax={max_width},lambda={fmt(lam)}"
                if row.mean_gain > 1e-9:
                    raise AssertionError("normalized mixture beat uniform entropy")
                print(
                    f"{row.target_bits:4d} {row.max_payload_width:5d} "
                    f"{fmt(row.lam):>7} {fmt(row.witness_mass):>9} "
                    f"{row.support:8d} {fmt(row.winner_fraction):>9} "
                    f"{fmt(row.mean_len):>9} {fmt(row.mean_gain):>9} "
                    f"{fmt(row.p95_len):>9} {fmt(row.max_len):>9} "
                    f"{fmt(row.divergence):>9} {row.verdict}"
                )
    print(f"\nbest nonzero-lambda mean gain: {fmt(best_nonzero)} bits/layer at {best_label}")


def print_theorem() -> None:
    print()
    print("== theorem ==")
    print("Arithmetic/bits-back coding can normalize raw and witness routes,")
    print("but normalization is exactly the bill the H190 oracle omitted.")
    print("For arbitrary uniform inputs the mean length is N+D(U||Q),")
    print("so selected short files are paid for by longer tails elsewhere.")
    print("A recursive positive slope still needs a separate gamma>1")
    print("fertility/source law or a generated/reachable restriction.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-bits", action="append", default=[])
    parser.add_argument("--max-payload-width", action="append", default=[])
    parser.add_argument("--lam", action="append", default=[])
    args = parser.parse_args()

    print_table(args)
    print_theorem()


if __name__ == "__main__":
    main()
