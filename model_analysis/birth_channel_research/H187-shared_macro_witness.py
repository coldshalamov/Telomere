#!/usr/bin/env python3
"""H187 - shared macro-witness / batch seed accounting.

This kernel tests whether one witness can carry many spans and thereby alter
the paid row-mass bound.

For arbitrary uniform targets, a macro witness that emits T target bits and has
W seed/rank bits can name at most 2^W target tuples.  The hit fraction is
2^(W-T).  Sharing a witness can amortize parse/tier overhead, but it does not
create more target tuples than its rank bits name.

The honest useful mode is layer packing: store many independent seed ranks under
one public width/macro header.  That removes repeated Lotus overhead but leaves
the same witness supply.  H176 tests the recursive trellis version; this kernel
keeps the local accounting exact and small.
"""

from __future__ import annotations

import argparse
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


def ceil_log2(value: int) -> int:
    if value <= 1:
        return 0
    return (value - 1).bit_length()


def fixed_arity_bits(max_arity: int) -> int:
    return ceil_log2(max_arity)


@dataclass(frozen=True)
class MacroRow:
    spans: int
    target_bits_each: int
    rank_bits_each: int
    total_target_bits: int
    independent_v1_bits: int
    packed_layer_bits: int
    joint_seed_bits: int
    contiguous_fixed_bits: int
    packed_save_vs_independent: int
    joint_save_vs_independent: int
    packed_coverage_log2: int
    joint_coverage_log2: int
    repeated_paid_coverage_log2_p16: int
    verdict: str


def row(spans: int, target_bits_each: int, rank_bits_each: int) -> MacroRow:
    total_target_bits = spans * target_bits_each
    total_rank_bits = spans * rank_bits_each

    independent_v1 = spans * costs.record_cost_for_payload_width(1, rank_bits_each)
    width_header = costs.lotus_cost_for_value(rank_bits_each)
    packed_layer = spans * (costs.arity_cost(1) + rank_bits_each) + width_header

    # One joint seed/rank of width sum W_i.  It names the same number of target
    # tuples as the independent ranks, with only one Lotus tier/header.
    joint_seed = costs.arity_cost(1) + costs.j3d1_cost_for_payload_width(total_rank_bits)

    # Treat the whole batch as one contiguous fixed-arity record.  This is only
    # a fair comparison when spans are public/contiguous and max_arity>=spans.
    contiguous_fixed = fixed_arity_bits(spans) + costs.j3d1_cost_for_payload_width(total_rank_bits)

    packed_cov_log2 = total_rank_bits - total_target_bits
    joint_cov_log2 = total_rank_bits - total_target_bits
    repeated_paid_coverage_log2 = 16 * (joint_seed - total_target_bits)
    if joint_seed < packed_layer:
        verdict = "joint seed saves parse overhead only"
    elif packed_layer < independent_v1:
        verdict = "layer packing saves Lotus overhead only"
    else:
        verdict = "no local benefit"
    return MacroRow(
        spans=spans,
        target_bits_each=target_bits_each,
        rank_bits_each=rank_bits_each,
        total_target_bits=total_target_bits,
        independent_v1_bits=independent_v1,
        packed_layer_bits=packed_layer,
        joint_seed_bits=joint_seed,
        contiguous_fixed_bits=contiguous_fixed,
        packed_save_vs_independent=independent_v1 - packed_layer,
        joint_save_vs_independent=independent_v1 - joint_seed,
        packed_coverage_log2=packed_cov_log2,
        joint_coverage_log2=joint_cov_log2,
        repeated_paid_coverage_log2_p16=repeated_paid_coverage_log2,
        verdict=verdict,
    )


def print_table(args: argparse.Namespace) -> None:
    spans_values = parse_int_list(args.spans, [2, 4, 8, 16])
    target_values = parse_int_list(args.target_bits, [8, 16, 32])
    rank_values = parse_int_list(args.rank_bits, [4, 8, 12, 16])

    print("== H187 shared macro-witness / batch seed accounting ==")
    print(
        "Coverage log2 is W_total - T_total. Header savings do not change this hit fraction."
    )
    print(
        f"{'m':>3} {'T_i':>5} {'W_i':>5} {'T':>6} {'indV1':>7} "
        f"{'packed':>7} {'joint':>7} {'contig':>7} {'saveP':>6} "
        f"{'saveJ':>6} {'covLog':>7} {'P16log':>7} {'verdict':<38}"
    )
    for spans in spans_values:
        for target_bits in target_values:
            for rank_bits in rank_values:
                if spans * rank_bits > costs.MAX_PAYLOAD_WIDTH_BITS:
                    continue
                r = row(spans, target_bits, rank_bits)
                print(
                    f"{r.spans:3d} {r.target_bits_each:5d} {r.rank_bits_each:5d} "
                    f"{r.total_target_bits:6d} {r.independent_v1_bits:7d} "
                    f"{r.packed_layer_bits:7d} {r.joint_seed_bits:7d} "
                    f"{r.contiguous_fixed_bits:7d} {r.packed_save_vs_independent:6d} "
                    f"{r.joint_save_vs_independent:6d} {r.joint_coverage_log2:7d} "
                    f"{r.repeated_paid_coverage_log2_p16:7d} {r.verdict:<38}"
                )


def print_theorem() -> None:
    print()
    print("== theorem ==")
    print("A shared macro witness can amortize parse/tier overhead,")
    print("but a W-bit rank still names at most 2^W target tuples.")
    print("For T emitted target bits, arbitrary-data coverage is at most 2^(W-T).")
    print("Any apparent joint-seed boost beyond that is a generated/source promise,")
    print("an unpriced residual, or an overfull witness inventory.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spans", action="append", default=[])
    parser.add_argument("--target-bits", action="append", default=[])
    parser.add_argument("--rank-bits", action="append", default=[])
    args = parser.parse_args()

    print_table(args)
    print_theorem()


if __name__ == "__main__":
    main()
