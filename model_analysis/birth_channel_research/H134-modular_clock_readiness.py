#!/usr/bin/env python3
"""H134 - modular/CRT clock readiness ledger.

Question: can even/odd, CRT residues, sign lanes, Fibonacci-like registers, or
other modular clocks tell the decoder a record's birth/open epoch more cheaply
than an explicit pass tag?

If a seed class carries residues modulo m_1..m_k, a record selected for a
specific residue vector loses seed supply by prod(m_i). The number of epochs
distinguished is at most lcm(m_i). Thus:

    cost >= log2(prod m_i) >= log2(lcm m_i) >= log2(P)

for P live epochs. Public position/lane clocks can make the class visible, but
then only 1/P of slots are eligible, which is the same match-supply currency.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from functools import reduce
from math import gcd


@dataclass(frozen=True)
class ClockRow:
    epochs: int
    moduli: tuple[int, ...]
    lcm_value: int
    product: int
    cost_bits: float
    ideal_bits: float
    overhead_bits: float
    note: str


def lcm(a: int, b: int) -> int:
    return a // gcd(a, b) * b


def lcm_many(values: tuple[int, ...]) -> int:
    return reduce(lcm, values, 1)


def best_moduli(epochs: int, max_modulus: int = 32, max_factors: int = 5) -> tuple[int, ...]:
    best: tuple[int, ...] | None = None
    best_product: int | None = None
    candidates = list(range(2, max_modulus + 1))
    for count in range(1, max_factors + 1):
        for combo in itertools.combinations_with_replacement(candidates, count):
            lcm_value = lcm_many(combo)
            if lcm_value < epochs:
                continue
            product = math.prod(combo)
            if best_product is None or product < best_product or (product == best_product and combo < best):
                best = combo
                best_product = product
    if best is None:
        return (epochs,)
    return best


def row_for(epochs: int) -> ClockRow:
    moduli = best_moduli(epochs)
    lcm_value = lcm_many(moduli)
    product = math.prod(moduli)
    cost = math.log2(product)
    ideal = math.log2(epochs)
    overhead = cost - ideal
    if lcm_value == epochs and product == epochs:
        note = "exact, no better than pass tag"
    elif product == lcm_value:
        note = "coprime CRT, equals log2(lcm)"
    else:
        note = "non-coprime residues waste bits"
    return ClockRow(epochs, moduli, lcm_value, product, cost, ideal, overhead, note)


def zeckendorf_count(limit: int) -> int:
    """Number of subsets with no adjacent Fibonacci terms below a limit.

    This is a toy for Fibonacci/Zeckendorf readiness registers. It counts
    symbols, not compression. A uniform choice among M symbols still costs
    at least log2(M) bits through seed supply or explicit code length.
    """

    fibs = [1, 2]
    while fibs[-1] + fibs[-2] <= limit:
        fibs.append(fibs[-1] + fibs[-2])

    count = 0

    def dfs(index: int, prev_used: bool) -> None:
        nonlocal count
        if index == len(fibs):
            count += 1
            return
        dfs(index + 1, False)
        if not prev_used:
            dfs(index + 1, True)

    dfs(0, False)
    return count


def print_rows(rows: list[ClockRow]) -> None:
    print("== modular/CRT clock readiness ledger ==")
    print("Seed-class residue cost is log2(product moduli); distinguishable epochs are <= lcm.")
    print(
        f"{'P live':>7} {'moduli':>18} {'lcm':>7} {'prod':>8} "
        f"{'cost':>9} {'ideal':>9} {'over':>9} note"
    )
    for item in rows:
        print(
            f"{item.epochs:7d} {str(item.moduli):>18} {item.lcm_value:7d} "
            f"{item.product:8d} {item.cost_bits:9.6f} {item.ideal_bits:9.6f} "
            f"{item.overhead_bits:9.6f} {item.note}"
        )
    print()


def print_lifetime_rows() -> None:
    print("== finite lifetime target ==")
    print("If public mechanics bound record lifetime to L, only L+1 ages need discrimination.")
    print(f"{'max lifetime L':>14} {'ages':>7} {'min bits':>10} {'reading'}")
    for lifetime in (1, 2, 3, 7, 15, 63):
        ages = lifetime + 1
        bits = math.log2(ages)
        reading = "two-epoch parity" if lifetime == 1 else "finite-age class"
        print(f"{lifetime:14d} {ages:7d} {bits:10.6f} {reading}")
    print()


def print_zeckendorf_rows() -> None:
    print("== Fibonacci/Zeckendorf register sanity check ==")
    print("Richer register grammars change representation, not the entropy floor.")
    print(f"{'limit':>7} {'symbols':>9} {'floor bits':>11}")
    for limit in (8, 16, 32, 64, 128):
        symbols = zeckendorf_count(limit)
        print(f"{limit:7d} {symbols:9d} {math.log2(symbols):11.6f}")
    print()


def print_reading(rows: list[ClockRow]) -> None:
    worst_overhead = max(rows, key=lambda item: item.overhead_bits)
    print("== reading ==")
    print(
        "CRT clocks can be perfectly efficient when the moduli are coprime and "
        "their lcm matches the live epoch count, but perfect efficiency is still "
        "only equality with an ordinary log2(P) pass tag."
    )
    print(
        f"Non-coprime or awkward clocks are worse; in this sweep P={worst_overhead.epochs} "
        f"has overhead {worst_overhead.overhead_bits:.6f} bits."
    )
    print(
        "Therefore modular clocks are useful stateless engineering only after "
        "another invariant bounds lifetime. They do not provide a free many-pass "
        "birth/open channel."
    )


def main() -> None:
    result = [row_for(epochs) for epochs in (2, 3, 4, 5, 8, 16, 64, 256, 4096)]
    print_rows(result)
    print_lifetime_rows()
    print_zeckendorf_rows()
    print_reading(result)


if __name__ == "__main__":
    main()
