#!/usr/bin/env python3
"""
H39 - two-layer source-shaped fertility kernel.

Idea:

    Use H37/H38 d-choice public lanes as stateless routing, then ask how much
    predeclared future-source value is needed to pay the lane tax.

This is not a uniform all-data compression claim. It is the constructive
source-shaped target left by H38: prove that a fixed public developmental law
can provide value_lift > -log2(1-(1-r)^d), while uniform controls stay negative.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil, log2
import random


def binary_entropy(p: float) -> float:
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -(p * log2(p) + (1.0 - p) * log2(1.0 - p))


def bernoulli_cross_entropy(p_source: float, p_model: float) -> float:
    return -(
        p_source * log2(p_model)
        + (1.0 - p_source) * log2(1.0 - p_model)
    )


def lane_loss(active_fraction: float, choices: int) -> float:
    hit_fraction = 1.0 - ((1.0 - active_fraction) ** choices)
    return -log2(hit_fraction)


@dataclass(frozen=True)
class SourceLiftRow:
    active_fraction: float
    choices: int
    future_bits: int
    bias: float
    lane_loss_bits: float
    source_value_lift: float
    source_net_after_lane: float
    uniform_model_penalty: float
    uniform_net_after_lane: float
    crosses_source: bool
    uniform_control_negative: bool


def source_lift_rows() -> list[SourceLiftRow]:
    rows: list[SourceLiftRow] = []
    for active_fraction, choices in (
        (0.10, 8),
        (0.10, 16),
        (0.10, 32),
        (0.25, 8),
        (0.25, 16),
    ):
        loss = lane_loss(active_fraction, choices)
        for future_bits in (1, 2, 4, 8):
            for bias in (0.60, 0.70, 0.75, 0.80, 0.85, 0.90):
                source_value = future_bits * (1.0 - binary_entropy(bias))
                uniform_penalty = future_bits * (
                    bernoulli_cross_entropy(0.5, bias) - 1.0
                )
                source_net = source_value - loss
                uniform_net = -loss - uniform_penalty
                rows.append(
                    SourceLiftRow(
                        active_fraction=active_fraction,
                        choices=choices,
                        future_bits=future_bits,
                        bias=bias,
                        lane_loss_bits=loss,
                        source_value_lift=source_value,
                        source_net_after_lane=source_net,
                        uniform_model_penalty=uniform_penalty,
                        uniform_net_after_lane=uniform_net,
                        crosses_source=source_net > 0.0,
                        uniform_control_negative=uniform_net < 0.0,
                    )
                )
    return rows


@dataclass(frozen=True)
class BitsNeededRow:
    active_fraction: float
    choices: int
    bias: float
    lift_per_future_bit: float
    lane_loss_bits: float
    future_bits_needed: int
    achieved_source_net: float
    uniform_net_at_needed_bits: float


def bits_needed_rows() -> list[BitsNeededRow]:
    rows: list[BitsNeededRow] = []
    for active_fraction, choices in ((0.10, 8), (0.10, 16), (0.10, 32), (0.25, 8)):
        loss = lane_loss(active_fraction, choices)
        for bias in (0.60, 0.70, 0.75, 0.80, 0.85, 0.90):
            lift_per_bit = 1.0 - binary_entropy(bias)
            needed = ceil(loss / lift_per_bit) if lift_per_bit > 0.0 else 10**9
            source_value = needed * lift_per_bit
            uniform_penalty = needed * (bernoulli_cross_entropy(0.5, bias) - 1.0)
            rows.append(
                BitsNeededRow(
                    active_fraction=active_fraction,
                    choices=choices,
                    bias=bias,
                    lift_per_future_bit=lift_per_bit,
                    lane_loss_bits=loss,
                    future_bits_needed=needed,
                    achieved_source_net=source_value - loss,
                    uniform_net_at_needed_bits=-loss - uniform_penalty,
                )
            )
    return rows


@dataclass(frozen=True)
class MixtureRow:
    active_fraction: float
    choices: int
    future_bits: int
    source_bias: float
    mixture_weight: float
    model_bias: float
    source_value_lift: float
    uniform_penalty: float
    source_net_after_lane: float
    uniform_net_after_lane: float


def mixture_rows() -> list[MixtureRow]:
    rows: list[MixtureRow] = []
    active_fraction = 0.10
    choices = 16
    loss = lane_loss(active_fraction, choices)
    for future_bits in (2, 4, 8):
        for source_bias in (0.75, 0.80, 0.85):
            for mixture_weight in (0.25, 0.50, 0.75, 1.0):
                model_bias = (1.0 - mixture_weight) * 0.5 + mixture_weight * source_bias
                source_ce = future_bits * bernoulli_cross_entropy(
                    source_bias, model_bias
                )
                uniform_ce = future_bits * bernoulli_cross_entropy(0.5, model_bias)
                source_value = future_bits - source_ce
                uniform_penalty = uniform_ce - future_bits
                rows.append(
                    MixtureRow(
                        active_fraction=active_fraction,
                        choices=choices,
                        future_bits=future_bits,
                        source_bias=source_bias,
                        mixture_weight=mixture_weight,
                        model_bias=model_bias,
                        source_value_lift=source_value,
                        uniform_penalty=uniform_penalty,
                        source_net_after_lane=source_value - loss,
                        uniform_net_after_lane=-loss - uniform_penalty,
                    )
                )
    return rows


@dataclass(frozen=True)
class SupportDeficitRow:
    active_fraction: float
    choices: int
    support_deficit_bits: float
    lane_loss_bits: float
    source_net_after_lane: float
    uniform_support_fraction_log2: float


def support_deficit_rows() -> list[SupportDeficitRow]:
    rows: list[SupportDeficitRow] = []
    for active_fraction, choices in ((0.10, 8), (0.10, 16), (0.10, 32), (0.25, 8)):
        loss = lane_loss(active_fraction, choices)
        for support_deficit_bits in (0.10, 0.25, 0.296, 0.50, 1.0, 2.0):
            rows.append(
                SupportDeficitRow(
                    active_fraction=active_fraction,
                    choices=choices,
                    support_deficit_bits=support_deficit_bits,
                    lane_loss_bits=loss,
                    source_net_after_lane=support_deficit_bits - loss,
                    uniform_support_fraction_log2=-support_deficit_bits,
                )
            )
    return rows


@dataclass(frozen=True)
class ClassCorrelationRow:
    kind: str
    active_fraction: float
    choices: int
    child_count: int
    value_per_child: float
    q_fertile: float
    q_infertile: float
    measured_class_fraction: float
    global_easy_rate: float
    all_value: float
    fertile_value: float
    value_lift: float
    lane_loss_bits: float
    net_after_lane: float


def class_correlation_rows(trials: int = 200_000) -> list[ClassCorrelationRow]:
    """Monte Carlo check of the exact H28/H38 lift definition.

    In the source row, public class membership changes future-child easiness.
    In the uniform control, easiness has the same global marginal but is
    independent of public class membership.
    """

    rows: list[ClassCorrelationRow] = []
    rng = random.Random(39039)
    for active_fraction, choices in ((0.10, 8), (0.10, 16), (0.25, 8)):
        f_d = 1.0 - ((1.0 - active_fraction) ** choices)
        loss = lane_loss(active_fraction, choices)
        for child_count, value_per_child, q_fertile, q_infertile in (
            (4, 2.0, 0.50, 0.20),
            (4, 1.0, 0.50, 0.20),
            (2, 2.0, 0.50, 0.20),
            (4, 2.0, 0.40, 0.25),
        ):
            global_q = f_d * q_fertile + (1.0 - f_d) * q_infertile
            for kind in ("source", "uniform"):
                class_count = 0
                all_value_sum = 0.0
                class_value_sum = 0.0
                easy_count = 0
                total_children = trials * child_count
                for _ in range(trials):
                    in_class = rng.random() < f_d
                    q = q_fertile if (kind == "source" and in_class) else (
                        q_infertile if kind == "source" else global_q
                    )
                    value = 0.0
                    for _child in range(child_count):
                        if rng.random() < q:
                            value += value_per_child
                            easy_count += 1
                    all_value_sum += value
                    if in_class:
                        class_count += 1
                        class_value_sum += value
                all_value = all_value_sum / trials
                fertile_value = class_value_sum / class_count if class_count else 0.0
                lift = fertile_value - all_value
                rows.append(
                    ClassCorrelationRow(
                        kind=kind,
                        active_fraction=active_fraction,
                        choices=choices,
                        child_count=child_count,
                        value_per_child=value_per_child,
                        q_fertile=q_fertile,
                        q_infertile=q_infertile,
                        measured_class_fraction=class_count / trials,
                        global_easy_rate=easy_count / total_children,
                        all_value=all_value,
                        fertile_value=fertile_value,
                        value_lift=lift,
                        lane_loss_bits=loss,
                        net_after_lane=lift - loss,
                    )
                )
    return rows


def print_source_lift_table() -> None:
    print("== source lift vs d-choice lane tax ==")
    print(
        "Future bits are drawn from a fixed public Bernoulli source. Source rows "
        "get entropy deficit; uniform controls pay cross-entropy plus lane tax."
    )
    print(
        f"{'r':>5} {'d':>3} {'future':>6} {'p':>5} {'lane':>8} "
        f"{'source lift':>12} {'source net':>11} {'uniform net':>12}"
    )
    for row in source_lift_rows():
        if row.active_fraction == 0.10 and row.choices in (8, 16):
            if row.future_bits in (1, 2, 4) and row.bias in (0.70, 0.75, 0.80, 0.85):
                print(
                    f"{row.active_fraction:5.2f} {row.choices:3d} "
                    f"{row.future_bits:6d} {row.bias:5.2f} "
                    f"{row.lane_loss_bits:8.3f} "
                    f"{row.source_value_lift:12.3f} "
                    f"{row.source_net_after_lane:11.3f} "
                    f"{row.uniform_net_after_lane:12.3f}"
                )
    print()


def print_bits_needed_table() -> None:
    print("== future bits needed to cross source row ==")
    print(
        "This prices the smallest public developmental bias needed to beat the "
        "stateless d-choice lane tax."
    )
    print(
        f"{'r':>5} {'d':>3} {'p':>5} {'lift/bit':>10} {'lane':>8} "
        f"{'bits needed':>11} {'source net':>11} {'uniform net':>12}"
    )
    for row in bits_needed_rows():
        if row.active_fraction in (0.10, 0.25) and row.choices in (8, 16):
            if row.bias in (0.70, 0.75, 0.80, 0.85):
                print(
                    f"{row.active_fraction:5.2f} {row.choices:3d} "
                    f"{row.bias:5.2f} {row.lift_per_future_bit:10.3f} "
                    f"{row.lane_loss_bits:8.3f} {row.future_bits_needed:11d} "
                    f"{row.achieved_source_net:11.3f} "
                    f"{row.uniform_net_at_needed_bits:12.3f}"
                )
    print()


def print_mixture_table() -> None:
    print("== public mixture model sanity check ==")
    print(
        "A less aggressive public model reduces both source gain and uniform "
        "penalty. The profile weight is fixed, not fit per file."
    )
    print(
        f"{'future':>6} {'p_src':>6} {'mix':>5} {'p_model':>7} "
        f"{'source lift':>12} {'source net':>11} {'uniform net':>12}"
    )
    for row in mixture_rows():
        if row.future_bits in (2, 4) and row.source_bias in (0.75, 0.80):
            print(
                f"{row.future_bits:6d} {row.source_bias:6.2f} "
                f"{row.mixture_weight:5.2f} {row.model_bias:7.3f} "
                f"{row.source_value_lift:12.3f} "
                f"{row.source_net_after_lane:11.3f} "
                f"{row.uniform_net_after_lane:12.3f}"
            )
    print()


def print_support_table() -> None:
    print("== support-deficit version ==")
    print(
        "If a public developmental source restricts future support by v bits, "
        "the source gains v bits and uniform support fraction is 2^-v."
    )
    print(
        f"{'r':>5} {'d':>3} {'support v':>10} {'lane':>8} "
        f"{'source net':>11} {'log2 U support':>15}"
    )
    for row in support_deficit_rows():
        if row.active_fraction == 0.10 and row.choices in (8, 16, 32):
            print(
                f"{row.active_fraction:5.2f} {row.choices:3d} "
                f"{row.support_deficit_bits:10.3f} {row.lane_loss_bits:8.3f} "
                f"{row.source_net_after_lane:11.3f} "
                f"{row.uniform_support_fraction_log2:15.3f}"
            )
    print()


def print_class_correlation_table() -> None:
    print("== measured public-class future value lift ==")
    print(
        "This is the exact H28/H38 test: value_lift = E[V|C]-E[V]. "
        "The uniform control keeps the same global easy-child rate but removes "
        "class correlation."
    )
    print(
        f"{'kind':>7} {'r':>5} {'d':>3} {'k':>3} {'w':>4} "
        f"{'q1':>5} {'q0':>5} {'f':>7} {'qbar':>7} {'all V':>7} "
        f"{'C V':>7} {'lift':>8} {'net':>8}"
    )
    for row in class_correlation_rows():
        if row.active_fraction == 0.10 and row.choices == 16:
            print(
                f"{row.kind:>7} {row.active_fraction:5.2f} {row.choices:3d} "
                f"{row.child_count:3d} {row.value_per_child:4.1f} "
                f"{row.q_fertile:5.2f} {row.q_infertile:5.2f} "
                f"{row.measured_class_fraction:7.4f} "
                f"{row.global_easy_rate:7.4f} {row.all_value:7.3f} "
                f"{row.fertile_value:7.3f} {row.value_lift:8.3f} "
                f"{row.net_after_lane:8.3f}"
            )
    print()


def main() -> None:
    print_source_lift_table()
    print_bits_needed_table()
    print_mixture_table()
    print_support_table()
    print_class_correlation_table()
    print("CONCLUSION:")
    print(
        "H39 crosses only in the intended source-shaped sense: a predeclared "
        "future law with entropy deficit can beat the reduced d-choice lane "
        "tax, while uniform controls are negative. For r=0.10,d=16 the lane tax "
        "is 0.296 bits/selected record; two future bits at bias p=0.75 already "
        "provide about 0.378 bits of source lift. This is a constructive "
        "stateless developmental target, not a roughly-all-data uniform escape."
    )


if __name__ == "__main__":
    main()
