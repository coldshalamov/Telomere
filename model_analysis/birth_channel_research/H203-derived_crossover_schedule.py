#!/usr/bin/env python3
"""H203 - decoder-derived crossover schedule.

H202 charged the crossover rank.  The obvious mutation is to make the
crossover schedule decoder-derived from the parent roots or digest-tail state:
no breakpoint or segment-parent rank is stored.

This kernel tests that mutation.  Each ordered parent tuple deterministically
chooses one crossover schedule, so the support is bounded by the number of
parent tuples.  The exact tiny rows enumerate the resulting recombinant
phenotypes; the large rows price the H198 bound.
"""

from __future__ import annotations

import argparse
import hashlib
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
    spec = importlib.util.spec_from_file_location("h198_native_developmental_tree_for_h203", H198_PATH)
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


def split_atoms(blob: bytes, atom_bits: int, leaves: int) -> tuple[bytes, ...]:
    if atom_bits % 8 != 0:
        raise ValueError("H203 exact enumeration uses byte-aligned atoms")
    atom_bytes = atom_bits // 8
    expected = atom_bytes * leaves
    if len(blob) == expected:
        return tuple(blob[i : i + atom_bytes] for i in range(0, len(blob), atom_bytes))
    if len(blob) % leaves != 0:
        raise ValueError(f"expected {expected} bytes, got {len(blob)}")
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


def digest_index(label: bytes, modulus: int, salt: int) -> int:
    if modulus <= 0:
        raise ValueError("modulus must be positive")
    digest = hashlib.blake2b(label + salt.to_bytes(2, "big"), digest_size=32).digest()
    return int.from_bytes(digest, "big") % modulus


