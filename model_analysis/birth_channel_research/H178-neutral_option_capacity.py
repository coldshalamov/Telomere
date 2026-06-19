#!/usr/bin/env python3
"""H178 - neutral option capacity bound for near-equal witnesses.

H177 shows a total-cover layer with strict paid savings is subcritical under
the uniform hash law. The obvious mutation is to allow near-equal or bloating
records, then use the free choice among multiple matching seeds to steer the
next layer toward fertility.

This kernel prices that escape hatch.

If a current record has H matching witnesses at the same emitted cost, choosing
which witness to emit is free only because the chosen seed is already part of
the record. That neutral choice can steer at most log2(H) bits of future state.

For a prefix arity code with Kraft mass Kf and slack s:

    s > 0: current record saves s bits, but cover degree Kf*2^-s is subcritical.
    s = 0: flat record, at best critical.
    s < 0: record bloats by b=-s bits, cover degree Kf*2^b is supercritical.

The strongest possible slack flywheel would convert every neutral option bit
into future compression. This kernel compares that fantasy upper bound with the
current bloat bill.
"""

from __future__ import annotations

import argparse
import hashlib
import math
import random
from dataclasses import dataclass


V1_ARITY_BITS = {1: 2, 2: 2, 3: 3, 4: 3, 5: 3}
LN2 = math.log(2.0)


def ceil_log2(value: int) -> int:
    if value <= 1:
        return 0
    return (value - 1).bit_length()


def arity_bits(arity: int, max_arity: int, code: str) -> int:
    if code == "v1":
        if arity > 5:
            raise ValueError("v1 arity code supports only K<=5")
        return V1_ARITY_BITS[arity]
    if code == "fixed":
        return ceil_log2(max_arity)
    raise ValueError(code)


def kraft_sum(max_arity: int, code: str) -> float:
    return sum(2.0 ** (-arity_bits(a, max_arity, code)) for a in range(1, max_arity + 1))


def stable_seed(*parts: object) -> int:
    digest = hashlib.blake2b(digest_size=16)
    for part in parts:
        digest.update(str(part).encode("ascii"))
        digest.update(b"\0")
    return int.from_bytes(digest.digest(), "big")


def poisson_expected_log2_cond(lambda_: float) -> float:
    """Return E[log2(H) | H > 0] for H ~ Poisson(lambda)."""

    if lambda_ <= 0.0:
        return 0.0
    if lambda_ > 200.0:
        # Delta-method expansion for large lambda. Conditioning on H>0 is
        # negligible at this scale.
        return max(0.0, math.log2(lambda_) - 1.0 / (2.0 * lambda_ * LN2))

    p0 = math.exp(-lambda_)
    p = p0
    total = 0.0
    k_max = int(math.ceil(lambda_ + 14.0 * math.sqrt(lambda_ + 1.0) + 40.0))
    for k in range(1, k_max + 1):
        p *= lambda_ / k
        total += p * math.log2(k)
    support = 1.0 - p0
    return total / support if support > 0.0 else 0.0


def edge_support(lambda_: float) -> float:
    if lambda_ <= 0.0:
        return 0.0
    if lambda_ > 745.0:
        return 1.0
    return -math.expm1(-lambda_)


@dataclass(frozen=True)
class Row:
    code: str
    max_arity: int
    slack: int
    kraft: float
    lambda_total: float
    edge_support: float
    option_bits: float
    current_gain: float
    fantasy_net: float
    path_support: float | None
    regime: str


def edge_probability(ell: int, slack: int) -> float:
    exponent = ell + slack
    if exponent <= 0:
        return 1.0
    return 2.0 ** (-exponent)


def trial_support(
    *,
    items: int,
    max_arity: int,
    code: str,
    slack: int,
    seed: int,
    trial_index: int,
) -> bool:
    rng = random.Random(stable_seed("H178", seed, trial_index, max_arity, code, slack))
    reachable = [False] * (items + 1)
    reachable[0] = True
    for start in range(items):
        if not reachable[start]:
            continue
        for arity in range(1, min(max_arity, items - start) + 1):
            ell = arity_bits(arity, max_arity, code)
            if rng.random() < edge_probability(ell, slack):
                reachable[start + arity] = True
    return reachable[items]


