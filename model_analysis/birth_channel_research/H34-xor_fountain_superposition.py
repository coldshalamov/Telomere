#!/usr/bin/env python3
"""
H34 - XOR / fountain superposition ledger.

Idea:

    Instead of storing one seed whose expansion equals the target span, store a
    small set/recipe of generated vectors whose XOR equals the span.

This makes decode order irrelevant: the decoder reads the recipe, regenerates
the vectors, XORs them, and obtains the previous layer. The question is whether
the recipe/selector can be shorter than the target for roughly all data.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from math import exp, log, log2
import random


LN2 = log(2.0)


def log2_choose_power2(universe_log2: int, k: int) -> float:
    """log2(C(2^universe_log2, k)) for small k without materializing 2^u."""

    if k < 0:
        raise ValueError("k must be nonnegative")
    if k == 0:
        return 0.0
    if universe_log2 <= 53:
        universe = float(2**universe_log2)
        if k > universe:
            return float("-inf")
        return sum(
            universe_log2 + log(1.0 - (i / universe)) / LN2 - log2(i + 1)
            for i in range(k)
        )

    # In this file k is tiny compared with 2^u. This branch keeps the formula
    # stable if a larger universe is added later.
    return sum(universe_log2 - log2(i + 1) for i in range(k))


def poissonized_coverage(log2_domain: float, target_bits: int) -> float:
    """Expected covered fraction if domain elements map like random targets."""

    load_log2 = log2_domain - target_bits
    if load_log2 > 12:
        return 1.0
    if load_log2 < -40:
        return 2.0**load_log2
    return 1.0 - exp(-(2.0**load_log2))


def log2_fraction(value: float) -> float:
    if value <= 0.0:
        return float("-inf")
    return log2(value)


@dataclass(frozen=True)
class SparseXorRow:
    target_bits: int
    seed_addr_bits: int
    xor_arity: int
    unordered_selector_bits: float
    direct_index_bits: int
    coverage: float
    unordered_excess_vs_raw: float
    direct_excess_vs_raw: int


def sparse_xor_rows() -> list[SparseXorRow]:
    rows: list[SparseXorRow] = []
    for target_bits in (64, 128, 1024):
        for seed_addr_bits in (8, 16, 32):
            for xor_arity in (2, 4, 8, 16, 64):
                if xor_arity > 2**seed_addr_bits:
                    continue
                unordered = log2_choose_power2(seed_addr_bits, xor_arity)
                rows.append(
                    SparseXorRow(
                        target_bits=target_bits,
                        seed_addr_bits=seed_addr_bits,
                        xor_arity=xor_arity,
                        unordered_selector_bits=unordered,
                        direct_index_bits=xor_arity * seed_addr_bits,
                        coverage=poissonized_coverage(unordered, target_bits),
                        unordered_excess_vs_raw=unordered - target_bits,
                        direct_excess_vs_raw=(xor_arity * seed_addr_bits)
                        - target_bits,
                    )
                )
    return rows


@dataclass(frozen=True)
class LinearBasisRow:
    target_bits: int
    rank: int
    coefficient_bits: int
    coverage_log2: int
    net_if_reachable: int
    all_data: bool


def linear_basis_rows() -> list[LinearBasisRow]:
    rows: list[LinearBasisRow] = []
    for target_bits in (64, 128, 1024):
        for rank in (target_bits // 4, target_bits // 2, target_bits):
            rows.append(
                LinearBasisRow(
                    target_bits=target_bits,
                    rank=rank,
                    coefficient_bits=rank,
                    coverage_log2=rank - target_bits,
                    net_if_reachable=target_bits - rank,
                    all_data=rank >= target_bits,
                )
            )
    return rows


@dataclass(frozen=True)
class FountainRow:
    target_bits: int
    desired_coverage: float
    required_recipe_bits: float
    excess_vs_raw: float


def fountain_rows() -> list[FountainRow]:
    rows: list[FountainRow] = []
    for target_bits in (64, 128, 1024):
        for desired in (0.50, 0.90, 0.99, 0.999999):
            # Random recipes cover fraction 1-exp(-S/2^n). Thus S must be
            # -ln(1-c) * 2^n, before record overhead or collision proof.
            required = target_bits + log2(-log(1.0 - desired))
            rows.append(
                FountainRow(
                    target_bits=target_bits,
                    desired_coverage=desired,
                    required_recipe_bits=required,
                    excess_vs_raw=required - target_bits,
                )
            )
    return rows


@dataclass(frozen=True)
class ExactToyRow:
    target_bits: int
    seed_count: int
    xor_arity: int
    domain_size: int
    unique_targets: int
    selector_bits: float
    support_bits: float
    average_multiplicity_bits: float
    excess_selector_vs_raw: float


def exact_toy_rows() -> list[ExactToyRow]:
    rng = random.Random(34034)
    rows: list[ExactToyRow] = []
    for target_bits, seed_count, xor_arity in (
        (12, 16, 2),
        (12, 24, 3),
        (12, 32, 4),
        (12, 32, 5),
    ):
        vectors = [rng.randrange(1 << target_bits) for _ in range(seed_count)]
        outputs: set[int] = set()
        domain_size = 0
        for combo in combinations(range(seed_count), xor_arity):
            value = 0
            for idx in combo:
                value ^= vectors[idx]
            outputs.add(value)
            domain_size += 1
        selector_bits = log2(domain_size)
        support_bits = log2(len(outputs))
        multiplicity_bits = log2(domain_size / len(outputs))
        rows.append(
            ExactToyRow(
                target_bits=target_bits,
                seed_count=seed_count,
                xor_arity=xor_arity,
                domain_size=domain_size,
                unique_targets=len(outputs),
                selector_bits=selector_bits,
                support_bits=support_bits,
                average_multiplicity_bits=multiplicity_bits,
                excess_selector_vs_raw=selector_bits - target_bits,
            )
        )
    return rows


def print_sparse_xor_table() -> None:
    print("== sparse unordered XOR selector ==")
    print(
        "Domain size is C(2^seed_bits, k). If this domain is smaller than "
        "2^target_bits, most targets are unreachable; if larger, the selector "
        "already costs at least raw entropy."
    )
    print(
        f"{'target':>7} {'seedbits':>8} {'k':>4} {'selector':>10} "
        f"{'idx bits':>8} {'coverage':>12} {'sel-raw':>9} {'idx-raw':>8}"
    )
    for row in sparse_xor_rows():
        if row.target_bits in (64, 128) and row.seed_addr_bits in (16, 32):
            if row.xor_arity in (2, 4, 8, 16):
                print(
                    f"{row.target_bits:7d} {row.seed_addr_bits:8d} "
                    f"{row.xor_arity:4d} {row.unordered_selector_bits:10.3f} "
                    f"{row.direct_index_bits:8d} {row.coverage:12.6g} "
                    f"{row.unordered_excess_vs_raw:9.3f} "
                    f"{row.direct_excess_vs_raw:8d}"
                )
    print()


def print_linear_basis_table() -> None:
    print("== public linear basis ==")
    print(
        "A rank-r public GF(2) basis covers exactly 2^r targets. Full coverage "
        "needs r target_bits of coefficients."
    )
    print(
        f"{'target':>7} {'rank':>7} {'coeff bits':>11} "
        f"{'log2 coverage':>14} {'net if hit':>11} {'all data?':>10}"
    )
    for row in linear_basis_rows():
        print(
            f"{row.target_bits:7d} {row.rank:7d} {row.coefficient_bits:11d} "
            f"{row.coverage_log2:14d} {row.net_if_reachable:11d} "
            f"{str(row.all_data):>10}"
        )
    print()


def print_fountain_table() -> None:
    print("== random fountain recipe coverage ==")
    print(
        "A c-bit public recipe family has at most 2^c possible outputs. Under "
        "the uniform hash law, high coverage needs c slightly above raw size."
    )
    print(
        f"{'target':>7} {'coverage':>10} {'recipe bits':>12} "
        f"{'excess/raw':>11}"
    )
    for row in fountain_rows():
        if row.target_bits in (64, 128):
            print(
                f"{row.target_bits:7d} {row.desired_coverage:10.6f} "
                f"{row.required_recipe_bits:12.3f} {row.excess_vs_raw:11.3f}"
            )
    print()


def print_exact_toy_table() -> None:
    print("== exact small XOR support check ==")
    print(
        "The tiny enumeration shows the multiplicity illusion: once support is "
        "near full, selector_bits = support_bits + multiplicity_bits."
    )
    print(
        f"{'target':>7} {'M':>4} {'k':>3} {'domain':>8} {'unique':>8} "
        f"{'selector':>10} {'support':>9} {'mult':>8} {'sel-raw':>9}"
    )
    for row in exact_toy_rows():
        print(
            f"{row.target_bits:7d} {row.seed_count:4d} {row.xor_arity:3d} "
            f"{row.domain_size:8d} {row.unique_targets:8d} "
            f"{row.selector_bits:10.3f} {row.support_bits:9.3f} "
            f"{row.average_multiplicity_bits:8.3f} "
            f"{row.excess_selector_vs_raw:9.3f}"
        )
    print()


def main() -> None:
    print_sparse_xor_table()
    print_linear_basis_table()
    print_fountain_table()
    print_exact_toy_table()
    print("CONCLUSION:")
    print(
        "XOR/fountain superposition is stateless and order-insensitive, so it "
        "does solve the parse-order part of the problem. It does not create a "
        "free compression channel under the uniform law: sparse combinations "
        "miss most targets, full-rank linear combinations cost raw entropy, "
        "and random recipe families need at least raw-size selectors for high "
        "coverage. Extra decompositions are multiplicity bits that can at best "
        "be bits-backed to the raw bound, not below it without a non-uniform "
        "source prior or a paid hidden selector."
    )


if __name__ == "__main__":
    main()
