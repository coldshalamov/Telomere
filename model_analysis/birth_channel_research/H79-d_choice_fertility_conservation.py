#!/usr/bin/env python3
"""H79 - d-choice fertility conservation audit.

This kernel separates two meanings of "d choices":

1. placement d-choice:
   A stored record has d public candidate cells. The decoder can recompute the
   canonical placement. This can reduce coordinate/lane supply loss.

2. witness d-choice:
   The encoder has d independent seed witnesses for the same previous bytes and
   picks the one whose *encoded output stream* lands in a fertile class. This
   can bias the next layer, but the multiplicity itself is an information
   channel with cost about log2(d).

The apparent loophole is to charge the cheap placement lane loss while claiming
the much larger future source/fertility gain from witness selection. H79 prices
both currencies on the same rows.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


def h2(p: float) -> float:
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -(p * math.log2(p) + (1.0 - p) * math.log2(1.0 - p))


def lane_hit_fraction(fertile_fraction: float, choices: int) -> float:
    return 1.0 - (1.0 - fertile_fraction) ** choices


def lane_loss(fertile_fraction: float, choices: int) -> float:
    return -math.log2(lane_hit_fraction(fertile_fraction, choices))


def bernoulli_kl(p: float, q: float) -> float:
    """D(Bernoulli(p) || Bernoulli(q)) in bits."""

    total = 0.0
    if p > 0.0:
        total += p * math.log2(p / q)
    if p < 1.0:
        total += (1.0 - p) * math.log2((1.0 - p) / (1.0 - q))
    return total


def choices_for_hit(fertile_fraction: float, target_hit: float) -> int:
    if target_hit <= fertile_fraction:
        return 1
    if target_hit >= 1.0:
        return math.inf  # type: ignore[return-value]
    return max(
        1,
        math.ceil(math.log(1.0 - target_hit) / math.log(1.0 - fertile_fraction)),
    )


@dataclass(frozen=True)
class ConservationRow:
    fertile_fraction: float
    choices: int
    hit_fraction: float
    placement_lane_loss: float
    witness_choice_cost: float
    class_kl_created: float
    apparent_gain_if_lane_priced: float
    honest_choice_margin: float


def conservation_rows() -> list[ConservationRow]:
    rows: list[ConservationRow] = []
    for fertile_fraction in (0.01, 0.03, 0.10, 0.25, 0.50):
        for choices in (1, 2, 4, 7, 8, 16, 23, 32, 64, 128):
            hit = lane_hit_fraction(fertile_fraction, choices)
            kl = bernoulli_kl(hit, fertile_fraction)
            witness_cost = math.log2(choices)
            placement_cost = lane_loss(fertile_fraction, choices)
            rows.append(
                ConservationRow(
                    fertile_fraction=fertile_fraction,
                    choices=choices,
                    hit_fraction=hit,
                    placement_lane_loss=placement_cost,
                    witness_choice_cost=witness_cost,
                    class_kl_created=kl,
                    apparent_gain_if_lane_priced=kl - placement_cost,
                    honest_choice_margin=kl - witness_cost,
                )
            )
    return rows


@dataclass(frozen=True)
class RetentionRow:
    fertile_fraction: float
    target: str
    required_hit: float
    choices_needed: int
    placement_lane_loss: float
    witness_choice_cost: float
    class_kl_created: float
    honest_choice_margin: float


RETENTION_TARGETS = [
    ("toy H59/H58 c*~0.146", 0.146),
    ("toy H7 c*~0.155", 0.155),
    ("exact H74 c*~0.508", 0.508),
    ("exact H74 pFF~0.903", 0.903),
]


def retention_rows() -> list[RetentionRow]:
    rows: list[RetentionRow] = []
    for fertile_fraction in (0.10, 0.25, 0.50):
        for label, required_hit in RETENTION_TARGETS:
            d = choices_for_hit(fertile_fraction, required_hit)
            hit = lane_hit_fraction(fertile_fraction, d)
            kl = bernoulli_kl(hit, fertile_fraction)
            rows.append(
                RetentionRow(
                    fertile_fraction=fertile_fraction,
                    target=label,
                    required_hit=required_hit,
                    choices_needed=d,
                    placement_lane_loss=lane_loss(fertile_fraction, d),
                    witness_choice_cost=math.log2(d),
                    class_kl_created=kl,
                    honest_choice_margin=kl - math.log2(d),
                )
            )
    return rows


@dataclass(frozen=True)
class FinitePassRow:
    target: str
    miss_bits_per_record: float
    fertile_fraction: float
    choices: int
    lane_loss_bits: float
    steady_value_lift_needed: float
    finite_value_lift: float
    passes_to_cross: int | None


def passes_to_cross(miss: float, lane: float, value_lift: float) -> int | None:
    threshold = miss + lane
    if value_lift <= threshold:
        return None
    # Total over P passes: -P*(miss+lane) + (P-1)*value_lift.
    return max(2, math.floor(value_lift / (value_lift - threshold)) + 1)


def finite_pass_rows() -> list[FinitePassRow]:
    targets = [
        ("H12 perfect-credit miss", 0.746),
        ("H9 fixed-slack miss", 1.261),
        ("H7 raw first-hit miss", 1.357),
    ]
    rows: list[FinitePassRow] = []
    for label, miss in targets:
        for fertile_fraction, choices in ((0.10, 16), (0.10, 23), (0.10, 64)):
            lane = lane_loss(fertile_fraction, choices)
            needed = miss + lane
            for lift_multiplier in (0.95, 1.05, 1.50):
                value = needed * lift_multiplier
                rows.append(
                    FinitePassRow(
                        target=label,
                        miss_bits_per_record=miss,
                        fertile_fraction=fertile_fraction,
                        choices=choices,
                        lane_loss_bits=lane,
                        steady_value_lift_needed=needed,
                        finite_value_lift=value,
                        passes_to_cross=passes_to_cross(miss, lane, value),
                    )
                )
    return rows


def print_conservation_rows() -> None:
    print("== d-choice source creation conservation ==")
    print(
        "If d choices are independent witness alternatives, the created "
        "fertility KL must be paid by witness multiplicity, not by the "
        "cheaper placement lane loss."
    )
    print(
        f"{'r':>6} {'d':>5} {'hit':>9} {'place loss':>11} "
        f"{'log d':>8} {'KL made':>9} {'fake net':>9} {'honest net':>10}"
    )
    for row in conservation_rows():
        if row.fertile_fraction in (0.10, 0.25) and row.choices in (
            1,
            4,
            7,
            16,
            23,
            64,
        ):
            print(
                f"{row.fertile_fraction:6.2f} {row.choices:5d} "
                f"{row.hit_fraction:9.4f} {row.placement_lane_loss:11.3f} "
                f"{row.witness_choice_cost:8.3f} {row.class_kl_created:9.3f} "
                f"{row.apparent_gain_if_lane_priced:9.3f} "
                f"{row.honest_choice_margin:10.3f}"
            )
    print()


def print_retention_rows() -> None:
    print("== choices needed for H77 retention thresholds ==")
    print(
        "The d needed can look cheap under placement loss. If the same d is "
        "used to bias record values, log2(d) is the honest multiplicity bill."
    )
    print(
        f"{'r':>6} {'target':<22} {'need hit':>9} {'d':>5} "
        f"{'place loss':>11} {'log d':>8} {'KL made':>9} {'honest net':>10}"
    )
    for row in retention_rows():
        if row.fertile_fraction == 0.10 or row.target.startswith("exact"):
            print(
                f"{row.fertile_fraction:6.2f} {row.target:<22} "
                f"{row.required_hit:9.3f} {row.choices_needed:5d} "
                f"{row.placement_lane_loss:11.3f} {row.witness_choice_cost:8.3f} "
                f"{row.class_kl_created:9.3f} {row.honest_choice_margin:10.3f}"
            )
    print()


def print_finite_pass_rows() -> None:
    print("== finite-pass public lane value threshold ==")
    print(
        "For a recurring lane, steady positive value needs "
        "future_lift > current_miss + lane_loss. The first pass pays before "
        "it can harvest the fertility it created."
    )
    print(
        f"{'target':<25} {'r':>5} {'d':>4} {'lane':>7} {'need':>7} "
        f"{'lift':>7} {'P cross':>8}"
    )
    for row in finite_pass_rows():
        if row.finite_value_lift in (
            row.steady_value_lift_needed * 1.05,
            row.steady_value_lift_needed * 1.50,
        ):
            p_cross = "never" if row.passes_to_cross is None else str(row.passes_to_cross)
            print(
                f"{row.target:<25} {row.fertile_fraction:5.2f} "
                f"{row.choices:4d} {row.lane_loss_bits:7.3f} "
                f"{row.steady_value_lift_needed:7.3f} "
                f"{row.finite_value_lift:7.3f} {p_cross:>8}"
            )
    print()


def main() -> None:
    print_conservation_rows()
    print_retention_rows()
    print_finite_pass_rows()
    print("== verdict ==")
    print(
        "Public d-choice placement remains useful for coordinate/salt lanes. "
        "It does not by itself create a high-fertility record-value source. "
        "When d choices are actually alternative witnesses for the same bytes, "
        "the created source KL is bounded by log2(d), so the future gain is "
        "paid by witness multiplicity. The next surviving target must either "
        "use position/phase as the thing being refreshed, or measure a real "
        "value lift that exceeds miss + lane loss without borrowing witness "
        "choice bits."
    )


if __name__ == "__main__":
    main()
