#!/usr/bin/env python3
"""H146 - slack superposition transfer.

This reopens the user's non-greedy "superposition" idea directly:

    do not take the first/cheapest valid replacement;
    keep the visible replacement that is slightly larger now if it is
    more fertile on the next pass.

The decoder does not receive the discarded alternatives. It reads only the
selected visible record string. The public rule is a search rule, not a side
channel.

This is an exact tiny kernel. It uses H96's paid V1/J3D1 record family over
1-bit atoms so record strings can themselves be treated as the next bit layer.
For each starting word x, it enumerates every paid description c of x with

    len(c) <= len(x) + slack

then compares:

* cheapest-now: minimize current visible length;
* future-only: maximize exact all-description saving of c next pass;
* two-pass: maximize current saving + exact next-pass collective saving.

The same-length random control asks whether the selected visible genotype is
actually more fertile than an arbitrary bit string of the same length. A real
breakthrough still has to scale this signal to production B/K/D and replace the
collective future-value bound with an actually selected next record stream.
"""

from __future__ import annotations

import argparse
import importlib.util
import math
import random
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from statistics import mean


HERE = Path(__file__).resolve().parent
H96_PATH = HERE / "H96-neutral_transfer_operator.py"
H96_SPEC = importlib.util.spec_from_file_location("h96_for_h146", H96_PATH)
if H96_SPEC is None or H96_SPEC.loader is None:
    raise RuntimeError(f"could not load {H96_PATH}")
h96 = importlib.util.module_from_spec(H96_SPEC)
sys.modules[H96_SPEC.name] = h96
H96_SPEC.loader.exec_module(h96)


@dataclass(frozen=True)
class Candidate:
    bits: str
    cost: int
    current_saving: float
    future_saving: float
    future_vs_random: float

    @property
    def two_pass_saving(self) -> float:
        return self.current_saving + self.future_saving


@dataclass(frozen=True)
class PolicyMeans:
    current: float
    future: float
    total: float
    future_vs_random: float
    selected_len: float


@dataclass(frozen=True)
class SlackRow:
    atoms: int
    max_arity: int
    depth_bits: int
    slack: int
    coverage: float
    avg_candidates: float
    cheapest: PolicyMeans
    future_only: PolicyMeans
    two_pass: PolicyMeans
    random_candidate: PolicyMeans
    two_pass_lift_over_cheapest: float
    two_pass_lift_over_random_candidate: float
    two_pass_gain_per_atom: float
    two_pass_missing_per_word: float


def word_bits(word: int, atoms: int) -> str:
    return format(word, f"0{atoms}b")


def finite_mean(values: list[float]) -> float:
    finite = [value for value in values if math.isfinite(value)]
    return mean(finite) if finite else float("-inf")


def finite_delta(left: float, right: float) -> float:
    if math.isfinite(left) and math.isfinite(right):
        return left - right
    return float("-inf")


