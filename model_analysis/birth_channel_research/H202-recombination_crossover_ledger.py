#!/usr/bin/env python3
"""H202 - recombination / crossover selector ledger.

H198 gives a native generated tree.  H201 showed that XOR/sum superposition of
several generated trees is paid by selected-root rank.  This kernel tests the
more biological-looking mutation: store several generated parent roots plus a
crossover grammar over the leaf sequence.

The generous model charges:

    [mode][parent root records...][arithmetic-coded crossover rank]

Parent count and crossover count are fixed by the public mode in the lower
bound.  Charging them would only worsen the rows.  The exact tiny model
enumerates recombinant phenotypes; the large model reports the support/rank
ceiling for H198-scale rows.
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
    spec = importlib.util.spec_from_file_location("h198_native_developmental_tree_for_h202", H198_PATH)
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


def log2_comb(n: int, k: int) -> float:
    if k < 0 or k > n:
        return -math.inf
    if k == 0 or k == n:
        return 0.0
    return (math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)) / math.log(2.0)


def crossover_grammar_bits(leaves: int, parent_count: int, crossovers: int) -> float:
    """Ideal rank bits for a public t-crossover grammar.

    Choose t breakpoints among the L-1 interior boundaries, choose the first
    segment parent, then choose a different parent at each boundary.  For two
    parents this is exactly ``1 + log2 C(L-1,t)``.
    """

    if leaves < 1:
        raise ValueError("leaves must be positive")
    if parent_count < 1:
        raise ValueError("parent_count must be positive")
    if crossovers < 0 or crossovers > leaves - 1:
        return -math.inf
    if parent_count == 1 and crossovers > 0:
        return -math.inf
    if parent_count == 1:
        return log2_comb(leaves - 1, crossovers)
    return (
        log2_comb(leaves - 1, crossovers)
        + math.log2(parent_count)
        + crossovers * math.log2(parent_count - 1)
    )


def split_atoms(blob: bytes, atom_bits: int, leaves: int) -> tuple[bytes, ...]:
    if atom_bits % 8 != 0:
        raise ValueError("H202 exact enumeration uses byte-aligned atoms")
    atom_bytes = atom_bits // 8
    expected = atom_bytes * leaves
    if len(blob) == expected:
        return tuple(blob[i : i + atom_bytes] for i in range(0, len(blob), atom_bytes))
    if len(blob) % leaves != 0:
        raise ValueError(f"expected {expected} bytes, got {len(blob)}")
    # H198's expand_bits helper emits whole digest blocks, while the logical
    # ledger charges only the leading atom_bits from each leaf.
    leaf_bytes = len(blob) // leaves
    if leaf_bytes < atom_bytes:
        raise ValueError(f"leaf buffer too short: {leaf_bytes} < {atom_bytes}")
    return tuple(blob[i * leaf_bytes : i * leaf_bytes + atom_bytes] for i in range(leaves))


def phenotypes(
    *,
    root_bits: int,
    cell_bits: int,
    atom_bits: int,
    branch: int,
    passes: int,
) -> list[tuple[bytes, ...]]:
    leaves = branch**passes
    return [
        split_atoms(
            H198.develop_leaves(
                root=root,
                root_bits=root_bits,
                cell_bits=cell_bits,
                atom_bits=atom_bits,
                branch=branch,
                passes=passes,
            ),
            atom_bits,
            leaves,
        )
        for root in range(1 << root_bits)
    ]


def parent_paths(parent_count: int, crossovers: int) -> list[tuple[int, ...]]:
    if parent_count == 1:
        return [(0,)] if crossovers == 0 else []
    paths: list[tuple[int, ...]] = []

    def visit(path: tuple[int, ...]) -> None:
        if len(path) == crossovers + 1:
            paths.append(path)
            return
        for parent in range(parent_count):
            if parent != path[-1]:
                visit(path + (parent,))

    for start in range(parent_count):
        visit((start,))
    return paths


def recombinant(
    parent_atoms: tuple[tuple[bytes, ...], ...],
    breakpoints: tuple[int, ...],
    path: tuple[int, ...],
) -> tuple[bytes, ...]:
    leaves = len(parent_atoms[0])
    out: list[bytes] = []
    segment = 0
    next_break_idx = 0
    next_break = breakpoints[next_break_idx] if breakpoints else leaves + 1
    for leaf in range(leaves):
        while leaf == next_break:
            segment += 1
            next_break_idx += 1
            next_break = (
                breakpoints[next_break_idx] if next_break_idx < len(breakpoints) else leaves + 1
            )
        out.append(parent_atoms[path[segment]][leaf])
    return tuple(out)


@dataclass(frozen=True)
class ExactRow:
    root_bits: int
    cell_bits: int
    atom_bits: int
    branch: int
    passes: int
    parent_count: int
    crossovers: int
    leaves: int
    out_bits: int
    grammar_bits: float
    selection_bits: float
    support: int
    support_log2: float
    paid_index_net: float
    native_bits: float
    native_net: float
    support_gap: float


def exact_row(
    *,
    root_bits: int,
    cell_bits: int,
    atom_bits: int,
    branch: int,
    passes: int,
    parent_count: int,
    crossovers: int,
    fixed_pass_count: bool,
) -> ExactRow:
    leaves = branch**passes
    pheno = phenotypes(
        root_bits=root_bits,
        cell_bits=cell_bits,
        atom_bits=atom_bits,
        branch=branch,
        passes=passes,
    )
    grammar_bits = crossover_grammar_bits(leaves, parent_count, crossovers)
    if math.isinf(grammar_bits):
        raise ValueError("invalid crossover grammar")
    support: set[tuple[bytes, ...]] = set()
    paths = parent_paths(parent_count, crossovers)
    breakpoints_iter = list(itertools.combinations(range(1, leaves), crossovers))
    for roots in itertools.product(range(len(pheno)), repeat=parent_count):
        parent_atoms = tuple(pheno[root] for root in roots)
        for breakpoints in breakpoints_iter:
            for path in paths:
                support.add(recombinant(parent_atoms, breakpoints, path))
    support_log2 = math.log2(len(support)) if support else -math.inf
    selection_bits = parent_count * root_bits + grammar_bits
    pass_header = 0 if fixed_pass_count else costs.lotus_cost_for_value(passes)
    root_record_bits = costs.record_cost_for_payload_width(branch, root_bits)
    native_bits = MODE_BITS + pass_header + parent_count * root_record_bits + grammar_bits
    out_bits = atom_bits * leaves
    return ExactRow(
        root_bits=root_bits,
        cell_bits=cell_bits,
        atom_bits=atom_bits,
        branch=branch,
        passes=passes,
        parent_count=parent_count,
        crossovers=crossovers,
        leaves=leaves,
        out_bits=out_bits,
        grammar_bits=grammar_bits,
        selection_bits=selection_bits,
        support=len(support),
        support_log2=support_log2,
        paid_index_net=support_log2 - selection_bits,
        native_bits=native_bits,
        native_net=support_log2 - native_bits,
        support_gap=out_bits - support_log2,
    )


@dataclass(frozen=True)
class BoundRow:
    out_bits: int
    root_bits: int
    branch: int
    passes: int
    parent_count: int
    crossovers: int
    leaves: int
    grammar_bits: float
    support_bound: float
    support_gap: float
    paid_index_net_bound: float
    native_fixed_bits: float
    native_stored_bits: float
    native_fixed_net_bound: float
    native_stored_net_bound: float


def bound_row(
    *,
    out_bits: int,
    root_bits: int,
    branch: int,
    passes: int,
    parent_count: int,
    crossovers: int,
) -> BoundRow:
    leaves = branch**passes
    grammar_bits = crossover_grammar_bits(leaves, parent_count, crossovers)
    if math.isinf(grammar_bits):
        raise ValueError("invalid crossover grammar")
    root_record_bits = costs.record_cost_for_payload_width(branch, root_bits)
    pass_header = costs.lotus_cost_for_value(passes)
    support_bound = min(float(out_bits), parent_count * root_bits + grammar_bits)
    native_fixed_bits = MODE_BITS + parent_count * root_record_bits + grammar_bits
    native_stored_bits = MODE_BITS + pass_header + parent_count * root_record_bits + grammar_bits
    paid_index_bits = parent_count * root_bits + grammar_bits
    return BoundRow(
        out_bits=out_bits,
        root_bits=root_bits,
        branch=branch,
        passes=passes,
        parent_count=parent_count,
        crossovers=crossovers,
        leaves=leaves,
        grammar_bits=grammar_bits,
        support_bound=support_bound,
        support_gap=max(0.0, out_bits - support_bound),
        paid_index_net_bound=support_bound - paid_index_bits,
        native_fixed_bits=native_fixed_bits,
        native_stored_bits=native_stored_bits,
        native_fixed_net_bound=support_bound - native_fixed_bits,
        native_stored_net_bound=support_bound - native_stored_bits,
    )


def print_exact(args: argparse.Namespace) -> None:
    parents = parse_int_list(args.parents, [2, 4])
    crossovers = parse_int_list(args.crossovers, [0, 1, 2, 3])
    print("== H202 exact recombinant support ==")
    print("Exact rows enumerate H198 phenotypes, ordered parent roots, breakpoints, and segment paths.")
    print(
        f"{'G':>3} {'C':>3} {'B':>3} {'A':>2} {'P':>2} {'p':>2} {'t':>2} "
        f"{'L':>3} {'N':>4} {'gram':>9} {'sel':>9} {'supp':>8} "
        f"{'logSupp':>9} {'paidNet':>9} {'native':>9} {'natNet':>9} {'gap':>9}"
    )
    for parent_count in parents:
        for t in crossovers:
            if t > args.branch**args.passes - 1:
                continue
            row = exact_row(
                root_bits=args.root_bits,
                cell_bits=args.cell_bits,
                atom_bits=args.atom_bits,
                branch=args.branch,
                passes=args.passes,
                parent_count=parent_count,
                crossovers=t,
                fixed_pass_count=args.fixed_pass_count,
            )
            print(
                f"{row.root_bits:3d} {row.cell_bits:3d} {row.atom_bits:3d} "
                f"{row.branch:2d} {row.passes:2d} {row.parent_count:2d} "
                f"{row.crossovers:2d} {row.leaves:3d} {row.out_bits:4d} "
                f"{fmt(row.grammar_bits):>9} {fmt(row.selection_bits):>9} "
                f"{row.support:8d} {fmt(row.support_log2):>9} "
                f"{fmt(row.paid_index_net):>9} {fmt(row.native_bits):>9} "
                f"{fmt(row.native_net):>9} {fmt(row.support_gap):>9}"
            )


def print_bounds(args: argparse.Namespace) -> None:
    parents = parse_int_list(args.bound_parents, [2, 4])
    crossovers = parse_int_list(args.bound_crossovers, [0, 1, 2, 4, 8, 16, 32])
    print()
    print("== H202 large H198 crossover bounds ==")
    print("Support bound is intentionally generous: parent root rank + crossover rank.")
    print(
        f"{'N':>8} {'G':>3} {'A':>2} {'P':>2} {'p':>2} {'t':>3} {'L':>6} "
        f"{'gram':>10} {'suppBd':>10} {'gap':>10} {'paidNet':>9} "
        f"{'fixedNet':>10} {'storedNet':>10}"
    )
    for parent_count in parents:
        for t in crossovers:
            if t > args.bound_branch**args.bound_passes - 1:
                continue
            row = bound_row(
                out_bits=args.bound_out_bits,
                root_bits=args.bound_root_bits,
                branch=args.bound_branch,
                passes=args.bound_passes,
                parent_count=parent_count,
                crossovers=t,
            )
            print(
                f"{row.out_bits:8d} {row.root_bits:3d} {row.branch:2d} "
                f"{row.passes:2d} {row.parent_count:2d} {row.crossovers:3d} "
                f"{row.leaves:6d} {fmt(row.grammar_bits):>10} "
                f"{fmt(row.support_bound):>10} {fmt(row.support_gap):>10} "
                f"{fmt(row.paid_index_net_bound):>9} "
                f"{fmt(row.native_fixed_net_bound):>10} "
                f"{fmt(row.native_stored_net_bound):>10}"
            )


def print_theorem() -> None:
    print()
    print("== theorem ==")
    print("A recombinant child is determined by parent roots plus crossover rank.")
    print("Therefore support_bits <= parent_root_bits + crossover_rank_bits.")
    print("Paying the ideal parent/rank selector makes paid-index net <= 0.")
    print("Native H198 parent records subtract the Lotus/root overhead per parent:")
    print("native_net <= p*G - (mode + p*record_cost + optional_pass_header).")
    print("Extra breakpoints can increase support, but the same breakpoint rank")
    print("is exactly the decoder bill unless it is public/fixed.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root-bits", type=int, default=3)
    parser.add_argument("--cell-bits", type=int, default=8)
    parser.add_argument("--atom-bits", type=int, default=8)
    parser.add_argument("--branch", type=int, default=2)
    parser.add_argument("--passes", type=int, default=2)
    parser.add_argument("--parents", action="append", default=[])
    parser.add_argument("--crossovers", action="append", default=[])
    parser.add_argument("--fixed-pass-count", action="store_true")
    parser.add_argument("--bound-out-bits", type=int, default=500_000)
    parser.add_argument("--bound-root-bits", type=int, default=16)
    parser.add_argument("--bound-branch", type=int, default=5)
    parser.add_argument("--bound-passes", type=int, default=6)
    parser.add_argument("--bound-parents", action="append", default=[])
    parser.add_argument("--bound-crossovers", action="append", default=[])
    args = parser.parse_args()

    print_exact(args)
    print_bounds(args)
    print_theorem()


if __name__ == "__main__":
    main()
