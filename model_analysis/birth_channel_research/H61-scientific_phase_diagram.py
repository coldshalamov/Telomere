#!/usr/bin/env python3
"""H61 - scientific phase diagram for maintained stateless recursion.

This script is a triage map. It does not search seeds and it does not assert
that any frontier has crossed. It asks: if a new idea moves one knob, how many
honest bits still have to move before the result becomes paid and parseable?

The three regimes are deliberately kept separate:

* uniform arbitrary data: public/stateless codes cannot have negative expected
  excess under the uniform law;
* public mechanism lanes: parseability can be free, but match supply or
  witness gap must be paid;
* source-shaped mechanisms: a non-uniform law can cross, but only by naming the
  entropy/value lift that uniform data lacks.
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


def exception_ledger_bits(passes: int, old_fraction: float) -> float:
    if old_fraction <= 0.0:
        return 0.0
    if old_fraction >= 1.0:
        return math.log2(max(1, passes - 1))
    return h2(old_fraction) + old_fraction * math.log2(max(1, passes - 1))


def log2_comb(n: int, k: int) -> float:
    if k < 0 or k > n:
        return float("-inf")
    return (
        math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)
    ) / math.log(2.0)


def binary_kl(c: float, p: float) -> float:
    if c <= 0.0:
        return -math.log2(1.0 - p) if p < 1.0 else float("inf")
    if c >= 1.0:
        return -math.log2(p) if p > 0.0 else float("inf")
    if p <= 0.0 or p >= 1.0:
        return float("inf")
    return c * math.log2(c / p) + (1.0 - c) * math.log2((1.0 - c) / (1.0 - p))


@dataclass(frozen=True)
class CloseFrontier:
    name: str
    atoms: int | None
    excess_bits: float
    note: str

    @property
    def excess_per_atom(self) -> float:
        if self.atoms is None:
            return self.excess_bits
        return self.excess_bits / self.atoms


@dataclass(frozen=True)
class WitnessFrontier:
    name: str
    missing_bits_per_record: float
    records_per_atom: float
    gain_per_atom: float

    @property
    def missing_bits_per_atom(self) -> float:
        return self.missing_bits_per_record * self.records_per_atom


@dataclass(frozen=True)
class LaneRow:
    active_fraction: float
    choices: int
    lane_loss_bits: float
    lift_standalone: float
    lift_with_h7_gap: float
    lift_with_best_uniform_gap: float


@dataclass(frozen=True)
class NearTotalRow:
    passes: int
    old_fraction: float
    ledger_bits_per_atom: float
    ledger_bits_per_rewrite: float
    net_if_two_bits_per_rewrite: float


@dataclass(frozen=True)
class RoughAllRow:
    saving_bits: int
    desired_coverage: float
    uniform_max_coverage: float
    required_lift: float
    kl_deficit_bits: float


@dataclass(frozen=True)
class LengthPathRow:
    passes: int
    total_saving: int
    path_bits: float
    net_after_path: float


CLOSE_FRONTIERS = [
    CloseFrontier(
        "H59 raw/Q mixture T1",
        atoms=384,
        excess_bits=0.053411,
        note="public mixture; train chose alpha=0.2, held-out positive",
    ),
    CloseFrontier(
        "H58 frozen bucket Q",
        atoms=384,
        excess_bits=0.229195,
        note="best public Q expected-bit row so far",
    ),
    CloseFrontier(
        "H12 perfect-credit upper bound",
        atoms=None,
        excess_bits=0.008196,
        note="bits/atom miss; assumes unavailable perfect witness credit",
    ),
    CloseFrontier(
        "H7 raw first-hit total cover",
        atoms=None,
        excess_bits=0.011929,
        note="bits/atom miss in exact total-cover witness model",
    ),
    CloseFrontier(
        "H9 fixed slack 0",
        atoms=None,
        excess_bits=0.012314,
        note="bits/atom miss for fixed local slack",
    ),
]


WITNESS_FRONTIERS = [
    WitnessFrontier(
        "H7 raw first-hit delta, B4 K128 D512",
        missing_bits_per_record=1.357,
        records_per_atom=0.008789,
        gain_per_atom=-0.011929,
    ),
    WitnessFrontier(
        "H9 fixed slack 0, B4 K128 D512",
        missing_bits_per_record=1.261,
        records_per_atom=0.009765,
        gain_per_atom=-0.012314,
    ),
    WitnessFrontier(
        "H12 perfect-credit upper bound, slack -8",
        missing_bits_per_record=0.746,
        records_per_atom=0.010987,
        gain_per_atom=-0.008196,
    ),
]


def lane_rows() -> list[LaneRow]:
    rows: list[LaneRow] = []
    h7_gap = WITNESS_FRONTIERS[0].missing_bits_per_record
    best_uniform_record_gap = min(row.missing_bits_per_record for row in WITNESS_FRONTIERS)
    for r in (0.03, 0.10, 0.25, 0.50):
        for d in (1, 4, 16, 64, 128):
            loss = lane_loss(r, d)
            rows.append(
                LaneRow(
                    active_fraction=r,
                    choices=d,
                    lane_loss_bits=loss,
                    lift_standalone=loss,
                    lift_with_h7_gap=h7_gap + loss,
                    lift_with_best_uniform_gap=best_uniform_record_gap + loss,
                )
            )
    return rows


def near_total_rows() -> list[NearTotalRow]:
    rows: list[NearTotalRow] = []
    for passes in (64, 256, 4096):
        for old_fraction in (0.10, 0.03, 0.01, 0.003, 0.001):
            ledger = exception_ledger_bits(passes, old_fraction)
            rewritten = max(1e-12, 1.0 - old_fraction)
            per_rewrite = ledger / rewritten
            rows.append(
                NearTotalRow(
                    passes=passes,
                    old_fraction=old_fraction,
                    ledger_bits_per_atom=ledger,
                    ledger_bits_per_rewrite=per_rewrite,
                    net_if_two_bits_per_rewrite=2.0 - per_rewrite,
                )
            )
    return rows


def rough_all_rows() -> list[RoughAllRow]:
    rows: list[RoughAllRow] = []
    for saving in (8, 32, 64, 128):
        p = 2.0 ** (-saving)
        for coverage in (0.50, 0.90, 0.99):
            rows.append(
                RoughAllRow(
                    saving_bits=saving,
                    desired_coverage=coverage,
                    uniform_max_coverage=p,
                    required_lift=coverage / p,
                    kl_deficit_bits=binary_kl(coverage, p),
                )
            )
    return rows


def length_path_rows() -> list[LengthPathRow]:
    rows: list[LengthPathRow] = []
    for passes, total_saving in ((8, 8), (64, 64), (64, 128), (64, 256), (256, 512)):
        path = 0.0 if passes <= 1 else log2_comb(total_saving - 1, passes - 1)
        rows.append(
            LengthPathRow(
                passes=passes,
                total_saving=total_saving,
                path_bits=path,
                net_after_path=total_saving - path,
            )
        )
    return rows


def print_close_frontiers() -> None:
    print("== closest honest frontiers ==")
    print(
        f"{'frontier':<38} {'reported gap':>13} "
        f"{'gap/atom':>11} {'reading':<48}"
    )
    for row in sorted(CLOSE_FRONTIERS, key=lambda value: value.excess_per_atom):
        reported = f"{row.excess_bits:.6f}"
        if row.atoms is not None:
            reported = f"{reported}/{row.atoms}"
        print(
            f"{row.name:<38} {reported:>13} "
            f"{row.excess_per_atom:11.6f} {row.note:<48}"
        )
    print()


def print_witness_frontiers() -> None:
    print("== paid witness gaps ==")
    print(
        f"{'frontier':<42} {'miss/rec':>10} {'rec/atom':>10} "
        f"{'miss/atom':>11} {'gain/atom':>11}"
    )
    for row in sorted(WITNESS_FRONTIERS, key=lambda value: value.missing_bits_per_atom):
        print(
            f"{row.name:<42} {row.missing_bits_per_record:10.3f} "
            f"{row.records_per_atom:10.6f} {row.missing_bits_per_atom:11.6f} "
            f"{row.gain_per_atom:11.6f}"
        )
    print()


def print_lane_phase() -> None:
    print("== public lane value-lift phase boundary ==")
    print("Rows show real value/source lift needed per selected record.")
    print(
        f"{'r':>6} {'d':>5} {'lane loss':>10} {'standalone':>11} "
        f"{'H7 gap':>10} {'best gap':>10}"
    )
    for row in lane_rows():
        if row.active_fraction in (0.10, 0.25, 0.50) and row.choices in (4, 16, 64, 128):
            print(
                f"{row.active_fraction:6.2f} {row.choices:5d} "
                f"{row.lane_loss_bits:10.3f} {row.lift_standalone:11.3f} "
                f"{row.lift_with_h7_gap:10.3f} {row.lift_with_best_uniform_gap:10.3f}"
            )
    print()


def print_near_total() -> None:
    print("== near-total state-ledger boundary ==")
    print("This is the branch where open/carry is genuinely cheap because almost")
    print("everything rewrites. It does not solve the witness problem by itself.")
    print(
        f"{'P':>6} {'old eps':>8} {'ledger/atom':>12} "
        f"{'ledger/rewrite':>15} {'net if 2b':>10}"
    )
    for row in near_total_rows():
        if row.passes in (64, 4096) and row.old_fraction in (0.03, 0.01, 0.003, 0.001):
            print(
                f"{row.passes:6d} {row.old_fraction:8.3f} "
                f"{row.ledger_bits_per_atom:12.6f} {row.ledger_bits_per_rewrite:15.6f} "
                f"{row.net_if_two_bits_per_rewrite:10.6f}"
            )
    print()


def print_rough_all_gate() -> None:
    print("== roughly-all uniform gate ==")
    print("A paid S-bit saving covers at most 2^-S of uniform inputs. Broader")
    print("coverage needs this much source lift, or a public invariant not yet found.")
    print(
        f"{'S':>5} {'coverage':>9} {'uniform max':>13} "
        f"{'lift needed':>14} {'KL deficit':>12}"
    )
    for row in rough_all_rows():
        if row.saving_bits in (8, 128) and row.desired_coverage in (0.90, 0.99):
            print(
                f"{row.saving_bits:5d} {row.desired_coverage:9.2f} "
                f"{row.uniform_max_coverage:13.3e} {row.required_lift:14.6g} "
                f"{row.kl_deficit_bits:12.6f}"
            )
    print()


def print_length_path() -> None:
    print("== recursive length-path boundary ==")
    print("EOF/non-prefix helps one-shot. Recursive variable savings owe the")
    print("positive-saving path unless a public invariant fixes it.")
    print(f"{'P':>6} {'S':>6} {'path bits':>12} {'net S-path':>12}")
    for row in length_path_rows():
        print(
            f"{row.passes:6d} {row.total_saving:6d} "
            f"{row.path_bits:12.6f} {row.net_after_path:12.6f}"
        )
    print()


def print_decision_rules() -> None:
    print("== decision rules for new ideas ==")
    print("1. Uniform arbitrary-data claim: must beat the public-code KL check,")
    print("   which current evidence says is impossible without a hidden selector.")
    print("2. Public stateless lane: decode can be free, but lane_loss or witness")
    print("   gap must be beaten by real value lift.")
    print("3. Source-shaped/DNA-like lane: allowed, but the source lift must be")
    print("   named and measured; otherwise it is just the hidden channel.")
    print("4. EOF/board/checksum/best-of tricks are not rejected by name. They are")
    print("   kept if their selector, arrangement, or path ledger stays below the")
    print("   measured frontier gap.")


def main() -> None:
    print_close_frontiers()
    print_witness_frontiers()
    print_lane_phase()
    print_near_total()
    print_rough_all_gate()
    print_length_path()
    print_decision_rules()


if __name__ == "__main__":
    main()