def support_estimate(
    *,
    items: int,
    trials: int,
    max_arity: int,
    code: str,
    slack: int,
    seed: int,
) -> float | None:
    if trials <= 0:
        return None
    supported = sum(
        1
        for trial_index in range(trials)
        if trial_support(
            items=items,
            max_arity=max_arity,
            code=code,
            slack=slack,
            seed=seed,
            trial_index=trial_index,
        )
    )
    return supported / trials


def run_row(max_arity: int, code: str, slack: int, args: argparse.Namespace) -> Row:
    kraft = kraft_sum(max_arity, code)
    lambda_total = kraft * (2.0 ** (-slack))
    option_bits = poisson_expected_log2_cond(lambda_total)
    current_gain = float(slack)
    if slack > 0:
        regime = "compressive-subcritical"
    elif slack == 0:
        regime = "flat-critical" if kraft >= 1.0 else "flat-subcritical"
    else:
        regime = "bloating-supercritical" if lambda_total > 1.0 else "bloating"
    return Row(
        code=code,
        max_arity=max_arity,
        slack=slack,
        kraft=kraft,
        lambda_total=lambda_total,
        edge_support=edge_support(lambda_total),
        option_bits=option_bits,
        current_gain=current_gain,
        fantasy_net=current_gain + option_bits,
        path_support=support_estimate(
            items=args.items,
            trials=args.trials,
            max_arity=max_arity,
            code=code,
            slack=slack,
            seed=args.seed,
        ),
        regime=regime,
    )


def parse_int_list(values: list[str], default: list[int]) -> list[int]:
    if not values:
        return default
    out: list[int] = []
    for raw in values:
        out.extend(int(part) for part in raw.split(",") if part)
    return out


def fmt(value: float) -> str:
    return f"{value:.6f}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--code", choices=["v1", "fixed"], default="v1")
    parser.add_argument("--max-arity", action="append", default=[])
    parser.add_argument("--slack", action="append", default=[])
    parser.add_argument("--items", type=int, default=128)
    parser.add_argument("--trials", type=int, default=0)
    parser.add_argument("--seed", type=int, default=178178)
    args = parser.parse_args()

    max_arities = parse_int_list(args.max_arity, [5] if args.code == "v1" else [8, 16, 32, 64, 128])
    slacks = parse_int_list(args.slack, list(range(-8, 5)))
    if args.code == "v1" and any(k > 5 for k in max_arities):
        raise ValueError("v1 arity code supports K<=5")

    rows = [run_row(k, args.code, slack, args) for k in max_arities for slack in slacks]

    print("== H178 neutral option capacity ==")
    print(
        "slack s is current paid gain/record. Negative s is bloat. "
        "option is E[log2 matching witnesses | at least one]."
    )
    print(
        f"{'code':<6} {'K':>4} {'s':>4} {'Kraft':>9} {'lambda':>10} "
        f"{'edgeP':>9} {'pathP':>9} {'option':>9} {'gain':>8} {'fantasy':>9} {'regime':<24}"
    )
    for row in rows:
        path = "NA" if row.path_support is None else fmt(row.path_support)
        print(
            f"{row.code:<6} {row.max_arity:4d} {row.slack:4d} "
            f"{fmt(row.kraft):>9} {fmt(row.lambda_total):>10} "
            f"{fmt(row.edge_support):>9} {path:>9} {fmt(row.option_bits):>9} "
            f"{fmt(row.current_gain):>8} {fmt(row.fantasy_net):>9} {row.regime:<24}"
        )

    supercritical = [row for row in rows if row.lambda_total > 1.0 and row.slack < 0]
    if supercritical:
        best = max(supercritical, key=lambda row: row.fantasy_net)
        supported = [row for row in supercritical if row.path_support is None or row.path_support >= 0.95]
        best_supported = max(supported, key=lambda row: row.fantasy_net) if supported else None
        print()
        print("== reading ==")
        print(
            "Best supercritical slack row under the fantasy conversion bound: "
            f"code={best.code}, K={best.max_arity}, s={best.slack}, "
            f"fantasy_net={best.fantasy_net:.6f} bits/record, "
            f"path_support={best.path_support if best.path_support is not None else 'NA'}."
        )
        if best_supported is not None:
            print(
                "Best row with estimated path support >=0.95: "
                f"code={best_supported.code}, K={best_supported.max_arity}, "
                f"s={best_supported.slack}, fantasy_net={best_supported.fantasy_net:.6f}."
            )
        print("Rows with tiny positive fantasy value still require fallback/exception accounting.")


if __name__ == "__main__":
    main()
