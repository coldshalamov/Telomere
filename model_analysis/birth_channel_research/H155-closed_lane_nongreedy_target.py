#!/usr/bin/env python3
"""H155 - closed-lane non-greedy target ledger.

This combines the closest lawful pieces:

* H105: public two-epoch lanes + class-local ranks remove readiness tax, but
  the best honest collective witness still has a base Kraft gap.
* H152: non-greedy visible path choice has real lift over greedy.
* H151/H120: closure and payload-width parseability are the remaining bills.

The question is not "did these tiny domains form one production codec?" They
do not. The question is sharper:

    Is the measured visible non-greedy lift numerically large enough, as a
    cross-domain target transfer, to cover the current public-lane witness
    miss? How much remains once closure/width stress bills are considered?

No open/carry/birth-pass entropy is charged here; this is the total-cover/public
lane branch. Cloud/rank mass is also not credited.
"""

from __future__ import annotations

import importlib.util
import math
import sys
from dataclasses import dataclass
from pathlib import Path


HERE = Path(__file__).resolve().parent


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


H105 = load_module("h105_for_h155", HERE / "H105-forced_rewrite_collective_target.py")
H151 = load_module("h151_for_h155", HERE / "H151-closure_kraft_ledger.py")
H152 = load_module("h152_for_h155", HERE / "H152-superposition_gap_ledger.py")


# H120/H142 repeatedly measured this equivalence class around 5.34 bits/record
# for selected width streams. H155 keeps it as an explicit stress column, not
# as a lawful exact cost for every row. It applies only to future mechanisms
# that still have a comparable non-public selected-width distribution.
WIDTH_EQUIV_BITS_PER_RECORD = 5.341012


@dataclass(frozen=True)
class TransferRow:
    h105_mode: str
    h105_k: int
    h105_d: int
    h152_atoms: int
    h152_k: int
    h152_d: int
    slack: int
    base_gap_bits_per_word: float
    public_missing_bits_per_record: float
    implied_records_per_word: float
    visible_lift_bits_per_word: float
    selected_gain_bits_per_word: float
    cloud_gap_bits: float
    best_mid_bits: float
    best_final_bits: float
    closure_tax_mid_bits: float
    closure_tax_final_bits: float
    base_after_visible_lift: float
    mid_closure_after_lift: float
    width_after_lift: float
    all_bills_after_lift: float


def closure_tax(block_bits: int, max_arity: int, depth_bits: int, stream_bits: int) -> float:
    grammar = H151.build_grammar(
        block_bits=block_bits,
        max_arity=max_arity,
        depth_bits=depth_bits,
        max_record_len=max(64, stream_bits + 16),
    )
    row = H151.closure_rows(grammar, [stream_bits], max_stream_bits=max(64, stream_bits))[0]
    return row.closure_tax


def h152_row(atoms: int, max_arity: int, depth_bits: int, slack: int) -> H152.SlackRow:
    kernel = H152.SuperpositionGapKernel(
        atoms=atoms,
        max_arity=max_arity,
        depth_bits=depth_bits,
        seed=146146,
    )
    return kernel.row_for_slack(slack)


def rows() -> list[TransferRow]:
    h105_rows = [
        row for row in H105.rows()
        if row.mode in ("custom_record", "custom_rank", "paid_lotus")
    ]
    h152_rows = [
        h152_row(4, 4, 7, 12),
        h152_row(5, 5, 8, 10),
        h152_row(6, 5, 7, 18),
    ]
    result: list[TransferRow] = []
    for target in h105_rows:
        base_gap = max(0.0, -target.collective_log2_z)
        for transfer in h152_rows:
            mid_bits = int(round(transfer.best_mid_bits))
            final_bits = int(round(transfer.best_final_bits))
            # Stress test: if a future public-lane mechanism must make an
            # arbitrary intermediate land in the valid stream language, H151
            # prices that as match-supply thinning. This is not an extra debit
            # on H152's exact selected y -> c -> x row, whose direct failure is
            # already represented by selected_gain_bits_per_word.
            mid_tax = closure_tax(1, transfer.max_arity, transfer.depth_bits, mid_bits)
            final_tax = closure_tax(1, transfer.max_arity, transfer.depth_bits, final_bits)
            width_bill = WIDTH_EQUIV_BITS_PER_RECORD * target.implied_records_per_word
            base_after = base_gap - transfer.visible_lift_over_greedy
            mid_after = base_gap + mid_tax - transfer.visible_lift_over_greedy
            width_after = base_gap + width_bill - transfer.visible_lift_over_greedy
            all_after = base_gap + mid_tax + width_bill - transfer.visible_lift_over_greedy
            result.append(
                TransferRow(
                    h105_mode=target.mode,
                    h105_k=target.max_arity,
                    h105_d=target.depth_bits,
                    h152_atoms=transfer.atoms,
                    h152_k=transfer.max_arity,
                    h152_d=transfer.depth_bits,
                    slack=transfer.slack,
                    base_gap_bits_per_word=base_gap,
                    public_missing_bits_per_record=target.public_bonus_bits_per_record,
                    implied_records_per_word=target.implied_records_per_word,
                    visible_lift_bits_per_word=transfer.visible_lift_over_greedy,
                    selected_gain_bits_per_word=transfer.selected_gain,
                    cloud_gap_bits=transfer.cloud_gap_bits,
                    best_mid_bits=transfer.best_mid_bits,
                    best_final_bits=transfer.best_final_bits,
                    closure_tax_mid_bits=mid_tax,
                    closure_tax_final_bits=final_tax,
                    base_after_visible_lift=base_after,
                    mid_closure_after_lift=mid_after,
                    width_after_lift=width_after,
                    all_bills_after_lift=all_after,
                )
            )
    return result


