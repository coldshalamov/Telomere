#!/usr/bin/env python3
"""H195 - public multi-salt witness-mass smoothing.

After H190-H194, the remaining arbitrary-uniform target is precise:

    keep nonzero witness mass q,
    keep support from collapsing,
    make Q(x) nearly uniform so D(U||Q) is near zero.

This kernel tests whether many public independent salt/lane inventories can
smooth witness mass enough to cross.  It is intentionally not a corpus search:
for tiny N it enumerates all outputs, hashes exact V1/J3D1 witnesses into them
under public lane labels, and computes the exact leftover-Kraft mixture

    Q(x) = (1-q)/2^N + s_x.

It reports the mean paid length, KL gap, support, mass variance, and how the
gap changes as lanes increase.  A positive gain would violate the Jensen/Kraft
bound and is asserted against.
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


def hash_to_output(label: bytes, lane: int, payload_width: int, rank: int, target_bits: int) -> int:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(label)
    digest.update(lane.to_bytes(4, "big"))
    digest.update(payload_width.to_bytes(2, "big"))
    digest.update(rank.to_bytes((rank.bit_length() + 7) // 8 or 1, "big"))
    digest.update(target_bits.to_bytes(2, "big"))
    return int.from_bytes(digest.digest(), "big") & ((1 << target_bits) - 1)


@dataclass(frozen=True)
class Row:
    target_bits: int
    max_payload_width: int
    lanes: int
    mode: str
    descriptions: int
    support: int
    witness_mass: float
    mean_len: float
    gain: float
    kl_gap: float
    p95_len: float
    max_len: float
    cv_mass: float
    mean_witness_per_output: float
    verdict: str


def build_masses(target_bits: int, max_payload_width: int, lanes: int) -> tuple[list[float], int, float]:
    output_count = 1 << target_bits
    masses = [0.0] * output_count
    descriptions = 0
    total_mass = 0.0
    for lane in range(lanes):
        for payload_width in range(1, max_payload_width + 1):
            count = costs.payload_width_count_exact(payload_width)
            record_bits = costs.record_cost_for_payload_width(1, payload_width)
            # Lane id is public but must be coded if lanes are alternative syntax.
            # Use fixed-width lane prefix; lanes=1 costs zero.
            lane_bits = 0 if lanes <= 1 else math.ceil(math.log2(lanes))
            length = record_bits + lane_bits
            mass = 2.0 ** (-length)
            descriptions += count
            total_mass += count * mass
            for rank in range(count):
                out = hash_to_output(b"H195-lane\0", lane, payload_width, rank, target_bits)
                masses[out] += mass
    return masses, descriptions, total_mass


def select_top_mass(masses: list[float], keep_fraction: float) -> tuple[list[float], float]:
    if keep_fraction >= 1.0:
        return masses[:], sum(masses)
    if keep_fraction <= 0.0:
        return [0.0] * len(masses), 0.0
    keep = max(1, int(round(len(masses) * keep_fraction)))
    threshold = sorted(masses, reverse=True)[keep - 1]
    selected = [mass if mass >= threshold else 0.0 for mass in masses]
    return selected, sum(selected)


def row_for(target_bits: int, max_payload_width: int, lanes: int, mode: str) -> Row:
    masses, descriptions, total_mass = build_masses(target_bits, max_payload_width, lanes)
    if mode.startswith("top"):
        keep_fraction = float(mode[3:]) / 100.0
        masses, total_mass = select_top_mass(masses, keep_fraction)
    output_count = 1 << target_bits
    if total_mass >= 1.0:
        raise AssertionError("overfull witness mass")
    raw_p = (1.0 - total_mass) / output_count
    probs = [raw_p + mass for mass in masses]
    lengths = [-math.log2(prob) for prob in probs]
    mean_len = sum(lengths) / output_count
    gain = target_bits - mean_len
    mean_mass = total_mass / output_count
    variance = sum((mass - mean_mass) ** 2 for mass in masses) / output_count
    cv = math.sqrt(variance) / mean_mass if mean_mass > 0.0 else 0.0
    support = sum(1 for mass in masses if mass > 0.0)
    p95 = sorted(lengths)[min(output_count - 1, math.ceil(output_count * 0.95) - 1)]
    verdict = "BUG: smoothing crossed uniform" if gain > 1e-12 else "smoothing conserved"
    return Row(
        target_bits=target_bits,
        max_payload_width=max_payload_width,
        lanes=lanes,
        mode=mode,
        descriptions=descriptions,
        support=support,
        witness_mass=total_mass,
        mean_len=mean_len,
        gain=gain,
        kl_gap=mean_len - target_bits,
        p95_len=p95,
        max_len=max(lengths),
        cv_mass=cv,
        mean_witness_per_output=mean_mass,
        verdict=verdict,
    )


def print_table(args: argparse.Namespace) -> None:
    target_bits_values = parse_int_list(args.target_bits, [8, 12])
    max_width_values = parse_int_list(args.max_payload_width, [4, 8])
    lanes_values = parse_int_list(args.lanes, [1, 2, 4, 8, 16])
    modes = args.mode or ["all", "top10"]
    print("== H195 public multi-salt witness-mass smoothing ==")
    print(
        "Lane id is charged as fixed public syntax bits. gain>0 would violate the uniform Kraft bound."
    )
    print(
        "Defaults are deliberately bounded; pass explicit --target-bits/--lanes for wider probes."
    )
    print(
        f"{'N':>4} {'Wmax':>5} {'lanes':>6} {'mode':<6} {'desc':>9} "
        f"{'support':>8} {'q':>9} {'mean':>9} {'gain':>10} "
        f"{'D':>10} {'p95':>9} {'max':>9} {'cv':>9} {'verdict'}"
    )
    best: Row | None = None
    for target_bits in target_bits_values:
        for max_width in max_width_values:
            for lanes in lanes_values:
                for mode in modes:
                    row = row_for(target_bits, max_width, lanes, mode)
                    if row.gain > 1e-9:
                        raise AssertionError("witness smoothing beat uniform entropy")
                    if row.support > 0 and (best is None or row.gain > best.gain):
                        best = row
                    print(
                        f"{row.target_bits:4d} {row.max_payload_width:5d} "
                        f"{row.lanes:6d} {row.mode:<6} {row.descriptions:9d} "
                        f"{row.support:8d} {fmt(row.witness_mass):>9} "
                        f"{fmt(row.mean_len):>9} {fmt(row.gain):>10} "
                        f"{fmt(row.kl_gap):>10} {fmt(row.p95_len):>9} "
                        f"{fmt(row.max_len):>9} {fmt(row.cv_mass):>9} {row.verdict}"
                    )
    if best is not None:
        print()
        print(
            "nearest nonzero-support gain: "
            f"{fmt(best.gain)} at N={best.target_bits},W={best.max_payload_width},"
            f"lanes={best.lanes},mode={best.mode},q={fmt(best.witness_mass)},"
            f"support={best.support}"
        )


def print_theorem() -> None:
    print()
    print("== theorem ==")
    print("Many public lanes can smooth witness mass, reducing D(U||Q),")
    print("but lane identifiers consume Kraft mass and Q still normalizes.")
    print("If the aggregate witness mass s_x becomes exactly uniform, the")
    print("mean ties raw; it cannot go below raw. Rows near zero either have")
    print("tiny q, nearly uniform q, or both. Selecting high-mass targets")
    print("creates a source restriction/support bill, not roughly-all-data")
    print("compression.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-bits", action="append", default=[])
    parser.add_argument("--max-payload-width", action="append", default=[])
    parser.add_argument("--lanes", action="append", default=[])
    parser.add_argument("--mode", action="append", default=[])
    args = parser.parse_args()

    print_table(args)
    print_theorem()


if __name__ == "__main__":
    main()
