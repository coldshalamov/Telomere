#!/usr/bin/env python3
"""H201 - multi-root generated superposition.

H199/H200 closed "one generated root + residual".  The next residual idea is
to make the residual itself generated: combine several H198 generated
phenotypes by XOR.  This is the natural linear/superposition version of the
generated tree.

For a codebook S of generated phenotypes, k-root XOR descriptions cover at most
the number of selected tuples/combinations.  If the selected roots are not
publicly fixed, their rank is a selector channel.  This kernel computes exact
small supports and large counting bounds under three prices:

    free_index      diagnostic hidden selector
    paid_index      ideal lower bound: log2(number of selections)
    native_records  k stored H198 root records
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
    spec = importlib.util.spec_from_file_location("h198_native_developmental_tree_for_h201", H198_PATH)
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


def gf2_rank(values: list[int], bits: int) -> int:
    basis: dict[int, int] = {}
    for value in values:
        x = value
        while x:
            pivot = x.bit_length() - 1
            if pivot not in basis:
                basis[pivot] = x
                break
            x ^= basis[pivot]
    return len(basis)


def log2_comb(n: int, k: int) -> float:
    if k < 0 or k > n:
        return -math.inf
    return math.log2(math.comb(n, k))


@dataclass(frozen=True)
class ExactRow:
    root_bits: int
    cell_bits: int
    atom_bits: int
    branch: int
    passes: int
    k: int
    out_bits: int
    roots: int
    unique_codewords: int
    rank: int
    xor_support: int
    xor_log2: float
    selection_log2: float
    native_bits: int
    free_net: float
    paid_index_net: float
    native_net: float
    full_span_net_paid: float
    full_span_net_native: float


def exact_row(
    *,
    root_bits: int,
    cell_bits: int,
    atom_bits: int,
    branch: int,
    passes: int,
    k: int,
    fixed_pass_count: bool,
) -> ExactRow:
    out_bits = atom_bits * (branch**passes)
    roots = 1 << root_bits
    codewords = [
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
    ]
    unique = sorted(set(codewords))
    support: set[int] = set()
    if k == 0:
        support.add(0)
    else:
        for combo in itertools.combinations(range(len(unique)), k):
            x = 0
            for idx in combo:
                x ^= unique[idx]
            support.add(x)
    selection_log2 = log2_comb(len(unique), k)
    pass_header = 0 if fixed_pass_count else costs.lotus_cost_for_value(passes)
    one_root_record = MODE_BITS + pass_header + costs.record_cost_for_payload_width(branch, root_bits)
    native_bits = k * one_root_record
    xor_log2 = math.log2(len(support)) if support else -math.inf
    rank = gf2_rank(unique, out_bits)
    full_span_log2 = min(rank, out_bits)
    return ExactRow(
        root_bits=root_bits,
        cell_bits=cell_bits,
        atom_bits=atom_bits,
        branch=branch,
        passes=passes,
        k=k,
        out_bits=out_bits,
        roots=roots,
        unique_codewords=len(unique),
        rank=rank,
        xor_support=len(support),
        xor_log2=xor_log2,
        selection_log2=selection_log2,
        native_bits=native_bits,
        free_net=xor_log2,
        paid_index_net=xor_log2 - selection_log2,
        native_net=xor_log2 - native_bits,
        full_span_net_paid=full_span_log2 - len(unique),
        full_span_net_native=full_span_log2 - (len(unique) * one_root_record),
    )


@dataclass(frozen=True)
class BoundRow:
    out_bits: int
    m_bits: int
    k: int
    native_root_bits: int
    tuple_log2: float
    unordered_log2: float
    span_dim_bound: int
    span_gap: int
    paid_tuple_net: float
    paid_unordered_net: float
    native_tuple_net: float
    full_span_bitmask_net: float


def bound_row(out_bits: int, m_bits: int, k: int, native_root_bits: int) -> BoundRow:
    m_count = 1 << m_bits
    tuple_log2 = k * m_bits
    unordered_log2 = log2_comb(m_count, k) if k <= 4096 else k * (m_bits - math.log2(max(1, k))) + 1.442695 * k
    span_dim = min(out_bits, m_count)
    return BoundRow(
        out_bits=out_bits,
        m_bits=m_bits,
        k=k,
        native_root_bits=native_root_bits,
        tuple_log2=tuple_log2,
        unordered_log2=unordered_log2,
        span_dim_bound=span_dim,
        span_gap=out_bits - span_dim,
        paid_tuple_net=tuple_log2 - tuple_log2,
        paid_unordered_net=unordered_log2 - unordered_log2,
        native_tuple_net=tuple_log2 - k * native_root_bits,
        full_span_bitmask_net=span_dim - m_count,
    )


def print_exact(args: argparse.Namespace) -> None:
    ks = parse_int_list(args.k, [1, 2, 3, 4, 8])
    print("== H201 exact multi-root XOR superposition ==")
    print("Exact rows use unique H198 generated codewords and unordered k-combinations.")
    print(
        f"{'G':>3} {'C':>3} {'B':>3} {'A':>2} {'P':>2} {'k':>3} {'N':>4} "
        f"{'uniq':>7} {'rank':>5} {'xor':>8} {'xorLog':>8} {'selLog':>8} "
        f"{'native':>7} {'paidNet':>9} {'natNet':>9}"
    )
    for k in ks:
        if k > (1 << args.root_bits):
            continue
        row = exact_row(
            root_bits=args.root_bits,
            cell_bits=args.cell_bits,
            atom_bits=args.atom_bits,
            branch=args.branch,
            passes=args.passes,
            k=k,
            fixed_pass_count=args.fixed_pass_count,
        )
        print(
            f"{row.root_bits:3d} {row.cell_bits:3d} {row.atom_bits:3d} "
            f"{row.branch:2d} {row.passes:2d} {row.k:3d} {row.out_bits:4d} "
            f"{row.unique_codewords:7d} {row.rank:5d} {row.xor_support:8d} "
            f"{fmt(row.xor_log2):>8} {fmt(row.selection_log2):>8} "
            f"{row.native_bits:7d} {fmt(row.paid_index_net):>9} "
            f"{fmt(row.native_net):>9}"
        )
    full = exact_row(
        root_bits=args.root_bits,
        cell_bits=args.cell_bits,
        atom_bits=args.atom_bits,
        branch=args.branch,
        passes=args.passes,
        k=1,
        fixed_pass_count=args.fixed_pass_count,
    )
    print()
    print(
        "full linear span diagnostic: "
        f"rank={full.rank}, span_support=2^{full.rank}, "
        f"bitmask_net={fmt(full.full_span_net_paid)}, "
        f"native_allroot_net={fmt(full.full_span_net_native)}"
    )


def print_bounds(args: argparse.Namespace) -> None:
    ks = parse_int_list(args.bound_k, [1, 2, 4, 8, 16, 32, 128])
    print()
    print("== large support/rank bounds ==")
    print(
        f"{'N':>8} {'m':>4} {'k':>5} {'native':>7} {'tupleLog':>10} "
        f"{'unordLog':>10} {'rankBd':>8} {'gap':>8} {'paidTuple':>10} "
        f"{'natTuple':>10} {'bitmask':>10}"
    )
    for k in ks:
        row = bound_row(args.bound_out_bits, args.bound_m_bits, k, args.bound_native_root_bits)
        print(
            f"{row.out_bits:8d} {row.m_bits:4d} {row.k:5d} "
            f"{row.native_root_bits:7d} {fmt(row.tuple_log2):>10} "
            f"{fmt(row.unordered_log2):>10} {row.span_dim_bound:8d} {row.span_gap:8d} "
            f"{fmt(row.paid_tuple_net):>10} {fmt(row.native_tuple_net):>10} "
            f"{fmt(row.full_span_bitmask_net):>10}"
        )


def print_theorem() -> None:
    print()
    print("== theorem ==")
    print("A k-root superposition has at most as many outputs as selected-root")
    print("descriptions. Paying the selected-root rank makes the ideal net <= 0;")
    print("native H198 root records subtract record overhead per root.")
    print("A full linear span can cover at most rank dimensions, but specifying")
    print("an arbitrary subset costs one bit per public codeword, so bitmask net")
    print("is rank - codebook_size <= 0.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root-bits", type=int, default=4)
    parser.add_argument("--cell-bits", type=int, default=8)
    parser.add_argument("--atom-bits", type=int, default=8)
    parser.add_argument("--branch", type=int, default=2)
    parser.add_argument("--passes", type=int, default=1)
    parser.add_argument("--k", action="append", default=[])
    parser.add_argument("--fixed-pass-count", action="store_true")
    parser.add_argument("--bound-out-bits", type=int, default=500_000)
    parser.add_argument("--bound-m-bits", type=int, default=16)
    parser.add_argument("--bound-native-root-bits", type=int, default=27)
    parser.add_argument("--bound-k", action="append", default=[])
    args = parser.parse_args()

    print_exact(args)
    print_bounds(args)
    print_theorem()


if __name__ == "__main__":
    main()
