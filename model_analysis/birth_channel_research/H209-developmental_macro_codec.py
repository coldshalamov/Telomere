#!/usr/bin/env python3
"""H209 - developmental visible-population macro codec.

H205-H208 are ledgers.  This kernel makes the best surviving generated branch
into an explicit finite codec:

* generated record: a visible root population unfolds through a public
  developmental law for P passes;
* raw escape: arbitrary non-reachable outputs round-trip literally;
* exact finite mode: enumerate a small output universe and verify all
  round-trips;
* symbolic mode: report the large H205/H208 rows without enumerating support.

The generated/reachable regime is strongly positive.  The arbitrary-uniform
ledger remains explicit: support membership, root-record overhead, and Kraft
fallback are all charged.
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


def int_to_bytes(value: int, bit_width: int) -> bytes:
    return value.to_bytes((bit_width + 7) // 8 or 1, "big")


def hash_bits(label: bytes, bit_width: int) -> int:
    digest = hashlib.blake2b(label, digest_size=32).digest()
    if bit_width <= 0:
        return 0
    return int.from_bytes(digest, "big") & ((1 << bit_width) - 1)


def bit_width_for_count(count: int) -> int:
    return max(1, math.ceil(math.log2(max(1, count))))


def log2_one_minus(q: float) -> float:
    if q >= 1.0:
        return -math.inf
    return math.log1p(-q) / math.log(2.0)


def parse_int_list(values: list[str], default: list[int]) -> list[int]:
    if not values:
        return default
    out: list[int] = []
    for value in values:
        out.extend(int(part) for part in value.split(",") if part)
    return out


@dataclass(frozen=True)
class Params:
    population_size: int
    root_bits: int
    cell_bits: int
    atom_bits: int
    arity: int
    passes: int

    @property
    def out_atoms(self) -> int:
        return self.population_size * (self.arity**self.passes)

    @property
    def out_bits(self) -> int:
        return self.out_atoms * self.atom_bits

    @property
    def root_rank_bits(self) -> int:
        return self.population_size * self.root_bits

    @property
    def root_tuple_count(self) -> int:
        return 1 << self.root_rank_bits


@dataclass(frozen=True)
class Code:
    mode: str
    payload: tuple[int, ...] | int


def unpack_roots(rank: int, params: Params) -> tuple[int, ...]:
    mask = (1 << params.root_bits) - 1
    return tuple(
        (rank >> (params.root_bits * i)) & mask for i in range(params.population_size)
    )


def root_rank(roots: tuple[int, ...], params: Params) -> int:
    rank = 0
    for i, root in enumerate(roots):
        if root < 0 or root >= (1 << params.root_bits):
            raise ValueError("root outside configured width")
        rank |= root << (params.root_bits * i)
    return rank


def child_population(
    population: tuple[int, ...],
    *,
    seed_bits: int,
    child_bits: int,
    arity: int,
    pass_index: int,
    slot_base: int,
) -> tuple[int, ...]:
    """Public inherited child law.

    The encoder does not choose parent indices, crossover points, or salts.
    The visible population and public coordinates determine them.
    """

    m = len(population)
    pop_blob = b"".join(int_to_bytes(seed, seed_bits) for seed in population)
    selector_bits = bit_width_for_count(m)
    out: list[int] = []
    for slot in range(arity):
        label = (
            b"H209-child\0"
            + pass_index.to_bytes(4, "big")
            + slot_base.to_bytes(8, "big")
            + slot.to_bytes(2, "big")
            + pop_blob
        )
        i = hash_bits(label + b"i", selector_bits) % m
        j = hash_bits(label + b"j", selector_bits) % m
        mix = population[i] ^ ((population[j] << 1) & ((1 << seed_bits) - 1)) ^ slot
        out.append(hash_bits(label + int_to_bytes(mix, seed_bits), child_bits))
    return tuple(out)


def develop_roots(roots: tuple[int, ...], params: Params) -> int:
    population = tuple(roots)
    seed_bits = params.root_bits
    slot_span = 1
    for pass_index in range(params.passes):
        next_population: list[int] = []
        for idx, _seed in enumerate(population):
            next_population.extend(
                child_population(
                    population,
                    seed_bits=seed_bits,
                    child_bits=params.cell_bits,
                    arity=params.arity,
                    pass_index=pass_index,
                    slot_base=idx * slot_span,
                )
            )
        population = tuple(next_population)
        seed_bits = params.cell_bits
        slot_span *= params.arity

    out = 0
    for idx, seed in enumerate(population):
        label = b"H209-leaf\0" + idx.to_bytes(8, "big")
        atom = hash_bits(label + int_to_bytes(seed, params.cell_bits), params.atom_bits)
        out = (out << params.atom_bits) | atom
    return out


def enumerate_support(params: Params, max_root_tuples: int) -> tuple[dict[int, tuple[int, ...]], int]:
    if params.root_tuple_count > max_root_tuples:
        raise ValueError(
            f"root tuple count {params.root_tuple_count} exceeds --max-root-tuples={max_root_tuples}"
        )
    support: dict[int, tuple[int, ...]] = {}
    collision_count = 0
    for rank in range(params.root_tuple_count):
        roots = unpack_roots(rank, params)
        output = develop_roots(roots, params)
        if output in support:
            collision_count += 1
        else:
            support[output] = roots
    return support, collision_count


def native_generated_bits(params: Params) -> int:
    return 1 + params.population_size * costs.record_cost_for_payload_width(
        params.arity, params.root_bits
    )


def packed_generated_bits(params: Params, extra_mode_bits: int) -> int:
    return params.root_rank_bits + extra_mode_bits


def pass_sizes(params: Params, root_bits_per_record: int) -> list[int]:
    internal_bits = costs.record_cost_for_payload_width(params.arity, params.cell_bits)
    sizes = [params.out_bits]
    for compressed_pass in range(1, params.passes):
        sizes.append(
            params.population_size
            * (params.arity ** (params.passes - compressed_pass))
            * internal_bits
        )
    sizes.append(params.population_size * root_bits_per_record)
    return sizes


def encode_exact(target: int, support: dict[int, tuple[int, ...]]) -> Code:
    if target in support:
        return Code("generated", support[target])
    return Code("raw", target)


def decode_exact(code: Code, params: Params) -> int:
    if code.mode == "generated":
        assert isinstance(code.payload, tuple)
        return develop_roots(code.payload, params)
    if code.mode == "raw":
        assert isinstance(code.payload, int)
        return code.payload
    raise ValueError(f"unknown mode {code.mode!r}")


@dataclass(frozen=True)
class ExactRow:
    params: Params
    support: int
    collisions: int
    roundtrip_ok: bool
    native_gen_bits: int
    packed_gen_bits: int
    raw_prefix_bits: int
    uniform_native_mean: float
    uniform_packed_mean: float
    generated_native_gain: int
    generated_packed_gain: int
    uniform_native_delta: float
    uniform_packed_delta: float
    support_log2: float
    membership_tax: float
    native_net_after_membership: float
    packed_net_after_membership: float


def exact_row(params: Params, max_root_tuples: int) -> ExactRow:
    support_map, collisions = enumerate_support(params, max_root_tuples)
    universe = 1 << params.out_bits
    roundtrip_ok = True
    for target in range(universe):
        code = encode_exact(target, support_map)
        if decode_exact(code, params) != target:
            roundtrip_ok = False
            break

    support = len(support_map)
    support_fraction = support / universe
    native_bits = native_generated_bits(params)
    packed_bits = packed_generated_bits(params, extra_mode_bits=1)
    raw_bits = params.out_bits + 1
    uniform_native_mean = support_fraction * native_bits + (1.0 - support_fraction) * raw_bits
    uniform_packed_mean = support_fraction * packed_bits + (1.0 - support_fraction) * raw_bits
    support_log2 = math.log2(support) if support else -math.inf
    membership_tax = params.out_bits - support_log2
    return ExactRow(
        params=params,
        support=support,
        collisions=collisions,
        roundtrip_ok=roundtrip_ok,
        native_gen_bits=native_bits,
        packed_gen_bits=packed_bits,
        raw_prefix_bits=raw_bits,
        uniform_native_mean=uniform_native_mean,
        uniform_packed_mean=uniform_packed_mean,
        generated_native_gain=params.out_bits - native_bits,
        generated_packed_gain=params.out_bits - packed_bits,
        uniform_native_delta=uniform_native_mean - params.out_bits,
        uniform_packed_delta=uniform_packed_mean - params.out_bits,
        support_log2=support_log2,
        membership_tax=membership_tax,
        native_net_after_membership=params.out_bits - native_bits - membership_tax,
        packed_net_after_membership=params.out_bits - packed_bits - membership_tax,
    )


@dataclass(frozen=True)
class SymbolicRow:
    params: Params
    mode: str
    generated_bits: int
    q: float
    raw_kraft_delta: float
    generated_gain: int
    uniform_upper_after_membership: int
    source_alpha_threshold: float
    min_step_gain: int


def symbolic_rows(params: Params, extra_mode_bits: int) -> list[SymbolicRow]:
    rows: list[SymbolicRow] = []
    native_bits = native_generated_bits(params)
    packed_bits = packed_generated_bits(params, extra_mode_bits=extra_mode_bits)
    for mode, gen_bits in [("native_v1_roots", native_bits), ("packed_roots", packed_bits)]:
        delta = gen_bits - params.root_rank_bits
        q = 2.0 ** (-delta) if delta >= 0 else math.inf
        raw_delta = math.inf if not (0.0 <= q < 1.0) else -log2_one_minus(q)
        generated_gain = params.out_bits - gen_bits
        threshold = (
            math.inf
            if not math.isfinite(raw_delta) or generated_gain <= 0
            else raw_delta / (generated_gain + raw_delta)
        )
        root_record = costs.record_cost_for_payload_width(params.arity, params.root_bits)
        sizes = pass_sizes(params, root_record)
        step_gains = [before - after for before, after in zip(sizes, sizes[1:])]
        rows.append(
            SymbolicRow(
                params=params,
                mode=mode,
                generated_bits=gen_bits,
                q=q,
                raw_kraft_delta=raw_delta,
                generated_gain=generated_gain,
                uniform_upper_after_membership=params.root_rank_bits - gen_bits,
                source_alpha_threshold=threshold,
                min_step_gain=min(step_gains) if step_gains else 0,
            )
        )
    return rows


def print_exact(args: argparse.Namespace) -> None:
    params = Params(
        population_size=args.population_size,
        root_bits=args.root_bits,
        cell_bits=args.cell_bits,
        atom_bits=args.atom_bits,
        arity=args.arity,
        passes=args.passes,
    )
    row = exact_row(params, args.max_root_tuples)
    print("== H209 exact finite codec ==")
    print("Mode: generated roots when reachable, raw literal escape otherwise.")
    print(
        f"M={params.population_size} G={params.root_bits} C={params.cell_bits} "
        f"B={params.atom_bits} A={params.arity} P={params.passes} N={params.out_bits}"
    )
    print(
        f"support={row.support}/{1 << params.out_bits} "
        f"log2support={fmt(row.support_log2)} collisions={row.collisions} "
        f"roundtrip={row.roundtrip_ok}"
    )
    print(
        f"nativeGen={row.native_gen_bits} packedGen={row.packed_gen_bits} "
        f"rawPrefix={row.raw_prefix_bits}"
    )
    print(
        f"generatedGain(native)={row.generated_native_gain} "
        f"generatedGain(packed)={row.generated_packed_gain}"
    )
    print(
        f"uniformMean(native)={fmt(row.uniform_native_mean)} "
        f"delta={fmt(row.uniform_native_delta)}"
    )
    print(
        f"uniformMean(packed)={fmt(row.uniform_packed_mean)} "
        f"delta={fmt(row.uniform_packed_delta)}"
    )
    print(
        f"membershipTax={fmt(row.membership_tax)} "
        f"netAfterMembership(native)={fmt(row.native_net_after_membership)} "
        f"netAfterMembership(packed)={fmt(row.packed_net_after_membership)}"
    )


def print_symbolic(args: argparse.Namespace) -> None:
    populations = parse_int_list(args.symbolic_population_size, [1, 32])
    roots = parse_int_list(args.symbolic_root_bits, [16])
    print()
    print("== H209 symbolic developmental macro rows ==")
    print(
        f"{'mode':<16} {'M':>3} {'G':>3} {'A':>2} {'P':>2} {'N':>10} "
        f"{'genBits':>8} {'gain':>10} {'uNet':>7} {'q':>10} "
        f"{'rawOH':>10} {'alpha*':>10} {'minStep':>8}"
    )
    rows: list[SymbolicRow] = []
    for population_size in populations:
        for root_bits in roots:
            params = Params(
                population_size=population_size,
                root_bits=root_bits,
                cell_bits=args.symbolic_cell_bits,
                atom_bits=args.symbolic_atom_bits,
                arity=args.symbolic_arity,
                passes=args.symbolic_passes,
            )
            rows.extend(symbolic_rows(params, args.extra_mode_bits))
    rows.sort(key=lambda row: (row.mode, -row.generated_gain))
    for row in rows:
        params = row.params
        print(
            f"{row.mode:<16} {params.population_size:3d} {params.root_bits:3d} "
            f"{params.arity:2d} {params.passes:2d} {params.out_bits:10d} "
            f"{row.generated_bits:8d} {row.generated_gain:10d} "
            f"{row.uniform_upper_after_membership:7d} {fmt(row.q):>10} "
            f"{fmt(row.raw_kraft_delta):>10} {fmt(row.source_alpha_threshold):>10} "
            f"{row.min_step_gain:8d}"
        )


def print_spec() -> None:
    print()
    print("== decode spec ==")
    print("generated: read public params, read M root witnesses, iterate the")
    print("public child law for P passes, then emit B-bit leaves in order.")
    print("raw: read the raw N-bit layer literally.  In the ideal Kraft-prior")
    print("version, raw length is N-log2(1-q); in the concrete prefix toy it")
    print("is N+1.  No birth-pass, open/carry, final-position, or selector map")
    print("is present.")
    print()
    print("== theorem ==")
    print("For the generated source, length is the root macro length and drift")
    print("is N-generatedBits.  For arbitrary uniform data, membership costs at")
    print("least N-log2(support), so the best packed-root no-fallback branch ties")
    print("and every parseable mode/fallback is non-positive after Kraft cost.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--population-size", type=int, default=1)
    parser.add_argument("--root-bits", type=int, default=3)
    parser.add_argument("--cell-bits", type=int, default=3)
    parser.add_argument("--atom-bits", type=int, default=2)
    parser.add_argument("--arity", type=int, default=2)
    parser.add_argument("--passes", type=int, default=2)
    parser.add_argument("--max-root-tuples", type=int, default=65536)
    parser.add_argument("--extra-mode-bits", type=int, default=1)
    parser.add_argument("--symbolic-population-size", action="append", default=[])
    parser.add_argument("--symbolic-root-bits", action="append", default=[])
    parser.add_argument("--symbolic-cell-bits", type=int, default=8)
    parser.add_argument("--symbolic-atom-bits", type=int, default=32)
    parser.add_argument("--symbolic-arity", type=int, default=5)
    parser.add_argument("--symbolic-passes", type=int, default=6)
    args = parser.parse_args()

    print_exact(args)
    print_symbolic(args)
    print_spec()


if __name__ == "__main__":
    main()
