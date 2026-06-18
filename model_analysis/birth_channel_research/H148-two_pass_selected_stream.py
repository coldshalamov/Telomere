#!/usr/bin/env python3
"""H148 - two-pass selected stream after slack superposition.

H146 measured non-greedy slack using a collective next-pass fertility score.
This file removes that optimism for a tiny exact domain:

    x --pass 1--> c1 --pass 2--> c2

Both arrows are actual paid visible record-string descriptions from the same
V1/J3D1 toy family. The final stored stream after two recursive passes is c2.
The decoder needs only the fixed pass count and the visible records.

The question is whether a larger intermediate c1 can be worthwhile because it
has a short selected parent c2.
"""

from __future__ import annotations

import argparse
import importlib.util
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from statistics import mean


HERE = Path(__file__).resolve().parent
H146_PATH = HERE / "H146-slack_superposition_transfer.py"
H146_SPEC = importlib.util.spec_from_file_location("h146_for_h148", H146_PATH)
if H146_SPEC is None or H146_SPEC.loader is None:
    raise RuntimeError(f"could not load {H146_PATH}")
h146 = importlib.util.module_from_spec(H146_SPEC)
sys.modules[H146_SPEC.name] = h146
H146_SPEC.loader.exec_module(h146)


@dataclass(frozen=True)
class PlainCandidate:
    bits: str
    cost: int


@dataclass(frozen=True)
class PairChoice:
    first: PlainCandidate
    second: PlainCandidate
    total_saving: float


@dataclass(frozen=True)
class StreamRow:
    atoms: int
    max_arity: int
    depth_bits: int
    slack1: int
    slack2: int
    pass1_coverage: float
    two_pass_coverage: float
    avg_first_candidates: float
    avg_second_candidates: float
    mean_first_len: float
    mean_final_len: float
    mean_total_saving: float
    mean_gain_per_atom: float
    best_word_saving: float
    positive_fraction: float


def finite_mean(values: list[float]) -> float:
    finite = [value for value in values if math.isfinite(value)]
    return mean(finite) if finite else float("-inf")


class TwoPassKernel:
    def __init__(
        self,
        *,
        atoms: int,
        max_arity: int,
        depth_bits: int,
        seed: int,
    ) -> None:
        self.atoms = atoms
        self.inner = h146.SuperpositionKernel(
            atoms=atoms,
            max_arity=max_arity,
            depth_bits=depth_bits,
            seed=seed,
            exact_random_len=0,
            random_samples=1,
        )

    def plain_candidates(self, bits: str, slack: int) -> list[PlainCandidate]:
        budget = len(bits) + slack
        best_by_bits: dict[str, PlainCandidate] = {}
        for description in self.inner.bounded_descriptions_for(bits, budget):
            candidate = PlainCandidate(bits=description.bits, cost=description.cost)
            old = best_by_bits.get(candidate.bits)
            if old is None or candidate.cost < old.cost:
                best_by_bits[candidate.bits] = candidate
        return list(best_by_bits.values())

    def best_pair(self, bits: str, slack1: int, slack2: int) -> tuple[PairChoice | None, int, int]:
        first_candidates = self.plain_candidates(bits, slack1)
        best: PairChoice | None = None
        total_second_candidates = 0
        for first in first_candidates:
            second_candidates = self.plain_candidates(first.bits, slack2)
            total_second_candidates += len(second_candidates)
            if not second_candidates:
                continue
            second = min(second_candidates, key=lambda item: (item.cost, item.bits))
            choice = PairChoice(
                first=first,
                second=second,
                total_saving=len(bits) - second.cost,
            )
            if best is None or (
                choice.total_saving,
                -choice.first.cost,
                -choice.second.cost,
                choice.first.bits,
                choice.second.bits,
            ) > (
                best.total_saving,
                -best.first.cost,
                -best.second.cost,
                best.first.bits,
                best.second.bits,
            ):
                best = choice
        return best, len(first_candidates), total_second_candidates

    def row(self, slack1: int, slack2: int) -> StreamRow:
        first_cover = 0
        second_cover = 0
        first_counts: list[float] = []
        second_counts: list[float] = []
        first_lens: list[float] = []
        final_lens: list[float] = []
        savings: list[float] = []

        for word in range(1 << self.atoms):
            bits = h146.word_bits(word, self.atoms)
            choice, first_count, second_count = self.best_pair(bits, slack1, slack2)
            if first_count:
                first_cover += 1
                first_counts.append(float(first_count))
            if choice is None:
                continue
            second_cover += 1
            second_counts.append(float(second_count))
            first_lens.append(float(choice.first.cost))
            final_lens.append(float(choice.second.cost))
            savings.append(choice.total_saving)

        total_words = 1 << self.atoms
        mean_saving = finite_mean(savings)
        return StreamRow(
            atoms=self.atoms,
            max_arity=self.inner.max_arity,
            depth_bits=self.inner.depth_bits,
            slack1=slack1,
            slack2=slack2,
            pass1_coverage=first_cover / total_words,
            two_pass_coverage=second_cover / total_words,
            avg_first_candidates=finite_mean(first_counts),
            avg_second_candidates=finite_mean(second_counts),
            mean_first_len=finite_mean(first_lens),
            mean_final_len=finite_mean(final_lens),
            mean_total_saving=mean_saving,
            mean_gain_per_atom=mean_saving / self.atoms,
            best_word_saving=max(savings) if savings else float("-inf"),
            positive_fraction=(
                sum(1 for value in savings if value > 0.0) / len(savings)
                if savings
                else 0.0
            ),
        )


