#!/usr/bin/env python3
"""H198 - Telomere-native developmental seed tree.

H183 proved the generated/reachable branch with an arbitrary public expander.
H198 makes the construction more Telomere-shaped:

    root record -> branch child seed records -> ... -> leaf phenotype atoms

Every internal node is a seed-bearing record with exact current V1/J3D1 record
costs.  The decoder derives every child seed from the parent seed, depth, and
slot, so no pass/birth/open ledger is needed.  This gives a true positive
recursive regime inside the reachable class and prices the arbitrary-uniform
membership tax beside it.
"""

from __future__ import annotations

import argparse
import hashlib
import math
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model_analysis.proof_kernel import costs


MODE_BITS = 1


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


def int_to_bytes(value: int, bit_width: int) -> bytes:
    return value.to_bytes((bit_width + 7) // 8 or 1, "big")


def hash_int(label: bytes, bit_width: int) -> int:
    digest = hashlib.blake2b(label, digest_size=32).digest()
    value = int.from_bytes(digest, "big")
    return value & ((1 << bit_width) - 1)


def expand_bits(label: bytes, out_bits: int) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) * 8 < out_bits:
        digest = hashlib.blake2b(digest_size=32)
        digest.update(label)
        digest.update(counter.to_bytes(8, "big"))
        out.extend(digest.digest())
        counter += 1
    extra = len(out) * 8 - out_bits
    if extra:
        out[-1] &= (0xFF << extra) & 0xFF
    return bytes(out)


def child_seed(parent: int, parent_bits: int, child_bits: int, depth: int, slot: int) -> int:
    label = (
        b"H198-child\0"
        + depth.to_bytes(4, "big")
        + slot.to_bytes(2, "big")
        + parent_bits.to_bytes(2, "big")
        + int_to_bytes(parent, parent_bits)
    )
    return hash_int(label, child_bits)


def leaf_atom(seed: int, seed_bits: int, atom_bits: int, depth: int, slot_path: tuple[int, ...]) -> bytes:
    label = (
        b"H198-leaf\0"
        + depth.to_bytes(4, "big")
        + len(slot_path).to_bytes(2, "big")
        + bytes(slot_path)
        + seed_bits.to_bytes(2, "big")
        + int_to_bytes(seed, seed_bits)
    )
    return expand_bits(label, atom_bits)


def develop_leaves(
    *,
    root: int,
    root_bits: int,
    cell_bits: int,
    branch: int,
    passes: int,
    atom_bits: int,
) -> bytes:
    leaves: list[bytes] = []

    def visit(seed: int, seed_bits: int, depth: int, path: tuple[int, ...]) -> None:
        if depth == passes:
            leaves.append(leaf_atom(seed, seed_bits, atom_bits, depth, path))
            return
        for slot in range(branch):
            child = child_seed(seed, seed_bits, cell_bits, depth, slot)
            visit(child, cell_bits, depth + 1, path + (slot,))

    visit(root, root_bits, 0, ())
    return b"".join(leaves)


def pass_sizes(
    *,
    branch: int,
    passes: int,
    atom_bits: int,
    root_record_bits: int,
    internal_record_bits: int,
) -> list[int]:
    sizes = [branch**passes * atom_bits]
    for compressed_pass in range(1, passes):
        sizes.append(branch ** (passes - compressed_pass) * internal_record_bits)
    if passes > 0:
        sizes.append(root_record_bits)
    return sizes


@dataclass(frozen=True)
class Row:
    root_bits: int
    cell_bits: int
    atom_bits: int
    branch: int
    passes: int
    out_bits: int
    paid_bits: int
    root_record_bits: int
    internal_record_bits: int
    inside_gain: int
    reachable_tax_upper: int
    uniform_net_upper: int
    uniform_net_observed: float | None
    all_passes_shrink: bool
    min_step_gain: int
    log2_len_ratio: float
    unique_roots: int | None
    roots_tested: int
    roundtrip_ok: bool


