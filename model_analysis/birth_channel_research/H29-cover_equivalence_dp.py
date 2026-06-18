#!/usr/bin/env python3
"""
H29 - exact cover-equivalence DP for tiny Total-Cover universes.

The legal collective witness idea is:

    Q(x) = sum_{covers c expanding to x} 2^-L(c)

and arithmetic-code the decoded layer x under public Q instead of transmitting
one selected cover. This can harvest duplicate-cover entropy without storing a
rank inside C_x.

This kernel is intentionally tiny and exact. It does not run a Telomere
compression search. It enumerates every N-bit target layer and every cover mass
induced by a deterministic toy seed universe, using exact V1/J3D1 record costs
for payload widths.
"""

from __future__ import annotations

import argparse
import hashlib
import math
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "model_analysis" / "proof_kernel"))

from costs import (  # noqa: E402
    payload_width_count_le,
    payload_width_for_seed_index,
    record_cost_for_payload_width,
)


INF = float("inf")


def hash_bits(label: str, *items: object, n_bits: int) -> str:
    material = "|".join([label, *(str(item) for item in items)]).encode()
    out = bytearray()
    counter = 0
    while len(out) * 8 < n_bits:
        h = hashlib.blake2s(material + counter.to_bytes(4, "big")).digest()
        out.extend(h)
        counter += 1
    bitstream = "".join(f"{byte:08b}" for byte in out)
    return bitstream[:n_bits]


@dataclass(frozen=True)
class EdgeTables:
    masses: dict[int, dict[str, float]]
    best_costs: dict[int, dict[str, float]]
    expected_masses: dict[int, float]
    seed_count: int


def build_edge_tables(block_bits: int, max_arity: int, payload_depth: int) -> EdgeTables:
    seed_count = payload_width_count_le(payload_depth)
    masses: dict[int, dict[str, float]] = {}
    best_costs: dict[int, dict[str, float]] = {}
    expected_masses: dict[int, float] = {}
    for arity in range(1, max_arity + 1):
        masses[arity] = {}
        best_costs[arity] = {}
        total_mass = 0.0
        for seed_index in range(seed_count):
            payload_width = payload_width_for_seed_index(seed_index)
            if payload_width > payload_depth:
                continue
            cost = record_cost_for_payload_width(arity, payload_width)
            mass = 2.0 ** (-cost)
            out = hash_bits("h29-cover-edge", block_bits, arity, seed_index, n_bits=arity * block_bits)
            masses[arity][out] = masses[arity].get(out, 0.0) + mass
            best_costs[arity][out] = min(best_costs[arity].get(out, INF), float(cost))
            total_mass += mass
        expected_masses[arity] = total_mass / (2.0 ** (arity * block_bits))
    return EdgeTables(masses, best_costs, expected_masses, seed_count)


@dataclass(frozen=True)
class LayerResult:
    bits: str
    q_mass: float
    best_local_bits: float
    collective_bits: float


def score_layer(bits: str, tables: EdgeTables, block_bits: int, max_arity: int) -> LayerResult:
    atoms = len(bits) // block_bits
    q_dp = [0.0] * (atoms + 1)
    b_dp = [INF] * (atoms + 1)
    q_dp[0] = 1.0
    b_dp[0] = 0.0
    for pos in range(atoms):
        if q_dp[pos] == 0.0 and b_dp[pos] == INF:
            continue
        for arity in range(1, max_arity + 1):
            end = pos + arity
            if end > atoms:
                continue
            seg = bits[pos * block_bits : end * block_bits]
            edge_mass = tables.masses[arity].get(seg, 0.0)
            if edge_mass:
                q_dp[end] += q_dp[pos] * edge_mass
            edge_cost = tables.best_costs[arity].get(seg, INF)
            if edge_cost < INF:
                b_dp[end] = min(b_dp[end], b_dp[pos] + edge_cost)
    q_mass = q_dp[atoms]
    collective_bits = -math.log2(q_mass) if q_mass > 0.0 else INF
    return LayerResult(bits, q_mass, b_dp[atoms], collective_bits)


def expected_uniform_mass(atoms: int, block_bits: int, max_arity: int, tables: EdgeTables) -> float:
    """Expected Q(x) if every edge output is perfectly uniform.

    In this model Q(x) is identical for every x:

        Q(x) = 2^(-N*B) * Z_N

    with Z_N computed by the arity/seed-code masses.
    """

    dp = [0.0] * (atoms + 1)
    dp[0] = 1.0
    for pos in range(atoms):
        for arity in range(1, max_arity + 1):
            end = pos + arity
            if end <= atoms:
                dp[end] += dp[pos] * tables.expected_masses[arity]
    return dp[atoms]


def all_bitstrings(n_bits: int) -> list[str]:
    return [format(i, f"0{n_bits}b") for i in range(1 << n_bits)]


