#!/usr/bin/env python3
"""H196 - self-induced source law / recursive output-law ledger.

H195 showed that a normalized public witness distribution Q cannot beat a
uniform N-bit layer:

    E_U[-log2 Q(X)] = N + D(U||Q).

The next possible escape is recursive: after one pass, maybe the emitted layer
is not uniform anymore.  This kernel prices that idea directly.  It shapes a
candidate next-layer source P toward H195 witness-rich outputs and separates:

    apparent block gain = N - E_P[-log2 Q(X)]
    source-law tax      = N - H(P)
    paid net            = H(P) - E_P[-log2 Q(X)] = -D(P||Q)

If a previous pass really produces P from arbitrary uniform data, the entropy
deficit N-H(P) is the reversible state/bias bill.  The best case P=Q ties; it
does not cross.  Positive apparent gain is therefore useful telemetry only
inside a declared source/reachable regime.
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


def hash_to_output(label: bytes, lane: int, payload_width: int, rank: int, target_bits: int) -> int:
    digest = hashlib.blake2b(digest_size=32)
    digest.update(label)
    digest.update(lane.to_bytes(4, "big"))
    digest.update(payload_width.to_bytes(2, "big"))
    digest.update(rank.to_bytes((rank.bit_length() + 7) // 8 or 1, "big"))
    digest.update(target_bits.to_bytes(2, "big"))
    return int.from_bytes(digest.digest(), "big") & ((1 << target_bits) - 1)


def build_q(target_bits: int, max_payload_width: int, lanes: int) -> tuple[list[float], float, int]:
    output_count = 1 << target_bits
    masses = [0.0] * output_count
    witness_mass = 0.0
    descriptions = 0
    lane_bits = 0 if lanes <= 1 else math.ceil(math.log2(lanes))
    for lane in range(lanes):
        for payload_width in range(1, max_payload_width + 1):
            count = costs.payload_width_count_exact(payload_width)
            record_bits = costs.record_cost_for_payload_width(1, payload_width)
            mass = 2.0 ** (-(record_bits + lane_bits))
            witness_mass += count * mass
            descriptions += count
            for rank in range(count):
                out = hash_to_output(b"H195-lane\0", lane, payload_width, rank, target_bits)
                masses[out] += mass
    if witness_mass >= 1.0:
        raise AssertionError("overfull witness mass")
    raw_p = (1.0 - witness_mass) / output_count
    return [raw_p + mass for mass in masses], witness_mass, descriptions


def entropy(probs: list[float]) -> float:
    return -sum(p * math.log2(p) for p in probs if p > 0.0)


def cross_entropy(source: list[float], model: list[float]) -> float:
    return -sum(p * math.log2(q) for p, q in zip(source, model) if p > 0.0)


def shaped_source(model: list[float], beta: float) -> list[float]:
    if beta == 0.0:
        return [1.0 / len(model)] * len(model)
    weights = [q**beta for q in model]
    total = sum(weights)
    return [weight / total for weight in weights]


@dataclass(frozen=True)
class Row:
    target_bits: int
    max_payload_width: int
    lanes: int
    beta: float
    witness_mass: float
    descriptions: int
    source_entropy: float
    cross_entropy: float
    apparent_gain: float
    source_tax: float
    paid_net: float
    kl_source_model: float
    support_999: int
    verdict: str


def row_for(
    target_bits: int,
    max_payload_width: int,
    lanes: int,
    beta: float,
    model: list[float],
    witness_mass: float,
    descriptions: int,
) -> Row:
    source = shaped_source(model, beta)
    h_source = entropy(source)
    ce = cross_entropy(source, model)
    apparent_gain = target_bits - ce
    source_tax = target_bits - h_source
    paid_net = apparent_gain - source_tax
    kl = ce - h_source
    if paid_net > 1e-10:
        raise AssertionError("source shaping beat its own entropy tax")
    sorted_source = sorted(source, reverse=True)
    acc = 0.0
    support_999 = 0
    for prob in sorted_source:
        acc += prob
        support_999 += 1
        if acc >= 0.999:
            break
    if beta == 0.0:
        verdict = "uniform H195 case"
    elif abs(beta - 1.0) < 1e-12:
        verdict = "P=Q ties after tax"
    else:
        verdict = "source bias pays KL"
    return Row(
        target_bits=target_bits,
        max_payload_width=max_payload_width,
        lanes=lanes,
        beta=beta,
        witness_mass=witness_mass,
        descriptions=descriptions,
        source_entropy=h_source,
        cross_entropy=ce,
        apparent_gain=apparent_gain,
        source_tax=source_tax,
        paid_net=paid_net,
        kl_source_model=kl,
        support_999=support_999,
        verdict=verdict,
    )


def print_table(args: argparse.Namespace) -> None:
    target_bits_values = parse_int_list(args.target_bits, [8])
    max_width_values = parse_int_list(args.max_payload_width, [8])
    lanes_values = parse_int_list(args.lanes, [16, 256, 4096])
    beta_values = parse_float_list(args.beta, [0.0, 0.5, 1.0, 2.0, 4.0])
    print("== H196 self-induced source law / recursive output-law ledger ==")
    print("Q is built from exact current V1/J3D1 record costs plus paid public lane ids.")
    print("beta=0 is uniform input; beta=1 sets the next-layer source P exactly to Q.")
    print(
        f"{'N':>4} {'Wmax':>5} {'lanes':>6} {'beta':>7} {'q':>9} "
        f"{'H(P)':>9} {'CE(P,Q)':>9} {'appGain':>10} {'srcTax':>10} "
        f"{'paidNet':>10} {'KL':>10} {'S999':>6} {'verdict'}"
    )
    best: Row | None = None
    for target_bits in target_bits_values:
        for max_width in max_width_values:
            for lanes in lanes_values:
                model, witness_mass, descriptions = build_q(target_bits, max_width, lanes)
                for beta in beta_values:
                    row = row_for(
                        target_bits,
                        max_width,
                        lanes,
                        beta,
                        model,
                        witness_mass,
                        descriptions,
                    )
                    if best is None or row.paid_net > best.paid_net:
                        best = row
                    print(
                        f"{row.target_bits:4d} {row.max_payload_width:5d} "
                        f"{row.lanes:6d} {row.beta:7.3f} {fmt(row.witness_mass):>9} "
                        f"{fmt(row.source_entropy):>9} {fmt(row.cross_entropy):>9} "
                        f"{fmt(row.apparent_gain):>10} {fmt(row.source_tax):>10} "
                        f"{fmt(row.paid_net):>10} {fmt(row.kl_source_model):>10} "
                        f"{row.support_999:6d} {row.verdict}"
                    )
    if best is not None:
        print()
        print(
            "best paid net: "
            f"{fmt(best.paid_net)} at N={best.target_bits},W={best.max_payload_width},"
            f"lanes={best.lanes},beta={fmt(best.beta)}"
        )


def print_theorem() -> None:
    print()
    print("== theorem ==")
    print("A recursive pass may make the next layer non-uniform, and that can")
    print("create apparent Telomere block gain under Q. For arbitrary data,")
    print("creating that law costs exactly N-H(P) bits per N-bit layer.")
    print("After that tax, the net is H(P)-CE(P,Q) = -D(P||Q) <= 0.")
    print("The best possible source law P=Q ties. Any positive apparent")
    print("row is therefore a generated/source-regime claim, not a roughly-all")
    print("data recursive breakthrough.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-bits", action="append", default=[])
    parser.add_argument("--max-payload-width", action="append", default=[])
    parser.add_argument("--lanes", action="append", default=[])
    parser.add_argument("--beta", action="append", default=[])
    args = parser.parse_args()

    print_table(args)
    print_theorem()


if __name__ == "__main__":
    main()
