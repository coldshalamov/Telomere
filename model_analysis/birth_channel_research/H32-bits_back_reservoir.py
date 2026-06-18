#!/usr/bin/env python3
"""
H32 - bits-back latent seed reservoir / entropy flywheel ledger.

Candidate:

    Q_p(x) = sum_z 2^-L(z) [expand(z)=x]

Encode x with a bits-back latent-cover code. The latent cover posterior yields
bits/tape that can seed the next pass's public salt/dither schedule.

Bits-back can recycle latent entropy, but its net codelength is still the
marginal -log Q(x) plus initial/final tape accounting. This ledger prices the
"salt reservoir" part so it cannot silently become a free selector.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import log2


@dataclass(frozen=True)
class BitsBackRow:
    passes: int
    marginal_gap_per_pass: float
    posterior_tape_bits_per_pass: float
    salt_bits_spent_per_pass: float
    salt_value_per_bit: float
    net_vs_raw: float
    final_tape_delta: float
    verdict: str


def bits_back_rows(raw_bits_per_pass: float = 1024.0) -> list[BitsBackRow]:
    """Return toy accounting rows.

    marginal_gap_per_pass is how far H29-like -log Q remains above raw.
    posterior_tape_bits_per_pass is latent ambiguity returned by bits-back.
    salt_bits_spent_per_pass are bits consumed to pick salt/dither choices.
    salt_value_per_bit is the hypothetical future compression benefit per salt bit.
    """

    rows: list[BitsBackRow] = []
    for passes in (1, 2, 8, 64, 1024):
        for marginal_gap in (0.0, 0.5, 2.0):
            for tape_bits in (0.0, 8.0, 64.0):
                for salt_bits in (0.0, 8.0, 64.0):
                    if salt_bits > tape_bits and tape_bits > 0:
                        continue
                    for value_per_bit in (0.0, 1.0, 1.2):
                        # Marginal Q cost is raw + gap. Bits-back can move tape
                        # between passes, but consumed salt tape must be returned
                        # or counted as final tape loss.
                        final_tape_delta = passes * (tape_bits - salt_bits)
                        salt_value = passes * salt_bits * value_per_bit
                        salt_cost = passes * salt_bits
                        net = -(passes * marginal_gap) + salt_value - salt_cost
                        if marginal_gap == 0 and value_per_bit <= 1.0:
                            verdict = "conserved"
                        elif value_per_bit > 1.0:
                            verdict = "needs gamma>1 source"
                        else:
                            verdict = "negative"
                        rows.append(
                            BitsBackRow(
                                passes=passes,
                                marginal_gap_per_pass=marginal_gap,
                                posterior_tape_bits_per_pass=tape_bits,
                                salt_bits_spent_per_pass=salt_bits,
                                salt_value_per_bit=value_per_bit,
                                net_vs_raw=net,
                                final_tape_delta=final_tape_delta,
                                verdict=verdict,
                            )
                        )
    return rows


def selected_rows() -> list[BitsBackRow]:
    rows = []
    wanted = {
        (64, 0.0, 64.0, 64.0, 1.0),
        (64, 0.5, 64.0, 64.0, 1.0),
        (64, 0.5, 64.0, 64.0, 1.2),
        (64, 2.0, 64.0, 64.0, 1.2),
        (1024, 0.5, 64.0, 64.0, 1.0),
        (1024, 0.5, 64.0, 64.0, 1.2),
        (1024, 0.0, 64.0, 8.0, 1.0),
    }
    for row in bits_back_rows():
        key = (
            row.passes,
            row.marginal_gap_per_pass,
            row.posterior_tape_bits_per_pass,
            row.salt_bits_spent_per_pass,
            row.salt_value_per_bit,
        )
        if key in wanted:
            rows.append(row)
    return rows


def print_table() -> None:
    print("== bits-back latent reservoir accounting ==")
    print(
        "Posterior cover ambiguity can be recycled as tape, but net length is "
        "still marginal -log Q plus initial/final tape. Salt tape has opportunity "
        "cost unless it is returned."
    )
    print(
        f"{'passes':>7} {'gap/pass':>9} {'tape/pass':>10} {'salt/pass':>10} "
        f"{'gamma':>7} {'net vs raw':>11} {'final tape':>11} {'verdict':>20}"
    )
    for row in selected_rows():
        print(
            f"{row.passes:7d} {row.marginal_gap_per_pass:9.3f} "
            f"{row.posterior_tape_bits_per_pass:10.3f} "
            f"{row.salt_bits_spent_per_pass:10.3f} "
            f"{row.salt_value_per_bit:7.3f} {row.net_vs_raw:11.3f} "
            f"{row.final_tape_delta:11.3f} {row.verdict:>20}"
        )
    print()


def print_conclusion() -> None:
    print("CONCLUSION:")
    print(
        "Bits-back is the right way to implement H29's latent-cover marginal "
        "without paying a selected-cover rank. It can also carry a salt tape "
        "through a fixed reverse decode order. But the tape is conserved state: "
        "using one bit of tape as a best-of-salt selector has one bit of "
        "opportunity cost unless a public fertility law gives value_per_bit > 1. "
        "Therefore H32 collapses to H29 + H30 + H28, not a new uniform all-data "
        "escape."
    )


def main() -> None:
    print_table()
    print_conclusion()


if __name__ == "__main__":
    main()
