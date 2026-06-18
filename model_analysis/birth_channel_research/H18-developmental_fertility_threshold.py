#!/usr/bin/env python3
"""Developmental fertility threshold for neutral Telomere choices.

H12 measured same-width neutral seed multiplicity. A neutral choice does not
change the current record length or decoded bytes, but it can choose among
multiple witnesses that reproduce the same span.

H12's simple upper bound credited one future saved bit per neutral choice bit.
That still missed. H18 asks the sharper biology-shaped question:

    how much amplification would be needed if a public developmental
    interpreter made one neutral choice bit control more than one future bit?

This does not reopen the uniform all-data claim. Under the uniform law, a
neutral bit cannot save more than one future bit in expectation without another
paid channel. The threshold is useful because it quantifies the smallest
premise change a source-shaped/developmental Telomere variant would need.
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass


@dataclass(frozen=True)
class H12Row:
    slack: int
    gain_per_atom: float
    missing_bits_per_record: float
    neutral_bits_per_record: float
    perfect_credit_gain_per_atom: float

    @property
    def neutral_bits_per_atom(self) -> float:
        return self.perfect_credit_gain_per_atom - self.gain_per_atom

    @property
    def records_per_atom(self) -> float:
        if self.neutral_bits_per_record <= 0.0:
            return 0.0
        return self.neutral_bits_per_atom / self.neutral_bits_per_record

    @property
    def gamma_to_cross(self) -> float:
        if self.neutral_bits_per_record <= 0.0:
            return math.inf
        return self.missing_bits_per_record / self.neutral_bits_per_record

    @property
    def extra_source_deficit_per_atom_to_cross(self) -> float:
        """Extra correlation over the one-for-one neutral-credit bound."""

        return max(0.0, -self.perfect_credit_gain_per_atom)


H12_BOUNDED_ROWS = [
    H12Row(-8, -0.050155, 4.565, 3.819, -0.008196),
    H12Row(-6, -0.045826, 4.171, 3.162, -0.011083),
    H12Row(-4, -0.039478, 3.593, 2.574, -0.011198),
    H12Row(-2, -0.026295, 2.393, 1.306, -0.011946),
    H12Row(0, -0.026007, 2.316, 0.507, -0.020313),
]


def gain_at_gamma(row: H12Row, gamma: float) -> float:
    return row.gain_per_atom + gamma * row.neutral_bits_per_atom


def render(rows: list[H12Row], gammas: list[float]) -> str:
    lines = [
        "# Developmental Fertility Threshold",
        "",
        "Rows reuse the stronger bounded H12 neutral-capacity measurements.",
        "`gamma` means future saved bits per neutral choice bit.",
        "",
        "| slack | gain/atom at gamma=0 | neutral bits/rec | rec/atom | perfect credit gamma=1 | gamma needed | extra source deficit at threshold (bits/atom) |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row.slack} | {row.gain_per_atom:.6f} | "
            f"{row.neutral_bits_per_record:.3f} | {row.records_per_atom:.6f} | "
            f"{row.perfect_credit_gain_per_atom:.6f} | {row.gamma_to_cross:.3f} | "
            f"{row.extra_source_deficit_per_atom_to_cross:.6f} |"
        )

    lines.extend(["", "## Gamma sweep", ""])
    header = "| slack | " + " | ".join(f"gamma {gamma:g}" for gamma in gammas) + " |"
    lines.append(header)
    lines.append("| ---: | " + " | ".join("---:" for _ in gammas) + " |")
    for row in rows:
        values = " | ".join(f"{gain_at_gamma(row, gamma):.6f}" for gamma in gammas)
        lines.append(f"| {row.slack} | {values} |")

    best = min(rows, key=lambda row: row.gamma_to_cross)
    lines.extend(
        [
            "",
            "## Reading",
            "",
            f"The lowest threshold is slack `{best.slack}`: `gamma > {best.gamma_to_cross:.3f}`.",
            "Equivalently, the best H12 row is short by only "
            f"`{best.extra_source_deficit_per_atom_to_cross:.6f}` bits/input atom "
            "after one-for-one neutral credit.",
            "",
            "Under a uniform source, gamma above one is an unpaid information",
            "amplifier and is disallowed by the H15/H2 counting guardrail. Under",
            "a public developmental source, gamma above one means the source has",
            "real correlations: one latent/regulatory choice constrains multiple",
            "future observable bits. That can be a legitimate source-shaped",
            "Telomere target if the interpreter is fixed publicly and the source",
            "entropy deficit is reported.",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--gammas",
        type=float,
        nargs="+",
        default=[1.0, 1.1, 1.2, 1.3, 1.5, 2.0],
        help="future saved bits per neutral bit to report",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(render(H12_BOUNDED_ROWS, args.gammas))


if __name__ == "__main__":
    main()
