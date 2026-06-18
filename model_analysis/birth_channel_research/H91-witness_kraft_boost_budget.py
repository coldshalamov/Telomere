#!/usr/bin/env python3
"""H91 - witness Kraft boost budget.

H90 proves that public laws over a fixed witness family are capped by log2 Z.
H91 asks what a real new mechanism would have to do to cross:

* flat per-word boost: how many bits/word are missing?
* per-record boost: how many bits must every selected/collective record save?

The per-record boost is modeled honestly inside the same exact H74 finite
domain by multiplying every edge/record weight by 2^bonus and recomputing both
total-cover mass and best-cover mass.

This is a target budget, not a proposed codec. Any mechanism that claims to
solve H89 must supply at least this much honest Kraft mass without hiding the
same information in a selector/profile/final layout.
"""

from __future__ import annotations

import importlib.util
import math
import sys
from dataclasses import dataclass
from pathlib import Path


H74_PATH = Path(__file__).resolve().with_name("H74-exact_latent_q_kernel.py")
_h74_spec = importlib.util.spec_from_file_location("h74_exact_latent_q_kernel", H74_PATH)
if _h74_spec is None or _h74_spec.loader is None:
    raise RuntimeError("could not load H74 exact latent Q kernel")
_h74 = importlib.util.module_from_spec(_h74_spec)
sys.modules[_h74_spec.name] = _h74
_h74_spec.loader.exec_module(_h74)


@dataclass(frozen=True)
class BoostRow:
    family: str
    base_z: float
    flat_bits_per_word_needed: float
    record_bonus_needed: float
    implied_records_per_word: float
    z_at_bonus: float


def scaled_tables(tables: list[list[float]], scale: float) -> list[list[float]]:
    return [[value * scale for value in row] for row in tables]


def mass_with_record_bonus(
    block_bits: int,
    atoms: int,
    max_arity: int,
    edge_weights: list[list[float]],
    edge_maxes: list[list[float]],
    record_bonus_bits: float,
) -> tuple[float, float]:
    scale = 2.0 ** record_bonus_bits
    weighted_totals = scaled_tables(edge_weights, scale)
    weighted_maxes = scaled_tables(edge_maxes, scale)
    total_mass = 0.0
    best_mass = 0.0
    for word in range(1 << (block_bits * atoms)):
        total, best = _h74.dp_mass_for_word(
            word,
            atoms,
            block_bits,
            max_arity,
            weighted_totals,
            weighted_maxes,
        )
        total_mass += total
        best_mass += best
    return total_mass, best_mass


def find_bonus(
    target_family: str,
    block_bits: int,
    atoms: int,
    max_arity: int,
    edge_weights: list[list[float]],
    edge_maxes: list[list[float]],
) -> tuple[float, float]:
    def family_mass(bonus: float) -> float:
        total, best = mass_with_record_bonus(
            block_bits,
            atoms,
            max_arity,
            edge_weights,
            edge_maxes,
            bonus,
        )
        return best if target_family == "best selected" else total

    lo = 0.0
    hi = 0.25
    while family_mass(hi) < 1.0:
        hi *= 2.0
        if hi > 64.0:
            raise RuntimeError("could not bracket bonus")
    for _ in range(36):
        mid = (lo + hi) / 2.0
        if family_mass(mid) < 1.0:
            lo = mid
        else:
            hi = mid
    bonus = (lo + hi) / 2.0
    return bonus, family_mass(bonus)


def rows(
    block_bits: int = 1,
    atoms: int = 12,
    max_arity: int = 6,
    depth_bits: int = 8,
    seed: int = 75,
) -> list[BoostRow]:
    edge_weights, edge_maxes = _h74.build_edge_weights(block_bits, max_arity, depth_bits, seed)
    base_total, base_best = mass_with_record_bonus(
        block_bits,
        atoms,
        max_arity,
        edge_weights,
        edge_maxes,
        0.0,
    )
    result: list[BoostRow] = []
    for family, base_z in (("best selected", base_best), ("all descriptions", base_total)):
        bonus, z_at_bonus = find_bonus(family, block_bits, atoms, max_arity, edge_weights, edge_maxes)
        flat_gap = -math.log2(base_z)
        result.append(
            BoostRow(
                family=family,
                base_z=base_z,
                flat_bits_per_word_needed=flat_gap,
                record_bonus_needed=bonus,
                implied_records_per_word=flat_gap / bonus if bonus > 0.0 else math.inf,
                z_at_bonus=z_at_bonus,
            )
        )
    return result


def print_rows(result: list[BoostRow]) -> None:
    print("== witness Kraft boost budget ==")
    print(
        f"{'family':<18} {'base Z':>12} {'flat bits':>10} "
        f"{'record bits':>12} {'records/word':>12} {'Z boosted':>11}"
    )
    for row in result:
        print(
            f"{row.family:<18} {row.base_z:12.9f} "
            f"{row.flat_bits_per_word_needed:10.6f} "
            f"{row.record_bonus_needed:12.6f} "
            f"{row.implied_records_per_word:12.3f} {row.z_at_bonus:11.9f}"
        )
    print()


def print_reading(result: list[BoostRow]) -> None:
    selected = next(row for row in result if row.family == "best selected")
    collective = next(row for row in result if row.family == "all descriptions")
    print("== reading ==")
    print(
        f"The selected-witness family needs {selected.flat_bits_per_word_needed:.6f} "
        f"flat bits/word or about {selected.record_bonus_needed:.6f} bits per "
        "record in this exact toy domain before any public source law can cross."
    )
    print(
        f"The collective all-description family is closer: it needs "
        f"{collective.flat_bits_per_word_needed:.6f} flat bits/word or about "
        f"{collective.record_bonus_needed:.6f} bits per record. That is the "
        "sharpest constructive budget exposed by H90."
    )
    print(
        "A claimed breakthrough should identify where these bits come from and "
        "show they are not paid back as witness delimiters, profile selectors, "
        "birth/pass ledgers, final-board coordinates, or rare-tail losses."
    )


def main() -> None:
    result = rows()
    print_rows(result)
    print_reading(result)


if __name__ == "__main__":
    main()
