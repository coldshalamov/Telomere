#!/usr/bin/env python3
"""H137 - closed-loop bits-back salt flywheel.

H32 priced posterior tape as a conserved reservoir. H137 makes the salting
version explicit:

    pass p decodes a latent cover
    posterior bits become tape
    tape bits choose/seed the next public salt schedule
    final tape is settled in the stream or charged as lost state

If a salt bit is used only to choose among uniform hash trials, its maximum
source-free value is one bit. Therefore a closed loop has non-positive slope
unless a separate fertility/source law gives value_per_salt_bit > 1.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class FlywheelRow:
    passes: int
    marginal_gap: float
    posterior_tape: float
    salt_spend: float
    value_per_salt_bit: float
    start_tape: float
    final_tape_delta: float
    settled_final_bits: float
    net_vs_raw: float
    slope_bits_per_pass: float
    verdict: str


def h2(p: float) -> float:
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -(p * math.log2(p) + (1.0 - p) * math.log2(1.0 - p))


def row(
    passes: int,
    marginal_gap: float,
    posterior_tape: float,
    salt_spend: float,
    value_per_salt_bit: float,
    start_tape: float = 0.0,
) -> FlywheelRow:
    produced = passes * posterior_tape
    consumed = passes * salt_spend
    final_delta = start_tape + produced - consumed

    # If final_delta is negative, the missing tape was an unstored initial state.
    # If it is positive, the leftover final ANS/tape state must be settled. A
    # settled surplus is not a compression dividend, so charge positive surplus
    # and negative deficit symmetrically as visible state.
    settled = abs(final_delta)

    salt_value = consumed * value_per_salt_bit
    salt_opportunity_cost = consumed
    net = -(passes * marginal_gap) + salt_value - salt_opportunity_cost - settled
    slope = net / passes
    if value_per_salt_bit <= 1.0 and marginal_gap >= 0.0:
        verdict = "conserved_or_negative"
    elif slope > 0.0:
        verdict = "requires_gamma_gt_1"
    else:
        verdict = "negative_after_settlement"
    return FlywheelRow(
        passes=passes,
        marginal_gap=marginal_gap,
        posterior_tape=posterior_tape,
        salt_spend=salt_spend,
        value_per_salt_bit=value_per_salt_bit,
        start_tape=start_tape,
        final_tape_delta=final_delta,
        settled_final_bits=settled,
        net_vs_raw=net,
        slope_bits_per_pass=slope,
        verdict=verdict,
    )


def selected_rows() -> list[FlywheelRow]:
    rows: list[FlywheelRow] = []
    for passes in (2, 64, 4096):
        for marginal_gap in (0.0, 0.25, 1.0):
            rows.append(row(passes, marginal_gap, posterior_tape=64.0, salt_spend=64.0, value_per_salt_bit=1.0))
            rows.append(row(passes, marginal_gap, posterior_tape=64.0, salt_spend=64.0, value_per_salt_bit=1.1))
            rows.append(row(passes, marginal_gap, posterior_tape=64.0, salt_spend=8.0, value_per_salt_bit=1.0))
            rows.append(row(passes, marginal_gap, posterior_tape=8.0, salt_spend=64.0, value_per_salt_bit=1.0))
    return rows


def exception_salt_rows() -> list[tuple[int, float, float]]:
    """Salt value needed to pay a near-total exception ledger.

    This connects the salt flywheel to H128/H130: if salt bits are used to
    maintain a near-total public board, the required value per salt bit must
    exceed one by the exception ledger plus witness gap divided by salt spend.
    """

    out: list[tuple[int, float, float]] = []
    salt_bits = 64.0
    witness_gap = 0.468557
    for passes in (64, 4096):
        for eps in (0.001, 0.01):
            exception_bits = h2(eps) + eps * math.log2(passes - 1)
            required_gamma = 1.0 + (witness_gap + exception_bits) / salt_bits
            out.append((passes, eps, required_gamma))
    return out


def print_rows(rows: list[FlywheelRow]) -> None:
    print("== closed-loop bits-back salt flywheel ==")
    print("Net = -gap + salt*(gamma-1) - final/initial tape settlement.")
    print(
        f"{'P':>5} {'gap':>6} {'tape':>7} {'salt':>7} {'gamma':>7} "
        f"{'final d':>9} {'settle':>9} {'net':>10} {'slope':>9} verdict"
    )
    for item in rows:
        if item.passes == 4096 and item.marginal_gap not in (0.25,):
            continue
        print(
            f"{item.passes:5d} {item.marginal_gap:6.3f} {item.posterior_tape:7.1f} "
            f"{item.salt_spend:7.1f} {item.value_per_salt_bit:7.3f} "
            f"{item.final_tape_delta:9.1f} {item.settled_final_bits:9.1f} "
            f"{item.net_vs_raw:10.3f} {item.slope_bits_per_pass:9.6f} {item.verdict}"
        )
    print()


def print_exception_rows() -> None:
    print("== gamma needed if salt also has to pay witness/exception margin ==")
    print("Assume 64 salt bits/record-equivalent and H105 witness gap 0.468557 bits.")
    print(f"{'P':>5} {'eps':>8} {'required gamma':>15}")
    for passes, eps, gamma in exception_salt_rows():
        print(f"{passes:5d} {eps:8.3g} {gamma:15.9f}")
    print()


def print_reading() -> None:
    print("== reading ==")
    print(
        "Bits-back can make salting stateless in decode order if the tape is "
        "canonical and settled, but it cannot make the salt choice free. A salt "
        "bit spent on uniform best-of-search has one bit of opportunity cost."
    )
    print(
        "The only positive slopes require gamma>1: a real fertility/source law "
        "where one salt bit creates more than one bit of future paid witness "
        "margin. That is not supplied by the reservoir itself."
    )


def main() -> None:
    print_rows(selected_rows())
    print_exception_rows()
    print_reading()


if __name__ == "__main__":
    main()
