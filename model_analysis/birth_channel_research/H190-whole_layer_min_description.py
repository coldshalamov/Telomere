#!/usr/bin/env python3
"""H190 - whole-layer minimum-description ledger.

This kernel attacks the broad macro-witness / canonical-minimum-cover loophole.

Instead of pricing a local record in isolation, enumerate a tiny complete output
space of N-bit layers.  A public deterministic decoder maps every canonical
V1/J3D1 seed witness up to a payload-width frontier into one N-bit layer.  The
encoder may choose the shortest available witness for that layer, otherwise a
raw fallback is used.

Two modes are reported:

* oracle_file_choice: compares raw N bits against a bare witness record.  This
  is an optimistic lower bound because the stream does not tell the decoder
  whether raw or witness syntax follows.
* paid_mode: prefixes raw/witness with one parse bit.  This is the smallest
  honest single-layer source-code version of the same idea.

If whole-layer macro witnesses, canonical minimum selection, collision
coalescence, or width/rank lookahead create an unpriced gain, it should show up
here as average paid length below N.  Under uniform targets it should not.
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


MODE_BITS = 1


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
    digest.update(b"H190-layer\0")
    digest.update(payload_width.to_bytes(2, "big"))
    digest.update(rank.to_bytes((rank.bit_length() + 7) // 8 or 1, "big"))
    digest.update(target_bits.to_bytes(2, "big"))
    value = int.from_bytes(digest.digest(), "big")
    return value & ((1 << target_bits) - 1)


@dataclass(frozen=True)
class Choice:
    payload_width: int
    rank: int
    length_bits: int


@dataclass(frozen=True)
class Row:
    target_bits: int
    max_payload_width: int
    descriptions: int
    oracle_mass: float
    paid_mass: float
    oracle_support: int
    paid_support: int
    oracle_avg: float
    paid_avg: float
    oracle_gain: float
    paid_gain: float
    oracle_bad_tail: int
    paid_bad_tail: int
    roundtrip_ok: bool
    verdict: str


def build_row(target_bits: int, max_payload_width: int) -> Row:
    if max_payload_width > costs.MAX_PAYLOAD_WIDTH_BITS:
        raise ValueError("max payload width exceeds exact J3D1 cap")
    output_count = 1 << target_bits
    oracle_raw = target_bits
    paid_raw = target_bits + MODE_BITS
    oracle_len = [oracle_raw] * output_count
    paid_len = [paid_raw] * output_count
    best_paid: list[Choice | None] = [None] * output_count

    descriptions = 0
    oracle_mass = 0.0
    paid_mass = 0.0
    for payload_width in range(1, max_payload_width + 1):
        count = costs.payload_width_count_exact(payload_width)
        record_bits = costs.record_cost_for_payload_width(1, payload_width)
        paid_bits = MODE_BITS + record_bits
        descriptions += count
        oracle_mass += count * (2.0 ** (-record_bits))
        paid_mass += count * (2.0 ** (-paid_bits))
        for rank in range(count):
            out = layer_from_witness(payload_width, rank, target_bits)
            if record_bits < oracle_len[out]:
                oracle_len[out] = record_bits
            if paid_bits < paid_len[out]:
                paid_len[out] = paid_bits
                best_paid[out] = Choice(payload_width, rank, paid_bits)

    oracle_avg = sum(oracle_len) / output_count
    paid_avg = sum(paid_len) / output_count
    oracle_support = sum(1 for value in oracle_len if value < oracle_raw)
    paid_support = sum(1 for value in paid_len if value < paid_raw)
    oracle_gain = target_bits - oracle_avg
    paid_gain = target_bits - paid_avg
    oracle_bad_tail = max(oracle_len) - target_bits
    paid_bad_tail = max(paid_len) - target_bits

    samples = [0, output_count // 3, output_count - 1]
    roundtrip_ok = True
    for sample in samples:
        encoded = encode_paid(sample, target_bits, best_paid)
        decoded = decode_paid(encoded, target_bits)
        roundtrip_ok = roundtrip_ok and (decoded == sample)

    if paid_gain > 1e-12:
        verdict = "BUG: paid whole-layer source code beats uniform entropy"
    elif oracle_gain > 0.0:
        verdict = "oracle-only gain; paid parse/fallback stays negative"
    else:
        verdict = "no whole-layer gain"
    return Row(
        target_bits=target_bits,
        max_payload_width=max_payload_width,
        descriptions=descriptions,
        oracle_mass=oracle_mass,
        paid_mass=paid_mass,
        oracle_support=oracle_support,
        paid_support=paid_support,
        oracle_avg=oracle_avg,
        paid_avg=paid_avg,
        oracle_gain=oracle_gain,
        paid_gain=paid_gain,
        oracle_bad_tail=oracle_bad_tail,
        paid_bad_tail=paid_bad_tail,
        roundtrip_ok=roundtrip_ok,
        verdict=verdict,
    )


def encode_paid(output: int, target_bits: int, best_paid: list[Choice | None]) -> tuple[str, int, int]:
    choice = best_paid[output]
    if choice is None:
        return ("raw", target_bits, output)
    return ("witness", choice.payload_width, choice.rank)


def decode_paid(encoded: tuple[str, int, int], target_bits: int) -> int:
    mode, a, b = encoded
    if mode == "raw":
        return b
    if mode == "witness":
        return layer_from_witness(a, b, target_bits)
    raise ValueError(mode)


def print_table(args: argparse.Namespace) -> None:
    target_bits_values = parse_int_list(args.target_bits, [8, 10, 12, 16])
    max_width_values = parse_int_list(args.max_payload_width, [4, 6, 8, 10, 12, 16])
    print("== H190 whole-layer minimum-description ledger ==")
    print(
        "Oracle omits the raw/witness parse bit. Paid mode charges one parse bit and exact V1/J3D1 records."
    )
    print(
        f"{'N':>4} {'Wmax':>5} {'desc':>8} {'massO':>9} {'massP':>9} "
        f"{'supO':>7} {'supP':>7} {'avgO':>9} {'avgP':>9} "
        f"{'gainO':>9} {'gainP':>9} {'tailP':>6} {'rt':>4} {'verdict'}"
    )
    for target_bits in target_bits_values:
        for max_width in max_width_values:
            if max_width > args.max_exact_width:
                continue
            row = build_row(target_bits, max_width)
            if row.paid_gain > 1e-9:
                raise AssertionError("paid whole-layer code beat uniform entropy")
            print(
                f"{row.target_bits:4d} {row.max_payload_width:5d} "
                f"{row.descriptions:8d} {fmt(row.oracle_mass):>9} "
                f"{fmt(row.paid_mass):>9} {row.oracle_support:7d} "
                f"{row.paid_support:7d} {fmt(row.oracle_avg):>9} "
                f"{fmt(row.paid_avg):>9} {fmt(row.oracle_gain):>9} "
                f"{fmt(row.paid_gain):>9} {row.paid_bad_tail:6d} "
                f"{str(row.roundtrip_ok):>4} {row.verdict}"
            )


def print_theorem() -> None:
    print()
    print("== theorem ==")
    print("A canonical minimum over many witnesses is just source coding over")
    print("a deterministic description inventory. The optimistic oracle can")
    print("show tiny local gains by omitting the parse/fallback distinction.")
    print("Once that distinction is paid, the uniform average length stays")
    print("at or above the N-bit raw layer. Collisions/coalescence only remove")
    print("available output names unless a source/reachable regime is declared.")


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