class SuperpositionKernel:
    def __init__(
        self,
        *,
        atoms: int,
        max_arity: int,
        depth_bits: int,
        seed: int,
        exact_random_len: int,
        random_samples: int,
    ) -> None:
        self.atoms = atoms
        self.max_arity = max_arity
        self.depth_bits = depth_bits
        self.seed = seed
        self.exact_random_len = exact_random_len
        self.random_samples = random_samples
        self.by_value, self.edge_weights, self.edge_maxes = h96.build_record_family(
            block_bits=1,
            max_arity=max_arity,
            depth_bits=depth_bits,
            seed=seed,
        )

    @lru_cache(maxsize=None)
    def bounded_descriptions_for(self, bits: str, budget: int) -> tuple[h96.Description, ...]:
        """Enumerate exactly, but prune records once they exceed the slack budget."""

        word = h96.word_from_bits(bits)
        atoms = len(bits)
        descriptions: list[h96.Description] = []

        def rec(pos: int, weight: float, cost: int, out_bits: str) -> None:
            if cost > budget:
                return
            if pos == atoms:
                descriptions.append(h96.Description(weight=weight, cost=cost, bits=out_bits))
                return
            for arity in range(1, min(self.max_arity, atoms - pos) + 1):
                value = h96.span_value(word, pos, arity, atoms)
                for record in self.by_value[arity][value]:
                    next_cost = cost + record.cost
                    if next_cost <= budget:
                        rec(
                            pos + arity,
                            weight * record.weight,
                            next_cost,
                            out_bits + record.bits,
                        )

        rec(0, 1.0, 0, "")
        return tuple(descriptions)

    @lru_cache(maxsize=None)
    def future_saving(self, bits: str) -> float:
        total, _ = h96.all_description_mass_for_bits(
            bits,
            self.max_arity,
            self.edge_weights,
            self.edge_maxes,
        )
        if total <= 0.0:
            return float("-inf")
        return len(bits) + math.log2(total)

    @lru_cache(maxsize=None)
    def expected_random_future(self, length: int) -> float:
        if length <= self.exact_random_len:
            values = [
                self.future_saving(word_bits(word, length))
                for word in range(1 << length)
            ]
            return finite_mean(values)

        rng = random.Random(self.seed * 1_000_003 + length * 97)
        values: list[float] = []
        for _ in range(self.random_samples):
            bits = "".join("1" if rng.randrange(2) else "0" for _ in range(length))
            values.append(self.future_saving(bits))
        return finite_mean(values)

    def candidates_for(self, bits: str, slack: int) -> list[Candidate]:
        budget = len(bits) + slack
        best_by_bits: dict[str, Candidate] = {}
        for description in self.bounded_descriptions_for(bits, budget):
            future = self.future_saving(description.bits)
            if not math.isfinite(future):
                continue
            random_future = self.expected_random_future(len(description.bits))
            candidate = Candidate(
                bits=description.bits,
                cost=description.cost,
                current_saving=len(bits) - description.cost,
                future_saving=future,
                future_vs_random=future - random_future,
            )
            old = best_by_bits.get(description.bits)
            if old is None or candidate.two_pass_saving > old.two_pass_saving:
                best_by_bits[description.bits] = candidate
        return list(best_by_bits.values())

    @staticmethod
    def pick(candidates: list[Candidate], policy: str) -> Candidate:
        if policy == "cheapest":
            return max(
                candidates,
                key=lambda item: (
                    item.current_saving,
                    item.future_saving,
                    item.future_vs_random,
                    item.bits,
                ),
            )
        if policy == "future":
            return max(
                candidates,
                key=lambda item: (
                    item.future_saving,
                    item.current_saving,
                    item.future_vs_random,
                    item.bits,
                ),
            )
        if policy == "two_pass":
            return max(
                candidates,
                key=lambda item: (
                    item.two_pass_saving,
                    item.future_saving,
                    item.current_saving,
                    item.bits,
                ),
            )
        raise ValueError(f"unknown policy {policy}")

    @staticmethod
    def means(items: list[Candidate]) -> PolicyMeans:
        return PolicyMeans(
            current=finite_mean([item.current_saving for item in items]),
            future=finite_mean([item.future_saving for item in items]),
            total=finite_mean([item.two_pass_saving for item in items]),
            future_vs_random=finite_mean([item.future_vs_random for item in items]),
            selected_len=finite_mean([float(item.cost) for item in items]),
        )

    def row_for_slack(self, slack: int) -> SlackRow:
        cheapest: list[Candidate] = []
        future_only: list[Candidate] = []
        two_pass: list[Candidate] = []
        random_candidates: list[Candidate] = []
        candidate_counts: list[int] = []
        rng = random.Random(self.seed + slack * 7919)

        for word in range(1 << self.atoms):
            bits = word_bits(word, self.atoms)
            candidates = self.candidates_for(bits, slack)
            if not candidates:
                continue
            candidate_counts.append(len(candidates))
            cheapest.append(self.pick(candidates, "cheapest"))
            future_only.append(self.pick(candidates, "future"))
            two_pass.append(self.pick(candidates, "two_pass"))
            random_candidates.append(candidates[rng.randrange(len(candidates))])

        coverage = len(candidate_counts) / (1 << self.atoms)
        cheapest_means = self.means(cheapest)
        future_means = self.means(future_only)
        two_pass_means = self.means(two_pass)
        random_means = self.means(random_candidates)
        missing = max(0.0, -two_pass_means.total)
        return SlackRow(
            atoms=self.atoms,
            max_arity=self.max_arity,
            depth_bits=self.depth_bits,
            slack=slack,
            coverage=coverage,
            avg_candidates=finite_mean([float(count) for count in candidate_counts]),
            cheapest=cheapest_means,
            future_only=future_means,
            two_pass=two_pass_means,
            random_candidate=random_means,
            two_pass_lift_over_cheapest=finite_delta(two_pass_means.total, cheapest_means.total),
            two_pass_lift_over_random_candidate=finite_delta(two_pass_means.total, random_means.total),
            two_pass_gain_per_atom=two_pass_means.total / self.atoms,
            two_pass_missing_per_word=missing,
        )


