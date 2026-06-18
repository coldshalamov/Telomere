#!/usr/bin/env python3
"""H105 - forced-rewrite collective witness target.

H102/H103 sharpened stateless readiness:

    public two-epoch lane + class-local seed rank => no visible parity tax

That helps only if the forced-rewrite witness family has positive base margin.
H105 tests the nearest exact collective/all-description witness families from
H94 and asks how many honest per-record bits are still missing.

Rows are exact over the H74 tiny domain (B=1,N=12). This is not a broad
compression test; it is a Kraft/accounting target:

* public-local: class supplied by public lane; no seed-class thinning;
* visible-parity: seed witness carries readiness; add 1 bit/record;
* exception ledger: near-total carry exceptions subtract visible bits/word.
"""

from __future__ import annotations

import importlib.util
import math
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

HERE = Path(__file__).resolve().parent


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


H74 = load_module("h74_for_h105", HERE / "H74-exact_latent_q_kernel.py")
H94 = load_module("h94_for_h105", HERE / "H94-normalized_rank_witness_sweep.py")


@dataclass(frozen=True)
class TargetRow:
    mode: str
    max_arity: int
    depth_bits: int
    selected_log2_z: float
    collective_log2_z: float
    public_bonus_bits_per_record: float
    visible_parity_bonus_bits_per_record: float
    exception_001_bonus_bits_per_record: float
    implied_records_per_word: float


def h2(p: float) -> float:
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -(p * math.log2(p) + (1.0 - p) * math.log2(1.0 - p))


def scale_tables(tables: list[list[float]], scale: float) -> list[list[float]]:
    return [[value * scale for value in row] for row in tables]


def masses_with_bonus(
    edge_weights: list[list[float]],
    edge_maxes: list[list[float]],
    block_bits: int,
    atoms: int,
    max_arity: int,
    bonus_bits: float,
) -> tuple[float, float]:
    scale = 2.0 ** bonus_bits
    weighted = scale_tables(edge_weights, scale)
    maxed = scale_tables(edge_maxes, scale)
    total = 0.0
    best = 0.0
    for word in range(1 << (block_bits * atoms)):
        word_total, word_best = H74.dp_mass_for_word(
            word,
            atoms,
            block_bits,
            max_arity,
            weighted,
            maxed,
        )
        total += word_total
        best += word_best
    return total, best


def find_bonus_for_target(
    edge_weights: list[list[float]],
    edge_maxes: list[list[float]],
    block_bits: int,
    atoms: int,
    max_arity: int,
    target_log2_mass: float,
    family: str = "collective",
) -> tuple[float, float]:
    def log_mass(bonus: float) -> float:
        total, best = masses_with_bonus(
            edge_weights,
            edge_maxes,
            block_bits,
            atoms,
            max_arity,
            bonus,
        )
        value = best if family == "selected" else total
        return math.log2(value) if value > 0.0 else float("-inf")

    if log_mass(0.0) >= target_log2_mass:
        return 0.0, log_mass(0.0)
    lo = 0.0
    hi = 0.25
    while log_mass(hi) < target_log2_mass:
        hi *= 2.0
        if hi > 64.0:
            raise RuntimeError("could not bracket bonus")
    for _ in range(28):
        mid = (lo + hi) / 2.0
        if log_mass(mid) < target_log2_mass:
            lo = mid
        else:
            hi = mid
    bonus = (lo + hi) / 2.0
    return bonus, log_mass(bonus)


def exception_bits_per_word(atoms: int, passes: int, eps: float) -> float:
    return atoms * (h2(eps) + eps * math.log2(passes - 1))


