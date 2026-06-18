#!/usr/bin/env python3
"""H54 - selector/referee budget for adaptive Total-Cover profiles.

Total-Cover removes per-record open/carry/birth entropy by invariant, but any
adaptive global knob still has to be known to the decoder. A final checksum or
trial-decode referee can identify the selected knob sequence only up to its
finite ambiguity budget.

If a pass chooses one profile from S public profiles, then P passes leave S^P
candidate profile sequences before the referee. A C-bit checksum with lambda
safety bits can honestly referee at most:

    P * log2(S) <= C - lambda

This ledger specializes H25's global-referee law to the H53-style global slack
ladder. It is not a compressor and it does not run seed searches.
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass


@dataclass(frozen=True)
class SelectorBudgetRow:
    profiles: int
    checksum_bits: int
    safety_bits: float
    selector_bits: float
    max_selectors: float


@dataclass(frozen=True)
class PassSafetyRow:
    profiles: int
    passes: int
    checksum_bits: int
    safety_bits: float
    ambiguity_bits: float
    margin_bits: float
    log2_false_survivors: float
    safe: bool


@dataclass(frozen=True)
class H53ReferenceRow:
    name: str
    mean_log2_rho: float
    selector_bits: float
    status: str


H53_REFERENCE_ROWS = [
    H53ReferenceRow(
        "H53 paid S={0,1,2}, B4 K192 D768",
        mean_log2_rho=0.004480,
        selector_bits=math.log2(3.0),
        status="expands after selector charge",
    ),
    H53ReferenceRow(
        "H53 unpaid S={0,1,2}, B4 K192 D768",
        mean_log2_rho=0.001973,
        selector_bits=0.0,
        status="still expands even if selector hidden",
    ),
]


def selector_budget(
    profiles: int,
    checksum_bits: int,
    safety_bits: float,
) -> SelectorBudgetRow:
    selector_bits = math.log2(profiles)
    max_selectors = max(0.0, checksum_bits - safety_bits) / selector_bits
    return SelectorBudgetRow(
        profiles=profiles,
        checksum_bits=checksum_bits,
        safety_bits=safety_bits,
        selector_bits=selector_bits,
        max_selectors=max_selectors,
    )


def pass_safety(
    profiles: int,
    passes: int,
    checksum_bits: int,
    safety_bits: float,
) -> PassSafetyRow:
    ambiguity_bits = passes * math.log2(profiles)
    margin_bits = checksum_bits - safety_bits - ambiguity_bits
    log2_false_survivors = ambiguity_bits - checksum_bits
    return PassSafetyRow(
        profiles=profiles,
        passes=passes,
        checksum_bits=checksum_bits,
        safety_bits=safety_bits,
        ambiguity_bits=ambiguity_bits,
        margin_bits=margin_bits,
        log2_false_survivors=log2_false_survivors,
        safe=margin_bits >= 0.0,
    )


def render_budget(rows: list[SelectorBudgetRow]) -> list[str]:
    lines = [
        "## Selector Capacity",
        "",
        "| profiles S | checksum C | safety lambda | selector bits | max global selectors |",
        "| ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row.profiles} | {row.checksum_bits} | {row.safety_bits:.1f} | "
            f"{row.selector_bits:.6f} | {row.max_selectors:.3f} |"
        )
    return lines


def render_passes(rows: list[PassSafetyRow]) -> list[str]:
    lines = [
        "## Pass Sequence Safety",
        "",
        "| profiles S | passes P | checksum C | ambiguity bits | margin after safety | log2 false survivors | status |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        status = "safe" if row.safe else "over budget"
        lines.append(
            f"| {row.profiles} | {row.passes} | {row.checksum_bits} | "
            f"{row.ambiguity_bits:.3f} | {row.margin_bits:.3f} | "
            f"{row.log2_false_survivors:.3f} | {status} |"
        )
    return lines


def render_h53_reference() -> list[str]:
    lines = [
        "## H53 Reference",
        "",
        "A referee can only select among candidate profile sequences. It cannot make",
        "a non-compressive unpaid row compressive. The current H53 bounded row is:",
        "",
        "| row | selector bits | mean log2 rho | status |",
        "| --- | ---: | ---: | --- |",
    ]
    for row in H53_REFERENCE_ROWS:
        lines.append(
            f"| {row.name} | {row.selector_bits:.3f} | "
            f"{row.mean_log2_rho:+.6f} | {row.status} |"
        )
    return lines


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profiles", type=int, nargs="+", default=[2, 3, 4, 8, 16])
    parser.add_argument("--checksum-bits", type=int, nargs="+", default=[64, 128, 256])
    parser.add_argument("--safety-bits", type=float, default=32.0)
    parser.add_argument("--passes", type=int, nargs="+", default=[8, 16, 32, 64, 128, 256])
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    budget_rows = [
        selector_budget(profiles, checksum, args.safety_bits)
        for checksum in args.checksum_bits
        for profiles in args.profiles
    ]
    pass_rows = [
        pass_safety(profiles, passes, checksum, args.safety_bits)
        for checksum in args.checksum_bits
        for profiles in args.profiles
        for passes in args.passes
    ]
    lines = [
        "# H54 - Selector Referee Budget",
        "",
        "A checksum/referee is a finite selector budget, not a free adaptive",
        "profile language. One global profile per pass costs `log2(S)` ambiguity",
        "bits unless a unique decoder invariant proves the profile.",
        "",
        *render_budget(budget_rows),
        "",
        *render_passes(pass_rows),
        "",
        *render_h53_reference(),
        "",
        "## Reading",
        "",
        "If `mean log2 rho` is still positive with the selector hidden, a referee",
        "cannot fix the compression sign. If a future unpaid row crosses but the",
        "paid row does not, a fixed checksum can only support a finite pass window:",
        "",
        "```text",
        "P_max = floor((C - lambda) / log2(S))",
        "```",
        "",
        "Arbitrary passes require either a proved unique invariant or a selector",
        "stream whose entropy grows as `P log2(S)`.",
    ]
    print("\n".join(lines))


if __name__ == "__main__":
    main()
