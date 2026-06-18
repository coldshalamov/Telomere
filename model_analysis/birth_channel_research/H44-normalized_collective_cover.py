#!/usr/bin/env python3
"""H44 - normalized collective-cover witness check.

H29 showed the right stateless collective-cover idea:

    Q_raw(x) = sum_{covers c expanding to x} 2^-L(c)

That harvests duplicate cover descriptions without sending a selected cover.
H44 adds the missing normalization/accounting view:

    Q(x) = Q_raw(x) / Z
    Z = sum_x Q_raw(x)

If Q covers all uniform x, the average code length under uniform data is:

    E_U[-log2 Q(X)] = n + KL(U || Q) >= n

So duplicate-cover savings can move bits between strings, and it can be a
source-shaped prior, but a normalized public cover distribution cannot beat raw
on roughly all uniform data.

The kernel is intentionally tiny and exact, reusing H29's exhaustive toy
universe and exact V1/J3D1 record costs. It is not a big Telomere search.
"""

from __future__ import annotations

import argparse
import importlib.util
import math
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

H29_PATH = ROOT / "model_analysis" / "birth_channel_research" / "H29-cover_equivalence_dp.py"
SPEC = importlib.util.spec_from_file_location("h29_cover_equivalence_dp", H29_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"could not load {H29_PATH}")
H29 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = H29
SPEC.loader.exec_module(H29)


@dataclass(frozen=True)
class Case:
    atoms: int
    block_bits: int
    max_arity: int
    payload_depth: int


DEFAULT_CASES = (
    Case(10, 1, 4, 8),
    Case(12, 1, 4, 8),
    Case(10, 1, 4, 10),
    Case(8, 2, 4, 8),
)


@dataclass(frozen=True)
class NormalizedResult:
    raw_bits: int
    coverage: float
    avg_best_local_bits: float
    avg_raw_collective_bits: float
    total_q_mass: float
    avg_normalized_bits: float
    excess_over_raw: float
    kl_uniform_to_q: float


def run_normalized_case(
    atoms: int,
    block_bits: int,
    max_arity: int,
    payload_depth: int,
) -> NormalizedResult:
    raw_bits = atoms * block_bits
    tables = H29.build_edge_tables(block_bits, max_arity, payload_depth)
    results = [
        H29.score_layer(bits, tables, block_bits, max_arity)
        for bits in H29.all_bitstrings(raw_bits)
    ]
    summary = H29.summarize(results, raw_bits)
    if summary["coverage"] < 1.0:
        # For partial support, pure Q is not a complete lossless code. Keep the
        # normalized-support result visible but report infinite all-data cost.
        avg_normalized_bits = float("inf")
        excess = float("inf")
        kl = float("inf")
    else:
        total_q = summary["total_q_mass"]
        avg_normalized_bits = summary["avg_collective_bits"] + math.log2(total_q)
        excess = avg_normalized_bits - raw_bits
        kl = excess
    return NormalizedResult(
        raw_bits=raw_bits,
        coverage=summary["coverage"],
        avg_best_local_bits=summary["avg_best_local_bits"],
        avg_raw_collective_bits=summary["avg_collective_bits"],
        total_q_mass=summary["total_q_mass"],
        avg_normalized_bits=avg_normalized_bits,
        excess_over_raw=excess,
        kl_uniform_to_q=kl,
    )


def render_case(case: Case) -> str:
    result = run_normalized_case(
        atoms=case.atoms,
        block_bits=case.block_bits,
        max_arity=case.max_arity,
        payload_depth=case.payload_depth,
    )
    return (
        f"{case.atoms:5d} {case.block_bits:3d} {case.max_arity:3d} "
        f"{case.payload_depth:5d} "
        f"{result.raw_bits:8.3f} {result.coverage:9.6f} "
        f"{result.avg_best_local_bits:12.6f} "
        f"{result.avg_raw_collective_bits:12.6f} "
        f"{result.total_q_mass:12.8f} "
        f"{result.avg_normalized_bits:12.6f} "
        f"{result.excess_over_raw:11.6f} "
        f"{result.kl_uniform_to_q:11.6f}"
    )


def print_exact_rows(cases: tuple[Case, ...]) -> None:
    print("== normalized collective-cover rows ==")
    print("Q_raw sums all cover masses. Q_norm=Q_raw/Z is the actual public code.")
    print(
        f"{'atoms':>5} {'B':>3} {'K':>3} {'D':>5} "
        f"{'raw':>8} {'coverage':>9} {'best local':>12} "
        f"{'raw -logQ':>12} {'Z':>12} {'norm bits':>12} "
        f"{'excess':>11} {'KL':>11}"
    )
    for case in cases:
        print(render_case(case))
    print()


def print_theorem() -> None:
    print("== counting theorem ==")
    print("For a fixed public normalized cover distribution Q over all n-bit layers:")
    print()
    print("  E_uniform[-log2 Q(X)] = n + KL(U || Q) >= n")
    print()
    print("Therefore a collective cover code can beat a selected-cover witness for")
    print("some strings and still fail the roughly-all-data requirement. A source")
    print("with distribution close to Q can compress; uniform data cannot average")
    print("below raw without a hidden selector, residual, or unpriced normalizer.")
    print()


def print_parser_note() -> None:
    print("== why this is still Telomere-native ==")
    print("The latent cover is not decoded as a selected list of records. The decoder")
    print("arithmetic-decodes the previous layer under public Q, then the next reverse")
    print("layer proceeds from that layer. This is stateless and order-insensitive.")
    print("The cost is that Q is a public source model; it is not a uniform escape.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--atoms", type=int, default=None)
    parser.add_argument("--block-bits", type=int, default=1)
    parser.add_argument("--max-arity", type=int, default=4)
    parser.add_argument("--payload-depth", type=int, default=8)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.atoms is None:
        cases = DEFAULT_CASES
    else:
        cases = (Case(args.atoms, args.block_bits, args.max_arity, args.payload_depth),)
    print_exact_rows(cases)
    print_theorem()
    print_parser_note()


if __name__ == "__main__":
    main()
