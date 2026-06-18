#!/usr/bin/env python3
"""H67 - typical geometric shrink vs rare blowup ledger.

Some repeated-pass rows track:

    E[log2 rho] < 0

That is a useful reproduction-number diagnostic, but it is not enough for the
goal "roughly all data over an arbitrary number of passes." Under uniform
content-blind coding, expected length cannot fall below raw. A negative
geometric drift can coexist with conservation only by rare large expansions.

This kernel prices that trap with a two-outcome toy law:

    rho = a < 1 with probability 1-epsilon
    rho = b > 1 with probability epsilon

where b is chosen so E[rho] = 1. Then we report E[log2 rho] and the probability
of avoiding any blowup over P passes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class DriftRow:
    shrink_factor: float
    bad_probability: float
    blowup_factor: float
    mean_log2_rho: float
    passes: int
    no_blowup_probability: float
    at_least_one_blowup_probability: float
    all_good_ratio: float
    one_blowup_ratio: float


def row(shrink_factor: float, bad_probability: float, passes: int) -> DriftRow:
    eps = bad_probability
    a = shrink_factor
    if not 0.0 < a < 1.0:
        raise ValueError("shrink_factor must be in (0,1)")
    if not 0.0 < eps < 1.0:
        raise ValueError("bad_probability must be in (0,1)")
    b = (1.0 - (1.0 - eps) * a) / eps
    mean_log = (1.0 - eps) * math.log2(a) + eps * math.log2(b)
    no_bad = (1.0 - eps) ** passes
    return DriftRow(
        shrink_factor=a,
        bad_probability=eps,
        blowup_factor=b,
        mean_log2_rho=mean_log,
        passes=passes,
        no_blowup_probability=no_bad,
        at_least_one_blowup_probability=1.0 - no_bad,
        all_good_ratio=a**passes,
        one_blowup_ratio=(a ** (passes - 1)) * b,
    )


def print_rows() -> None:
    print("== typical shrink / rare blowup conservation ==")
    print("b is chosen so E[rho]=1; negative E[log rho] is paid by rare blowups.")
    print(
        f"{'a':>7} {'eps':>8} {'b':>12} {'E log2 rho':>12} "
        f"{'P':>6} {'Pr no blowup':>13} {'Pr >=1 blowup':>14} "
        f"{'all-good ratio':>14} {'one-blowup ratio':>16}"
    )
    for a in (0.99, 0.95, 0.90):
        for eps in (0.10, 0.03, 0.01, 0.001):
            for passes in (64, 256, 4096):
                if passes == 4096 and eps > 0.01:
                    continue
                r = row(a, eps, passes)
                print(
                    f"{r.shrink_factor:7.3f} {r.bad_probability:8.3f} "
                    f"{r.blowup_factor:12.3f} {r.mean_log2_rho:12.6f} "
                    f"{r.passes:6d} {r.no_blowup_probability:13.6f} "
                    f"{r.at_least_one_blowup_probability:14.6f} "
                    f"{r.all_good_ratio:14.3e} {r.one_blowup_ratio:16.3e}"
                )
    print()


def print_reading() -> None:
    print("== reading ==")
    print("Negative geometric drift is a good local diagnostic, but for arbitrary")
    print("pass count a fixed per-pass bad fraction eventually hits almost every")
    print("input: Pr(at least one blowup) = 1-(1-eps)^P -> 1.")
    print()
    print("To claim roughly-all data for arbitrary P, the bad fraction must shrink")
    print("like O(1/P) or be exactly zero. Exact zero bad fraction with net shrink")
    print("would be an injective compression of all uniform inputs, which is the")
    print("counting wall. So any future negative-log-rho row must also report the")
    print("tail/blowup budget, not only the geometric mean.")


def main() -> None:
    print_rows()
    print_reading()


if __name__ == "__main__":
    main()
