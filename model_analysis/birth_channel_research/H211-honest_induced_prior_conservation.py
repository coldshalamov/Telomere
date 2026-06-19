#!/usr/bin/env python3
"""H211 - honest induced-prior conservation.

This is the concrete push-forward version of H196/H208.  It enumerates a tiny
all-data source, runs a canonical stateless Telomere-like encoder with raw
fallback, measures the actual emitted-token law P_emit, and then gives the next
pass three priors:

* actual_code: the normalized code lengths the first pass really used;
* class_uniform: a decoder-known public class model over selected witness/raw
  tokens;
* oracle_emit: Q = P_emit, the best possible induced prior.

If self-induced bias were a free recursive fuel, oracle_emit would show positive
paid drift.  It ties instead: H(P_emit) - CE(P_emit, P_emit) = 0.
"""

from __future__ import annotations

import argparse
import hashlib
import math
import sys
from collections import Counter
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


def hash_bits(label: bytes, width: int) -> int:
    digest = hashlib.blake2b(label, digest_size=32).digest()
    return int.from_bytes(digest, "big") & ((1 << width) - 1)


def log2_counter_entropy(counts: Counter[tuple[str, int]]) -> float:
    total = sum(counts.values())
    if total == 0:
        return 0.0
    entropy = 0.0
    for count in counts.values():
        p = count / total
        entropy -= p * math.log2(p)
    return entropy


def payload_width_count_exact(width: int) -> int:
    return costs.payload_width_count_exact(width)


def width_base_index(width: int) -> int:
    if width == 1:
        return 0
    return costs.payload_width_count_le(width - 1)


@dataclass(frozen=True)
class Witness:
    seed_index: int
    width: int
    output: int
    length: int


@dataclass(frozen=True)
class Encoded:
    token: tuple[str, int]
    output: int
    length: int


@dataclass(frozen=True)
class QModel:
    name: str
    cross_entropy: float
    apparent_gain: float
    source_tax: float
    paid_net: float
    kl_emit_q: float


def witnesses(n_bits: int, w_max: int, arity: int, mode_bits: int) -> list[Witness]:
    out: list[Witness] = []
    for width in range(1, w_max + 1):
        base = width_base_index(width)
        for offset in range(payload_width_count_exact(width)):
            seed_index = base + offset
            output = hash_bits(
                b"H211-witness\0"
                + arity.to_bytes(2, "big")
                + width.to_bytes(2, "big")
                + seed_index.to_bytes(8, "big"),
                n_bits,
            )
            length = mode_bits + costs.record_cost_for_payload_width(arity, width)
            out.append(Witness(seed_index=seed_index, width=width, output=output, length=length))
    return out


def canonical_encode(
    target: int,
    by_output: dict[int, list[Witness]],
    *,
    n_bits: int,
    raw_mode_bits: int,
) -> Encoded:
    raw_length = raw_mode_bits + n_bits
    best: Witness | None = None
    for candidate in by_output.get(target, []):
        if best is None or (candidate.length, candidate.seed_index) < (best.length, best.seed_index):
            best = candidate
    if best is not None and best.length < raw_length:
        return Encoded(token=("w", best.seed_index), output=target, length=best.length)
    return Encoded(token=("r", target), output=target, length=raw_length)


def decode(encoded: Encoded, witness_by_seed: dict[int, Witness]) -> int:
    kind, value = encoded.token
    if kind == "w":
        return witness_by_seed[value].output
    if kind == "r":
        return value
    raise ValueError(f"unknown token kind {kind!r}")


def cross_entropy_from_prob(
    counts: Counter[tuple[str, int]],
    q_prob: dict[tuple[str, int], float],
) -> float:
    total = sum(counts.values())
    ce = 0.0
    for token, count in counts.items():
        q = q_prob.get(token, 0.0)
        if q <= 0.0:
            return math.inf
        ce -= (count / total) * math.log2(q)
    return ce


