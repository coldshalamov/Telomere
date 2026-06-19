#!/usr/bin/env python3
"""H186 - state-tail / bits-back conservation certificate.

This kernel consolidates the digest-tail, syndrome, and bits-back state lanes.

State bits can help stateless decode as coordinates, but under the uniform hash
law they have three honest prices:

* observe tail: free, but not controllable; transfer mass is unchanged.
* condition tail: costs r bits of hit supply to force an r-bit next state.
* select among tails: costs log2(number of choices) as a selector/referee.
* bits-back tape: conserved unless a separate fertility/source law gives
  gamma > 1; final/initial settlement must be paid.
"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model_analysis.proof_kernel import costs


def fmt(value: float) -> str:
    if math.isinf(value):
        return "inf" if value > 0.0 else "-inf"
    if math.isnan(value):
        return "nan"
    if value == 0.0:
        return "0"
    if abs(value) >= 10_000.0 or abs(value) < 0.0001:
        return f"{value:.3e}"
    return f"{value:.6f}"


def parse_int_list(values: list[str], default: list[int]) -> list[int]:
    if not values:
        return default
    out: list[int] = []
    for value in values:
        out.extend(int(part) for part in value.split(",") if part)
    return out


def parse_float_list(values: list[str], default: list[float]) -> list[float]:
    if not values:
        return default
    out: list[float] = []
    for value in values:
        out.extend(float(part) for part in value.split(",") if part)
    return out


def ceil_log2(value: int) -> int:
    if value <= 1:
        return 0
    return (value - 1).bit_length()


def kraft_sum(max_arity: int, code: str) -> float:
    if code == "v1":
        if max_arity > 5:
            raise ValueError("v1 arity supports K<=5")
        return sum(2.0 ** (-costs.arity_cost(arity)) for arity in range(1, max_arity + 1))
    if code == "fixed":
        width = ceil_log2(max_arity)
        return max_arity * (2.0 ** (-width))
    raise ValueError(code)


@dataclass(frozen=True)
class StateRow:
    code: str
    max_arity: int
    saving: float
    state_bits: int
    mode: str
    public_fraction: float
    selector_choices: int
    base_mass: float
    row_mass: float
    log2_rho: float
    paid_gain_per_record: float
    verdict: str


@dataclass(frozen=True)
class TapeRow:
    gap_bits: float
    state_bits: int
    passes: int
    gamma: float
    settlement_bits: int
    net_bits: float
    net_per_pass: float
    verdict: str


def state_row(
    *,
    code: str,
    max_arity: int,
    saving: float,
    state_bits: int,
    mode: str,
    public_fraction: float,
    selector_choices: int,
) -> StateRow:
    base_mass = kraft_sum(max_arity, code) * (2.0 ** (-saving))
    selector_bits = math.log2(selector_choices) if selector_choices > 1 else 0.0
    if mode == "observe":
        row_mass = base_mass
        paid_gain = saving
        verdict = "free coordinate; no mass lift"
    elif mode == "condition_value":
        row_mass = base_mass * (2.0 ** (-state_bits))
        paid_gain = saving
        verdict = "forced state costs tail supply"
    elif mode == "condition_subset":
        row_mass = base_mass * public_fraction
        paid_gain = saving
        verdict = "public subset thins supply"
    elif mode == "selected_tail":
        gross = min(1.0, base_mass * selector_choices)
        row_mass = gross
        paid_gain = saving - selector_bits
        verdict = "gross lift bought by selector"
    else:
        raise ValueError(mode)
    log2_rho = math.log2(row_mass) if row_mass > 0.0 else float("-inf")
    return StateRow(
        code=code,
        max_arity=max_arity,
        saving=saving,
        state_bits=state_bits,
        mode=mode,
        public_fraction=public_fraction,
        selector_choices=selector_choices,
        base_mass=base_mass,
        row_mass=row_mass,
        log2_rho=log2_rho,
        paid_gain_per_record=paid_gain,
        verdict=verdict,
    )


def tape_row(gap_bits: float, state_bits: int, passes: int, gamma: float, settlement_bits: int) -> TapeRow:
    net = -passes * gap_bits + passes * state_bits * (gamma - 1.0) - settlement_bits
    net_per_pass = net / passes if passes else 0.0
    if gamma <= 1.0 and net > 1e-12:
        verdict = "BUG: balanced tape positive"
    elif gamma <= 1.0:
        verdict = "conserved or negative"
    elif settlement_bits > 0 and net <= 0.0:
        verdict = "fertility lift spent on settlement/gap"
    else:
        verdict = "positive only with gamma>1 fertility"
    return TapeRow(
        gap_bits=gap_bits,
        state_bits=state_bits,
        passes=passes,
        gamma=gamma,
        settlement_bits=settlement_bits,
        net_bits=net,
        net_per_pass=net_per_pass,
        verdict=verdict,
    )


def print_state_table(args: argparse.Namespace) -> None:
    state_bits_values = parse_int_list(args.state_bits, [0, 4, 8])
    savings_values = parse_float_list(args.saving, [-1.0, 0.0, 1.0])
    selector_values = parse_int_list(args.selector_choices, [1, 2, 4, 16])
    fraction_values = parse_float_list(args.public_fraction, [0.5, 0.1])
    modes = ["observe", "condition_value", "condition_subset", "selected_tail"]

    print("== H186 state-tail conservation certificate ==")
    print(
        "row_mass is the paid transfer mass. log2rho>0 would be recurrent supply growth."
    )
    print(
        f"{'mode':<17} {'code':<6} {'K':>4} {'s':>7} {'r':>3} {'f':>8} "
        f"{'d':>4} {'base':>9} {'rowMass':>9} {'log2rho':>9} "
        f"{'gain':>8} {'verdict':<36}"
    )
    for saving in savings_values:
        for state_bits in state_bits_values:
            for mode in modes:
                mode_fractions = fraction_values if mode == "condition_subset" else [1.0]
                mode_selectors = selector_values if mode == "selected_tail" else [1]
                for public_fraction in mode_fractions:
                    for selector_choices in mode_selectors:
                        row = state_row(
                            code=args.code,
                            max_arity=args.max_arity,
                            saving=saving,
                            state_bits=state_bits,
                            mode=mode,
                            public_fraction=public_fraction,
                            selector_choices=selector_choices,
                        )
                        print(
                            f"{row.mode:<17} {row.code:<6} {row.max_arity:4d} "
                            f"{fmt(row.saving):>7} {row.state_bits:3d} "
                            f"{fmt(row.public_fraction):>8} {row.selector_choices:4d} "
                            f"{fmt(row.base_mass):>9} {fmt(row.row_mass):>9} "
                            f"{fmt(row.log2_rho):>9} {fmt(row.paid_gain_per_record):>8} "
                            f"{row.verdict:<36}"
                        )


def print_tape_table(args: argparse.Namespace) -> None:
    gaps = parse_float_list(args.gap_bits, [0.01, 0.1, 1.0])
    state_bits_values = parse_int_list(args.state_bits, [4, 8])
    passes_values = parse_int_list(args.passes, [16, 64, 256])
    gammas = parse_float_list(args.gamma, [1.0, 1.01, 1.1, 2.0])

    print()
    print("== bits-back / posterior tape settlement ==")
    print(
        f"{'gap':>8} {'r':>3} {'P':>5} {'gamma':>8} {'settle':>7} "
        f"{'net':>10} {'net/P':>10} {'verdict':<38}"
    )
    for gap in gaps:
        for state_bits in state_bits_values:
            for passes in passes_values:
                for gamma in gammas:
                    settlement_bits = state_bits if args.settle_one_state else state_bits * passes
                    row = tape_row(gap, state_bits, passes, gamma, settlement_bits)
                    print(
                        f"{fmt(row.gap_bits):>8} {row.state_bits:3d} {row.passes:5d} "
                        f"{fmt(row.gamma):>8} {row.settlement_bits:7d} "
                        f"{fmt(row.net_bits):>10} {fmt(row.net_per_pass):>10} "
                        f"{row.verdict:<38}"
                    )


def print_theorem() -> None:
    print()
    print("== theorem ==")
    print("Observed digest-tail state is free only as an observed coordinate.")
    print("Conditioning state costs the same bits in match supply.")
    print("Selecting among state tails costs selector/referee entropy.")
    print("Bits-back tape is conserved at gamma=1; positive rows require")
    print("a separate gamma>1 fertility/source law already priced by H182/H183.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--code", choices=["v1", "fixed"], default="v1")
    parser.add_argument("--max-arity", type=int, default=5)
    parser.add_argument("--saving", action="append", default=[])
    parser.add_argument("--state-bits", action="append", default=[])
    parser.add_argument("--selector-choices", action="append", default=[])
    parser.add_argument("--public-fraction", action="append", default=[])
    parser.add_argument("--gap-bits", action="append", default=[])
    parser.add_argument("--passes", action="append", default=[])
    parser.add_argument("--gamma", action="append", default=[])
    parser.add_argument("--settle-one-state", action="store_true")
    args = parser.parse_args()

    print_state_table(args)
    print_tape_table(args)
    print_theorem()


if __name__ == "__main__":
    main()
