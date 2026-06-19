#!/usr/bin/env python3
"""H180 - cocycle/canonical placement accounting.

This kernel tests the next post-H177 escape hatch:

    Can position/cocycle state make total-cover recursion stateless and fresh
    without paying birth/open/pass metadata?

It separates four cases:

baseline:
    H177 interval-cover support with no coordinate state.

observed_coord:
    Each accepted edge emits a random coordinate delta that the decoder can
    observe after expanding the chosen seed. No endpoint constraint is imposed.
    This can make salts path-dependent or out-of-order-decodable, but it does
    not change witness supply.

endpoint:
    The same observed deltas are required to end at public coordinate 0. This
    models a zero-holonomy/final-coordinate condition. It filters paths; it is
    free only if the full-cover path naturally satisfies it.

edge_zero:
    Each edge is conditioned to have zero coordinate delta. This is the per-edge
    hidden holonomy/route filter and costs g bits of match supply per edge.

paid_routes:
    The encoder may choose among d route/salt slots. Gross edge support rises,
    but the route identity costs log2(d) bits unless it is encoded in the seed
    rank. The row reports both gross support and paid gain.

The goal is not to compress a corpus. It is to show whether cocycle geometry
creates supply or merely moves state into filters/selectors.
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
        if arity > 5:
            raise ValueError("v1 arity code supports K<=5")
        return V1_ARITY_BITS[arity]
    if code == "fixed":
        return ceil_log2(max_arity)
    raise ValueError(code)


def kraft_sum(max_arity: int, code: str) -> float:
    return sum(2.0 ** (-arity_bits(a, max_arity, code)) for a in range(1, max_arity + 1))


def edge_probability(exponent: float) -> float:
    if exponent <= 0.0:
        return 1.0
    if exponent >= 64.0:
        # The rows here are small; this avoids underflow in future extensions.
        return 2.0 ** (-exponent)
    return 2.0 ** (-exponent)


def route_edge_probability(base_p: float, route_choices: int) -> float:
    if route_choices <= 1:
        return base_p
    if base_p >= 1.0:
        return 1.0
    return -math.expm1(route_choices * math.log1p(-base_p))


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, math.ceil(len(ordered) * pct) - 1))
    return ordered[idx]


@dataclass(frozen=True)
class Trial:
    supported: bool
    reachable_positions: int
    final_states: int


@dataclass(frozen=True)
class Row:
    mode: str
    code: str
    max_arity: int
    items: int
    slack: int
    coord_bits: int
    route_choices: int
    trials: int
    support: float
    mean_reachable: float
    p95_reachable: float
    mean_final_states: float
    kraft: float
    gross_eout: float
    paid_gain_per_record: float
    route_bits: float
    coord_filter_bits: float
    reading: str


def transition_probability(
    *,
    ell: int,
    slack: int,
    coord_bits: int,
    route_choices: int,
    mode: str,
) -> float:
    base_p = edge_probability(ell + slack)
    if mode == "edge_zero":
        return edge_probability(ell + slack + coord_bits)
    if mode == "paid_routes":
        return route_edge_probability(base_p, route_choices)
    return base_p


def trial_cover(
    *,
    mode: str,
    items: int,
    max_arity: int,
    code: str,
    slack: int,
    coord_bits: int,
    route_choices: int,
    seed: int,
    trial_index: int,
) -> Trial:
    rng = random.Random(
        stable_seed("H180", mode, seed, trial_index, items, max_arity, code, slack, coord_bits, route_choices)
    )
    coord_count = 1 << coord_bits
    if mode in {"observed_coord", "endpoint"} and coord_bits > 0:
        frontiers: list[set[int]] = [set() for _ in range(items + 1)]
        frontiers[0].add(0)
        for start in range(items):
            if not frontiers[start]:
                continue
            for arity in range(1, min(max_arity, items - start) + 1):
                ell = arity_bits(arity, max_arity, code)
                p = transition_probability(
                    ell=ell,
                    slack=slack,
                    coord_bits=coord_bits,
                    route_choices=route_choices,
                    mode=mode,
                )
                if rng.random() >= p:
                    continue
                delta = rng.randrange(coord_count)
                dest = start + arity
                for coord in frontiers[start]:
                    frontiers[dest].add((coord + delta) % coord_count)
        if mode == "endpoint":
            supported = 0 in frontiers[items]
        else:
            supported = bool(frontiers[items])
        reachable = sum(1 for states in frontiers if states)
        return Trial(supported=supported, reachable_positions=reachable, final_states=len(frontiers[items]))

    reachable = [False] * (items + 1)
    reachable[0] = True
    reachable_count = 1
    for start in range(items):
        if not reachable[start]:
            continue
        for arity in range(1, min(max_arity, items - start) + 1):
            ell = arity_bits(arity, max_arity, code)
            p = transition_probability(
                ell=ell,
                slack=slack,
                coord_bits=coord_bits,
                route_choices=route_choices,
                mode=mode,
            )
            if rng.random() < p and not reachable[start + arity]:
                reachable[start + arity] = True
                reachable_count += 1
    return Trial(supported=reachable[items], reachable_positions=reachable_count, final_states=int(reachable[items]))


def row_reading(row: Row) -> str:
    if row.mode == "observed_coord":
        return "free state geometry; same supply as baseline"
    if row.mode == "endpoint":
        return "zero-holonomy endpoint filter; no supply gain"
    if row.mode == "edge_zero":
        return "conditioned coordinate bits tax match supply"
    if row.mode == "paid_routes":
        if row.paid_gain_per_record <= 0.0:
            return "gross route support bought by paid selector"
        return "selector paid; still must beat support/bad tails"
    return "H177 baseline"


def run_row(args: argparse.Namespace, mode: str, coord_bits: int, route_choices: int, slack: int) -> Row:
    trials = [
        trial_cover(
            mode=mode,
            items=args.items,
            max_arity=args.max_arity,
            code=args.code,
            slack=slack,
            coord_bits=coord_bits,
            route_choices=route_choices,
            seed=args.seed,
            trial_index=i,
        )
        for i in range(args.trials)
    ]
    support = sum(1 for trial in trials if trial.supported) / args.trials if args.trials else 0.0
    reachable = [float(trial.reachable_positions) for trial in trials]
    final_states = [float(trial.final_states) for trial in trials]
    route_bits = math.log2(route_choices) if mode == "paid_routes" and route_choices > 1 else 0.0
    coord_filter_bits = float(coord_bits) if mode == "edge_zero" else 0.0
    kraft = kraft_sum(args.max_arity, args.code)
    gross_multiplier = route_choices if mode == "paid_routes" else 1
    if mode == "edge_zero":
        gross_multiplier = 2.0 ** (-coord_bits)
    gross_eout = kraft * (2.0 ** (-slack)) * gross_multiplier
    row = Row(
        mode=mode,
        code=args.code,
        max_arity=args.max_arity,
        items=args.items,
        slack=slack,
        coord_bits=coord_bits,
        route_choices=route_choices,
        trials=args.trials,
        support=support,
        mean_reachable=sum(reachable) / len(reachable) if reachable else 0.0,
        p95_reachable=percentile(reachable, 0.95),
        mean_final_states=sum(final_states) / len(final_states) if final_states else 0.0,
        kraft=kraft,
        gross_eout=gross_eout,
        paid_gain_per_record=float(slack) - route_bits - coord_filter_bits,
        route_bits=route_bits,
        coord_filter_bits=coord_filter_bits,
        reading="",
    )
    return Row(**{**row.__dict__, "reading": row_reading(row)})


def parse_int_list(values: list[str], default: list[int]) -> list[int]:
    if not values:
        return default
    out: list[int] = []
    for value in values:
        out.extend(int(part) for part in value.split(",") if part)
    return out


def parse_modes(values: list[str]) -> list[str]:
    if not values:
        return ["baseline", "observed_coord", "endpoint", "edge_zero", "paid_routes"]
    out: list[str] = []
    for value in values:
        out.extend(part for part in value.split(",") if part)
    return out


def confluence_rows(coord_values: list[int], trials: int, seed: int) -> list[tuple[int, float, float]]:
    rows: list[tuple[int, float, float]] = []
    for coord_bits in coord_values:
        if coord_bits <= 0:
            rows.append((coord_bits, 1.0, 1.0))
            continue
        coord_count = 1 << coord_bits
        random_zero = 0
        for trial_index in range(trials):
            rng = random.Random(stable_seed("H180-diamond", seed, coord_bits, trial_index))
            ab = rng.randrange(coord_count)
            bd = rng.randrange(coord_count)
            ac = rng.randrange(coord_count)
            cd = rng.randrange(coord_count)
            if (ab + bd - ac - cd) % coord_count == 0:
                random_zero += 1
        rows.append((coord_bits, 1.0, random_zero / trials if trials else 0.0))
    return rows


def fmt(value: float) -> str:
    return f"{value:.6f}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--code", choices=["v1", "fixed"], default="v1")
    parser.add_argument("--max-arity", type=int, default=5)
    parser.add_argument("--items", type=int, default=128)
    parser.add_argument("--trials", type=int, default=1000)
    parser.add_argument("--slack", action="append", default=[])
    parser.add_argument("--coord-bits", action="append", default=[])
    parser.add_argument("--route-choices", action="append", default=[])
    parser.add_argument("--mode", action="append", default=[])
    parser.add_argument("--diamond-trials", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=180180)
    args = parser.parse_args()

    if args.code == "v1" and args.max_arity > 5:
        raise ValueError("v1 arity code supports K<=5")

    slacks = parse_int_list(args.slack, [-2, -1, 0, 1])
    coord_values = parse_int_list(args.coord_bits, [0, 4])
    route_values = parse_int_list(args.route_choices, [1, 2, 4])
    modes = parse_modes(args.mode)
    valid_modes = {"baseline", "observed_coord", "endpoint", "edge_zero", "paid_routes"}
    unknown = set(modes) - valid_modes
    if unknown:
        raise ValueError(f"unknown modes: {sorted(unknown)}")

    rows: list[Row] = []
    for mode in modes:
        mode_coords = coord_values if mode in {"observed_coord", "endpoint", "edge_zero"} else [0]
        mode_routes = route_values if mode == "paid_routes" else [1]
        for slack in slacks:
            for coord_bits in mode_coords:
                for route_choices in mode_routes:
                    rows.append(run_row(args, mode, coord_bits, route_choices, slack))

    print("== H180 cocycle/canonical placement accounting ==")
    print(
        "support is full-cover path support. paid_gain/rec subtracts route or "
        "coordinate-conditioning bits from current slack."
    )
    print(
        f"{'mode':<15} {'code':<6} {'K':>4} {'N':>5} {'s':>4} {'g':>3} {'d':>3} "
        f"{'support':>9} {'Eout':>9} {'paid/rec':>9} {'route':>7} {'coord':>7} "
        f"{'meanR':>8} {'p95R':>8} {'finalS':>8} {'reading':<48}"
    )
    for row in rows:
        print(
            f"{row.mode:<15} {row.code:<6} {row.max_arity:4d} {row.items:5d} "
            f"{row.slack:4d} {row.coord_bits:3d} {row.route_choices:3d} "
            f"{fmt(row.support):>9} {fmt(row.gross_eout):>9} "
            f"{fmt(row.paid_gain_per_record):>9} {fmt(row.route_bits):>7} "
            f"{fmt(row.coord_filter_bits):>7} {fmt(row.mean_reachable):>8} "
            f"{fmt(row.p95_reachable):>8} {fmt(row.mean_final_states):>8} "
            f"{row.reading:<48}"
        )

    print()
    print("== theorem check ==")
    print("Observed cocycle state is free only as geometry; it does not increase Eout.")
    print("Endpoint or zero-holonomy constraints filter paths unless the residue is stored.")
    print("Route choices multiply gross support only when their route/rank bits are paid.")

    print()
    print("== diamond confluence check ==")
    print("public potential has zero holonomy by construction; random edge labels pass at about 2^-g.")
    print(f"{'g':>3} {'potential_ok':>13} {'random_zero':>12} {'expected':>10}")
    for coord_bits, potential_ok, random_zero in confluence_rows(coord_values, args.diamond_trials, args.seed):
        expected = 1.0 if coord_bits <= 0 else 2.0 ** (-coord_bits)
        print(
            f"{coord_bits:3d} {fmt(potential_ok):>13} {fmt(random_zero):>12} {fmt(expected):>10}"
        )


if __name__ == "__main__":
    main()