def fmt(value: float) -> str:
    if value == float("inf"):
        return "inf"
    if value == float("-inf"):
        return "-inf"
    if abs(value) >= 1000.0 or (0.0 < abs(value) < 0.0001):
        return f"{value:.3e}"
    return f"{value:.6f}"


def print_rows(rows: list[SlackRow]) -> None:
    print("== slack superposition transfer ==")
    print(
        "The selected visible record string is the only output. Future score is "
        "exact all-description next-pass saving; random control is same length."
    )
    print(
        f"{'N':>2} {'K':>2} {'D':>2} {'s':>3} {'cov':>7} {'cand':>8} "
        f"{'cheap total':>12} {'2pass total':>12} {'2pass/atom':>11} "
        f"{'lift cheap':>11} {'lift random':>11} {'fert-rand':>10} "
        f"{'sel len':>8}"
    )
    for row in rows:
        print(
            f"{row.atoms:2d} {row.max_arity:2d} {row.depth_bits:2d} "
            f"{row.slack:3d} {fmt(row.coverage):>7} {fmt(row.avg_candidates):>8} "
            f"{fmt(row.cheapest.total):>12} {fmt(row.two_pass.total):>12} "
            f"{fmt(row.two_pass_gain_per_atom):>11} "
            f"{fmt(row.two_pass_lift_over_cheapest):>11} "
            f"{fmt(row.two_pass_lift_over_random_candidate):>11} "
            f"{fmt(row.two_pass.future_vs_random):>10} "
            f"{fmt(row.two_pass.selected_len):>8}"
        )
    print()


def print_best(rows: list[SlackRow]) -> None:
    full = [row for row in rows if row.coverage == 1.0]
    print("== best full-coverage rows ==")
    if not full:
        print("No full-coverage slack row in this tiny family.")
        print()
        return
    best = max(full, key=lambda row: row.two_pass.total)
    print(
        f"Best full row: N={best.atoms},K={best.max_arity},D={best.depth_bits},"
        f"s={best.slack}; two-pass total {best.two_pass.total:.6f} bits/word "
        f"({best.two_pass_gain_per_atom:.6f} bits/atom)."
    )
    print(
        f"Against cheapest-now it gains {best.two_pass_lift_over_cheapest:.6f} "
        f"bits/word; against random candidates it gains "
        f"{best.two_pass_lift_over_random_candidate:.6f} bits/word."
    )
    print(
        f"Selected genotypes have future fertility {best.two_pass.future_vs_random:.6f} "
        "bits above same-length random controls."
    )
    print()


def print_reading(rows: list[SlackRow]) -> None:
    full = [row for row in rows if row.coverage == 1.0]
    print("== reading ==")
    print(
        "Non-greedy slack is not a metadata hack here: the choice is fully "
        "visible as the selected record string, and discarded alternatives are "
        "not decoded or stored."
    )
    if not full:
        print(
            "The tested family does not even cover every starting word at the "
            "requested slacks, so it cannot be a total-cover recursive codec yet."
        )
        return
    best = max(full, key=lambda row: row.two_pass.total)
    if best.two_pass.total > 0.0:
        print(
            "This tiny collective-bound toy crosses on a two-pass objective. "
            "That is a live target, not a solution: the next pass still has to "
            "emit an actual selected record stream, not only spend collective "
            "Kraft mass."
        )
    else:
        print(
            "The non-greedy lift is real but insufficient in this exact toy. "
            f"The nearest full row still misses by {best.two_pass_missing_per_word:.6f} "
            "bits/word after using future fertility."
        )
    print(
        "If the selected future fertility stays above same-length random controls "
        "when scaled up, the next kernel should replace the collective future "
        "score with a bounded recurrent selected-stream pass."
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--atoms", type=int, default=5)
    parser.add_argument("--max-arity", type=int, default=5)
    parser.add_argument("--depth-bits", type=int, default=6)
    parser.add_argument("--seed", type=int, default=146146)
    parser.add_argument("--slack", type=int, action="append", default=[])
    parser.add_argument("--exact-random-len", type=int, default=12)
    parser.add_argument("--random-samples", type=int, default=512)
    args = parser.parse_args()

    kernel = SuperpositionKernel(
        atoms=args.atoms,
        max_arity=args.max_arity,
        depth_bits=args.depth_bits,
        seed=args.seed,
        exact_random_len=args.exact_random_len,
        random_samples=args.random_samples,
    )
    slacks = args.slack if args.slack else [0, 1, 2, 3, 4, 6, 8, 12]
    rows = [kernel.row_for_slack(slack) for slack in slacks]
    print_rows(rows)
    print_best(rows)
    print_reading(rows)


if __name__ == "__main__":
    main()
