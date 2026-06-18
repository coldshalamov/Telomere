#!/usr/bin/env python3
"""H136 - batch footprint mask DP.

H133 tests common-cause batches as arity-mass convolutions. H136 tests the
stronger board/egg-carton version: a batch may cover a non-contiguous footprint
of the remaining board.

State is the uncovered mask M. Let i be the first uncovered atom. A valid symbol
chooses a footprint sigma containing i, then pays a shape/footprint code and an
optimistic normalized witness rank whose total mass is 1 per shape.

If local shape mass is <= 1 at every state, induction gives Z(M) <= 1. Positive
rows therefore identify unpaid/overfull footprint syntax, not compression.
"""

from __future__ import annotations

import functools
import itertools
import math
from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True)
class MaskRow:
    mode: str
    atoms: int
    max_footprint: int
    log2_z: float
    max_local_mass: float
    valid_local_kraft: bool
    note: str


def log2_fraction(value: Fraction) -> float:
    if value <= 0:
        return float("-inf")
    return math.log2(value.numerator) - math.log2(value.denominator)


def first_bit(mask: int) -> int:
    return (mask & -mask).bit_length() - 1


def bits(mask: int, atoms: int) -> list[int]:
    return [index for index in range(atoms) if mask & (1 << index)]


def interval_shapes(mask: int, atoms: int, max_footprint: int) -> list[int]:
    anchor = first_bit(mask)
    out: list[int] = []
    for size in range(1, max_footprint + 1):
        if anchor + size > atoms:
            break
        shape = sum(1 << index for index in range(anchor, anchor + size))
        if shape & mask == shape:
            out.append(shape)
    return out


def all_mask_shapes(mask: int, atoms: int, max_footprint: int) -> list[int]:
    anchor = first_bit(mask)
    rest = [index for index in bits(mask, atoms) if index != anchor]
    out = [1 << anchor]
    for size in range(2, max_footprint + 1):
        for combo in itertools.combinations(rest, size - 1):
            shape = 1 << anchor
            for index in combo:
                shape |= 1 << index
            out.append(shape)
    return out


def gap_pair_shapes(mask: int, atoms: int, gap: int) -> list[int]:
    anchor = first_bit(mask)
    out = [1 << anchor]
    partner = anchor + gap
    if partner < atoms and (mask & (1 << partner)):
        out.append((1 << anchor) | (1 << partner))
    return out


def shape_weights(mode: str, shapes: list[int]) -> list[Fraction]:
    count = len(shapes)
    if count <= 0:
        return []
    if mode.endswith("_free"):
        return [Fraction(1, 1) for _ in shapes]
    if mode.endswith("_normalized"):
        return [Fraction(1, count) for _ in shapes]
    if mode.endswith("_ceil"):
        width = max(0, math.ceil(math.log2(count)))
        return [Fraction(1, 1 << width) for _ in shapes]
    raise ValueError(mode)


def solve(mode: str, atoms: int, max_footprint: int, gap: int = 2) -> tuple[Fraction, Fraction]:
    full = (1 << atoms) - 1
    max_local = Fraction(0, 1)

    @functools.lru_cache(maxsize=None)
    def dp(mask: int) -> Fraction:
        nonlocal max_local
        if mask == 0:
            return Fraction(1, 1)
        if mode.startswith("interval"):
            shapes = interval_shapes(mask, atoms, max_footprint)
        elif mode.startswith("all_masks"):
            shapes = all_mask_shapes(mask, atoms, max_footprint)
        elif mode.startswith("gap_pair"):
            shapes = gap_pair_shapes(mask, atoms, gap)
        else:
            raise ValueError(mode)
        weights = shape_weights(mode, shapes)
        local = sum(weights, Fraction(0, 1))
        max_local = max(max_local, local)
        total = Fraction(0, 1)
        for shape, weight in zip(shapes, weights):
            total += weight * dp(mask & ~shape)
        return total

    return dp(full), max_local


def row(mode: str, atoms: int = 12, max_footprint: int = 4) -> MaskRow:
    z, max_local = solve(mode, atoms, max_footprint)
    valid = max_local <= 1
    if valid and z == 1:
        note = "valid, zero margin"
    elif valid:
        note = "valid subprobability"
    else:
        note = "invalid unpaid footprint syntax"
    return MaskRow(
        mode=mode,
        atoms=atoms,
        max_footprint=max_footprint,
        log2_z=log2_fraction(z),
        max_local_mass=log2_fraction(max_local),
        valid_local_kraft=valid,
        note=note,
    )


def rows() -> list[MaskRow]:
    return [
        row("interval_normalized", max_footprint=6),
        row("interval_ceil", max_footprint=6),
        row("all_masks_normalized", max_footprint=3),
        row("all_masks_ceil", max_footprint=3),
        row("all_masks_free", max_footprint=3),
        row("all_masks_normalized", max_footprint=4),
        row("all_masks_ceil", max_footprint=4),
        row("all_masks_free", max_footprint=4),
        row("gap_pair_normalized", max_footprint=2),
        row("gap_pair_free", max_footprint=2),
    ]


def print_rows(result: list[MaskRow]) -> None:
    print("== batch footprint mask DP ==")
    print("Optimistic normalized witness rank mass = 1 per footprint; B=1,N=12.")
    print(
        f"{'mode':<22} {'K':>3} {'log2 Z':>10} {'max local':>10} {'valid':>7} note"
    )
    for item in result:
        print(
            f"{item.mode:<22} {item.max_footprint:3d} {item.log2_z:10.6f} "
            f"{item.max_local_mass:10.6f} {str(item.valid_local_kraft):>7} {item.note}"
        )
    print()


def print_reading(result: list[MaskRow]) -> None:
    invalid = [item for item in result if not item.valid_local_kraft]
    best_valid = max((item for item in result if item.valid_local_kraft), key=lambda item: item.log2_z)
    best_invalid = max(invalid, key=lambda item: item.log2_z)
    print("== reading ==")
    print(
        f"Best valid footprint row is {best_valid.mode}, K={best_valid.max_footprint}, "
        f"log2Z={best_valid.log2_z:.6f}: zero margin, not compression."
    )
    print(
        f"Best invalid row is {best_invalid.mode}, K={best_invalid.max_footprint}, "
        f"log2Z={best_invalid.log2_z:.6f}, but local mass reaches "
        f"log2={best_invalid.max_local_mass:.6f}."
    )
    print(
        "So non-contiguous egg-carton footprints can make parse/order public, "
        "but they do not create source-free Kraft mass. Crossings come from "
        "unpaid footprint choices."
    )


def main() -> None:
    result = rows()
    print_rows(result)
    print_reading(result)


if __name__ == "__main__":
    main()