def derived_schedule(
    *,
    roots: tuple[int, ...],
    root_bits: int,
    leaves: int,
    parent_count: int,
    crossovers: int,
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    breakpoints_all = list(itertools.combinations(range(1, leaves), crossovers))
    paths_all = parent_paths(parent_count, crossovers)
    root_bytes = b"".join(root.to_bytes((root_bits + 7) // 8 or 1, "big") for root in roots)
    label = (
        b"H203-derived-crossover\0"
        + root_bits.to_bytes(2, "big")
        + leaves.to_bytes(4, "big")
        + parent_count.to_bytes(2, "big")
        + crossovers.to_bytes(2, "big")
        + root_bytes
    )
    return (
        breakpoints_all[digest_index(label, len(breakpoints_all), 0)],
        paths_all[digest_index(label, len(paths_all), 1)],
    )


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
    parent_tuple_bits: int
    support: int
    support_log2: float
    paid_index_net: float
    native_fixed_bits: int
    native_stored_bits: int
    native_fixed_net: float
    native_stored_net: float
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
) -> ExactRow:
    leaves = branch**passes
    if crossovers > leaves - 1:
        raise ValueError("too many crossovers")
    pheno = phenotypes(
        root_bits=root_bits,
        cell_bits=cell_bits,
        atom_bits=atom_bits,
        branch=branch,
        passes=passes,
    )
    support: set[tuple[bytes, ...]] = set()
    for roots in itertools.product(range(len(pheno)), repeat=parent_count):
        breakpoints, path = derived_schedule(
            roots=roots,
            root_bits=root_bits,
            leaves=leaves,
            parent_count=parent_count,
            crossovers=crossovers,
        )
        parent_atoms = tuple(pheno[root] for root in roots)
        support.add(recombinant(parent_atoms, breakpoints, path))
    support_log2 = math.log2(len(support)) if support else -math.inf
    parent_tuple_bits = parent_count * root_bits
    root_record_bits = costs.record_cost_for_payload_width(branch, root_bits)
    pass_header = costs.lotus_cost_for_value(passes)
    native_fixed_bits = MODE_BITS + parent_count * root_record_bits
    native_stored_bits = MODE_BITS + pass_header + parent_count * root_record_bits
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
        parent_tuple_bits=parent_tuple_bits,
        support=len(support),
        support_log2=support_log2,
        paid_index_net=support_log2 - parent_tuple_bits,
        native_fixed_bits=native_fixed_bits,
        native_stored_bits=native_stored_bits,
        native_fixed_net=support_log2 - native_fixed_bits,
        native_stored_net=support_log2 - native_stored_bits,
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
    support_bound: int
    support_gap: int
    paid_index_net_bound: int
    native_fixed_net_bound: int
    native_stored_net_bound: int


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
    if crossovers > leaves - 1:
        raise ValueError("too many crossovers")
    root_record_bits = costs.record_cost_for_payload_width(branch, root_bits)
    pass_header = costs.lotus_cost_for_value(passes)
    support_bound = min(out_bits, parent_count * root_bits)
    return BoundRow(
        out_bits=out_bits,
        root_bits=root_bits,
        branch=branch,
        passes=passes,
        parent_count=parent_count,
        crossovers=crossovers,
        leaves=leaves,
        support_bound=support_bound,
        support_gap=max(0, out_bits - support_bound),
        paid_index_net_bound=support_bound - parent_count * root_bits,
        native_fixed_net_bound=support_bound - (MODE_BITS + parent_count * root_record_bits),
        native_stored_net_bound=support_bound
        - (MODE_BITS + pass_header + parent_count * root_record_bits),
    )


def print_exact(args: argparse.Namespace) -> None:
    parents = parse_int_list(args.parents, [2, 4])
    crossovers = parse_int_list(args.crossovers, [0, 1, 2, 3])
    print("== H203 exact decoder-derived crossover schedule ==")
    print("Each ordered parent tuple derives one public schedule from its root digest.")
    print(
        f"{'G':>3} {'C':>3} {'B':>3} {'A':>2} {'P':>2} {'p':>2} {'t':>2} "
        f"{'L':>3} {'N':>4} {'tuple':>6} {'supp':>8} {'logSupp':>9} "
        f"{'paidNet':>9} {'fixed':>6} {'fixNet':>9} {'stored':>6} {'stoNet':>9} {'gap':>9}"
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
            )
            print(
                f"{row.root_bits:3d} {row.cell_bits:3d} {row.atom_bits:3d} "
                f"{row.branch:2d} {row.passes:2d} {row.parent_count:2d} "
                f"{row.crossovers:2d} {row.leaves:3d} {row.out_bits:4d} "
                f"{row.parent_tuple_bits:6d} {row.support:8d} "
                f"{fmt(row.support_log2):>9} {fmt(row.paid_index_net):>9} "
                f"{row.native_fixed_bits:6d} {fmt(row.native_fixed_net):>9} "
                f"{row.native_stored_bits:6d} {fmt(row.native_stored_net):>9} "
                f"{fmt(row.support_gap):>9}"
            )


def print_bounds(args: argparse.Namespace) -> None:
    parents = parse_int_list(args.bound_parents, [2, 4])
    crossovers = parse_int_list(args.bound_crossovers, [0, 1, 2, 4, 8, 16, 32])
    print()
    print("== H203 large H198 derived-schedule bounds ==")
    print("The schedule is free because it is deterministic, so it adds no support rank.")
    print(
        f"{'N':>8} {'G':>3} {'A':>2} {'P':>2} {'p':>2} {'t':>3} {'L':>6} "
        f"{'suppBd':>8} {'gap':>8} {'paidNet':>9} {'fixedNet':>10} {'storedNet':>10}"
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
                f"{row.leaves:6d} {row.support_bound:8d} {row.support_gap:8d} "
                f"{fmt(row.paid_index_net_bound):>9} "
                f"{fmt(row.native_fixed_net_bound):>10} "
                f"{fmt(row.native_stored_net_bound):>10}"
            )


def print_theorem() -> None:
    print()
    print("== theorem ==")
    print("If a crossover schedule is a deterministic decoder-derived function")
    print("of the stored parent roots and public state, then each parent tuple")
    print("names at most one recombinant child.  Support is therefore bounded")
    print("by the parent tuple rank p*G.  The removed crossover-rank bill is")
    print("paid back as lost support, not as compression.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root-bits", type=int, default=3)
    parser.add_argument("--cell-bits", type=int, default=8)
    parser.add_argument("--atom-bits", type=int, default=8)
    parser.add_argument("--branch", type=int, default=2)
    parser.add_argument("--passes", type=int, default=2)
    parser.add_argument("--parents", action="append", default=[])
    parser.add_argument("--crossovers", action="append", default=[])
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
