#!/usr/bin/env python3
"""H70 - systematic response protocol for stateless recursive Telomere.

This kernel turns the current research state into falsifiable response axes.
It does not search for lucky matches. It asks what a proposed mechanism would
have to change, how many paid bits that change is worth, and which control
would catch the usual hidden-channel leak.

The goal is to make future work behave like a scientific phase study:

* pick one active knob;
* predict the sign and magnitude before testing;
* run only a small exact/counting kernel;
* keep the total-cover branch separate from salted open/carry branches;
* require a paired uniform/adversarial control.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


def h2(p: float) -> float:
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -(p * math.log2(p) + (1.0 - p) * math.log2(1.0 - p))


def lane_hit_fraction(active_fraction: float, choices: int) -> float:
    return 1.0 - (1.0 - active_fraction) ** choices


def lane_loss(active_fraction: float, choices: int) -> float:
    return -math.log2(lane_hit_fraction(active_fraction, choices))


def choices_needed(active_fraction: float, target_loss_bits: float) -> int:
    target_hit = 2.0 ** (-target_loss_bits)
    if target_hit >= 1.0:
        return math.inf  # type: ignore[return-value]
    return max(
        1,
        math.ceil(math.log(1.0 - target_hit) / math.log(1.0 - active_fraction)),
    )


def lambda_k(max_arity: int) -> float:
    lo, hi = 1.0, 2.0
    for _ in range(100):
        mid = (lo + hi) / 2.0
        value = sum(mid ** (-arity) for arity in range(1, max_arity + 1))
        if value > 1.0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def cover_entropy_rate(max_arity: int) -> float:
    return math.log2(lambda_k(max_arity))


def source_threshold(target_bits: float, f_mass: float, q_lift: float) -> float:
    """Minimum source probability of public class F to beat target_bits.

    Public Q gives each state in F a per-state lift q_lift over uniform and
    gives the complement the normalizing lift b. The source must visit F often
    enough that E_source[log2(Q/U)] exceeds target_bits.
    """

    if not 0.0 < f_mass < 1.0:
        raise ValueError("f_mass must be in (0,1)")
    if not 0.0 < q_lift < 1.0 / f_mass:
        raise ValueError("q_lift must leave positive complement mass")
    complement_lift = (1.0 - f_mass * q_lift) / (1.0 - f_mass)
    score_f = math.log2(q_lift)
    score_o = math.log2(complement_lift)
    return (target_bits - score_o) / (score_f - score_o)


def min_p_ff(c_star: float, p_of: float) -> float:
    """Minimum F->F retention needed to keep c_{t+1} >= c_star."""

    return max(0.0, min(1.0, (c_star - (1.0 - c_star) * p_of) / c_star))


def exception_ledger_bits(passes: int, exception_fraction: float) -> float:
    if exception_fraction <= 0.0:
        return 0.0
    if exception_fraction >= 1.0:
        return math.log2(max(1, passes - 1))
    return h2(exception_fraction) + exception_fraction * math.log2(max(1, passes - 1))


def max_passes_for_tail(bad_fraction: float, max_blowup_probability: float) -> int:
    """Largest P with 1-(1-eps)^P <= max_blowup_probability."""

    if bad_fraction <= 0.0:
        return math.inf  # type: ignore[return-value]
    if bad_fraction >= 1.0:
        return 0
    return max(
        0,
        math.floor(math.log(1.0 - max_blowup_probability) / math.log(1.0 - bad_fraction)),
    )


@dataclass(frozen=True)
class WitnessAxis:
    name: str
    missing_bits_per_record: float
    records_per_atom: float
    average_arity: float

    @property
    def missing_bits_per_atom(self) -> float:
        return self.missing_bits_per_record * self.records_per_atom

    @property
    def choice_multiplier_needed(self) -> float:
        return 2.0 ** self.missing_bits_per_record


@dataclass(frozen=True)
class SourceAxis:
    name: str
    target_bits_per_atom: float
    f_mass: float
    q_lift: float
    c_star: float
    retention_with_background: float
    retention_closed: float


@dataclass(frozen=True)
class ExperimentCard:
    name: str
    changed_knob: str
    prediction: str
    paid_currency: str
    control: str
    stop_rule: str


WITNESS_AXES = [
    WitnessAxis("H12 perfect-credit upper", 0.746, 0.010987, 91.02),
    WitnessAxis("H7 raw first-hit", 1.357, 0.008789, 113.78),
    WitnessAxis("H9 fixed slack 0", 1.261, 0.009765, 102.40),
]

ATOM_TARGETS = [
    ("H59 raw/Q mixture T1", 0.053411 / 384.0),
    ("H58 frozen bucket Q", 0.229195 / 384.0),
    ("H7 atom miss", 0.011929),
]


def source_axes() -> list[SourceAxis]:
    rows: list[SourceAxis] = []
    for name, target in ATOM_TARGETS:
        for f_mass, q_lift in ((0.10, 2.0), (0.10, 4.0), (0.01, 8.0)):
            c_star = source_threshold(target, f_mass, q_lift)
            rows.append(
                SourceAxis(
                    name=name,
                    target_bits_per_atom=target,
                    f_mass=f_mass,
                    q_lift=q_lift,
                    c_star=c_star,
                    retention_with_background=min_p_ff(c_star, f_mass),
                    retention_closed=min_p_ff(c_star, 0.0),
                )
            )
    return rows


def experiment_cards() -> list[ExperimentCard]:
    return [
        ExperimentCard(
            name="Corrected high-K total-cover rerun",
            changed_knob="rank-width sampler and K/D frontier",
            prediction=(
                "moves constants by about one payload bit per high-span record; "
                "does not evade public-code conservation"
            ),
            paid_currency="exact record cost and whole-cover excess",
            control="same rows with uniform held-out seeds and no profile retraining",
            stop_rule="stop if mean excess remains positive after corrected widthing",
        ),
        ExperimentCard(
            name="Whole-cover normalized Q",
            changed_knob="encode the selected cover as one public object",
            prediction=(
                "can harvest duplicate covers and reduce selected-cover cost; "
                "uniform average remains raw+KL(U||Q)"
            ),
            paid_currency="cross-entropy under the frozen public Q",
            control="uniform exact tiny domain or held-out uniform simulation",
            stop_rule="stop if mixture chooses raw-only or held-out excess stays positive",
        ),
        ExperimentCard(
            name="Public fertility/source class",
            changed_knob="non-uniform public high-fertility class F",
            prediction=(
                "small atom-level misses cross if c_t exceeds c* and the rewrite "
                "map maintains F"
            ),
            paid_currency="source KL/value lift, not hidden file-specific metadata",
            control="uniform input must remain negative under the same frozen F",
            stop_rule="stop if p_FF and p_OF cannot keep c_{t+1} above c*",
        ),
        ExperimentCard(
            name="Public lane plus d-choice routing",
            changed_knob="stateless placement geometry with multiple public choices",
            prediction=(
                "lowers lane loss as 1-(1-r)^d; still needs real value lift "
                "for compression"
            ),
            paid_currency="match-supply loss or value lift",
            control="random lane assignment with same r,d should not compress",
            stop_rule="stop if lane_loss plus witness gap exceeds measured lift",
        ),
        ExperimentCard(
            name="Near-total exception ledger",
            changed_knob="all-record rewrite except small exception set",
            prediction=(
                "open/carry entropy becomes small when eps is tiny; witness "
                "economics remain the gate"
            ),
            paid_currency="H(eps)+eps*log2(P-1) bits per atom",
            control="adversarial exception placement charged as subset entropy",
            stop_rule="stop if exceptions are content-selected and not near-total",
        ),
        ExperimentCard(
            name="Negative drift tail audit",
            changed_knob="typical shrink with rare expansions",
            prediction=(
                "E[log rho] can be negative while E[rho]=1; arbitrary-P claims "
                "need bad fraction O(1/P) or zero"
            ),
            paid_currency="tail/blowup probability",
            control="report Pr(at least one blowup) for target pass counts",
            stop_rule="stop if bad tail reaches almost all inputs over desired P",
        ),
        ExperimentCard(
            name="Final-board/public invariant",
            changed_knob="visible end-state arrangement or board orbit",
            prediction=(
                "valid only when visible-state entropy is already the intended "
                "message, not an unpaid selector"
            ),
            paid_currency="log2(valid end states) or visible-state capacity",
            control="pigeonhole count of valid final arrangements",
            stop_rule="stop if path/profile/position identity exceeds frontier gap",
        ),
    ]


def print_witness_response() -> None:
    print("== witness response axis ==")
    print("One bit removed from each selected record buys records/atom bits/atom.")
    print(
        f"{'target':<28} {'miss/rec':>9} {'rec/atom':>10} "
        f"{'miss/atom':>10} {'x choices':>10} {'cover h_K':>10}"
    )
    for row in WITNESS_AXES:
        k = max(2, int(round(row.average_arity)))
        print(
            f"{row.name:<28} {row.missing_bits_per_record:9.3f} "
            f"{row.records_per_atom:10.6f} {row.missing_bits_per_atom:10.6f} "
            f"{row.choice_multiplier_needed:10.3f} {cover_entropy_rate(k):10.6f}"
        )
    print()


def print_lane_response() -> None:
    print("== public lane response axis ==")
    print("d-choice can make a public lane cheap only by preserving hit supply.")
    print(f"{'r':>6} {'loss target':>12} {'d needed':>9} {'actual loss':>12}")
    for r in (0.03, 0.10, 0.25, 0.50):
        for target in (1.0, 0.5, 0.25, 0.10, 0.01):
            d = choices_needed(r, target)
            print(f"{r:6.2f} {target:12.3f} {d:9d} {lane_loss(r, d):12.6f}")
    print()


def print_source_response() -> None:
    print("== source/fertility response axis ==")
    print("Uniform controls stay negative; these rows are allowed source targets.")
    print(
        f"{'target':<24} {'f':>6} {'a':>6} {'c*':>9} "
        f"{'enrich':>9} {'pFF bg=f':>10} {'pFF bg=0':>10}"
    )
    for row in source_axes():
        if (row.f_mass, row.q_lift) in ((0.10, 2.0), (0.01, 8.0)):
            print(
                f"{row.name:<24} {row.f_mass:6.2f} {row.q_lift:6.1f} "
                f"{row.c_star:9.4f} {row.c_star / row.f_mass:9.3f} "
                f"{row.retention_with_background:10.4f} {row.retention_closed:10.4f}"
            )
    print()


def print_exception_response() -> None:
    print("== near-total exception response axis ==")
    print("This prices salted open/carry branches; total-cover does not pay it.")
    print(
        f"{'P':>6} {'eps':>8} {'ledger/atom':>12} "
        f"{'ledger/rewrite':>15} {'net if 2b':>10}"
    )
    for passes in (64, 256, 4096):
        for eps in (0.03, 0.01, 0.003, 0.001):
            ledger = exception_ledger_bits(passes, eps)
            per_rewrite = ledger / (1.0 - eps)
            print(
                f"{passes:6d} {eps:8.3f} {ledger:12.6f} "
                f"{per_rewrite:15.6f} {2.0 - per_rewrite:10.6f}"
            )
    print()


def print_tail_response() -> None:
    print("== negative-drift tail response axis ==")
    print("A fixed bad fraction eventually hits almost every long recursion path.")
    print(f"{'eps bad':>8} {'Pr blowup cap':>14} {'max P':>10}")
    for eps in (0.03, 0.01, 0.003, 0.001, 0.0001):
        for cap in (0.10, 0.50, 0.90):
            print(f"{eps:8.4f} {cap:14.2f} {max_passes_for_tail(eps, cap):10d}")
    print()


def print_cards() -> None:
    print("== experiment cards ==")
    for index, card in enumerate(experiment_cards(), start=1):
        print(f"{index}. {card.name}")
        print(f"   knob: {card.changed_knob}")
        print(f"   prediction: {card.prediction}")
        print(f"   paid currency: {card.paid_currency}")
        print(f"   control: {card.control}")
        print(f"   stop rule: {card.stop_rule}")
    print()


def print_reading() -> None:
    print("== reading ==")
    print("The active scientific target is not just 'try more K'.")
    print("The paid knobs with measurable leverage are:")
    print("  witness bits/record, public-lane hit supply, near-total exceptions,")
    print("  source/fertility value lift, public-Q cross-entropy, and tail risk.")
    print("A new idea is promising only if it names which knob it moves and")
    print("predicts enough movement to beat the current closest frontier.")


def main() -> None:
    print_witness_response()
    print_lane_response()
    print_source_response()
    print_exception_response()
    print_tail_response()
    print_cards()
    print_reading()


if __name__ == "__main__":
    main()
