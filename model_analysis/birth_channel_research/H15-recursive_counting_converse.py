#!/usr/bin/env python3
"""Recursive stateless counting converse for Total-Cover.

This is not a compression experiment. It is the finite counting wall behind
recursive, content-blind, stateless compression:

For any uniquely decodable final representation of n-bit inputs,

    Pr[L(X) <= n - s] <= 2^-s        for uniform X in {0,1}^n
    E[L(X)] >= n

Running P recursive passes and keeping the best result only changes the count
if the chosen pass/profile is an unpriced side channel. If the decoder must
know which pass/profile produced the final representation, paying the selector
restores the same bound.
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass


@dataclass(frozen=True)
class BoundRow:
    input_bits: int
    passes: int
    target_saving_bits: int
    free_selector_bound: float
    paid_selector_bits: int
    paid_net_saving_bits: int
    paid_bound: float
    max_short_inputs_paid: int | None
    total_inputs: int | None


def probability_bound(saving_bits: int) -> float:
    if saving_bits <= 0:
        return 1.0
    return 2.0 ** (-saving_bits)


def finite_short_count(input_bits: int, saving_bits: int) -> tuple[int | None, int | None]:
    """Return exact maximum count of n-bit inputs saving >=s when feasible."""

    if input_bits > 62:
        return None, None
    total_inputs = 1 << input_bits
    if saving_bits <= 0:
        return total_inputs, total_inputs
    # Kraft: if every successful codeword has length <= n-s, each consumes at
    # least 2^-(n-s) Kraft mass, so at most 2^(n-s) source strings can share
    # that much saving.
    max_codewords = 1 << max(0, input_bits - saving_bits)
    return min(total_inputs, max_codewords), total_inputs


def make_row(input_bits: int, passes: int, target_saving_bits: int) -> BoundRow:
    free_selector_saving = max(0.0, target_saving_bits - math.log2(max(1, passes)))
    paid_selector_bits = math.ceil(math.log2(max(1, passes)))
    paid_net_saving = target_saving_bits + paid_selector_bits
    max_short, total = finite_short_count(input_bits, paid_net_saving)
    return BoundRow(
        input_bits=input_bits,
        passes=passes,
        target_saving_bits=target_saving_bits,
        free_selector_bound=probability_bound(math.ceil(free_selector_saving)),
        paid_selector_bits=paid_selector_bits,
        paid_net_saving_bits=paid_net_saving,
        paid_bound=probability_bound(paid_net_saving),
        max_short_inputs_paid=max_short,
        total_inputs=total,
    )


def render(rows: list[BoundRow]) -> str:
    lines = [
        "# Recursive Stateless Counting Converse",
        "",
        "Rows show the probability upper bound for saving at least `s` bits on",
        "a uniform `n`-bit input after considering up to `P` recursive passes.",
        "A free pass selector gives at most `log2(P)` apparent bits; a paid",
        "selector restores the ordinary `2^-s` counting wall.",
        "",
        "| n | P | target saving s | free-selector bound | selector bits | paid net saving | paid bound | exact finite paid count |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        count = "n/a"
        if row.max_short_inputs_paid is not None and row.total_inputs is not None:
            count = f"{row.max_short_inputs_paid}/{row.total_inputs}"
        lines.append(
            f"| {row.input_bits} | {row.passes} | {row.target_saving_bits} | "
            f"{row.free_selector_bound:.6g} | {row.paid_selector_bits} | "
            f"{row.paid_net_saving_bits} | {row.paid_bound:.6g} | {count} |"
        )
    lines.extend(
        [
            "",
            "## Reading",
            "",
            "A recursive Telomere pass schedule is still one lossless code once the",
            "final representation includes whatever the decoder needs: pass count,",
            "profile id, layer length, seed witnesses, and headers. Therefore a",
            "claim of maintained positive savings on roughly all uniform inputs",
            "would require more short final codewords than a uniquely decodable",
            "code can have.",
            "",
            "This does not rule out non-uniform sources, public interpreters with a",
            "real prior, planted controls, or ordinary compression of structured",
            "data. It rules out content-blind uniform-law compression of roughly",
            "all inputs by recursive pass selection alone.",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-bits", type=int, default=1024)
    parser.add_argument("--passes", type=int, nargs="+", default=[1, 2, 4, 16, 256, 65536])
    parser.add_argument("--savings", type=int, nargs="+", default=[1, 8, 32, 128])
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = [
        make_row(args.input_bits, passes, saving)
        for passes in args.passes
        for saving in args.savings
    ]
    print(render(rows))


if __name__ == "__main__":
    main()
