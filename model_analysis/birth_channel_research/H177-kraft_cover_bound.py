#!/usr/bin/env python3
"""H177 - Kraft cover bound for total-cover Telomere.

This is the stripped theorem behind the H176 phase map.

For a public prefix arity code with lengths ell(a), a record that saves s bits
against its target span can expose at most

    2 ** (target_bits - ell(a) - s)

candidate witnesses. Under the uniform hash law, the interval edge exists with
probability at most 2 ** (-(ell(a) + s)). Therefore the expected outgoing cover
degree is bounded by

    2 ** (-s) * sum_a 2 ** (-ell(a)).

The Kraft sum is <= 1 for any prefix arity code. Strict paid savings (s > 0)
are subcritical unless another honest channel supplies extra witness mass.

This kernel simulates the corresponding interval DAG so the theorem has a
small executable sanity check beside the algebra.
"""

from __future__ import annotations

import argparse
import hashlib
import math
import random
from dataclasses import dataclass


V1_ARITY_BITS = {1: 2, 2: 2, 3: 3, 4: 3, 5: 3}


def stable_seed(*parts: object) -> int:
    digest = hashlib.blake2b(digest_size=16)
    for part in parts:
        digest.update(str(part).encode("ascii"))
        digest.update(b"\0")
    return int.from_bytes(digest.digest(), "big")


def ceil_log2(value: int) -> int:
    if value <= 1:
        return 0
    return (value - 1).bit_length()


def arity_bits(arity: int, max_arity: int, code: str) -> int:
    if code == "v1":
        return V1_ARITY_BITS[arity]
    if code == "fixed":
        return ceil_log2(max_arity)
    raise ValueError(code)


def kraft_sum(max_arity: int, code: str) -> float:
    return sum(2.0 ** (-arity_bits(a, max_arity, code)) for a in range(1, max_arity + 1))


def edge_probability(ell: int, slack: int) -> float:
    exponent = ell + slack
    if exponent <= 0:
        return 1.0
    return 2.0 ** (-exponent)


@dataclass(frozen=True)
class Row:
    code: str
    max_arity: int
    items: int
    slack: int
    trials: int
    kraft: float
    expected_out: float
    support: float
    mean_reachable: float
    p95_reachable: float


def trial_support(
    *,
    items: int,
    max_arity: int,
    code: str,
    slack: int,
    seed: int,
    trial_index: int,
) -> tuple[bool, int]:
    reachable = [False] * (items + 1)
    reachable[0] = True
    reachable_count = 1
    for start in range(items):
        if not reachable[start]:
            continue
        for arity in range(1, min(max_arity, items - start) + 1):
            ell = arity_bits(arity, max_arity, code)
            p = edge_probability(ell, slack)
            rng = random.Random(stable_seed("H177", seed, trial_index, start, arity, code, slack))
            if rng.random() < p and not reachable[start + arity]:
                reachable[start + arity] = True
                reachable_count += 1
    return reachable[items], reachable_count


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, math.ceil(len(ordered) * pct) - 1))
    return ordered[idx]


def run_row(args: argparse.Namespace, max_arity: int, slack: int) -> Row:
    results = [
        trial_support(
            items=args.items,
            max_arity=max_arity,
            code=args.code,
            slack=slack,
            seed=args.seed,
            trial_index=i,
        )
        for i in range(args.trials)
    ]
    supported = sum(1 for ok, _ in results if ok)
    reachable_counts = [count for _, count in results]
    kraft = kraft_sum(max_arity, args.code)
    return Row(
        code=args.code,
        max_arity=max_arity,
        items=args.items,
        slack=slack,
        trials=args.trials,
        kraft=kraft,
        expected_out=kraft * (2.0 ** (-slack)),
        support=supported / args.trials if args.trials else 0.0,
        mean_reachable=sum(reachable_counts) / len(reachable_counts),
        p95_reachable=percentile([float(value) for value in reachable_counts], 0.95),
    )


def fmt(value: float) -> str:
    return f"{value:.6f}"


def parse_int_list(values: list[str], default: list[int]) -> list[int]:
    if not values:
        return default
    out: list[int] = []
    for raw in values:
        out.extend(int(part) for part in raw.split(",") if part)
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--code", choices=["v1", "fixed"], default="v1")
    parser.add_argument("--max-arity", action="append", default=[])
    parser.add_argument("--slack", action="append", default=[])
    parser.add_argument("--items", type=int, default=128)
    parser.add_argument("--trials", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=177177)
    args = parser.parse_args()

    max_arities = parse_int_list(args.max_arity, [5] if args.code == "v1" else [8, 16, 32, 64, 128])
    slacks = parse_int_list(args.slack, [-2, -1, 0, 1, 2])
    if args.code == "v1" and any(k > 5 for k in max_arities):
        raise ValueError("v1 arity code supports K<=5")

    rows = [run_row(args, k, slack) for k in max_arities for slack in slacks]

    print("== H177 Kraft cover bound ==")
    print(
        "support is reachability of a full-cover interval path; "
        "s>0 means paid savings per record, s<0 means bloat per record."
    )
    print(
        f"{'code':<6} {'K':>4} {'N':>5} {'s':>4} {'trials':>7} "
        f"{'Kraft':>9} {'Eout':>9} {'support':>9} {'meanR':>9} {'p95R':>9}"
    )
    for row in rows:
        print(
            f"{row.code:<6} {row.max_arity:4d} {row.items:5d} {row.slack:4d} "
            f"{row.trials:7d} {fmt(row.kraft):>9} {fmt(row.expected_out):>9} "
            f"{fmt(row.support):>9} {fmt(row.mean_reachable):>9} {fmt(row.p95_reachable):>9}"
        )

    print()
    print("== theorem check ==")
    print("If s > 0 and the arity code is prefix-free, Eout <= 2^-s < 1.")
    print("Thus strict per-record savings are subcritical without a paid or derived supply boost.")


if __name__ == "__main__":
    main()