def fmt(value: float) -> str:
    if value == float("inf"):
        return "inf"
    if value == float("-inf"):
        return "-inf"
    if abs(value) >= 1000.0 or (0.0 < abs(value) < 0.0001):
        return f"{value:.3e}"
    return f"{value:.6f}"


def print_rows(rows: list[StreamRow]) -> None:
    print("== two-pass selected stream ==")
    print("Both passes choose actual visible record strings. Final stored stream is pass-2 output.")
    print(
        f"{'N':>2} {'K':>2} {'D':>2} {'s1':>3} {'s2':>3} "
        f"{'cov1':>7} {'cov2':>7} {'c1':>8} {'c2':>8} "
        f"{'len1':>8} {'final':>8} {'saving':>9} {'/atom':>9} {'best':>8} {'pos':>7}"
    )
    for row in rows:
        print(
            f"{row.atoms:2d} {row.max_arity:2d} {row.depth_bits:2d} "
            f"{row.slack1:3d} {row.slack2:3d} "
            f"{fmt(row.pass1_coverage):>7} {fmt(row.two_pass_coverage):>7} "
            f"{fmt(row.avg_first_candidates):>8} {fmt(row.avg_second_candidates):>8} "
            f"{fmt(row.mean_first_len):>8} {fmt(row.mean_final_len):>8} "
            f"{fmt(row.mean_total_saving):>9} {fmt(row.mean_gain_per_atom):>9} "
            f"{fmt(row.best_word_saving):>8} {fmt(row.positive_fraction):>7}"
        )
    print()


def print_reading(rows: list[StreamRow]) -> None:
    full = [row for row in rows if row.two_pass_coverage == 1.0]
    print("== reading ==")
    if not full:
        print(
            "No tested row has complete two-pass support, so this is not yet a "
            "total-cover recursive codec."
        )
    else:
        best = max(full, key=lambda row: row.mean_total_saving)
        print(
            f"Best full-support row saves {best.mean_total_saving:.6f} bits/word "
            f"({best.mean_gain_per_atom:.6f} bits/atom)."
        )
        if best.mean_total_saving <= 0.0:
            print(
                "Even after allowing a larger intermediate, the exact selected "
                "second pass does not compress this family."
            )
        else:
            print(
                "This row is a positive exact two-pass toy and needs a larger "
                "held-out/random-control rerun before promotion."
            )
    print(
        "This is stricter than H146: collective future mass is replaced by a "
        "real selected final stream."
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--atoms", type=int, default=4)
    parser.add_argument("--max-arity", type=int, default=4)
    parser.add_argument("--depth-bits", type=int, default=7)
    parser.add_argument("--seed", type=int, default=146146)
    parser.add_argument("--slack", type=int, action="append", default=[])
    args = parser.parse_args()

    kernel = TwoPassKernel(
        atoms=args.atoms,
        max_arity=args.max_arity,
        depth_bits=args.depth_bits,
        seed=args.seed,
    )
    slacks = args.slack if args.slack else [8, 12]
    rows = [kernel.row(slack, slack) for slack in slacks]
    print_rows(rows)
    print_reading(rows)


if __name__ == "__main__":
    main()
