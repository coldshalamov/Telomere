#!/usr/bin/env python3
"""H150 - selected-stream min-plus DP.

H148 tested two selected passes by brute force:

    x --selected record stream c1--> c1 --selected record stream c2--> c2

and quickly ran into second-pass enumeration. H150 replaces the second-pass
enumeration with an online min-plus parser state. It is still exact for P=2:
the final stream length is the cheapest actual record-stream description of
the generated intermediate c1.

No discarded alternatives are stored. The public rule is fixed: choose the
accepted path with minimum final length, then deterministic tie-breakers.
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
H96_SPEC = importlib.util.spec_from_file_location("h96_for_h150", H96_PATH)
if H96_SPEC is None or H96_SPEC.loader is None:
    raise RuntimeError(f"could not load {H96_PATH}")
h96 = importlib.util.module_from_spec(H96_SPEC)
sys.modules[H96_SPEC.name] = h96
H96_SPEC.loader.exec_module(h96)


INF = 10**9


@dataclass(frozen=True)
class ParserState:
    t: int
    hlen: int
    tail: int
    f: tuple[int, ...]


@dataclass(frozen=True)
class WordResult:
    pass1_supported: bool
    pass2_supported: bool
    best_final_bits: int | None
    best_intermediate_bits: int | None
    accepted_states: int
    terminal_states: int
    max_frontier_states: int


@dataclass(frozen=True)
class Row:
    atoms: int
    max_arity: int
    depth_bits: int
    slack1: int
    slack2: int
    pass1_coverage: float
    pass2_coverage: float
    mean_final_bits: float
    mean_intermediate_bits: float
    mean_gain: float
    mean_gain_per_atom: float
    positive_fraction: float
    mean_terminal_states: float
    mean_accepted_states: float
    max_frontier_states: int


def bits_for_word(word: int, atoms: int) -> str:
    return format(word, f"0{atoms}b")


def finite_mean(values: list[float]) -> float:
    finite = [value for value in values if math.isfinite(value)]
    return mean(finite) if finite else float("inf")


class SelectedStreamDP:
    def __init__(self, *, atoms: int, max_arity: int, depth_bits: int, seed: int) -> None:
        self.atoms = atoms
        self.max_arity = max_arity
        self.depth_bits = depth_bits
        self.by_value, _edge_weights, _edge_maxes = h96.build_record_family(
            block_bits=1,
            max_arity=max_arity,
            depth_bits=depth_bits,
            seed=seed,
        )
        self.min_cost: list[list[int]] = [[]]
        for arity in range(1, max_arity + 1):
            costs = [INF] * (1 << arity)
            for value in range(1 << arity):
                if self.by_value[arity][value]:
                    costs[value] = min(record.cost for record in self.by_value[arity][value])
            self.min_cost.append(costs)
        self.mask = (1 << max_arity) - 1

    @staticmethod
    def span_value(word: int, start: int, arity: int, atoms: int) -> int:
        return h96.span_value(word, start, arity, atoms)

    @lru_cache(maxsize=None)
    def feed_bit(self, state: ParserState, bit: int) -> ParserState:
        t = state.t + 1
        hlen = min(self.max_arity, state.hlen + 1)
        tail = ((state.tail << 1) | bit) & self.mask
        g = [INF] * (self.max_arity + 1)

        for d in range(1, min(self.max_arity, t) + 1):
            g[d] = state.f[d - 1]

        best = INF
        for arity in range(1, min(self.max_arity, t) + 1):
            prefix_cost = g[arity]
            if prefix_cost >= INF:
                continue
            value = tail & ((1 << arity) - 1)
            record_cost = self.min_cost[arity][value]
            if record_cost < INF:
                best = min(best, prefix_cost + record_cost)
        g[0] = best
        return ParserState(t=t, hlen=hlen, tail=tail, f=tuple(g))

    def feed_bits(self, state: ParserState, bits: str, max_t: int) -> ParserState | None:
        current = state
        if current.t + len(bits) > max_t:
            return None
        for char in bits:
            current = self.feed_bit(current, 1 if char == "1" else 0)
        return current

    @staticmethod
    def dominated(candidate: ParserState, existing: ParserState) -> bool:
        if (
            candidate.t != existing.t
            or candidate.hlen != existing.hlen
            or candidate.tail != existing.tail
        ):
            return False
        return all(e <= c for c, e in zip(candidate.f, existing.f))

    def add_state(self, states: set[ParserState], candidate: ParserState) -> None:
        for existing in list(states):
            if self.dominated(candidate, existing):
                return
            if self.dominated(existing, candidate):
                states.remove(existing)
        states.add(candidate)

    def word_result(self, word: int, slack1: int, slack2: int) -> WordResult:
        max_intermediate = self.atoms + slack1
        initial = ParserState(
            t=0,
            hlen=0,
            tail=0,
            f=tuple([0] + [INF] * self.max_arity),
        )
        frontiers: list[set[ParserState]] = [set() for _ in range(self.atoms + 1)]
        frontiers[0].add(initial)
        max_frontier = 1

        for pos in range(self.atoms):
            for state in list(frontiers[pos]):
                for arity in range(1, min(self.max_arity, self.atoms - pos) + 1):
                    value = self.span_value(word, pos, arity, self.atoms)
                    for record in self.by_value[arity][value]:
                        next_state = self.feed_bits(state, record.bits, max_intermediate)
                        if next_state is not None:
                            self.add_state(frontiers[pos + arity], next_state)
            max_frontier = max(max_frontier, *(len(frontier) for frontier in frontiers))

        terminals = frontiers[self.atoms]
        accepted = [
            state
            for state in terminals
            if state.f[0] < INF and state.f[0] <= state.t + slack2
        ]
        if not accepted:
            return WordResult(
                pass1_supported=bool(terminals),
                pass2_supported=False,
                best_final_bits=None,
                best_intermediate_bits=None,
                accepted_states=0,
                terminal_states=len(terminals),
                max_frontier_states=max_frontier,
            )
        best = min(accepted, key=lambda state: (state.f[0], state.t, state.tail, state.f))
        return WordResult(
            pass1_supported=True,
            pass2_supported=True,
            best_final_bits=best.f[0],
            best_intermediate_bits=best.t,
            accepted_states=len(accepted),
            terminal_states=len(terminals),
            max_frontier_states=max_frontier,
        )

    def row(self, slack1: int, slack2: int) -> Row:
        results = [self.word_result(word, slack1, slack2) for word in range(1 << self.atoms)]
        supported = [result for result in results if result.pass2_supported]
        final_bits = [float(result.best_final_bits) for result in supported if result.best_final_bits is not None]
        intermediate_bits = [
            float(result.best_intermediate_bits)
            for result in supported
            if result.best_intermediate_bits is not None
        ]
        gains = [self.atoms - value for value in final_bits]
        return Row(
            atoms=self.atoms,
            max_arity=self.max_arity,
            depth_bits=self.depth_bits,
            slack1=slack1,
            slack2=slack2,
            pass1_coverage=sum(1 for result in results if result.pass1_supported) / len(results),
            pass2_coverage=len(supported) / len(results),
            mean_final_bits=finite_mean(final_bits),
            mean_intermediate_bits=finite_mean(intermediate_bits),
            mean_gain=finite_mean(gains) if gains else float("-inf"),
            mean_gain_per_atom=(finite_mean(gains) / self.atoms if gains else float("-inf")),
            positive_fraction=(
                sum(1 for gain in gains if gain > 0.0) / len(gains) if gains else 0.0
            ),
            mean_terminal_states=finite_mean([float(result.terminal_states) for result in results]),
            mean_accepted_states=finite_mean([float(result.accepted_states) for result in results]),
            max_frontier_states=max(result.max_frontier_states for result in results),
        )


def fmt(value: float) -> str:
    if value == float("inf"):
        return "inf"
    if value == float("-inf"):
        return "-inf"
    if abs(value) >= 1000.0 or (0.0 < abs(value) < 0.0001):
        return f"{value:.3e}"
    return f"{value:.6f}"


def print_rows(rows: list[Row]) -> None:
    print("== selected-stream min-plus DP ==")
    print("Exact P=2 selected final stream length; no collective future score.")
    print(
        f"{'N':>2} {'K':>2} {'D':>2} {'s1':>3} {'s2':>3} "
        f"{'cov1':>7} {'cov2':>7} {'final':>8} {'mid':>8} "
        f"{'gain':>9} {'/atom':>9} {'pos':>7} {'term':>8} "
        f"{'accept':>8} {'max states':>10}"
    )
    for row in rows:
        print(
            f"{row.atoms:2d} {row.max_arity:2d} {row.depth_bits:2d} "
            f"{row.slack1:3d} {row.slack2:3d} "
            f"{fmt(row.pass1_coverage):>7} {fmt(row.pass2_coverage):>7} "
            f"{fmt(row.mean_final_bits):>8} {fmt(row.mean_intermediate_bits):>8} "
            f"{fmt(row.mean_gain):>9} {fmt(row.mean_gain_per_atom):>9} "
            f"{fmt(row.positive_fraction):>7} {fmt(row.mean_terminal_states):>8} "
            f"{fmt(row.mean_accepted_states):>8} {row.max_frontier_states:10d}"
        )
    print()


def print_reading(rows: list[Row]) -> None:
    print("== reading ==")
    if not rows:
        print("No rows.")
        return
    best_support = max(rows, key=lambda row: (row.pass2_coverage, -row.mean_final_bits))
    print(
        f"Best support row has pass2 coverage {best_support.pass2_coverage:.6f} "
        f"with mean final length {fmt(best_support.mean_final_bits)} bits."
    )
    positive = [row for row in rows if row.pass2_coverage == 1.0 and row.mean_gain > 0.0]
    if positive:
        best = max(positive, key=lambda row: row.mean_gain)
        print(
            f"Positive full-support row found: slack=({best.slack1},{best.slack2}), "
            f"mean gain {best.mean_gain:.6f} bits."
        )
    else:
        print(
            "No positive full-support row in this bounded DP. If support exists, "
            "the final selected stream is still longer than the original atoms."
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--atoms", type=int, default=4)
    parser.add_argument("--max-arity", type=int, default=4)
    parser.add_argument("--depth-bits", type=int, default=7)
    parser.add_argument("--seed", type=int, default=146146)
    parser.add_argument("--slack", type=int, action="append", default=[])
    args = parser.parse_args()

    kernel = SelectedStreamDP(
        atoms=args.atoms,
        max_arity=args.max_arity,
        depth_bits=args.depth_bits,
        seed=args.seed,
    )
    slacks = args.slack if args.slack else [8, 12, 16, 20]
    rows = [kernel.row(slack, slack) for slack in slacks]
    print_rows(rows)
    print_reading(rows)


if __name__ == "__main__":
    main()
