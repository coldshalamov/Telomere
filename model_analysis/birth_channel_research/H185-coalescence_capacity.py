#!/usr/bin/env python3
"""H185 - variable-to-one coalescence capacity.

This kernel tests whether many-to-one survivor collapse can create maintained
stateless compression over arbitrary data.

If an N-bit layer is mapped into an L-bit coalesced state, the average preimage
multiplicity over any covered set is about 2^(N-L).  A lossless decoder needs
the residual branch inside that preimage unless the source is restricted to one
representative per cell.  For roughly-all uniform data, that residual cancels
the apparent survivor collapse.

The same count gives a finite-pass coverage bound:

    coverage <= 2^(L-N)

so saving s bits per pass for P passes can cover at most 2^(-P*s) of arbitrary
N-bit inputs unless residual/source tax is paid.
"""

from __future__ import annotations

import argparse
import hashlib
import math
import random
from dataclasses import dataclass


def stable_seed(*parts: object) -> int:
    digest = hashlib.blake2b(digest_size=16)
    for part in parts:
        digest.update(str(part).encode("ascii"))
        digest.update(b"\0")
    return int.from_bytes(digest.digest(), "big")


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


def fmt(value: float) -> str:
    if math.isinf(value):
        return "inf" if value > 0 else "-inf"
    if math.isnan(value):
        return "nan"
    if value == 0.0:
        return "0"
    if abs(value) >= 10_000.0 or abs(value) < 0.0001:
        return f"{value:.3e}"
    return f"{value:.6f}"


@dataclass(frozen=True)
class CoalescenceRow:
    input_bits: int
    saved_bits: int
    covered_fraction: float
    output_bits: int
    apparent_gain: int
    residual_bits: float
    source_tax: float
    paid_net: float
    coverage_ceiling: float
    verdict: str


@dataclass(frozen=True)
class PassRow:
    saving_per_pass: float
    passes: int
    total_saving: float
    max_coverage: float
    target_coverage: float
    can_cover_target: bool
    max_passes_for_target: float


@dataclass(frozen=True)
class TinyMapRow:
    input_bits: int
    output_bits: int
    covered_inputs: int
    cells_used: int
    mean_preimage: float
    max_preimage: int
    residual_lower_bound: float
    apparent_gain: int
    paid_net_lower_bound: float


def coalescence_row(input_bits: int, saved_bits: int, covered_fraction: float) -> CoalescenceRow:
    output_bits = input_bits - saved_bits
    if output_bits < 0:
        raise ValueError("saved_bits cannot exceed input_bits")
    if not 0.0 < covered_fraction <= 1.0:
        raise ValueError("covered_fraction must be in (0,1]")
    coverage_ceiling = min(1.0, 2.0 ** (-saved_bits))
    residual_bits = max(0.0, saved_bits + math.log2(covered_fraction))
    source_tax = -math.log2(covered_fraction)
    paid_net = saved_bits - residual_bits - source_tax
    if covered_fraction > coverage_ceiling + 1e-15:
        verdict = "impossible without residual/source channel"
    elif paid_net > 1e-12:
        verdict = "BUG: positive after residual and tax"
    elif abs(paid_net) <= 1e-12:
        verdict = "collapse exactly conserved"
    else:
        verdict = "negative after source tax"
    return CoalescenceRow(
        input_bits=input_bits,
        saved_bits=saved_bits,
        covered_fraction=covered_fraction,
        output_bits=output_bits,
        apparent_gain=saved_bits,
        residual_bits=residual_bits,
        source_tax=source_tax,
        paid_net=paid_net,
        coverage_ceiling=coverage_ceiling,
        verdict=verdict,
    )


def pass_row(saving_per_pass: float, passes: int, target_coverage: float) -> PassRow:
    total_saving = saving_per_pass * passes
    max_coverage = 2.0 ** (-total_saving)
    max_passes = -math.log2(target_coverage) / saving_per_pass if saving_per_pass > 0 else math.inf
    return PassRow(
        saving_per_pass=saving_per_pass,
        passes=passes,
        total_saving=total_saving,
        max_coverage=max_coverage,
        target_coverage=target_coverage,
        can_cover_target=max_coverage >= target_coverage,
        max_passes_for_target=max_passes,
    )


def tiny_random_map(input_bits: int, output_bits: int, covered_fraction: float, seed: int) -> TinyMapRow:
    if input_bits > 20:
        raise ValueError("tiny map is intentionally bounded to <=20 input bits")
    inputs = 1 << input_bits
    outputs = 1 << output_bits
    covered = max(1, min(inputs, round(inputs * covered_fraction)))
    rng = random.Random(stable_seed("H185", input_bits, output_bits, covered_fraction, seed))
    counts = [0] * outputs
    selected = rng.sample(range(inputs), covered)
    for value in selected:
        # A fixed public coalescer. The random draw only synthesizes a typical
        # occupancy profile; it is not a search over data.
        digest = stable_seed("cell", value, seed)
        counts[digest % outputs] += 1
    used = [count for count in counts if count]
    mean_preimage = covered / len(used) if used else 0.0
    max_preimage = max(used, default=0)
    residual = math.log2(mean_preimage) if mean_preimage > 0.0 else 0.0
    apparent = input_bits - output_bits
    return TinyMapRow(
        input_bits=input_bits,
        output_bits=output_bits,
        covered_inputs=covered,
        cells_used=len(used),
        mean_preimage=mean_preimage,
        max_preimage=max_preimage,
        residual_lower_bound=residual,
        apparent_gain=apparent,
        paid_net_lower_bound=apparent - residual - (-math.log2(covered / inputs)),
    )