def row_for(mode: str, max_arity: int, depth_bits: int) -> TargetRow:
    block_bits = 1
    atoms = 12
    edge_weights, edge_maxes, _, _ = H94.build_edge_weights(
        mode,
        block_bits,
        max_arity,
        depth_bits,
        seed=92000 + max_arity * 100 + depth_bits,
    )
    total, best = masses_with_bonus(edge_weights, edge_maxes, block_bits, atoms, max_arity, 0.0)
    total_log = math.log2(total) if total > 0.0 else float("-inf")
    best_log = math.log2(best) if best > 0.0 else float("-inf")
    public_bonus, _ = find_bonus_for_target(
        edge_weights,
        edge_maxes,
        block_bits,
        atoms,
        max_arity,
        target_log2_mass=0.0,
    )
    exception_bonus, _ = find_bonus_for_target(
        edge_weights,
        edge_maxes,
        block_bits,
        atoms,
        max_arity,
        target_log2_mass=exception_bits_per_word(atoms, passes=64, eps=0.001),
    )
    flat_gap = max(0.0, -total_log)
    records_per_word = flat_gap / public_bonus if public_bonus > 0.0 else math.inf
    return TargetRow(
        mode=mode,
        max_arity=max_arity,
        depth_bits=depth_bits,
        selected_log2_z=best_log,
        collective_log2_z=total_log,
        public_bonus_bits_per_record=public_bonus,
        visible_parity_bonus_bits_per_record=public_bonus + 1.0,
        exception_001_bonus_bits_per_record=exception_bonus,
        implied_records_per_word=records_per_word,
    )


def rows() -> list[TargetRow]:
    # Best frontier rows from H94 plus the optimistic H92-style lower bound.
    return [
        row_for("h92_lower", 8, 12),
        row_for("custom_rank", 8, 10),
        row_for("custom_record", 6, 12),
        row_for("paid_lotus", 12, 12),
    ]


def print_rows(result: list[TargetRow]) -> None:
    print("== forced-rewrite collective target ==")
    print("Exact domain B=1,N=12. Bonus is honest per-record Kraft/margin still needed.")
    print(
        f"{'mode':<13} {'K':>3} {'D':>3} {'log2 best':>10} {'log2 total':>11} "
        f"{'public':>9} {'visible+1':>10} {'eps001':>9} {'rec/word':>9}"
    )
    for row in result:
        print(
            f"{row.mode:<13} {row.max_arity:3d} {row.depth_bits:3d} "
            f"{row.selected_log2_z:10.6f} {row.collective_log2_z:11.6f} "
            f"{row.public_bonus_bits_per_record:9.6f} "
            f"{row.visible_parity_bonus_bits_per_record:10.6f} "
            f"{row.exception_001_bonus_bits_per_record:9.6f} "
            f"{row.implied_records_per_word:9.3f}"
        )
    print()


def print_reading(result: list[TargetRow]) -> None:
    honest = [row for row in result if row.mode != "h92_lower"]
    best = min(honest, key=lambda row: row.public_bonus_bits_per_record)
    lower = next(row for row in result if row.mode == "h92_lower")
    print("== reading ==")
    print(
        f"The optimistic H92-style lower bound crosses without extra public-lane "
        f"tax: log2Z={lower.collective_log2_z:.6f}. That row is not paid."
    )
    print(
        f"Best honest row here is {best.mode} K={best.max_arity},D={best.depth_bits}: "
        f"public-local still needs {best.public_bonus_bits_per_record:.6f} "
        "bits/record of real witness margin."
    )
    print(
        f"Visible seed parity would raise that target to "
        f"{best.visible_parity_bonus_bits_per_record:.6f} bits/record, so H102/H103 "
        "really matter: public lanes remove about one bit/record of readiness tax."
    )
    print(
        f"Even a tiny T=64, eps=0.001 exception ledger moves the target to "
        f"{best.exception_001_bonus_bits_per_record:.6f} bits/record. The cleanest "
        "constructive target is therefore q=1 forced rewrite with public two-epoch "
        "lanes and a collective witness family whose paid log2Z exceeds zero."
    )


def main() -> None:
    result = rows()
    print_rows(result)
    print_reading(result)


if __name__ == "__main__":
    main()
