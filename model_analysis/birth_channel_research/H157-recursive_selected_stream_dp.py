#!/usr/bin/env python3
"""H157 - recursive selected-stream DP.

H150 proved a two-pass version of the user's non-greedy idea:

    x <- c1 <- c2

where only the final visible stream c2 is stored, and c1 is a real seed-record
stream. H152/H156 then separated two traps:

* cloud mass is not a stored selected stream;
* filler completion parses, but destroys seed-bearing freshness.

This kernel keeps the stricter object:

    every intermediate layer is a visible seed-record stream
    no filler records
    no hidden rank/oracle/cloud channel

It computes the exact cheapest selected stream for P recursive passes in a tiny
B=1 domain. The parser is recursive: when an upper record emits its witness
bits, those bits are fed into the parser for the next-lower pass, so lower
passes may bundle across upper-record boundaries. That is the H150 advantage,
extended beyond two passes.

Two bounded caps are explicit:

* mid_cap: maximum visible size of any generated intermediate layer;
* final_cap: maximum visible size of the final stored stream.

Rows report whether extra recursive depth actually lowers the final visible
stream for all small targets, or merely increases support/state count while
still expanding.
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
from typing import Iterable, Protocol


HERE = Path(__file__).resolve().parent
H96_PATH = HERE / "H96-neutral_transfer_operator.py"
H96_SPEC = importlib.util.spec_from_file_location("h96_for_h157", H96_PATH)
if H96_SPEC is None or H96_SPEC.loader is None:
    raise RuntimeError(f"cannot load {H96_PATH}")
h96 = importlib.util.module_from_spec(H96_SPEC)
sys.modules[H96_SPEC.name] = h96
H96_SPEC.loader.exec_module(h96)


INF = 10**9


class Parser(Protocol):
    max_t: int

    def initial(self):
        ...

    def feed_bits(self, state, bits: str):
        ...

    def terminal_cost(self, state) -> int:
        ...

    def dominates(self, left, right) -> bool:
        ...

    def state_count(self, state) -> int:
        ...


@dataclass(frozen=True)
class BaseState:
    t: int


class BaseParser:
    """L0 parser: storing a bit string costs its visible length."""

    def __init__(self, max_t: int) -> None:
        self.max_t = max_t

    def initial(self) -> BaseState:
        return BaseState(0)

    def feed_bits(self, state: BaseState, bits: str) -> BaseState | None:
        t = state.t + len(bits)
        if t > self.max_t:
            return None
        return BaseState(t)

    def terminal_cost(self, state: BaseState) -> int:
        return state.t

    def dominates(self, left: BaseState, right: BaseState) -> bool:
        return left.t <= right.t

    def state_count(self, state: BaseState) -> int:
        return 1


@dataclass(frozen=True)
class RecState:
    t: int
    hlen: int
    tail: int
    f: tuple[frozenset[object], ...]


def add_pruned(frontier: set[object], candidate: object, lower: Parser) -> None:
    for existing in list(frontier):
        if lower.dominates(existing, candidate):
            return
        if lower.dominates(candidate, existing):
            frontier.remove(existing)
    frontier.add(candidate)


def prune_frontier(items: Iterable[object], lower: Parser) -> frozenset[object]:
    frontier: set[object] = set()
    for item in items:
        add_pruned(frontier, item, lower)
    return frozenset(frontier)


class RecursiveParser:
    """Parser for L_p, built from a parser for L_(p-1)."""

    def __init__(
        self,
        *,
        level: int,
        max_t: int,
        max_arity: int,
        by_value: list[list[list[h96.Record]]],
        lower: Parser,
    ) -> None:
        self.level = level
        self.max_t = max_t
        self.max_arity = max_arity
        self.by_value = by_value
        self.lower = lower
        self.mask = (1 << max_arity) - 1

    @lru_cache(maxsize=None)
    def initial(self) -> RecState:
        return RecState(
            t=0,
            hlen=0,
            tail=0,
            f=(frozenset([self.lower.initial()]),)
            + tuple(frozenset() for _ in range(self.max_arity)),
        )

    @lru_cache(maxsize=None)
    def feed_bit(self, state: RecState, bit: int) -> RecState | None:
        t = state.t + 1
        if t > self.max_t:
            return None
        hlen = min(self.max_arity, state.hlen + 1)
        tail = ((state.tail << 1) | bit) & self.mask
        g: list[set[object]] = [set() for _ in range(self.max_arity + 1)]

        for d in range(1, min(self.max_arity, t) + 1):
            g[d].update(state.f[d - 1])

        for arity in range(1, min(self.max_arity, t) + 1):
            value = tail & ((1 << arity) - 1)
            if not g[arity]:
                continue
            for prefix_state in g[arity]:
                for record in self.by_value[arity][value]:
                    next_state = self.lower.feed_bits(prefix_state, record.bits)
                    if next_state is not None:
                        add_pruned(g[0], next_state, self.lower)

        return RecState(
            t=t,
            hlen=hlen,
            tail=tail,
            f=tuple(prune_frontier(bucket, self.lower) for bucket in g),
        )

    def feed_bits(self, state: RecState, bits: str) -> RecState | None:
        current: RecState | None = state
        for char in bits:
            if current is None:
                return None
            current = self.feed_bit(current, 1 if char == "1" else 0)
        return current

    def terminal_cost(self, state: RecState) -> int:
        if not state.f[0]:
            return INF
        return min(self.lower.terminal_cost(item) for item in state.f[0])

    def dominates(self, left: RecState, right: RecState) -> bool:
        if left.t != right.t or left.hlen != right.hlen or left.tail != right.tail:
            return False
        for left_bucket, right_bucket in zip(left.f, right.f):
            for right_state in right_bucket:
                if not any(self.lower.dominates(left_state, right_state) for left_state in left_bucket):
                    return False
        return True

    def state_count(self, state: RecState) -> int:
        total = 1
        for bucket in state.f:
            total += sum(self.lower.state_count(item) for item in bucket)
        return total


@dataclass(frozen=True)
class WordResult:
    supported: bool
    best_final_bits: int | None
    terminal_states: int
    max_frontier_states: int
    max_nested_states: int


@dataclass(frozen=True)
class Row:
    atoms: int
    max_arity: int
    depth_bits: int
    passes: int
    mid_cap_bits: int
    final_cap_bits: int
    coverage: float
    mean_final_bits: float
    mean_gain: float
    mean_gain_per_atom: float
    positive_fraction: float
    mean_terminal_states: float
    max_frontier_states: int
    max_nested_states: int


def bits_for_word(word: int, atoms: int) -> str:
    return format(word, f"0{atoms}b")


def finite_mean(values: list[float]) -> float:
    finite = [value for value in values if math.isfinite(value)]
    return mean(finite) if finite else float("inf")


def span_value(word: int, start: int, arity: int, atoms: int) -> int:
    return h96.span_value(word, start, arity, atoms)


class RecursiveSelectedStreamKernel:
    def __init__(
        self,
        *,
        atoms: int,
        max_arity: int,
        depth_bits: int,
        cap_bits: int,
        final_cap_bits: int,
        seed: int,
    ) -> None:
        self.atoms = atoms
        self.max_arity = max_arity
        self.depth_bits = depth_bits
        self.cap_bits = cap_bits
        self.final_cap_bits = final_cap_bits
        self.by_value, _edge_weights, _edge_maxes = h96.build_record_family(
            block_bits=1,
            max_arity=max_arity,
            depth_bits=depth_bits,
            seed=seed,
        )

    def parser_for_passes(self, passes: int) -> Parser:
        parser: Parser = BaseParser(self.final_cap_bits)
        for level in range(1, passes + 1):
            parser = RecursiveParser(
                level=level,
                max_t=self.cap_bits,
                max_arity=self.max_arity,
                by_value=self.by_value,
                lower=parser,
            )
        return parser

    def word_result(self, word: int, passes: int) -> WordResult:
        lower = self.parser_for_passes(passes - 1)
        frontiers: list[set[object]] = [set() for _ in range(self.atoms + 1)]
        frontiers[0].add(lower.initial())
        max_frontier = 1
        max_nested = lower.state_count(lower.initial())

        for pos in range(self.atoms):
            for state in list(frontiers[pos]):
                for arity in range(1, min(self.max_arity, self.atoms - pos) + 1):
                    value = span_value(word, pos, arity, self.atoms)
                    for record in self.by_value[arity][value]:
                        next_state = lower.feed_bits(state, record.bits)
                        if next_state is None:
                            continue
                        add_pruned(frontiers[pos + arity], next_state, lower)
                        max_nested = max(max_nested, lower.state_count(next_state))
            max_frontier = max(max_frontier, *(len(frontier) for frontier in frontiers))

        terminal = frontiers[self.atoms]
        costs = [lower.terminal_cost(state) for state in terminal]
        finite_costs = [cost for cost in costs if cost < INF]
        if not finite_costs:
            return WordResult(
                supported=False,
                best_final_bits=None,
                terminal_states=len(terminal),
                max_frontier_states=max_frontier,
                max_nested_states=max_nested,
            )
        return WordResult(
            supported=True,
            best_final_bits=min(finite_costs),
            terminal_states=len(terminal),
            max_frontier_states=max_frontier,
            max_nested_states=max_nested,
        )

    def row(self, passes: int) -> Row:
        results = [self.word_result(word, passes) for word in range(1 << self.atoms)]
        supported = [result for result in results if result.supported and result.best_final_bits is not None]
        final_bits = [float(result.best_final_bits) for result in supported if result.best_final_bits is not None]
        gains = [self.atoms - value for value in final_bits]
        return Row(
            atoms=self.atoms,
            max_arity=self.max_arity,
            depth_bits=self.depth_bits,
            passes=passes,
            mid_cap_bits=self.cap_bits,
            final_cap_bits=self.final_cap_bits,
            coverage=len(supported) / len(results),
            mean_final_bits=finite_mean(final_bits),
            mean_gain=finite_mean(gains) if gains else float("-inf"),
            mean_gain_per_atom=(finite_mean(gains) / self.atoms if gains else float("-inf")),
            positive_fraction=(
                sum(1 for gain in gains if gain > 0.0) / len(gains) if gains else 0.0
            ),
            mean_terminal_states=finite_mean([float(result.terminal_states) for result in results]),
            max_frontier_states=max(result.max_frontier_states for result in results),
            max_nested_states=max(result.max_nested_states for result in results),
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
    print("== recursive selected-stream DP ==")
    print("Every layer is seed-bearing; no filler, rank cloud, or hidden selector.")
    print(
        f"{'N':>2} {'K':>2} {'D':>2} {'P':>2} {'mid':>4} {'final':>5} "
        f"{'cov':>7} {'final':>8} {'gain':>9} {'/atom':>9} "
        f"{'pos':>7} {'term':>8} {'frontier':>8} {'nested':>8}"
    )
    for row in rows:
        print(
            f"{row.atoms:2d} {row.max_arity:2d} {row.depth_bits:2d} "
            f"{row.passes:2d} {row.mid_cap_bits:4d} {row.final_cap_bits:5d} "
            f"{fmt(row.coverage):>7} {fmt(row.mean_final_bits):>8} "
            f"{fmt(row.mean_gain):>9} {fmt(row.mean_gain_per_atom):>9} "
            f"{fmt(row.positive_fraction):>7} "
            f"{fmt(row.mean_terminal_states):>8} "
            f"{row.max_frontier_states:8d} {row.max_nested_states:8d}"
        )
    print()


def print_reading(rows: list[Row]) -> None:
    print("== reading ==")
    full = [row for row in rows if row.coverage == 1.0]
    if full:
        best = max(full, key=lambda row: row.mean_gain)
        print(
            f"Best full-coverage row: N={best.atoms},K={best.max_arity},"
            f"D={best.depth_bits},P={best.passes},mid={best.mid_cap_bits},"
            f"final={best.final_cap_bits}; "
            f"mean gain {fmt(best.mean_gain)} bits/word."
        )
    else:
        best = max(rows, key=lambda row: (row.coverage, row.mean_gain))
        print(
            f"No full-coverage row. Best support row has coverage "
            f"{fmt(best.coverage)} and mean gain {fmt(best.mean_gain)} bits/word."
        )

    positive = [row for row in full if row.mean_gain > 0.0]
    if positive:
        row = max(positive, key=lambda item: item.mean_gain)
        print(
            "A positive selected-stream row exists in this tiny closed language. "
            f"It needs immediate follow-up at larger N and held-out seeds: "
            f"P={row.passes}, mid={row.mid_cap_bits}, "
            f"final={row.final_cap_bits}, gain={fmt(row.mean_gain)}."
        )
    else:
        print(
            "In this bounded exact family, adding recursive selected depth does "
            "not make roughly-all targets smaller. Non-greedy closure is lawful "
            "here, but the visible seed-bearing strings still cost more than the "
            "raw tiny targets."
        )
    print(
        "The cap columns are part of the claim: raising mid_cap allows larger "
        "upward detours, while final_cap bounds the exact search. They are not "
        "hidden stop-time channels; only final visible record bits are counted."
    )


def default_jobs(args: argparse.Namespace) -> list[tuple[int, int, int, int, int]]:
    if args.job:
        jobs: list[tuple[int, int, int, int, int]] = []
        for item in args.job:
            parts = item.split(",")
            if len(parts) == 4:
                atoms, max_arity, depth_bits, cap_bits = parts
                final_cap_bits = int(cap_bits) * 2
            elif len(parts) == 5:
                atoms, max_arity, depth_bits, cap_bits, final_cap_bits = parts
                final_cap_bits = int(final_cap_bits)
            else:
                raise ValueError("--job must be N,K,D,mid_cap[,final_cap]")
            jobs.append(
                (
                    int(atoms),
                    int(max_arity),
                    int(depth_bits),
                    int(cap_bits),
                    final_cap_bits,
                )
            )
        return jobs
    return [
        (3, 3, 3, 18, 44),
        (4, 3, 4, 22, 52),
        (4, 4, 4, 24, 56),
        (5, 4, 4, 26, 60),
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", action="append", default=[], help="N,K,D,mid_cap[,final_cap]")
    parser.add_argument("--passes", type=int, action="append", default=[])
    parser.add_argument("--seed", type=int, default=146146)
    args = parser.parse_args()

    passes_values = args.passes or [1, 2, 3]
    rows: list[Row] = []
    for atoms, max_arity, depth_bits, cap_bits, final_cap_bits in default_jobs(args):
        kernel = RecursiveSelectedStreamKernel(
            atoms=atoms,
            max_arity=max_arity,
            depth_bits=depth_bits,
            cap_bits=cap_bits,
            final_cap_bits=final_cap_bits,
            seed=args.seed,
        )
        for passes in passes_values:
            rows.append(kernel.row(passes))
    print_rows(rows)
    print_reading(rows)


if __name__ == "__main__":
    main()