def summarize(results: list[LayerResult], raw_bits: int) -> dict[str, float]:
    covered = [r for r in results if r.q_mass > 0.0 and r.best_local_bits < INF]
    if not covered:
        raise RuntimeError("no covered strings")
    avg_best = sum(r.best_local_bits for r in covered) / len(covered)
    avg_collective = sum(r.collective_bits for r in covered) / len(covered)
    avg_duplicate_saving = sum(
        r.best_local_bits - r.collective_bits for r in covered
    ) / len(covered)
    total_q = sum(r.q_mass for r in results)
    below_raw_collective = sum(1 for r in covered if r.collective_bits < raw_bits)
    below_raw_best = sum(1 for r in covered if r.best_local_bits < raw_bits)
    return {
        "coverage": len(covered) / len(results),
        "total_q_mass": total_q,
        "avg_best_local_bits": avg_best,
        "avg_collective_bits": avg_collective,
        "avg_duplicate_saving_bits": avg_duplicate_saving,
        "collective_gain_vs_raw": raw_bits - avg_collective,
        "best_local_gain_vs_raw": raw_bits - avg_best,
        "collective_below_raw_fraction": below_raw_collective / len(results),
        "best_local_below_raw_fraction": below_raw_best / len(results),
        "min_collective_bits": min(r.collective_bits for r in covered),
        "max_collective_bits": max(r.collective_bits for r in covered),
    }


def best_escape_mixture(results: list[LayerResult], raw_bits: int) -> tuple[float, float]:
    """Mix collective Q with a raw uniform escape and return best alpha, avg bits."""

    raw_p = 2.0 ** (-raw_bits)
    best_alpha = 0.0
    best_avg = raw_bits
    for step in range(0, 101):
        alpha = step / 100.0
        total = 0.0
        for r in results:
            p = alpha * r.q_mass + (1.0 - alpha) * raw_p
            total += -math.log2(p)
        avg = total / len(results)
        if avg < best_avg:
            best_alpha = alpha
            best_avg = avg
    return best_alpha, best_avg


def run_case(atoms: int, block_bits: int, max_arity: int, payload_depth: int) -> str:
    raw_bits = atoms * block_bits
    tables = build_edge_tables(block_bits, max_arity, payload_depth)
    results = [
        score_layer(bits, tables, block_bits, max_arity)
        for bits in all_bitstrings(raw_bits)
    ]
    summary = summarize(results, raw_bits)
    expected_q = expected_uniform_mass(atoms, block_bits, max_arity, tables)
    expected_collective_bits = -math.log2(expected_q)
    alpha, mix_avg = best_escape_mixture(results, raw_bits)

    lines = []
    lines.append("== H29 exact cover-equivalence DP ==")
    lines.append(
        f"N={atoms} atoms, B={block_bits}, K={max_arity}, payload_depth={payload_depth}, "
        f"seed_count/arity={tables.seed_count}"
    )
    lines.append(f"raw_bits = {raw_bits}")
    lines.append("")
    lines.append("sampled deterministic seed universe:")
    lines.append(f"  coverage                         = {summary['coverage']:.6f}")
    lines.append(f"  total Q mass                      = {summary['total_q_mass']:.6f}")
    lines.append(f"  avg best local cover bits         = {summary['avg_best_local_bits']:.6f}")
    lines.append(f"  avg collective -log2 Q bits       = {summary['avg_collective_bits']:.6f}")
    lines.append(f"  avg duplicate-cover saving        = {summary['avg_duplicate_saving_bits']:.6f}")
    lines.append(f"  best-local gain vs raw            = {summary['best_local_gain_vs_raw']:.6f}")
    lines.append(f"  collective gain vs raw            = {summary['collective_gain_vs_raw']:.6f}")
    lines.append(f"  collective below raw fraction     = {summary['collective_below_raw_fraction']:.6f}")
    lines.append(f"  best-local below raw fraction     = {summary['best_local_below_raw_fraction']:.6f}")
    lines.append(f"  collective bit range              = {summary['min_collective_bits']:.6f} .. {summary['max_collective_bits']:.6f}")
    lines.append("")
    lines.append("raw escape mixture:")
    lines.append(f"  best alpha on collective Q        = {alpha:.2f}")
    lines.append(f"  best uniform average bits         = {mix_avg:.6f}")
    lines.append(f"  best uniform gain vs raw          = {raw_bits - mix_avg:.6f}")
    lines.append("")
    lines.append("expected uniform edge-mass row:")
    lines.append(f"  Q_expected(x)                     = {expected_q:.12g}")
    lines.append(f"  -log2 Q_expected(x)               = {expected_collective_bits:.6f}")
    lines.append(f"  expected gain vs raw              = {raw_bits - expected_collective_bits:.6f}")
    lines.append("")
    lines.append("CONCLUSION:")
    lines.append(
        "Cover-equivalence merging harvests real duplicate descriptions relative to "
        "one selected cover, but the public Q distribution does not give a "
        "uniform all-data average win. A raw escape mixture chooses alpha=0 "
        "when judged on uniform layers. The remaining use is minority/source-"
        "shaped coding, not maintained recursive compression over roughly all "
        "uniform data."
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--atoms", type=int, default=12)
    parser.add_argument("--block-bits", type=int, default=1)
    parser.add_argument("--max-arity", type=int, default=4)
    parser.add_argument("--payload-depth", type=int, default=8)
    args = parser.parse_args()
    print(run_case(args.atoms, args.block_bits, args.max_arity, args.payload_depth))


if __name__ == "__main__":
    main()
