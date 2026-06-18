#!/usr/bin/env python3
"""H152 - superposition gap ledger.

The user is right that an optimal recursive witness need not greedily shrink at
every layer. A first visible replacement can bloat, then a later selected stream
can shrink it. That is legal if the final stored stream itself decodes through
the bloated intermediate into the target.

This kernel separates three quantities that are easy to conflate:

* greedy-visible: choose the shortest current intermediate c that decodes to x;
* non-greedy-visible: choose any allowed c whose cheapest next selected stream
  y is shortest, so y -> c -> x is an honest stateless two-pass witness;
* cloud/oracle: sum the whole future description mass over all allowed c. The
  gap between cloud mass and the best selected y is the rank/arithmetic channel
  that would have to be paid or made into a real public distribution.

The model is tiny and exact over B=1 words using the H96 paid V1/J3D1 record
family. It does not run Telomere compression tests.
"""

from __future__ import annotations

import argparse
import importlib.util
import math
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from statistics import mean


HERE = Path(__file__).resolve().parent
H96_PATH = HERE / "H96-neutral_transfer_operator.py"
H96_SPEC = importlib.util.spec_from_file_location("h96_for_h152", H96_PATH)
if H96_SPEC is None or H96_SPEC.loader is None:
    raise RuntimeError(f"could not load {H96_PATH}")
h96 = importlib.util.module_from_spec(H96_SPEC)
sys.modules[H96_SPEC.name] = h96
H96_SPEC.loader.exec_module(h96)


@dataclass(frozen=True)
class WordRow:
    word: int
    first_candidates: int
    first_supported: bool
    selected_supported: bool
    greedy_mid_bits: int | None
    greedy_final_bits: int | None
    best_mid_bits: int | None
    best_final_bits: int | None
    cloud_bits: float
    selected_gain: float
    greedy_gain: float
    visible_lift_over_greedy: float
    cloud_gain: float
    cloud_gap_bits: float
    best_duplicate_gap_bits: float
    non_greedy_mid: bool


@dataclass(frozen=True)
class SlackRow:
    atoms: int
    max_arity: int
    depth_bits: int
    slack: int
    first_coverage: float
    selected_coverage: float
    average_candidates: float
    greedy_mid_bits: float
    best_mid_bits: float
    greedy_final_bits: float
    best_final_bits: float
    selected_gain: float
    greedy_gain: float
    visible_lift_over_greedy: float
    cloud_gain: float
    cloud_gap_bits: float
    best_duplicate_gap_bits: float
    non_greedy_mid_fraction: float
    positive_selected_fraction: float


def bits_for_word(word: int, atoms: int) -> str:
    return format(word, f"0{atoms}b")


def finite_mean(values: list[float]) -> float:
    finite = [value for value in values if math.isfinite(value)]
    return mean(finite) if finite else float("inf")


def neg_log2_weight(weight: float) -> float:
    if weight <= 0.0:
        return float("inf")
    return -math.log2(weight)