def fmt(value: float) -> str:
    if value == float("inf"):
        return "inf"
    if value == float("-inf"):
        return "-inf"
    if abs(value) >= 1000.0 or (0.0 < abs(value) < 0.0001):
        return f"{value:.3e}"
    return f"{value:.6f}"


def print_rows(items: list[TransferRow]) -> None:
    print("== closed-lane non-greedy target ledger ==")
    print("No open/carry/birth entropy charged; public lanes are assumed.")
    print(
        f"{'mode':<13} {'K/D':>7} {'N':>2} {'tK/D/s':>9} "
        f"{'baseGap':>8} {'miss/rec':>8} {'rec/w':>7} {'lift':>8} "
        f"{'selGain':>9} {'cloud':>8} {'mid':>6} {'final':>7} "
        f"{'taxMid':>8} {'taxFin':>8} {'base-lift':>10} "
        f"{'+closure':>9} {'+width':>9} {'all':>9}"
    )
    for row in items:
        print(
            f"{row.h105_mode:<13} {row.h105_k:2d}/{row.h105_d:<4d} "
            f"{row.h152_atoms:2d} "
            f"{row.h152_k:2d}/{row.h152_d}/{row.slack:<2d} "
            f"{fmt(row.base_gap_bits_per_word):>8} "
            f"{fmt(row.public_missing_bits_per_record):>8} "
            f"{fmt(row.implied_records_per_word):>7} "
            f"{fmt(row.visible_lift_bits_per_word):>8} "
            f"{fmt(row.selected_gain_bits_per_word):>9} "
            f"{fmt(row.cloud_gap_bits):>8} "
            f"{fmt(row.best_mid_bits):>6} {fmt(row.best_final_bits):>7} "
            f"{fmt(row.closure_tax_mid_bits):>8} "
            f"{fmt(row.closure_tax_final_bits):>8} "
            f"{fmt(row.base_after_visible_lift):>10} "
            f"{fmt(row.mid_closure_after_lift):>9} "
            f"{fmt(row.width_after_lift):>9} "
            f"{fmt(row.all_bills_after_lift):>9}"
        )
    print()


def print_reading(items: list[TransferRow]) -> None:
    print("== reading ==")
    best_base = min(items, key=lambda row: row.base_after_visible_lift)
    best_all = min(items, key=lambda row: row.all_bills_after_lift)
    print(
        f"Best base-only target transfer: {best_base.h105_mode} with H152 "
        f"N={best_base.h152_atoms},K={best_base.h152_k},D={best_base.h152_d},"
        f"s={best_base.slack}. Cross-domain visible lift exceeds the H105 "
        f"base gap by {fmt(-best_base.base_after_visible_lift)} bits/word."
    )
    print(
        "That is the good news: non-greedy selected-stream lift is numerically "
        "large enough to matter on the public-lane witness miss."
    )
    print(
        f"The bad news is the same row still has selected_gain="
        f"{fmt(best_base.selected_gain_bits_per_word)} bits/word and closure "
        f"stress at the intermediate length of {fmt(best_base.closure_tax_mid_bits)} bits."
    )
    print(
        f"Once the stress columns include closure and the H120 width-equivalence "
        f"bill, the best stacked row still misses by {fmt(best_all.all_bills_after_lift)} "
        "bits/word. The cloud column is deliberately not credited; H153 priced it "
        "as public-Q KL loss or a hidden rank stream."
    )
    print(
        "Next target: an exact selected-stream transfer that preserves the "
        "base-only lift while internalizing or making unnecessary the separate "
        "width/closure bills by construction, without reducing seed address "
        "space as in H154."
    )


def main() -> None:
    result = rows()
    print_rows(result)
    print_reading(result)


if __name__ == "__main__":
    main()
