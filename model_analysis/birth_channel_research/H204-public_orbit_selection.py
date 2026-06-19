#!/usr/bin/env python3
"""H204 - public recombination orbit with visible selection.

H203 made one crossover schedule decoder-derived.  The next biological mutation
is a public orbit of schedules plus a visible accept/reject law:

    candidates_j = Recombine(parent_tuple, schedule_j)
    accept_j = F(candidates_j)

If the decoder chooses the first accepted candidate, the schedule is free but
there is still at most one child per parent tuple.  If the encoder chooses an
accepted candidate, the accepted index is a selector.  This kernel reports both
ledgers.
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
    spec = importlib.util.spec_from_file_location("h198_native_developmental_tree_for_h204", H198_PATH)
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
        raise ValueError("H204 exact enumeration uses byte-aligned atoms")
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
    paths: list[tuple[int, ...]] = []

    def visit(path: tuple[int, ...]) -> None:
        if len(path) == crossovers + 1:
            paths.append(path)
            return
        for parent in range(parent_count):
            if not path or parent != path[-1]:
                visit(path + (parent,))

    visit(())
    return paths


def digest_index(label: bytes, modulus: int, salt: int) -> int:
    digest = hashlib.blake2b(label + salt.to_bytes(4, "big"), digest_size=32).digest()
    return int.from_bytes(digest, "big") % modulus


def orbit_schedule(
    *,
    roots: tuple[int, ...],
    root_bits: int,
    leaves: int,
    parent_count: int,
    crossovers: int,
    orbit_index: int,
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    breakpoints_all = list(itertools.combinations(range(1, leaves), crossovers))
    paths_all = parent_paths(parent_count, crossovers)
    root_bytes = b"".join(root.to_bytes((root_bits + 7) // 8 or 1, "big") for root in roots)
    label = (
        b"H204-public-orbit\0"
        + root_bits.to_bytes(2, "big")
        + leaves.to_bytes(4, "big")
        + parent_count.to_bytes(2, "big")
        + crossovers.to_bytes(2, "big")
        + orbit_index.to_bytes(4, "big")
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


def prefix_zero(child: tuple[bytes, ...], zero_bits: int, out_bits: int) -> bool:
    if zero_bits <= 0:
        return True
    blob = b"".join(child)
    value = int.from_bytes(blob, "big")
    return (value >> (out_bits - zero_bits)) == 0


@dataclass(frozen=True)
class ExactRow:
    root_bits: int
    atom_bits: int
    branch: int
    passes: int
    parent_count: int
    crossovers: int
    orbit_size: int
    zero_bits: int
    out_bits: int
    parent_tuple_bits: int
    accepted_choices: int
    tuples_with_accept: int
    canonical_support: int
    canonical_log2: float
    canonical_paid_net: float
    indexed_support: int
    indexed_log2: float
    indexed_selector_log2: float
    indexed_paid_net: float
    native_first_net: float
    native_index_net: float


def exact_row(
    *,
    root_bits: int,
    cell_bits: int,
    atom_bits: int,
    branch: int,
    passes: int,
    parent_count: int,
    crossovers: int,
    orbit_size: int,
    zero_bits: int,
) -> ExactRow:
    leaves = branch**passes
    if crossovers > leaves - 1:
        raise ValueError("too many crossovers")
    out_bits = atom_bits * leaves
    pheno = phenotypes(
        root_bits=root_bits,
        cell_bits=cell_bits,
        atom_bits=atom_bits,
        branch=branch,
        passes=passes,
    )
    canonical_support: set[tuple[bytes, ...]] = set()
    indexed_support: set[tuple[bytes, ...]] = set()
    accepted_choices = 0
    tuples_with_accept = 0
    for roots in itertools.product(range(len(pheno)), repeat=parent_count):
        parent_atoms = tuple(pheno[root] for root in roots)
        first: tuple[bytes, ...] | None = None
        for j in range(orbit_size):
            breakpoints, path = orbit_schedule(
                roots=roots,
                root_bits=root_bits,
                leaves=leaves,
                parent_count=parent_count,
                crossovers=crossovers,
                orbit_index=j,
            )
            child = recombinant(parent_atoms, breakpoints, path)
            if prefix_zero(child, zero_bits, out_bits):
                accepted_choices += 1
                indexed_support.add(child)
                if first is None:
                    first = child
        if first is not None:
            tuples_with_accept += 1
            canonical_support.add(first)
    parent_tuple_bits = parent_count * root_bits
    canonical_log2 = math.log2(len(canonical_support)) if canonical_support else -math.inf
    indexed_log2 = math.log2(len(indexed_support)) if indexed_support else -math.inf
    indexed_selector_log2 = math.log2(accepted_choices) if accepted_choices else -math.inf
    root_record_bits = costs.record_cost_for_payload_width(branch, root_bits)
    native_first_bits = MODE_BITS + parent_count * root_record_bits
    native_index_bits = native_first_bits + math.log2(orbit_size)
    return ExactRow(
        root_bits=root_bits,
        atom_bits=atom_bits,
        branch=branch,
        passes=passes,
        parent_count=parent_count,
        crossovers=crossovers,
        orbit_size=orbit_size,
        zero_bits=zero_bits,
        out_bits=out_bits,
        parent_tuple_bits=parent_tuple_bits,
        accepted_choices=accepted_choices,
        tuples_with_accept=tuples_with_accept,
        canonical_support=len(canonical_support),
        canonical_log2=canonical_log2,
        canonical_paid_net=canonical_log2 - parent_tuple_bits,
        indexed_support=len(indexed_support),
        indexed_log2=indexed_log2,
        indexed_selector_log2=indexed_selector_log2,
        indexed_paid_net=indexed_log2 - indexed_selector_log2,
        native_first_net=canonical_log2 - native_first_bits,
        native_index_net=indexed_log2 - native_index_bits,
    )


@dataclass(frozen=True)
class BoundRow:
    out_bits: int
    root_bits: int
    branch: int
    passes: int
    parent_count: int
    orbit_size: int
    zero_bits: int
    accept_any_log2: float
    canonical_support_bound: float
    indexed_support_bound: float
    canonical_native_net: float
    indexed_native_net: float


def log2_accept_any(orbit_size: int, zero_bits: int) -> float:
    q = 2.0 ** (-zero_bits)
    any_q = 1.0 - (1.0 - q) ** orbit_size
    if any_q <= 0.0:
        return -math.inf
    return math.log2(any_q)


def bound_row(
    *,
    out_bits: int,
    root_bits: int,
    branch: int,
    passes: int,
    parent_count: int,
    orbit_size: int,
    zero_bits: int,
) -> BoundRow:
    root_record_bits = costs.record_cost_for_payload_width(branch, root_bits)
    parent_bits = parent_count * root_bits
    accept_any = log2_accept_any(orbit_size, zero_bits)
    canonical_support = min(float(out_bits), parent_bits + accept_any)
    indexed_support = min(float(out_bits), parent_bits + math.log2(orbit_size) - zero_bits)
    native_first_bits = MODE_BITS + parent_count * root_record_bits
    native_index_bits = native_first_bits + math.log2(orbit_size)
    return BoundRow(
        out_bits=out_bits,
        root_bits=root_bits,
        branch=branch,
        passes=passes,
        parent_count=parent_count,
        orbit_size=orbit_size,
        zero_bits=zero_bits,
        accept_any_log2=accept_any,
        canonical_support_bound=canonical_support,
        indexed_support_bound=indexed_support,
        canonical_native_net=canonical_support - native_first_bits,
        indexed_native_net=indexed_support - native_index_bits,
    )


def print_exact(args: argparse.Namespace) -> None:
    parents = parse_int_list(args.parents, [2])
    orbits = parse_int_list(args.orbit_size, [1, 4, 16])
    zeros = parse_int_list(args.zero_bits, [0, 1, 2])
    print("== H204 exact public orbit selection ==")
    print("canon = first accepted candidate, no index. indexed = chosen accepted candidate, index paid.")
    print(
        f"{'G':>3} {'B':>3} {'A':>2} {'P':>2} {'p':>2} {'t':>2} {'S':>3} {'z':>2} "
        f"{'acc':>6} {'okT':>5} {'canLog':>8} {'canNet':>8} "
        f"{'idxLog':>8} {'idxSel':>8} {'idxNet':>8} {'natCan':>8} {'natIdx':>8}"
    )
    for parent_count in parents:
        for orbit_size in orbits:
            for zero_bits in zeros:
                row = exact_row(
                    root_bits=args.root_bits,
                    cell_bits=args.cell_bits,
                    atom_bits=args.atom_bits,
                    branch=args.branch,
                    passes=args.passes,
                    parent_count=parent_count,
                    crossovers=args.crossovers,
                    orbit_size=orbit_size,
                    zero_bits=zero_bits,
                )
                print(
                    f"{row.root_bits:3d} {row.atom_bits:3d} {row.branch:2d} "
                    f"{row.passes:2d} {row.parent_count:2d} {row.crossovers:2d} "
                    f"{row.orbit_size:3d} {row.zero_bits:2d} "
                    f"{row.accepted_choices:6d} {row.tuples_with_accept:5d} "
                    f"{fmt(row.canonical_log2):>8} {fmt(row.canonical_paid_net):>8} "
                    f"{fmt(row.indexed_log2):>8} {fmt(row.indexed_selector_log2):>8} "
                    f"{fmt(row.indexed_paid_net):>8} {fmt(row.native_first_net):>8} "
                    f"{fmt(row.native_index_net):>8}"
                )


def print_bounds(args: argparse.Namespace) -> None:
    parents = parse_int_list(args.bound_parents, [2, 4])
    orbits = parse_int_list(args.bound_orbit_size, [1, 4, 16, 256])
    zeros = parse_int_list(args.bound_zero_bits, [0, 1, 4, 8])
    print()
    print("== H204 large H198 orbit-selection bounds ==")
    print(
        f"{'N':>8} {'G':>3} {'p':>2} {'S':>4} {'z':>2} {'logAny':>8} "
        f"{'canSupp':>8} {'idxSupp':>8} {'natCan':>8} {'natIdx':>8}"
    )
    for parent_count in parents:
        for orbit_size in orbits:
            for zero_bits in zeros:
                row = bound_row(
                    out_bits=args.bound_out_bits,
                    root_bits=args.bound_root_bits,
                    branch=args.bound_branch,
                    passes=args.bound_passes,
                    parent_count=parent_count,
                    orbit_size=orbit_size,
                    zero_bits=zero_bits,
                )
                print(
                    f"{row.out_bits:8d} {row.root_bits:3d} {row.parent_count:2d} "
                    f"{row.orbit_size:4d} {row.zero_bits:2d} "
                    f"{fmt(row.accept_any_log2):>8} {fmt(row.canonical_support_bound):>8} "
                    f"{fmt(row.indexed_support_bound):>8} "
                    f"{fmt(row.canonical_native_net):>8} "
                    f"{fmt(row.indexed_native_net):>8}"
                )


def print_theorem() -> None:
    print()
    print("== theorem ==")
    print("Canonical visible selection chooses at most one child per parent tuple,")
    print("so it cannot exceed p*G support and usually thins it.  Indexed")
    print("selection can use the orbit, but the accepted index/rank is the")
    print("decoder bill; native records keep the same parent-root overhead.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root-bits", type=int, default=3)
    parser.add_argument("--cell-bits", type=int, default=8)
    parser.add_argument("--atom-bits", type=int, default=8)
    parser.add_argument("--branch", type=int, default=2)
    parser.add_argument("--passes", type=int, default=2)
    parser.add_argument("--parents", action="append", default=[])
    parser.add_argument("--crossovers", type=int, default=1)
    parser.add_argument("--orbit-size", action="append", default=[])
    parser.add_argument("--zero-bits", action="append", default=[])
    parser.add_argument("--bound-out-bits", type=int, default=500_000)
    parser.add_argument("--bound-root-bits", type=int, default=16)
    parser.add_argument("--bound-branch", type=int, default=5)
    parser.add_argument("--bound-passes", type=int, default=6)
    parser.add_argument("--bound-parents", action="append", default=[])
    parser.add_argument("--bound-orbit-size", action="append", default=[])
    parser.add_argument("--bound-zero-bits", action="append", default=[])
    args = parser.parse_args()

    print_exact(args)
    print_bounds(args)
    print_theorem()


if __name__ == "__main__":
    main()