class SuperpositionGapKernel:
    def __init__(self, *, atoms: int, max_arity: int, depth_bits: int, seed: int) -> None:
        self.atoms = atoms
        self.max_arity = max_arity
        self.depth_bits = depth_bits
        self.seed = seed
        self.by_value, self.edge_weights, self.edge_maxes = h96.build_record_family(
            block_bits=1,
            max_arity=max_arity,
            depth_bits=depth_bits,
            seed=seed,
        )

    @lru_cache(maxsize=None)
    def bounded_descriptions_for(self, bits: str, budget: int) -> tuple[h96.Description, ...]:
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
    def future_mass_and_best(self, bits: str) -> tuple[float, float]:
        return h96.all_description_mass_for_bits(
            bits,
            self.max_arity,
            self.edge_weights,
            self.edge_maxes,
        )

    def row_for_word(self, word: int, slack: int) -> WordRow:
        target_bits = bits_for_word(word, self.atoms)
        budget = self.atoms + slack
        descriptions = self.bounded_descriptions_for(target_bits, budget)
        if not descriptions:
            return WordRow(
                word=word,
                first_candidates=0,
                first_supported=False,
                selected_supported=False,
                greedy_mid_bits=None,
                greedy_final_bits=None,
                best_mid_bits=None,
                best_final_bits=None,
                cloud_bits=float("inf"),
                selected_gain=float("-inf"),
                greedy_gain=float("-inf"),
                visible_lift_over_greedy=float("-inf"),
                cloud_gain=float("-inf"),
                cloud_gap_bits=float("inf"),
                best_duplicate_gap_bits=float("inf"),
                non_greedy_mid=False,
            )

        greedy = min(descriptions, key=lambda item: (item.cost, item.bits))
        cloud_mass = 0.0
        best_weight = 0.0
        best_mid_cost: int | None = None
        greedy_best_weight = 0.0
        best_duplicate_gap = 0.0

        # De-duplicate identical visible intermediates; different first paths to
        # the same c are not stored in the two-pass final file.
        seen: set[str] = set()
        for description in descriptions:
            if description.bits in seen:
                continue
            seen.add(description.bits)
            future_total, future_best = self.future_mass_and_best(description.bits)
            if future_total <= 0.0:
                continue
            cloud_mass += future_total
            if future_best > best_weight:
                best_weight = future_best
                best_mid_cost = description.cost
            if description.bits == greedy.bits:
                greedy_best_weight = future_best
            if future_best > 0.0:
                best_duplicate_gap = max(
                    best_duplicate_gap,
                    math.log2(future_total / future_best),
                )

        if best_weight <= 0.0:
            return WordRow(
                word=word,
                first_candidates=len(seen),
                first_supported=True,
                selected_supported=False,
                greedy_mid_bits=greedy.cost,
                greedy_final_bits=None,
                best_mid_bits=None,
                best_final_bits=None,
                cloud_bits=float("inf"),
                selected_gain=float("-inf"),
                greedy_gain=float("-inf"),
                visible_lift_over_greedy=float("-inf"),
                cloud_gain=float("-inf"),
                cloud_gap_bits=float("inf"),
                best_duplicate_gap_bits=float("inf"),
                non_greedy_mid=False,
            )

        best_final = neg_log2_weight(best_weight)
        greedy_final = neg_log2_weight(greedy_best_weight)
        cloud_bits = neg_log2_weight(cloud_mass)
        selected_gain = self.atoms - best_final
        greedy_gain = self.atoms - greedy_final
        cloud_gain = self.atoms - cloud_bits
        cloud_gap = math.log2(cloud_mass / best_weight)
        visible_lift = greedy_final - best_final if math.isfinite(greedy_final) else float("inf")
        non_greedy = best_mid_cost is not None and best_mid_cost != greedy.cost

        return WordRow(
            word=word,
            first_candidates=len(seen),
            first_supported=True,
            selected_supported=True,
            greedy_mid_bits=greedy.cost,
            greedy_final_bits=int(round(greedy_final)) if math.isfinite(greedy_final) else None,
            best_mid_bits=best_mid_cost,
            best_final_bits=int(round(best_final)),
            cloud_bits=cloud_bits,
            selected_gain=selected_gain,
            greedy_gain=greedy_gain,
            visible_lift_over_greedy=visible_lift,
            cloud_gain=cloud_gain,
            cloud_gap_bits=cloud_gap,
            best_duplicate_gap_bits=best_duplicate_gap,
            non_greedy_mid=non_greedy,
        )

    def row_for_slack(self, slack: int) -> SlackRow:
        rows = [self.row_for_word(word, slack) for word in range(1 << self.atoms)]
        selected = [row for row in rows if row.selected_supported]
        first = [row for row in rows if row.first_supported]
        return SlackRow(
            atoms=self.atoms,
            max_arity=self.max_arity,
            depth_bits=self.depth_bits,
            slack=slack,
            first_coverage=len(first) / len(rows),
            selected_coverage=len(selected) / len(rows),
            average_candidates=finite_mean([float(row.first_candidates) for row in first]),
            greedy_mid_bits=finite_mean([float(row.greedy_mid_bits) for row in selected if row.greedy_mid_bits is not None]),
            best_mid_bits=finite_mean([float(row.best_mid_bits) for row in selected if row.best_mid_bits is not None]),
            greedy_final_bits=finite_mean([float(row.greedy_final_bits) for row in selected if row.greedy_final_bits is not None]),
            best_final_bits=finite_mean([float(row.best_final_bits) for row in selected if row.best_final_bits is not None]),
            selected_gain=finite_mean([row.selected_gain for row in selected]),
            greedy_gain=finite_mean([row.greedy_gain for row in selected]),
            visible_lift_over_greedy=finite_mean([row.visible_lift_over_greedy for row in selected]),
            cloud_gain=finite_mean([row.cloud_gain for row in selected]),
            cloud_gap_bits=finite_mean([row.cloud_gap_bits for row in selected]),
            best_duplicate_gap_bits=finite_mean([row.best_duplicate_gap_bits for row in selected]),
            non_greedy_mid_fraction=(
                sum(1 for row in selected if row.non_greedy_mid) / len(selected)
                if selected
                else 0.0
            ),
            positive_selected_fraction=sum(1 for row in rows if row.selected_gain > 0.0) / len(rows),
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
    print("== superposition gap ledger ==")
    print("Means are over selected-supported words unless the column is coverage/fraction.")
    print(
        f"{'N':>2} {'K':>2} {'D':>2} {'s':>3} {'cov1':>7} {'cov2':>7} "
        f"{'cand':>8} {'gMid':>7} {'bMid':>7} {'gFinal':>8} "
        f"{'bFinal':>8} {'selGain':>9} {'visLift':>9} {'cloudG':>9} "
        f"{'cloudGap':>9} {'dupGap':>8} {'nonG':>7} {'pos':>7}"
    )
    for row in rows:
        print(
            f"{row.atoms:2d} {row.max_arity:2d} {row.depth_bits:2d} "
            f"{row.slack:3d} {fmt(row.first_coverage):>7} "
            f"{fmt(row.selected_coverage):>7} {fmt(row.average_candidates):>8} "
            f"{fmt(row.greedy_mid_bits):>7} {fmt(row.best_mid_bits):>7} "
            f"{fmt(row.greedy_final_bits):>8} {fmt(row.best_final_bits):>8} "
            f"{fmt(row.selected_gain):>9} {fmt(row.visible_lift_over_greedy):>9} "
            f"{fmt(row.cloud_gain):>9} {fmt(row.cloud_gap_bits):>9} "
            f"{fmt(row.best_duplicate_gap_bits):>8} "
            f"{fmt(row.non_greedy_mid_fraction):>7} "
            f"{fmt(row.positive_selected_fraction):>7}"
        )
    print()


def print_reading(rows: list[SlackRow]) -> None:
    print("== reading ==")
    if not rows:
        print("No rows.")
        return
    best = max(rows, key=lambda row: (row.selected_coverage, row.selected_gain))
    print(
        f"Best selected-support row: slack={best.slack}, cov2={best.selected_coverage:.6f}, "
        f"mean final={fmt(best.best_final_bits)} bits for {best.atoms} input bits."
    )
    print(
        f"Non-greedy visible selection improves over greedy-now by "
        f"{fmt(best.visible_lift_over_greedy)} bits on supported words, "
        f"with non-greedy intermediates chosen {best.non_greedy_mid_fraction:.6f} of the time."
    )
    print(
        f"The collective cloud is {fmt(best.cloud_gap_bits)} bits better than the "
        "best explicit final stream on average. That gap is not free; it is the "
        "rank/arithmetic channel needed to use the whole superposition instead "
        "of one visible witness."
    )
    if best.selected_coverage == 1.0 and best.selected_gain > 0.0:
        print("A positive full-support visible two-pass row was found.")
    else:
        print(
            "No positive full-support visible two-pass row appears in this tiny "
            "paid family. The useful signal is the measured non-greedy lift, "
            "not yet a maintained recursive compression mechanism."
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--atoms", type=int, default=4)
    parser.add_argument("--max-arity", type=int, default=4)
    parser.add_argument("--depth-bits", type=int, default=7)
    parser.add_argument("--seed", type=int, default=146146)
    parser.add_argument("--slack", type=int, action="append", default=[])
    args = parser.parse_args()

    kernel = SuperpositionGapKernel(
        atoms=args.atoms,
        max_arity=args.max_arity,
        depth_bits=args.depth_bits,
        seed=args.seed,
    )
    slacks = args.slack if args.slack else [8, 12, 16, 20]
    rows = [kernel.row_for_slack(slack) for slack in slacks]
    print_rows(rows)
    print_reading(rows)


if __name__ == "__main__":
    main()