def run_row(
    *,
    root_bits: int,
    cell_bits: int,
    atom_bits: int,
    branch: int,
    passes: int,
    include_pass_count: bool,
    max_enum_roots: int,
    max_enum_work_bits: int,
) -> Row:
    if branch < 1 or branch > 5:
        raise ValueError("current V1 arity supports branch 1..5")
    root_record_bits = costs.record_cost_for_payload_width(branch, root_bits)
    internal_record_bits = costs.record_cost_for_payload_width(branch, cell_bits)
    pass_header = costs.lotus_cost_for_value(passes) if include_pass_count else 0
    paid_bits = MODE_BITS + pass_header + root_record_bits
    sizes = pass_sizes(
        branch=branch,
        passes=passes,
        atom_bits=atom_bits,
        root_record_bits=root_record_bits,
        internal_record_bits=internal_record_bits,
    )
    step_gains = [before - after for before, after in zip(sizes, sizes[1:])]
    out_bits = sizes[0]
    inside_gain = out_bits - paid_bits
    reachable_tax_upper = out_bits - root_bits
    uniform_net_upper = inside_gain - reachable_tax_upper

    roots = 1 << root_bits
    roots_tested = min(roots, max_enum_roots)
    unique_roots: int | None = None
    uniform_net_observed: float | None = None
    if roots <= max_enum_roots and roots * out_bits <= max_enum_work_bits:
        seen = {
            develop_leaves(
                root=root,
                root_bits=root_bits,
                cell_bits=cell_bits,
                branch=branch,
                passes=passes,
                atom_bits=atom_bits,
            )
            for root in range(roots)
        }
        unique_roots = len(seen)
        support_log2 = math.log2(unique_roots) if unique_roots > 0 else -math.inf
        uniform_net_observed = inside_gain - (out_bits - support_log2)
    sample_root = min(roots - 1, roots // 3)
    a = develop_leaves(
        root=sample_root,
        root_bits=root_bits,
        cell_bits=cell_bits,
        branch=branch,
        passes=passes,
        atom_bits=atom_bits,
    )
    b = develop_leaves(
        root=sample_root,
        root_bits=root_bits,
        cell_bits=cell_bits,
        branch=branch,
        passes=passes,
        atom_bits=atom_bits,
    )
    return Row(
        root_bits=root_bits,
        cell_bits=cell_bits,
        atom_bits=atom_bits,
        branch=branch,
        passes=passes,
        out_bits=out_bits,
        paid_bits=paid_bits,
        root_record_bits=root_record_bits,
        internal_record_bits=internal_record_bits,
        inside_gain=inside_gain,
        reachable_tax_upper=reachable_tax_upper,
        uniform_net_upper=uniform_net_upper,
        uniform_net_observed=uniform_net_observed,
        all_passes_shrink=all(gain > 0 for gain in step_gains),
        min_step_gain=min(step_gains) if step_gains else 0,
        log2_len_ratio=math.log2(paid_bits / out_bits),
        unique_roots=unique_roots,
        roots_tested=roots_tested,
        roundtrip_ok=a == b,
    )


def print_table(args: argparse.Namespace) -> None:
    roots = parse_int_list(args.root_bits, [8, 12, 16])
    cells = parse_int_list(args.cell_bits, [8, 12, 16])
    atoms = parse_int_list(args.atom_bits, [16, 24, 32])
    branches = parse_int_list(args.branch, [2, 3, 4, 5])
    passes_values = parse_int_list(args.passes, [2, 4, 6])
    include_pass_count = not args.fixed_pass_count
    rows: list[Row] = []
    for root_bits in roots:
        for cell_bits in cells:
            for atom_bits in atoms:
                for branch in branches:
                    for passes in passes_values:
                        rows.append(
                            run_row(
                                root_bits=root_bits,
                                cell_bits=cell_bits,
                                atom_bits=atom_bits,
                                branch=branch,
                                passes=passes,
                                include_pass_count=include_pass_count,
                                max_enum_roots=args.max_enum_roots,
                                max_enum_work_bits=args.max_enum_work_bits,
                            )
                        )

    rows.sort(key=lambda r: (not r.all_passes_shrink, -r.inside_gain, r.uniform_net_upper))
    print("== H198 Telomere-native developmental seed tree ==")
    print("Root/internal records use exact current V1/J3D1 costs; branch is V1 arity.")
    print("uniform_net_upper subtracts the optimistic reachable-set tax out_bits-root_bits.")
    print(
        f"{'G':>3} {'C':>3} {'B':>3} {'A':>2} {'P':>2} {'out':>8} "
        f"{'paid':>5} {'rRec':>5} {'iRec':>5} {'gainIn':>8} {'tax':>8} "
        f"{'uNet':>6} {'uObs':>9} {'minStep':>8} {'shrink':>6} "
        f"{'log2len':>9} {'unique':>12} {'rt'}"
    )
    for row in rows[: args.limit]:
        unique = "sampled"
        if row.unique_roots is not None:
            unique = f"{row.unique_roots}/{row.roots_tested}"
        u_obs = "n/a" if row.uniform_net_observed is None else fmt(row.uniform_net_observed)
        print(
            f"{row.root_bits:3d} {row.cell_bits:3d} {row.atom_bits:3d} "
            f"{row.branch:2d} {row.passes:2d} {row.out_bits:8d} {row.paid_bits:5d} "
            f"{row.root_record_bits:5d} {row.internal_record_bits:5d} "
            f"{row.inside_gain:8d} {row.reachable_tax_upper:8d} "
            f"{row.uniform_net_upper:6d} {u_obs:>9} {row.min_step_gain:8d} "
            f"{str(row.all_passes_shrink):>6} {fmt(row.log2_len_ratio):>9} "
            f"{unique:>12} {row.roundtrip_ok}"
        )
    best_inside = max(rows, key=lambda r: r.inside_gain)
    best_uniform = max(rows, key=lambda r: r.uniform_net_upper)
    print()
    print(
        "best inside generated gain: "
        f"{best_inside.inside_gain} at G={best_inside.root_bits},C={best_inside.cell_bits},"
        f"B={best_inside.atom_bits},A={best_inside.branch},P={best_inside.passes}"
    )
    print(
        "best optimistic arbitrary-uniform net: "
        f"{best_uniform.uniform_net_upper} at G={best_uniform.root_bits},"
        f"C={best_uniform.cell_bits},B={best_uniform.atom_bits},"
        f"A={best_uniform.branch},P={best_uniform.passes}"
    )


def print_spec(args: argparse.Namespace) -> None:
    print()
    print("== exact decode spec ==")
    print("Header: H198 mode plus optional Lotus pass count.")
    print("Stored item: one root record [arity=branch][root witness].")
    print("For depth d and slot j, child seed = H(parent_seed,d,j) truncated to C bits.")
    print("Leaves emit B-bit atoms via H(leaf_seed,path).")
    print("All pass salts are path/depth/parent-derived; no birth/open/carry ledger exists.")


def print_theorem() -> None:
    print()
    print("== theorem ==")
    print("Inside the reachable class, H198 is maintained recursive compression:")
    print("each generated parent is a valid exact witness for its child bundle.")
    print("For arbitrary uniform data, support is at most 2^G final phenotypes,")
    print("so membership costs at least out_bits-G and cancels the root saving.")
    print("Native tree geometry preserves witness supply, but it does not remove")
    print("the reachable-set tax.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root-bits", action="append", default=[])
    parser.add_argument("--cell-bits", action="append", default=[])
    parser.add_argument("--atom-bits", action="append", default=[])
    parser.add_argument("--branch", action="append", default=[])
    parser.add_argument("--passes", action="append", default=[])
    parser.add_argument("--fixed-pass-count", action="store_true")
    parser.add_argument("--max-enum-roots", type=int, default=4096)
    parser.add_argument("--max-enum-work-bits", type=int, default=2_000_000)
    parser.add_argument("--limit", type=int, default=24)
    args = parser.parse_args()
    print_table(args)
    print_spec(args)
    print_theorem()


if __name__ == "__main__":
    main()
