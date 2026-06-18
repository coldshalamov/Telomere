#!/usr/bin/env python3
"""H142 - intrinsic witness-boundary optimizer.

H141 proves the fixed-delta supply converse. H142 prices the other common
"hide the width in the seed" variants against the selected-width ledger:

* optimal Kraft seed classes;
* simple residue/modulus classes;
* terminator/self-sync witness languages;
* neutral multiplicity discounts when several matching seeds exist.

No compression search is performed. The kernel answers a narrow question:
could an intrinsic seed-boundary language reduce H120's measured width bill
from about 5.34 bits/record to the ~1.54 bits/record needed to cross?
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class LedgerRow:
    name: str
    local_delta_per_atom_pass: float
    selected_per_atom_pass: float
    measured_width_entropy_per_record: float

    @property
    def break_even_width_bits(self) -> float:
        return -self.local_delta_per_atom_pass / self.selected_per_atom_pass

    @property
    def measured_total_delta(self) -> float:
        return self.local_delta_per_atom_pass + (
            self.selected_per_atom_pass * self.measured_width_entropy_per_record
        )


@dataclass(frozen=True)
class TerminatorRow:
    terminator_zeros: int
    total_len: int
    valid_count: int
    loss_bits: float


@dataclass(frozen=True)
class NeutralRow:
    expected_matches: float
    class_fraction: float
    rare_loss_bits: float
    effective_loss_bits: float


def h2_profile_entropy(probabilities: list[float]) -> float:
    return -sum(p * math.log2(p) for p in probabilities if p > 0.0)


def geometric_profile(class_count: int, target_entropy: float) -> list[float]:
    if target_entropy <= 0.0:
        return [1.0] + [0.0] * (class_count - 1)
    if target_entropy >= math.log2(class_count):
        return [1.0 / class_count] * class_count

    def entropy_for_ratio(ratio: float) -> float:
        weights = [ratio**i for i in range(class_count)]
        total = sum(weights)
        return h2_profile_entropy([weight / total for weight in weights])

    lo = 0.0
    hi = 1.0
    for _ in range(80):
        mid = (lo + hi) / 2.0
        if entropy_for_ratio(mid) < target_entropy:
            lo = mid
        else:
            hi = mid
    ratio = (lo + hi) / 2.0
    weights = [ratio**i for i in range(class_count)]
    total = sum(weights)
    return [weight / total for weight in weights]


def optimal_kraft_loss(probabilities: list[float]) -> float:
    """Continuous optimum for seed-class sizes N_w under Kraft.

    Minimize sum p(w) log2(2^w / N_w) subject to
    sum N_w 2^-w <= 1. The optimizer is N_w = p(w) 2^w, so the loss is H(W).
    """

    return h2_profile_entropy(probabilities)


def residue_loss(class_count: int) -> float:
    return math.log2(class_count)


def terminator_count(total_len: int, terminator_zeros: int) -> int:
    """Count strings of total_len ending in 0^t with no earlier 0^t."""

    t = terminator_zeros
    if total_len < t:
        return 0
    # State is the current suffix length of consecutive zeros, capped at t.
    dp = [0] * t
    dp[0] = 1
    for pos in range(total_len):
        next_dp = [0] * t
        for suffix_zeros, count in enumerate(dp):
            if count == 0:
                continue
            # Append 1: reset suffix.
            next_dp[0] += count
            # Append 0: either progress or terminate. Only allow termination
            # exactly at the final position.
            if suffix_zeros + 1 == t:
                if pos == total_len - 1:
                    # Do not add to state; this is a completed codeword.
                    pass
            else:
                next_dp[suffix_zeros + 1] += count
        if pos == total_len - 1:
            # Count transitions that terminated at the final bit.
            terminated = 0
            for suffix_zeros, count in enumerate(dp):
                if suffix_zeros + 1 == t:
                    terminated += count
            return terminated
        dp = next_dp
    return 0


def terminator_rows() -> list[TerminatorRow]:
    rows: list[TerminatorRow] = []
    for zeros in (2, 3, 4, 5):
        for total_len in (8, 16, 32, 64):
            count = terminator_count(total_len, zeros)
            loss = total_len - math.log2(count) if count > 0 else float("inf")
            rows.append(
                TerminatorRow(
                    terminator_zeros=zeros,
                    total_len=total_len,
                    valid_count=count,
                    loss_bits=loss,
                )
            )
    return rows


def neutral_loss(expected_matches: float, class_fraction: float) -> float:
    if expected_matches <= 0.0:
        return -math.log2(class_fraction)
    any_match = 1.0 - math.exp(-expected_matches)
    class_match = 1.0 - math.exp(-expected_matches * class_fraction)
    if class_match <= 0.0:
        return float("inf")
    return -math.log2(class_match / any_match)


def neutral_rows() -> list[NeutralRow]:
    rows: list[NeutralRow] = []
    for expected_matches in (0.01, 0.1, 0.5, 1.0, 4.0, 16.0):
        for class_fraction in (0.5, 0.25, 0.125):
            rows.append(
                NeutralRow(
                    expected_matches=expected_matches,
                    class_fraction=class_fraction,
                    rare_loss_bits=-math.log2(class_fraction),
                    effective_loss_bits=neutral_loss(expected_matches, class_fraction),
                )
            )
    return rows


def ledgers() -> list[LedgerRow]:
    # H120 seed=118001 scale-1024 row. The selected rate is derived from:
    # total_seed_class_delta = local_delta + selected_rate * entropy.
    h120_entropy = 5.341012
    h120_local = -0.055664
    h120_total = 0.137322
    h120_selected_rate = (h120_total - h120_local) / h120_entropy
    return [
        LedgerRow(
            name="H120_seed118_pooled",
            local_delta_per_atom_pass=h120_local,
            selected_per_atom_pass=h120_selected_rate,
            measured_width_entropy_per_record=h120_entropy,
        ),
        LedgerRow(
            name="hypothetical_half_entropy",
            local_delta_per_atom_pass=h120_local,
            selected_per_atom_pass=h120_selected_rate,
            measured_width_entropy_per_record=h120_entropy / 2.0,
        ),
    ]


def fmt(value: float) -> str:
    if value == float("inf"):
        return "inf"
    if abs(value) >= 1000.0:
        return f"{value:.3e}"
    return f"{value:.6f}"


def print_ledger_rows(items: list[LedgerRow]) -> None:
    print("== intrinsic boundary target ==")
    print(
        f"{'ledger':<25} {'local':>10} {'sel/atom':>10} {'width H':>9} "
        f"{'break-even H':>13} {'total':>10}"
    )
    for row in items:
        print(
            f"{row.name:<25} {row.local_delta_per_atom_pass:10.6f} "
            f"{row.selected_per_atom_pass:10.6f} "
            f"{row.measured_width_entropy_per_record:9.6f} "
            f"{row.break_even_width_bits:13.6f} "
            f"{row.measured_total_delta:10.6f}"
        )
    print()


def print_kraft_profiles(items: list[LedgerRow]) -> None:
    print("== optimal Kraft class loss ==")
    print("Profiles are geometric over 64 widths, tuned to the target entropy.")
    print(f"{'ledger':<25} {'target H':>9} {'optimizer':>10} {'residue64':>10} {'crosses?':>9}")
    for row in items:
        profile = geometric_profile(64, row.measured_width_entropy_per_record)
        kraft = optimal_kraft_loss(profile)
        crosses = kraft <= row.break_even_width_bits
        print(
            f"{row.name:<25} {row.measured_width_entropy_per_record:9.6f} "
            f"{kraft:10.6f} {residue_loss(64):10.6f} {str(crosses):>9}"
        )
    print()


def print_terminators(rows: list[TerminatorRow]) -> None:
    print("== terminator/self-sync losses ==")
    print(f"{'zeros':>5} {'len':>5} {'valid':>12} {'loss bits':>10}")
    for row in rows:
        if row.total_len in (16, 32, 64):
            print(
                f"{row.terminator_zeros:5d} {row.total_len:5d} "
                f"{row.valid_count:12d} {fmt(row.loss_bits):>10}"
            )
    print()


def print_neutral(rows: list[NeutralRow]) -> None:
    print("== neutral multiplicity discount for seed classes ==")
    print(f"{'lambda':>8} {'class f':>8} {'rare loss':>10} {'effective':>10}")
    for row in rows:
        if row.class_fraction in (0.5, 0.25) and row.expected_matches in (0.1, 1.0, 4.0, 16.0):
            print(
                f"{row.expected_matches:8.3f} {row.class_fraction:8.3f} "
                f"{row.rare_loss_bits:10.6f} {row.effective_loss_bits:10.6f}"
            )
    print()


def print_reading() -> None:
    print("== reading ==")
    print(
        "The optimal intrinsic width class loss is exactly H(W). For the H120 "
        "pooled ledger, H(W)=5.341012 bits/record but break-even is only about "
        "1.54 bits/record."
    )
    print(
        "Residue classes are worse unless their class probabilities match the "
        "selected width law. Terminators/self-sync codes are ordinary prefix "
        "languages and pay their delimiter as reduced seed inventory."
    )
    print(
        "Neutral multiplicity can discount class loss only when expected "
        "matches per target are already large. In the compressive rare-match "
        "regime it returns to -log2(class_fraction)."
    )


def main() -> None:
    ledger_items = ledgers()
    print_ledger_rows(ledger_items)
    print_kraft_profiles(ledger_items)
    print_terminators(terminator_rows())
    print_neutral(neutral_rows())
    print_reading()


if __name__ == "__main__":
    main()
