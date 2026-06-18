#!/usr/bin/env python3
"""
H26 - value/count separation ledger for position, lane, and seed-class signals.

This is the narrow remaining escape hatch behind several "math trick" ideas:

    use relative position / a ready lane / a public seed class to tell the
    decoder which salt, pass, or open/carry state applies.

The decoder-visible signal can be real and stateless. The question is whether
the signal is also compressive. Under the uniform hash law, a class that carries
b bits of state has fraction 2^-b of the seed/position supply, so the match
frontier loses b bits. The only way this can be net-positive is if that same
public class has extra compression value per eligible seed.

No compression search is run here. This is only a counting ledger.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import log2


GROSS_BITS_PER_MATCH = 2.0
BOARD_ATOMS = 1_000_000


def binary_entropy(p: float) -> float:
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -(p * log2(p) + (1.0 - p) * log2(1.0 - p))


@dataclass(frozen=True)
class StateClassRow:
    state_bits: float
    class_fraction: float
    supply_loss_bits: float
    explicit_state_net: float
    public_class_net_no_lift: float
    value_lift_needed: float


def state_class_rows(gross_bits: float = GROSS_BITS_PER_MATCH) -> list[StateClassRow]:
    rows: list[StateClassRow] = []
    for state_bits in (1, 2, 3, 4, 6, 8, 10, 16):
        class_fraction = 2.0 ** (-state_bits)
        supply_loss = state_bits
        rows.append(
            StateClassRow(
                state_bits=state_bits,
                class_fraction=class_fraction,
                supply_loss_bits=supply_loss,
                explicit_state_net=gross_bits - state_bits,
                public_class_net_no_lift=gross_bits - supply_loss,
                value_lift_needed=max(0.0, supply_loss - gross_bits),
            )
        )
    return rows


@dataclass(frozen=True)
class ReadyLaneRow:
    ready_fraction: float
    boundary_bits_per_open: float
    hidden_subset_bits_per_open: float
    public_lane_supply_loss: float
    public_lane_net_no_lift: float
    value_lift_needed: float


def ready_lane_rows(
    board_atoms: int = BOARD_ATOMS, gross_bits: float = GROSS_BITS_PER_MATCH
) -> list[ReadyLaneRow]:
    rows: list[ReadyLaneRow] = []
    for ready_fraction in (0.5, 0.25, 0.125, 0.10, 0.0625, 0.01):
        opened = ready_fraction * board_atoms
        boundary_bits_per_open = log2(board_atoms + 1) / opened
        hidden_subset_bits_per_open = binary_entropy(ready_fraction) / ready_fraction
        public_lane_supply_loss = log2(1.0 / ready_fraction)
        rows.append(
            ReadyLaneRow(
                ready_fraction=ready_fraction,
                boundary_bits_per_open=boundary_bits_per_open,
                hidden_subset_bits_per_open=hidden_subset_bits_per_open,
                public_lane_supply_loss=public_lane_supply_loss,
                public_lane_net_no_lift=gross_bits - public_lane_supply_loss,
                value_lift_needed=max(0.0, public_lane_supply_loss - gross_bits),
            )
        )
    return rows


@dataclass(frozen=True)
class LiftRow:
    state_bits: float
    value_lift: float
    net_bits: float
    crosses: bool


def lift_sweep(
    state_bits: float = 6.0, gross_bits: float = GROSS_BITS_PER_MATCH
) -> list[LiftRow]:
    rows: list[LiftRow] = []
    for value_lift in (0.0, 0.5, 1.0, 2.0, 3.0, 4.0, 6.0, 8.0):
        net_bits = gross_bits + value_lift - state_bits
        rows.append(
            LiftRow(
                state_bits=state_bits,
                value_lift=value_lift,
                net_bits=net_bits,
                crosses=net_bits > 0.0,
            )
        )
    return rows


@dataclass(frozen=True)
class GammaRow:
    state_bits: float
    gamma: float
    value_lift: float
    net_bits: float


def developmental_gamma_rows(
    state_bits: float = 6.0, gross_bits: float = GROSS_BITS_PER_MATCH
) -> list[GammaRow]:
    rows: list[GammaRow] = []
    for gamma in (0.0, 0.25, 0.50, 0.667, 0.75, 1.0, 1.2):
        value_lift = gamma * state_bits
        rows.append(
            GammaRow(
                state_bits=state_bits,
                gamma=gamma,
                value_lift=value_lift,
                net_bits=gross_bits + value_lift - state_bits,
            )
        )
    return rows


def print_state_class_table() -> None:
    print("== decoder-visible seed/position class under uniform hash ==")
    print(
        "A class that tells the decoder b bits of state occupies 2^-b of the "
        "eligible supply."
    )
    print(
        "With no extra value in that class, replacing a stored state tag by a "
        "public class is conserved."
    )
    print(
        f"{'b state':>8} {'class frac':>12} {'supply loss':>12} "
        f"{'stored-tag net':>15} {'class net':>11} {'lift to >0':>11}"
    )
    for row in state_class_rows():
        print(
            f"{row.state_bits:8.1f} {row.class_fraction:12.6g} "
            f"{row.supply_loss_bits:12.3f} {row.explicit_state_net:15.3f} "
            f"{row.public_class_net_no_lift:11.3f} {row.value_lift_needed:11.3f}"
        )
    print()


def print_ready_lane_table() -> None:
    print("== ready-boundary / active-lane accounting ==")
    print(
        "A single boundary is cheap only after the ready positions are public. "
        "If the ready set is content-selected, the subset layout is the bill."
    )
    print(
        f"{'ready r':>8} {'boundary/open':>14} {'hidden subset/open':>19} "
        f"{'public lane loss':>16} {'lane net':>10} {'lift to >0':>11}"
    )
    for row in ready_lane_rows():
        print(
            f"{row.ready_fraction:8.4f} {row.boundary_bits_per_open:14.6f} "
            f"{row.hidden_subset_bits_per_open:19.6f} "
            f"{row.public_lane_supply_loss:16.6f} "
            f"{row.public_lane_net_no_lift:10.3f} "
            f"{row.value_lift_needed:11.3f}"
        )
    print()


def print_lift_sweep() -> None:
    print("== finite-pass value lift target (example: 64 states, b=6) ==")
    print(
        "For 64 salts/passes/lanes, a public class needs four extra value bits "
        "per selected record to beat a 2-bit gross match."
    )
    print(f"{'b state':>8} {'value lift':>11} {'net bits':>10} {'crosses':>8}")
    for row in lift_sweep():
        verdict = "yes" if row.crosses else "no"
        print(
            f"{row.state_bits:8.1f} {row.value_lift:11.3f} "
            f"{row.net_bits:10.3f} {verdict:>8}"
        )
    print()


def print_developmental_target() -> None:
    print("== source-shaped/developmental target ==")
    print(
        "If a public class has value lift gamma*b, finite T crosses when "
        "gross + gamma*b > b. Unbounded T needs gamma >= 1 asymptotically."
    )
    print(f"{'b state':>8} {'gamma':>8} {'value lift':>11} {'net bits':>10}")
    for row in developmental_gamma_rows():
        print(
            f"{row.state_bits:8.1f} {row.gamma:8.3f} "
            f"{row.value_lift:11.3f} {row.net_bits:10.3f}"
        )
    print()


def main() -> None:
    print_state_class_table()
    print_ready_lane_table()
    print_lift_sweep()
    print_developmental_target()
    print("CONCLUSION:")
    print(
        "Position/lane classes are valid stateless decode geometry, but under "
        "uniform hash they spend one match-supply bit for each state bit they "
        "make visible. The missing piece is not another boundary marker; it is "
        "a decoder-visible class whose compression value separates from its "
        "count by enough to satisfy E[value|class]-E[value] > supply_loss-gross."
    )


if __name__ == "__main__":
    main()
