#!/usr/bin/env python3
"""
H28 - public fertility-class target.

H26/H27 leave one constructive opening:

    a decoder-visible public class C has small count fraction f, but records in
    C are more valuable by more than log2(1/f).

This is the biology-shaped target: position/locus/class is visible to the
decoder and also predictive of downstream fertility. Under the uniform hash law
the class is independent of the target and the lift is zero. Under a public
developmental source law it could be positive, but then the premise has changed
from content-blind roughly-all-data compression to source-shaped compression.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import log2


@dataclass(frozen=True)
class FertilityClassRow:
    class_fraction: float
    supply_loss: float
    uniform_lift: float
    uniform_extra_net: float
    lift_needed: float


def fertility_class_rows() -> list[FertilityClassRow]:
    rows: list[FertilityClassRow] = []
    for class_fraction in (0.5, 0.25, 0.125, 0.10, 0.0625, 0.01, 1 / 64, 1 / 1024):
        supply_loss = log2(1.0 / class_fraction)
        uniform_lift = 0.0
        rows.append(
            FertilityClassRow(
                class_fraction=class_fraction,
                supply_loss=supply_loss,
                uniform_lift=uniform_lift,
                uniform_extra_net=uniform_lift - supply_loss,
                lift_needed=supply_loss,
            )
        )
    return rows


@dataclass(frozen=True)
class DevelopmentalRow:
    class_fraction: float
    gamma: float
    supply_loss: float
    value_lift: float
    extra_net: float
    crosses: bool


def developmental_rows() -> list[DevelopmentalRow]:
    rows: list[DevelopmentalRow] = []
    for class_fraction in (0.25, 0.10, 1 / 64):
        supply_loss = log2(1.0 / class_fraction)
        for gamma in (0.0, 0.5, 0.75, 1.0, 1.2, 1.5):
            value_lift = gamma * supply_loss
            extra_net = value_lift - supply_loss
            rows.append(
                DevelopmentalRow(
                    class_fraction=class_fraction,
                    gamma=gamma,
                    supply_loss=supply_loss,
                    value_lift=value_lift,
                    extra_net=extra_net,
                    crosses=extra_net > 0.0,
                )
            )
    return rows


@dataclass(frozen=True)
class NeutralRow:
    neutral_bits: float
    gamma: float
    future_value: float
    net_after_capacity_bound: float
    crosses_capacity: bool


def neutral_rows() -> list[NeutralRow]:
    """Model neutral choice as a future-fertility channel.

    A same-cost neutral choice of c bits can steer at most c bits of future value
    under a one-for-one conservation bound. gamma>1 is the target for a real
    developmental amplifier; gamma<=1 is conserved.
    """
    rows: list[NeutralRow] = []
    for neutral_bits in (0.5, 1.0, 2.0, 4.0, 8.0):
        for gamma in (0.0, 0.5, 1.0, 1.2):
            future_value = gamma * neutral_bits
            net = future_value - neutral_bits
            rows.append(
                NeutralRow(
                    neutral_bits=neutral_bits,
                    gamma=gamma,
                    future_value=future_value,
                    net_after_capacity_bound=net,
                    crosses_capacity=net > 0.0,
                )
            )
    return rows


def print_uniform_class_table() -> None:
    print("== public fertility class under uniform hash ==")
    print(
        "A decoder-visible class with fraction f costs log2(1/f) supply bits. "
        "Under uniform hash its target/value lift is zero."
    )
    print(
        f"{'class f':>10} {'supply loss':>12} {'uniform lift':>13} "
        f"{'extra net':>11} {'lift needed':>12}"
    )
    for row in fertility_class_rows():
        print(
            f"{row.class_fraction:10.6g} {row.supply_loss:12.6f} "
            f"{row.uniform_lift:13.6f} {row.uniform_extra_net:11.6f} "
            f"{row.lift_needed:12.6f}"
        )
    print()


def print_developmental_table() -> None:
    print("== developmental value/count separation target ==")
    print(
        "gamma means value_lift = gamma * supply_loss. A public class crosses "
        "only when gamma > 1 before ordinary record costs."
    )
    print(
        f"{'class f':>10} {'gamma':>7} {'supply loss':>12} "
        f"{'value lift':>12} {'extra net':>11} {'crosses':>8}"
    )
    for row in developmental_rows():
        verdict = "yes" if row.crosses else "no"
        print(
            f"{row.class_fraction:10.6g} {row.gamma:7.3f} "
            f"{row.supply_loss:12.6f} {row.value_lift:12.6f} "
            f"{row.extra_net:11.6f} {verdict:>8}"
        )
    print()


def print_neutral_table() -> None:
    print("== neutral-choice future fertility bound ==")
    print(
        "Neutral same-cost seed choice is useful only if each neutral bit saves "
        "more than one future bit. Uniform future value has gamma=0."
    )
    print(
        f"{'neutral bits':>12} {'gamma':>7} {'future value':>13} "
        f"{'net vs cap':>11} {'crosses':>8}"
    )
    for row in neutral_rows():
        verdict = "yes" if row.crosses_capacity else "no"
        print(
            f"{row.neutral_bits:12.3f} {row.gamma:7.3f} "
            f"{row.future_value:13.3f} {row.net_after_capacity_bound:11.3f} "
            f"{verdict:>8}"
        )
    print()


def main() -> None:
    print_uniform_class_table()
    print_developmental_table()
    print_neutral_table()
    print("CONCLUSION:")
    print(
        "The public fertility-class idea is the right next target, but it is "
        "not a uniform-hash all-data solution unless a class can predict value "
        "despite being independent of the target. The falsifiable breakthrough "
        "criterion is value_lift > log2(1/f), with random controls staying "
        "negative and only a public developmental source crossing."
    )


if __name__ == "__main__":
    main()
