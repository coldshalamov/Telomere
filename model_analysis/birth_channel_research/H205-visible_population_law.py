#!/usr/bin/env python3
"""H205 - visible population / neutral-allele generated law.

H202-H204 close recombination as an arbitrary residual mechanism.  This kernel
keeps the biology analogy but changes the claim boundary: store a visible final
population of seed records, then let decode deterministically derive the whole
lineage from those records.  Parent choices, crossover schedules, salts, and
child seeds are inherited state, not selected metadata.

This is a generated/reachable positive regime.  The arbitrary-uniform
membership tax is reported explicitly.
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


def hash_bits(label: bytes, bit_width: int) -> int:
    digest = hashlib.blake2b(label, digest_size=32).digest()
    return int.from_bytes(digest, "big") & ((1 << bit_width) - 1)


def leaf_bits(seed: int, seed_bits: int, atom_bits: int, label: bytes) -> int:
    return hash_bits(label + seed_bits.to_bytes(2, "big") + int_to_bytes(seed, seed_bits), atom_bits)


def children(
    *,
    population: tuple[int, ...],
    seed_bits: int,
    child_bits: int,
    branch: int,
    pass_index: int,
    slot_base: int,
) -> tuple[int, ...]:
    """Derive child seeds from the visible population and public position.

    This is intentionally a public inherited law, not an encoder-selected
    parent/crossover channel.  It mixes two digest-derived parents per child.
    """

    m = len(population)
    pop_blob = b"".join(int_to_bytes(seed, seed_bits) for seed in population)
    out: list[int] = []
    for slot in range(branch):
        label = (
            b"H205-child\0"
            + pass_index.to_bytes(4, "big")
            + slot_base.to_bytes(8, "big")
            + slot.to_bytes(2, "big")
            + pop_blob
        )
        i = hash_bits(label + b"i", max(1, math.ceil(math.log2(m)))) % m
        j = hash_bits(label + b"j", max(1, math.ceil(math.log2(m)))) % m
        mix = population[i] ^ ((population[j] << 1) & ((1 << seed_bits) - 1)) ^ slot
        child = hash_bits(label + int_to_bytes(mix, seed_bits), child_bits)
        out.append(child)
    return tuple(out)


def develop_population(
    *,
    roots: tuple[int, ...],
    root_bits: int,
    cell_bits: int,
    atom_bits: int,
    branch: int,
    passes: int,
) -> tuple[int, ...]:
    population = tuple(roots)
    seed_bits = root_bits
    slot_span = 1
    for pass_index in range(passes):
        next_population: list[int] = []
        for idx in range(len(population)):
            child_pop = children(
                population=population,
                seed_bits=seed_bits,
                child_bits=cell_bits,
                branch=branch,
                pass_index=pass_index,
                slot_base=idx * slot_span,
            )
            next_population.extend(child_pop)
        population = tuple(next_population)
        seed_bits = cell_bits
        slot_span *= branch
    atoms: list[int] = []
    for idx, seed in enumerate(population):
        label = b"H205-leaf\0" + idx.to_bytes(8, "big")
        atoms.append(leaf_bits(seed, cell_bits, atom_bits, label))
    return tuple(atoms)


def log2_unique_support(
    *,
    root_bits: int,
    cell_bits: int,
    atom_bits: int,
    branch: int,
    passes: int,
    population_size: int,
    max_enum_tuples: int,
    max_enum_work_bits: int,
) -> tuple[int | None, float | None, int]:
    total = 1 << (population_size * root_bits)
    out_bits = population_size * (branch**passes) * atom_bits
    if total > max_enum_tuples or total * out_bits > max_enum_work_bits:
        return None, None, total
    seen: set[tuple[int, ...]] = set()
    for rank in range(total):
        roots = tuple((rank >> (root_bits * i)) & ((1 << root_bits) - 1) for i in range(population_size))
        seen.add(
            develop_population(
                roots=roots,
                root_bits=root_bits,
                cell_bits=cell_bits,
                atom_bits=atom_bits,
                branch=branch,
                passes=passes,
            )
        )
    return len(seen), math.log2(len(seen)) if seen else -math.inf, total


@dataclass(frozen=True)
class Row:
    population_size: int
    root_bits: int
    cell_bits: int
    atom_bits: int
    branch: int
    passes: int
    out_bits: int
    paid_bits: int
    root_record_bits: int
    inside_gain: int
    reachable_tax_upper: int
    uniform_net_upper: int
    min_step_gain: int
    all_passes_shrink: bool
    unique: int | None
    support_log2: float | None
    enum_total: int
    observed_uniform_net: float | None


def pass_sizes(
    *,
    population_size: int,
    branch: int,
    passes: int,
    atom_bits: int,
    root_record_bits: int,
    internal_record_bits: int,
) -> list[int]:
    sizes = [population_size * (branch**passes) * atom_bits]
    for compressed_pass in range(1, passes):
        sizes.append(population_size * (branch ** (passes - compressed_pass)) * internal_record_bits)
    if passes > 0:
        sizes.append(population_size * root_record_bits)
    return sizes


def run_row(
    *,
    population_size: int,
    root_bits: int,
    cell_bits: int,
    atom_bits: int,
    branch: int,
    passes: int,
    max_enum_tuples: int,
    max_enum_work_bits: int,
) -> Row:
    root_record_bits = costs.record_cost_for_payload_width(branch, root_bits)
    internal_record_bits = costs.record_cost_for_payload_width(branch, cell_bits)
    paid_bits = MODE_BITS + population_size * root_record_bits
    out_bits = population_size * (branch**passes) * atom_bits
    inside_gain = out_bits - paid_bits
    support_bits_upper = population_size * root_bits
    reachable_tax_upper = out_bits - support_bits_upper
    uniform_net_upper = inside_gain - reachable_tax_upper
    sizes = pass_sizes(
        population_size=population_size,
        branch=branch,
        passes=passes,
        atom_bits=atom_bits,
        root_record_bits=root_record_bits,
        internal_record_bits=internal_record_bits,
    )
    step_gains = [before - after for before, after in zip(sizes, sizes[1:])]
    unique, support_log2, enum_total = log2_unique_support(
        root_bits=root_bits,
        cell_bits=cell_bits,
        atom_bits=atom_bits,
        branch=branch,
        passes=passes,
        population_size=population_size,
        max_enum_tuples=max_enum_tuples,
        max_enum_work_bits=max_enum_work_bits,
    )
    observed_uniform_net = None
    if support_log2 is not None:
        observed_uniform_net = inside_gain - (out_bits - support_log2)
    return Row(
        population_size=population_size,
        root_bits=root_bits,
        cell_bits=cell_bits,
        atom_bits=atom_bits,
        branch=branch,
        passes=passes,
        out_bits=out_bits,
        paid_bits=paid_bits,
        root_record_bits=root_record_bits,
        inside_gain=inside_gain,
        reachable_tax_upper=reachable_tax_upper,
        uniform_net_upper=uniform_net_upper,
        min_step_gain=min(step_gains) if step_gains else 0,
        all_passes_shrink=all(gain > 0 for gain in step_gains),
        unique=unique,
        support_log2=support_log2,
        enum_total=enum_total,
        observed_uniform_net=observed_uniform_net,
    )


def neutral_tail_row(lambda_hits: float, states: int) -> tuple[float, float]:
    if states <= 0:
        raise ValueError("states must be positive")
    if lambda_hits <= 0.0:
        return 0.0, math.inf
    success = 1.0 - math.exp(-lambda_hits / states)
    miss_tax = -math.log2(success) if success > 0.0 else math.inf
    return success, miss_tax


def print_table(args: argparse.Namespace) -> None:
    pops = parse_int_list(args.population_size, [1, 2, 4, 8, 32])
    roots = parse_int_list(args.root_bits, [4, 8, 16])
    print("== H205 visible population / neutral-allele generated law ==")
    print("Stored final population derives parent choices, crossover/salts, and child seeds.")
    print(
        f"{'M':>3} {'G':>3} {'C':>3} {'B':>3} {'A':>2} {'P':>2} {'out':>9} "
        f"{'paid':>6} {'rRec':>5} {'gainIn':>10} {'tax':>9} {'uNet':>7} "
        f"{'uObs':>9} {'minStep':>8} {'shrink':>6} {'unique':>12}"
    )
    rows: list[Row] = []
    for population_size in pops:
        for root_bits in roots:
            rows.append(
                run_row(
                    population_size=population_size,
                    root_bits=root_bits,
                    cell_bits=args.cell_bits,
                    atom_bits=args.atom_bits,
                    branch=args.branch,
                    passes=args.passes,
                    max_enum_tuples=args.max_enum_tuples,
                    max_enum_work_bits=args.max_enum_work_bits,
                )
            )
    rows.sort(key=lambda row: (-row.inside_gain, row.uniform_net_upper))
    for row in rows[: args.limit]:
        unique = "sampled"
        if row.unique is not None:
            unique = f"{row.unique}/{row.enum_total}"
        u_obs = "n/a" if row.observed_uniform_net is None else fmt(row.observed_uniform_net)
        print(
            f"{row.population_size:3d} {row.root_bits:3d} {row.cell_bits:3d} "
            f"{row.atom_bits:3d} {row.branch:2d} {row.passes:2d} "
            f"{row.out_bits:9d} {row.paid_bits:6d} {row.root_record_bits:5d} "
            f"{row.inside_gain:10d} {row.reachable_tax_upper:9d} "
            f"{row.uniform_net_upper:7d} {u_obs:>9} {row.min_step_gain:8d} "
            f"{str(row.all_passes_shrink):>6} {unique:>12}"
        )


def print_neutral(args: argparse.Namespace) -> None:
    lambdas = [float(value) for value in args.lambda_hits.split(",")]
    states = parse_int_list(args.states, [2, 4, 16, 256])
    print()
    print("== neutral-tail control capacity ==")
    print("Required control class exists with probability 1-exp(-lambda/S).")
    print(f"{'lambda':>8} {'S':>6} {'success':>10} {'missTax':>10}")
    for lam in lambdas:
        for state_count in states:
            success, miss_tax = neutral_tail_row(lam, state_count)
            print(f"{fmt(lam):>8} {state_count:6d} {fmt(success):>10} {fmt(miss_tax):>10}")


def print_theorem() -> None:
    print()
    print("== theorem ==")
    print("Visible population laws are fully stateless generated codecs: the")
    print("decoder owns the population and all inherited update rules.  For")
    print("arbitrary uniform data, support is at most 2^(M*G), so the source")
    print("membership tax is out_bits-M*G and the net upper bound is paid-M*G.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--population-size", action="append", default=[])
    parser.add_argument("--root-bits", action="append", default=[])
    parser.add_argument("--cell-bits", type=int, default=8)
    parser.add_argument("--atom-bits", type=int, default=32)
    parser.add_argument("--branch", type=int, default=5)
    parser.add_argument("--passes", type=int, default=6)
    parser.add_argument("--max-enum-tuples", type=int, default=65536)
    parser.add_argument("--max-enum-work-bits", type=int, default=2_000_000)
    parser.add_argument("--limit", type=int, default=24)
    parser.add_argument("--lambda-hits", default="0.25,1,4,16")
    parser.add_argument("--states", action="append", default=[])
    args = parser.parse_args()

    print_table(args)
    print_neutral(args)
    print_theorem()


if __name__ == "__main__":
    main()
