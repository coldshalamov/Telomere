#!/usr/bin/env python3
"""H87 - native soft-law cycle ledger.

H86 found a strong measured value tail: soft visible laws can buy more future
value than their entropy deficit. H87 prices the repeatable-cycle question.

For a candidate visible law P over n-bit words:

    delta = D(P || U) = n - H(P)
    lift  = E_P[V] - E_U[V]

If a fixed native grammar can keep the next layer P-shaped, the optimistic
source-shaped cycle margin against a witness miss m is:

    source_cycle_margin = lift - m

But a roughly-all uniform startup must also turn n bits of uniform source
entropy into a P-shaped visible layer. A P-shaped symbol carries only H(P)
bits, so the minimum output symbol-rate expansion is n / H(P), and the
fixed-word expansion bill is:

    startup_shape_bill = n * (n / H(P) - 1)

This is a counting/capacity bill, not an implementation artifact. A positive
source-shaped cycle is therefore not yet a roughly-all-data solution; it needs
a native invariant that creates fertility without selecting a low-entropy
source subset.
"""

from __future__ import annotations

import importlib.util
import math
import sys
from dataclasses import dataclass
from pathlib import Path


H80_PATH = Path(__file__).resolve().with_name("H80-public_q_fertility_lane.py")
_h80_spec = importlib.util.spec_from_file_location("h80_public_q_fertility_lane", H80_PATH)
if _h80_spec is None or _h80_spec.loader is None:
    raise RuntimeError("could not load H80 public-Q fertility lane kernel")
_h80 = importlib.util.module_from_spec(_h80_spec)
sys.modules[_h80_spec.name] = _h80
_h80_spec.loader.exec_module(_h80)


H84_MISS = 0.216226
H58_MISS = 0.229195
H7_RECORD_MISS = 1.357


def entropy(probabilities: list[float]) -> float:
    return -sum(p * math.log2(p) for p in probabilities if p > 0.0)


def expectation(probabilities: list[float], values: list[float]) -> float:
    return sum(p * value for p, value in zip(probabilities, values))


def tilted_law(values: list[float], theta: float) -> list[float]:
    exponents = [theta * value for value in values]
    max_exponent = max(exponents)
    weights = [2.0 ** (exponent - max_exponent) for exponent in exponents]
    total = sum(weights)
    return [weight / total for weight in weights]


def theta_for_delta(values: list[float], target_delta: float) -> float:
    if target_delta <= 0.0:
        return 0.0
    hi = 1.0
    while law_stats(tilted_law(values, hi), values).delta < target_delta:
        hi *= 2.0
        if hi > 256.0:
            raise RuntimeError("could not bracket delta")
    lo = 0.0
    for _ in range(120):
        mid = (lo + hi) / 2.0
        if law_stats(tilted_law(values, mid), values).delta < target_delta:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


@dataclass(frozen=True)
class LawStats:
    delta: float
    entropy_bits: float
    lift: float


@dataclass(frozen=True)
class CycleRow:
    name: str
    delta: float
    entropy_bits: float
    lift: float
    shape_bill: float
    cycle_h84: float
    startup_h84: float
    cycle_h58: float
    startup_h58: float
    cycle_h7: float
    max_all_fraction_h58: float


def law_stats(probabilities: list[float], values: list[float]) -> LawStats:
    raw_bits = math.log2(len(probabilities))
    h_p = entropy(probabilities)
    uniform_value = sum(values) / len(values)
    return LawStats(
        delta=raw_bits - h_p,
        entropy_bits=h_p,
        lift=expectation(probabilities, values) - uniform_value,
    )


def shape_bill(raw_bits: float, entropy_bits: float) -> float:
    if entropy_bits <= 0.0:
        return math.inf
    return raw_bits * (raw_bits / entropy_bits - 1.0)


def max_uniform_fraction(saved_bits: float) -> float:
    if saved_bits <= 0.0:
        return 1.0
    return 2.0 ** (-saved_bits)


