#!/usr/bin/env python3
"""H199 - generated tree plus arbitrary residual attachment.

H198 gives maintained stateless recursion inside a generated/reachable class.
The next possible wedge is to encode arbitrary data as:

    generated root + residual from the generated phenotype to the target.

This kernel prices that residual exactly for tiny H198 codebooks.  The residual
language is a Hamming ball around each generated phenotype.  The same counting
applies to XOR masks, syndrome residuals, or nearest-codeword offsets: the
support of root/residual pairs is at most

    unique_generated_phenotypes * residual_count.

So, after paying the residual rank, the arbitrary-uniform net is bounded by the
root overhead.  Exact union coverage is computed for small N to catch overlap
and collision bills rather than assuming disjoint balls.
"""

from __future__ import annotations

import argparse
import importlib.util
import itertools
import math
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model_analysis.proof_kernel import costs


MODE_BITS = 1
H198_PATH = Path(__file__).with_name("H198-native_developmental_tree.py")


def load_h198():
    spec = importlib.util.spec_from_file_location("h198_native_developmental_tree", H198_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load H198 module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


H198 = load_h198()


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


def phenotype_int(
    *,
    root: int,
    root_bits: int,
    cell_bits: int,
    atom_bits: int,
    branch: int,
    passes: int,
    out_bits: int,
) -> int:
    blob = H198.develop_leaves(
        root=root,
        root_bits=root_bits,
        cell_bits=cell_bits,
        branch=branch,
        passes=passes,
        atom_bits=atom_bits,
    )
    value = int.from_bytes(blob, "big")
    extra = len(blob) * 8 - out_bits
    if extra > 0:
        value >>= extra
    return value & ((1 << out_bits) - 1)


def hamming_ball_masks(bits: int, radius: int) -> list[int]:
    masks = [0]
    positions = range(bits)
    for weight in range(1, radius + 1):
        for combo in itertools.combinations(positions, weight):
            mask = 0
            for pos in combo:
                mask |= 1 << pos
            masks.append(mask)
    return masks


def ball_size(bits: int, radius: int) -> int:
    return sum(math.comb(bits, weight) for weight in range(radius + 1))


def entropy_ball_approx(bits: int, radius: int) -> float:
    if radius < 0:
        return 0.0
    if radius >= bits:
        return float(bits)
    # Exact sum is fine for the modest N used here and avoids approximation
    # drift in the reported bill.
    return math.log2(ball_size(bits, radius))


@dataclass(frozen=True)
class ExactRow:
    root_bits: int
    cell_bits: int
    atom_bits: int
    branch: int
    passes: int
    radius: int
    out_bits: int
    paid_root_bits: int
    roots: int
    unique_roots: int
    residual_count: int
    residual_log2: float
    residual_ceil_bits: int
    covered: int
    covered_log2: float
    coverage: float
    ideal_net: float
    ceil_net: float
    pair_bound_net: float
    roundtrip_ok: bool


def exact_row(
    *,
    root_bits: int,
    cell_bits: int,
    atom_bits: int,
    branch: int,
    passes: int,
    radius: int,
    fixed_pass_count: bool,
) -> ExactRow:
    out_bits = atom_bits * (branch**passes)
    roots = 1 << root_bits
    pass_header = 0 if fixed_pass_count else costs.lotus_cost_for_value(passes)
    paid_root = MODE_BITS + pass_header + costs.record_cost_for_payload_width(branch, root_bits)
    codewords = {
        phenotype_int(
            root=root,
            root_bits=root_bits,
            cell_bits=cell_bits,
            atom_bits=atom_bits,
            branch=branch,
            passes=passes,
            out_bits=out_bits,
        )
        for root in range(roots)
    }
    masks = hamming_ball_masks(out_bits, radius)
    covered_set: set[int] = set()
    for codeword in codewords:
        for mask in masks:
            covered_set.add(codeword ^ mask)
    residual_count = len(masks)
    residual_log2 = math.log2(residual_count)
    residual_ceil = ceil_log2(residual_count)
    covered = len(covered_set)
    covered_log2 = math.log2(covered) if covered else -math.inf
    ideal_net = covered_log2 - paid_root - residual_log2
    ceil_net = covered_log2 - paid_root - residual_ceil
    pair_bound_net = math.log2(len(codewords)) - paid_root
    sample = next(iter(codewords))
    roundtrip_ok = sample in covered_set
    if ideal_net > pair_bound_net + 1e-9:
        raise AssertionError("residual union beat pair-count bound")
    return ExactRow(
        root_bits=root_bits,
        cell_bits=cell_bits,
        atom_bits=atom_bits,
        branch=branch,
        passes=passes,
        radius=radius,
        out_bits=out_bits,
        paid_root_bits=paid_root,
        roots=roots,
        unique_roots=len(codewords),
        residual_count=residual_count,
        residual_log2=residual_log2,
        residual_ceil_bits=residual_ceil,
        covered=covered,
        covered_log2=covered_log2,
        coverage=covered / (2**out_bits),
        ideal_net=ideal_net,
        ceil_net=ceil_net,
        pair_bound_net=pair_bound_net,
        roundtrip_ok=roundtrip_ok,
    )


@dataclass(frozen=True)
class BoundRow:
    out_bits: int
    root_bits: int
    paid_root_bits: int
    radius: int
    residual_log2: float
    union_bound_log2: float
    ideal_net_bound: float
    full_cover_gap: float


def bound_row(out_bits: int, root_bits: int, paid_root_bits: int, radius: int) -> BoundRow:
    residual_log2 = entropy_ball_approx(out_bits, radius)
    union_log2 = min(float(out_bits), root_bits + residual_log2)
    ideal_net = union_log2 - paid_root_bits - residual_log2
    return BoundRow(
        out_bits=out_bits,
        root_bits=root_bits,
        paid_root_bits=paid_root_bits,
        radius=radius,
        residual_log2=residual_log2,
        union_bound_log2=union_log2,
        ideal_net_bound=ideal_net,
        full_cover_gap=out_bits - union_log2,
    )


def print_exact(args: argparse.Namespace) -> None:
    radii = parse_int_list(args.radius, [0, 1, 2, 3, 4])
    print("== H199 exact H198 root + Hamming residual ==")
    print("Residual radius is public per row; residual bits are charged as log2(ball).")
    print(
        f"{'G':>3} {'C':>3} {'B':>3} {'A':>2} {'P':>2} {'r':>2} {'N':>4} "
        f"{'paid':>5} {'uniq':>8} {'Rcnt':>8} {'Rlog':>9} {'cover':>8} "
        f"{'covLog':>9} {'covFrac':>9} {'idealNet':>10} {'ceilNet':>10} "
        f"{'pairBd':>9} {'rt'}"
    )
    best: ExactRow | None = None
    for radius in radii:
        row = exact_row(
            root_bits=args.root_bits,
            cell_bits=args.cell_bits,
            atom_bits=args.atom_bits,
            branch=args.branch,
            passes=args.passes,
            radius=radius,
            fixed_pass_count=args.fixed_pass_count,
        )
        if best is None or row.ideal_net > best.ideal_net:
            best = row
        print(
            f"{row.root_bits:3d} {row.cell_bits:3d} {row.atom_bits:3d} "
            f"{row.branch:2d} {row.passes:2d} {row.radius:2d} {row.out_bits:4d} "
            f"{row.paid_root_bits:5d} {row.unique_roots:4d}/{row.roots:<3d} "
            f"{row.residual_count:8d} {fmt(row.residual_log2):>9} "
            f"{row.covered:8d} {fmt(row.covered_log2):>9} "
            f"{fmt(row.coverage):>9} {fmt(row.ideal_net):>10} "
            f"{fmt(row.ceil_net):>10} {fmt(row.pair_bound_net):>9} "
            f"{row.roundtrip_ok}"
        )
    if best is not None:
        print()
        print(
            "best exact residual net: "
            f"{fmt(best.ideal_net)} at radius={best.radius}; "
            f"pair-count bound={fmt(best.pair_bound_net)}"
        )


def print_bounds(args: argparse.Namespace) -> None:
    print()
    print("== pair-count support bound on larger H198 rows ==")
    out_bits = args.bound_out_bits
    paid = args.bound_paid_root_bits
    root_bits = args.bound_root_bits
    radii = parse_int_list(args.bound_radius, [0, 1, 2, 4, 8, 16, 32])
    print(
        f"{'N':>8} {'G':>4} {'paid':>5} {'r':>5} {'Rlog':>12} "
        f"{'unionLog':>12} {'gap':>12} {'netBound':>10}"
    )
    for radius in radii:
        row = bound_row(out_bits, root_bits, paid, radius)
        print(
            f"{row.out_bits:8d} {row.root_bits:4d} {row.paid_root_bits:5d} "
            f"{row.radius:5d} {fmt(row.residual_log2):>12} "
            f"{fmt(row.union_bound_log2):>12} {fmt(row.full_cover_gap):>12} "
            f"{fmt(row.ideal_net_bound):>10}"
        )


def print_theorem() -> None:
    print()
    print("== theorem ==")
    print("For root+residual pairs, support <= |roots| * |residuals|.")
    print("After paying the residual rank, arbitrary-uniform net is at most")
    print("log2(unique_roots) - paid_root_bits, before any collision/overlap bill.")
    print("Full coverage forces residual_log2 ~= N-log2(unique_roots), so it")
    print("cancels the reachable-set membership tax rather than beating it.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root-bits", type=int, default=4)
    parser.add_argument("--cell-bits", type=int, default=8)
    parser.add_argument("--atom-bits", type=int, default=8)
    parser.add_argument("--branch", type=int, default=2)
    parser.add_argument("--passes", type=int, default=1)
    parser.add_argument("--radius", action="append", default=[])
    parser.add_argument("--fixed-pass-count", action="store_true")
    parser.add_argument("--bound-out-bits", type=int, default=500_000)
    parser.add_argument("--bound-root-bits", type=int, default=16)
    parser.add_argument("--bound-paid-root-bits", type=int, default=27)
    parser.add_argument("--bound-radius", action="append", default=[])
    args = parser.parse_args()

    print_exact(args)
    print_bounds(args)
    print_theorem()


if __name__ == "__main__":
    main()