def print_coalescence_table(args: argparse.Namespace) -> None:
    input_values = parse_int_list(args.input_bits, [64, 256, 4096])
    savings_values = parse_int_list(args.saved_bits, [1, 2, 4, 8, 16])
    coverage_values = parse_float_list(args.coverage, [1.0, 0.9, 0.5, 0.1, 0.01])

    print("== H185 variable-to-one coalescence capacity ==")
    print(
        "Residual lower bound is the preimage branch after covering fraction f; source tax is -log2(f)."
    )
    print(
        f"{'N':>6} {'s':>4} {'f':>8} {'L':>6} {'gain':>6} {'resid':>9} "
        f"{'tax':>9} {'paidNet':>9} {'fMax':>9} {'verdict':<42}"
    )
    for input_bits in input_values:
        for saved_bits in savings_values:
            if saved_bits > input_bits:
                continue
            for coverage in coverage_values:
                row = coalescence_row(input_bits, saved_bits, coverage)
                print(
                    f"{row.input_bits:6d} {row.saved_bits:4d} {fmt(row.covered_fraction):>8} "
                    f"{row.output_bits:6d} {row.apparent_gain:6d} {fmt(row.residual_bits):>9} "
                    f"{fmt(row.source_tax):>9} {fmt(row.paid_net):>9} "
                    f"{fmt(row.coverage_ceiling):>9} {row.verdict:<42}"
                )


def print_pass_table(args: argparse.Namespace) -> None:
    savings = parse_float_list(args.saving_per_pass, [0.01, 0.1, 0.5, 1.0, 2.0])
    passes_values = parse_int_list(args.passes, [1, 2, 4, 8, 16, 64, 256])
    targets = parse_float_list(args.target_coverage, [0.9, 0.5, 0.1])

    print()
    print("== finite-pass roughly-all coverage ceiling ==")
    print(
        f"{'s/pass':>8} {'P':>5} {'save':>9} {'fMax':>9} "
        f"{'target':>8} {'ok?':>5} {'Pmax':>9}"
    )
    for saving in savings:
        for target in targets:
            for passes in passes_values:
                row = pass_row(saving, passes, target)
                print(
                    f"{fmt(row.saving_per_pass):>8} {row.passes:5d} "
                    f"{fmt(row.total_saving):>9} {fmt(row.max_coverage):>9} "
                    f"{fmt(row.target_coverage):>8} {str(row.can_cover_target):>5} "
                    f"{fmt(row.max_passes_for_target):>9}"
                )


def print_tiny_map(args: argparse.Namespace) -> None:
    if args.tiny_input_bits <= 0:
        return
    row = tiny_random_map(args.tiny_input_bits, args.tiny_output_bits, args.tiny_coverage, args.seed)
    print()
    print("== tiny random coalescer occupancy check ==")
    print(
        f"N={row.input_bits} L={row.output_bits} covered={row.covered_inputs} "
        f"cells={row.cells_used} meanPre={fmt(row.mean_preimage)} "
        f"maxPre={row.max_preimage} residLB={fmt(row.residual_lower_bound)} "
        f"gain={row.apparent_gain} paidNetLB={fmt(row.paid_net_lower_bound)}"
    )


def print_theorem() -> None:
    print()
    print("== theorem ==")
    print("Many-to-one survivor collapse is not lossless by itself.")
    print("For arbitrary uniform data, either the residual preimage branch is stored,")
    print("or the source is restricted to one representative per cell and pays tax.")
    print("Maintained saving s over P passes can cover at most 2^(-P*s)")
    print("of all inputs unless that missing information is paid elsewhere.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-bits", action="append", default=[])
    parser.add_argument("--saved-bits", action="append", default=[])
    parser.add_argument("--coverage", action="append", default=[])
    parser.add_argument("--saving-per-pass", action="append", default=[])
    parser.add_argument("--passes", action="append", default=[])
    parser.add_argument("--target-coverage", action="append", default=[])
    parser.add_argument("--tiny-input-bits", type=int, default=12)
    parser.add_argument("--tiny-output-bits", type=int, default=8)
    parser.add_argument("--tiny-coverage", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=185185)
    args = parser.parse_args()

    print_coalescence_table(args)
    print_pass_table(args)
    print_tiny_map(args)
    print_theorem()


if __name__ == "__main__":
    main()