def row_for_law(name: str, probabilities: list[float], values: list[float]) -> CycleRow:
    raw_bits = math.log2(len(probabilities))
    stats = law_stats(probabilities, values)
    bill = shape_bill(raw_bits, stats.entropy_bits)
    cycle_h84 = stats.lift - H84_MISS
    startup_h84 = stats.lift - H84_MISS - bill
    cycle_h58 = stats.lift - H58_MISS
    startup_h58 = stats.lift - H58_MISS - bill
    cycle_h7 = stats.lift - H7_RECORD_MISS
    return CycleRow(
        name=name,
        delta=stats.delta,
        entropy_bits=stats.entropy_bits,
        lift=stats.lift,
        shape_bill=bill,
        cycle_h84=cycle_h84,
        startup_h84=startup_h84,
        cycle_h58=cycle_h58,
        startup_h58=startup_h58,
        cycle_h7=cycle_h7,
        max_all_fraction_h58=max_uniform_fraction(max(startup_h58, cycle_h58)),
    )


def law_for_delta(values: list[float], delta: float) -> list[float]:
    theta = theta_for_delta(values, delta)
    return tilted_law(values, theta)


def row_for_theta(name: str, values: list[float], theta: float) -> CycleRow:
    return row_for_law(name, tilted_law(values, theta), values)


def print_rows(rows: list[CycleRow]) -> None:
    print("== native soft-law cycle ledger ==")
    print(
        "cycle_* assumes a fixed native grammar keeps the layer P-shaped. "
        "startup_* additionally charges the uniform-to-P capacity bill."
    )
    print(
        f"{'law':<14} {'delta':>9} {'H(P)':>9} {'lift':>9} {'shape':>9} "
        f"{'cyc H84':>9} {'start H84':>10} {'cyc H58':>9} "
        f"{'start H58':>10} {'cyc H7':>9} {'max all':>9}"
    )
    for row in rows:
        print(
            f"{row.name:<14} {row.delta:9.6f} {row.entropy_bits:9.6f} "
            f"{row.lift:9.6f} {row.shape_bill:9.6f} {row.cycle_h84:9.6f} "
            f"{row.startup_h84:10.6f} {row.cycle_h58:9.6f} "
            f"{row.startup_h58:10.6f} {row.cycle_h7:9.6f} "
            f"{row.max_all_fraction_h58:9.6f}"
        )
    print()


def print_thresholds(values: list[float]) -> None:
    print("== soft-law thresholds ==")
    print(f"{'target':<18} {'theta':>8} {'delta':>9} {'shape':>9} {'lift':>9} {'startup':>10}")
    for target_name, miss in (("H84 one-shot", H84_MISS), ("H58 nearest", H58_MISS), ("H7 record", H7_RECORD_MISS)):
        lo = 0.0
        hi = 0.001
        while True:
            row = row_for_theta(target_name, values, hi)
            if row.lift - miss >= 0.0:
                break
            hi *= 2.0
            if hi > 256.0:
                raise RuntimeError("could not bracket threshold")
        for _ in range(100):
            mid = (lo + hi) / 2.0
            if row_for_theta(target_name, values, mid).lift - miss < 0.0:
                lo = mid
            else:
                hi = mid
        theta = (lo + hi) / 2.0
        row = row_for_theta(target_name, values, theta)
        startup = row.lift - miss - row.shape_bill
        print(
            f"{target_name:<18} {theta:8.5f} {row.delta:9.6f} {row.shape_bill:9.6f} "
            f"{row.lift:9.6f} {startup:10.6f}"
        )
    print()


def print_reading() -> None:
    print("== reading ==")
    print(
        "H86's soft laws are strong enough for source-shaped cycles if a native "
        "grammar can keep the output P-shaped and if score lift translates into "
        "real witness savings. That does not make a roughly-all uniform "
        "compressor: turning arbitrary uniform data into a lower-entropy visible "
        "law pays a capacity bill, and any positive saved-bit claim can cover "
        "only a 2^-s fraction of all uniform strings unless another visible "
        "state is charged. The next target is therefore very narrow: a fixed "
        "parseable grammar whose output remains high-entropy and fertile without "
        "selecting a low-entropy subset of inputs."
    )


def main() -> None:
    domain = _h80.exact_domain()
    values = domain.scores
    candidate_deltas = [0.001, 0.005205, 0.005870, 0.03, 0.10, 0.216226, 0.50, 1.0, 1.158938, 1.365022]
    rows = [
        row_for_law(f"d={delta:.6f}", law_for_delta(values, delta), values)
        for delta in candidate_deltas
    ]
    rows.append(row_for_law("Q/native", domain.q, values))
    print_rows(rows)
    print_thresholds(values)
    print_reading()


if __name__ == "__main__":
    main()
