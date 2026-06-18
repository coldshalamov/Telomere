#!/usr/bin/env python3
"""
H38 - combined fertility-lane threshold.

Idea:

    Combine the strongest adjacent pieces:

    H18 neutral witness multiplicity      -> c neutral bits / record
    H28 public fertility class            -> value_lift must beat supply loss
    H36 developmental source              -> possible gamma > 1 source value
    H37 d-choice public lane routing      -> supply loss = -log2(1-(1-r)^d)

This kernel prices the combination. It is not a compression run.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil, inf, log, log2


@dataclass(frozen=True)
class NeutralCapacityRow:
    slack: int
    gain_per_atom_gamma0: float
    missing_bits_per_record: float
    neutral_bits_per_record: float
    perfect_credit_gain_per_atom: float

    @property
    def neutral_bits_per_atom(self) -> float:
        return self.perfect_credit_gain_per_atom - self.gain_per_atom_gamma0

    @property
    def records_per_atom(self) -> float:
        if self.neutral_bits_per_record <= 0.0:
            return 0.0
        return self.neutral_bits_per_atom / self.neutral_bits_per_record

    @property
    def gamma_needed_no_lane(self) -> float:
        return self.missing_bits_per_record / self.neutral_bits_per_record


H18_ROWS = [
    NeutralCapacityRow(-8, -0.050155, 4.565, 3.819, -0.008196),
    NeutralCapacityRow(-6, -0.045826, 4.171, 3.162, -0.011083),
    NeutralCapacityRow(-4, -0.039478, 3.593, 2.574, -0.011198),
    NeutralCapacityRow(-2, -0.026295, 2.393, 1.306, -0.011946),
    NeutralCapacityRow(0, -0.026007, 2.316, 0.507, -0.020313),
]


def lane_loss(active_fraction: float, choices: int) -> float:
    hit_fraction = 1.0 - ((1.0 - active_fraction) ** choices)
    return -log2(hit_fraction)


def gamma_needed(row: NeutralCapacityRow, active_fraction: float, choices: int) -> float:
    return (row.missing_bits_per_record + lane_loss(active_fraction, choices)) / (
        row.neutral_bits_per_record
    )


def gain_at_gamma(
    row: NeutralCapacityRow, active_fraction: float, choices: int, gamma: float
) -> float:
    return (
        row.gain_per_atom_gamma0
        - (lane_loss(active_fraction, choices) * row.records_per_atom)
        + (gamma * row.neutral_bits_per_atom)
    )


@dataclass(frozen=True)
class CombinedRow:
    slack: int
    active_fraction: float
    choices: int
    lane_loss_bits: float
    gamma_to_cross: float
    gain_gamma0: float
    gain_gamma1: float
    source_deficit_gamma1_atom: float


def combined_rows() -> list[CombinedRow]:
    rows: list[CombinedRow] = []
    for row in H18_ROWS:
        for active_fraction in (0.01, 0.05, 0.10, 0.25, 0.50):
            for choices in (1, 2, 4, 8, 16, 32):
                lane = lane_loss(active_fraction, choices)
                gain0 = gain_at_gamma(row, active_fraction, choices, 0.0)
                gain1 = gain_at_gamma(row, active_fraction, choices, 1.0)
                rows.append(
                    CombinedRow(
                        slack=row.slack,
                        active_fraction=active_fraction,
                        choices=choices,
                        lane_loss_bits=lane,
                        gamma_to_cross=gamma_needed(row, active_fraction, choices),
                        gain_gamma0=gain0,
                        gain_gamma1=gain1,
                        source_deficit_gamma1_atom=max(0.0, -gain1),
                    )
                )
    return rows


@dataclass(frozen=True)
class ChoicesForTaxRow:
    active_fraction: float
    target_loss_bits: float
    choices_needed: int
    achieved_loss_bits: float


def choices_needed_for_loss(active_fraction: float, target_loss_bits: float) -> int:
    target_hit_fraction = 2.0 ** (-target_loss_bits)
    if target_hit_fraction >= 1.0:
        return inf  # type: ignore[return-value]
    numerator = log(1.0 - target_hit_fraction)
    denominator = log(1.0 - active_fraction)
    return max(1, ceil(numerator / denominator))


def choices_for_tax_rows() -> list[ChoicesForTaxRow]:
    rows: list[ChoicesForTaxRow] = []
    for active_fraction in (0.01, 0.05, 0.10, 0.25, 0.50):
        for target_loss_bits in (2.0, 1.0, 0.5, 0.25, 0.10):
            choices = choices_needed_for_loss(active_fraction, target_loss_bits)
            rows.append(
                ChoicesForTaxRow(
                    active_fraction=active_fraction,
                    target_loss_bits=target_loss_bits,
                    choices_needed=choices,
                    achieved_loss_bits=lane_loss(active_fraction, choices),
                )
            )
    return rows


@dataclass(frozen=True)
class StandaloneClassRow:
    active_fraction: float
    choices: int
    lane_loss_bits: float
    required_value_lift: float
    uniform_value_lift: float
    uniform_extra_net: float


def standalone_class_rows() -> list[StandaloneClassRow]:
    rows: list[StandaloneClassRow] = []
    for active_fraction in (0.01, 0.05, 0.10, 0.25, 0.50):
        for choices in (1, 2, 4, 8, 16, 32):
            loss = lane_loss(active_fraction, choices)
            rows.append(
                StandaloneClassRow(
                    active_fraction=active_fraction,
                    choices=choices,
                    lane_loss_bits=loss,
                    required_value_lift=loss,
                    uniform_value_lift=0.0,
                    uniform_extra_net=-loss,
                )
            )
    return rows


def print_best_h18_baseline() -> None:
    print("== H18 neutral baseline ==")
    print(
        "H18's best no-lane row is slack -8: it needs gamma > 1.195 because "
        "one-for-one neutral credit is still short."
    )
    print(
        f"{'slack':>6} {'missing/rec':>12} {'neutral/rec':>12} "
        f"{'rec/atom':>10} {'gamma no lane':>14} {'gain gamma1':>13}"
    )
    for row in H18_ROWS:
        print(
            f"{row.slack:6d} {row.missing_bits_per_record:12.3f} "
            f"{row.neutral_bits_per_record:12.3f} "
            f"{row.records_per_atom:10.6f} {row.gamma_needed_no_lane:14.3f} "
            f"{row.perfect_credit_gain_per_atom:13.6f}"
        )
    print()


def print_combined_threshold_table() -> None:
    print("== H18 + d-choice public fertility lane ==")
    print(
        "A public lane is an added filter. d-choice lowers that added tax, but "
        "the H18 current witness deficit still has to be paid by future value."
    )
    print(
        f"{'slack':>6} {'r':>6} {'d':>4} {'lane loss':>10} "
        f"{'gamma needed':>13} {'gain g=1':>11} {'deficit g=1':>13}"
    )
    for row in combined_rows():
        if row.slack == -8 and row.active_fraction in (0.10, 0.25, 0.50):
            if row.choices in (1, 4, 8, 16, 32):
                print(
                    f"{row.slack:6d} {row.active_fraction:6.2f} "
                    f"{row.choices:4d} {row.lane_loss_bits:10.3f} "
                    f"{row.gamma_to_cross:13.3f} {row.gain_gamma1:11.6f} "
                    f"{row.source_deficit_gamma1_atom:13.6f}"
                )
    print()


def print_standalone_class_table() -> None:
    print("== public fertility class alone ==")
    print(
        "Without neutral-current deficit, the value lift needed per selected "
        "record is just the d-choice lane tax. Uniform lift remains zero."
    )
    print(
        f"{'r':>6} {'d':>4} {'lane loss':>10} {'required lift':>14} "
        f"{'uniform net':>12}"
    )
    for row in standalone_class_rows():
        if row.active_fraction in (0.10, 0.25, 0.50) and row.choices in (
            1,
            4,
            8,
            16,
            32,
        ):
            print(
                f"{row.active_fraction:6.2f} {row.choices:4d} "
                f"{row.lane_loss_bits:10.3f} {row.required_value_lift:14.3f} "
                f"{row.uniform_extra_net:12.3f}"
            )
    print()


def print_choices_needed_table() -> None:
    print("== choices needed for a target lane tax ==")
    print(
        "This is the engineering target for public fertility lanes: enough "
        "choices can make the stateless lane tax small, but not negative."
    )
    print(
        f"{'r':>6} {'target loss':>12} {'d needed':>9} {'achieved':>10}"
    )
    for row in choices_for_tax_rows():
        if row.active_fraction in (0.01, 0.10, 0.25):
            print(
                f"{row.active_fraction:6.2f} {row.target_loss_bits:12.3f} "
                f"{row.choices_needed:9d} {row.achieved_loss_bits:10.3f}"
            )
    print()


def main() -> None:
    print_best_h18_baseline()
    print_combined_threshold_table()
    print_standalone_class_table()
    print_choices_needed_table()
    print("CONCLUSION:")
    print(
        "d-choice routing does not make the neutral/developmental branch a "
        "uniform all-data solution. Uniform value lift is still zero, and a "
        "public lane is still a filter. It does, however, lower the value-lift "
        "target for source-shaped fertility classes: for r=0.10,d=8 the lane "
        "tax is only 0.812 bits/selected record, and for d=16 it is 0.296. "
        "The honest next target is therefore a source-shaped two-layer kernel "
        "that proves value_lift above that reduced tax while random controls "
        "stay negative."
    )


if __name__ == "__main__":
    main()