def q_models(
    encoded: list[Encoded],
    *,
    n_bits: int,
    h_emit: float,
    mean_emit_bits: float,
) -> list[QModel]:
    counts: Counter[tuple[str, int]] = Counter(item.token for item in encoded)
    total = len(encoded)
    witness_tokens = [token for token in counts if token[0] == "w"]
    raw_tokens = [token for token in counts if token[0] == "r"]

    actual_q = {item.token: 2.0 ** (-item.length) for item in encoded}
    actual_z = sum(actual_q.values())
    actual_q = {token: q / actual_z for token, q in actual_q.items()}

    class_q: dict[tuple[str, int], float] = {}
    if witness_tokens:
        class_mass_w = len(witness_tokens) / total
        for token in witness_tokens:
            class_q[token] = class_mass_w / len(witness_tokens)
    if raw_tokens:
        class_mass_r = len(raw_tokens) / total
        for token in raw_tokens:
            class_q[token] = class_mass_r / len(raw_tokens)

    oracle_q = {token: count / total for token, count in counts.items()}

    rows: list[QModel] = []
    for name, q in [
        ("actual_code", actual_q),
        ("class_uniform", class_q),
        ("oracle_emit", oracle_q),
    ]:
        ce = cross_entropy_from_prob(counts, q)
        apparent = mean_emit_bits - ce
        source_tax = mean_emit_bits - h_emit
        paid_net = h_emit - ce
        rows.append(
            QModel(
                name=name,
                cross_entropy=ce,
                apparent_gain=apparent,
                source_tax=source_tax,
                paid_net=paid_net,
                kl_emit_q=ce - h_emit,
            )
        )
    return rows


def run(args: argparse.Namespace) -> None:
    universe = 1 << args.n_bits
    all_witnesses = witnesses(args.n_bits, args.w_max, args.arity, args.mode_bits)
    by_output: dict[int, list[Witness]] = {}
    by_seed: dict[int, Witness] = {}
    for witness in all_witnesses:
        by_output.setdefault(witness.output, []).append(witness)
        by_seed[witness.seed_index] = witness

    encoded: list[Encoded] = []
    roundtrip = True
    for target in range(universe):
        item = canonical_encode(target, by_output, n_bits=args.n_bits, raw_mode_bits=args.raw_mode_bits)
        encoded.append(item)
        if decode(item, by_seed) != target:
            roundtrip = False

    counts: Counter[tuple[str, int]] = Counter(item.token for item in encoded)
    lengths = [item.length for item in encoded]
    h_emit = log2_counter_entropy(counts)
    mean_emit_bits = sum(lengths) / len(lengths)
    first_delta = mean_emit_bits - args.n_bits
    support = sum(1 for token in counts if token[0] == "w")
    raw_count = sum(1 for token in counts if token[0] == "r")
    model_rows = q_models(encoded, n_bits=args.n_bits, h_emit=h_emit, mean_emit_bits=mean_emit_bits)

    print("== H211 honest induced-prior conservation ==")
    print(
        f"N={args.n_bits} arity={args.arity} Wmax={args.w_max} "
        f"witnesses={len(all_witnesses)} cases={universe} roundtrip={roundtrip}"
    )
    print(
        f"unique_emit={len(counts)} H_emit={fmt(h_emit)} mean_emit_bits={fmt(mean_emit_bits)} "
        f"first_pass_delta={fmt(first_delta)} support_witness={support} raw={raw_count}"
    )
    print(
        f"{'Q_mode':<14} {'CE_emit_Q':>11} {'appGain':>10} {'srcTax':>10} "
        f"{'paidNet':>10} {'KL':>10} {'twoPassDelta':>13} {'verdict':>12}"
    )
    for row in model_rows:
        two_pass_delta = row.cross_entropy - args.n_bits
        verdict = "tie" if abs(row.paid_net) < 1e-12 else "negative"
        print(
            f"{row.name:<14} {fmt(row.cross_entropy):>11} {fmt(row.apparent_gain):>10} "
            f"{fmt(row.source_tax):>10} {fmt(row.paid_net):>10} "
            f"{fmt(row.kl_emit_q):>10} {fmt(two_pass_delta):>13} {verdict:>12}"
        )

    print()
    print("== theorem ==")
    print("The actual emitted stream is an injective push-forward of the uniform")
    print("input, so H_emit=N in this all-data toy.  Giving the next pass the")
    print("oracle prior Q=P_emit only reaches CE=N.  Any implementable mismatch")
    print("loses by KL; any positive apparent gain is exactly the source/shape tax")
    print("created by the first pass's emitted representation.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-bits", type=int, default=8)
    parser.add_argument("--w-max", type=int, default=8)
    parser.add_argument("--arity", type=int, default=1)
    parser.add_argument("--mode-bits", type=int, default=1)
    parser.add_argument("--raw-mode-bits", type=int, default=1)
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
