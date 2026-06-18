#!/usr/bin/env python3
"""H133 - common-cause batch witness audit.

Question: can one base witness derive several child witnesses and thereby
avoid the per-record boundary/width bill?

Under the uniform hash law, a batch symbol that expands to A atoms is still a
public code symbol with weight 2^-L. If the batch is just m ordinary child
records tied to one common cause, its honest arity mass is the m-fold
convolution of the child record masses. If it claims a shared-overhead discount
without removing mass elsewhere, the total symbol mass becomes overfull.

This kernel extends H108's exact recurrence:

    Z_0 = 1
    Z_n = sum_A W_A Z_{n-A}

where W_A is either:
* base custom_record arity mass;
* an m-child batch convolution of that base mass;
* a public mixture of base and batch masses with total mass <= 1;
* or an intentionally discounted batch, which is flagged invalid when its
  symbol mass exceeds 1.
"""

from __future__ import annotations

import importlib.util
import math
import sys
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path


HERE = Path(__file__).resolve().parent
H108_PATH = HERE / "H108-prefix_record_grammar_converse.py"
H108_SPEC = importlib.util.spec_from_file_location("h108_for_h133", H108_PATH)
if H108_SPEC is None or H108_SPEC.loader is None:
    raise RuntimeError(f"could not load {H108_PATH}")
h108 = importlib.util.module_from_spec(H108_SPEC)
sys.modules[H108_SPEC.name] = h108
H108_SPEC.loader.exec_module(h108)


@dataclass(frozen=True)
class BatchRow:
    mode: str
    child_records: int
    discount_bits: int
    mix_num: int
    mix_den: int
    log2_symbol_mass: float
    log2_z: float
    valid_kraft: bool
    note: str


def log2_fraction(value: Fraction) -> float:
    if value <= 0:
        return float("-inf")
    return math.log2(value.numerator) - math.log2(value.denominator)


def mass_dict(masses: list[Fraction]) -> dict[int, Fraction]:
    return {arity: mass for arity, mass in enumerate(masses, start=1) if mass}


def convolve(left: dict[int, Fraction], right: dict[int, Fraction]) -> dict[int, Fraction]:
    out: dict[int, Fraction] = {}
    for a, wa in left.items():
        for b, wb in right.items():
            out[a + b] = out.get(a + b, Fraction(0, 1)) + wa * wb
    return out


def batch_mass(base: dict[int, Fraction], child_records: int) -> dict[int, Fraction]:
    out = {0: Fraction(1, 1)}
    for _ in range(child_records):
        out = convolve(out, base)
    out.pop(0, None)
    return out


def mix_mass(
    base: dict[int, Fraction],
    batch: dict[int, Fraction],
    mix_num: int,
    mix_den: int,
) -> dict[int, Fraction]:
    lam = Fraction(mix_num, mix_den)
    out: dict[int, Fraction] = {}
    for arity, mass in base.items():
        out[arity] = out.get(arity, Fraction(0, 1)) + lam * mass
    for arity, mass in batch.items():
        out[arity] = out.get(arity, Fraction(0, 1)) + (1 - lam) * mass
    return out


def scale_mass(masses: dict[int, Fraction], discount_bits: int) -> dict[int, Fraction]:
    scale = Fraction(1 << discount_bits, 1)
    return {arity: mass * scale for arity, mass in masses.items()}


def symbol_mass(masses: dict[int, Fraction]) -> Fraction:
    return sum(masses.values(), Fraction(0, 1))


def cover_mass(masses: dict[int, Fraction], atoms: int) -> Fraction:
    dp = [Fraction(0, 1) for _ in range(atoms + 1)]
    dp[0] = Fraction(1, 1)
    for n in range(1, atoms + 1):
        total = Fraction(0, 1)
        for arity, mass in masses.items():
            if arity <= n:
                total += mass * dp[n - arity]
        dp[n] = total
    return dp[atoms]


def row(
    mode: str,
    masses: dict[int, Fraction],
    atoms: int,
    child_records: int,
    discount_bits: int = 0,
    mix_num: int = 0,
    mix_den: int = 1,
    note: str = "",
) -> BatchRow:
    sym = symbol_mass(masses)
    z = cover_mass(masses, atoms)
    valid = sym <= 1
    if not note:
        note = "valid redistribution" if valid else "invalid overfull discount"
    return BatchRow(
        mode=mode,
        child_records=child_records,
        discount_bits=discount_bits,
        mix_num=mix_num,
        mix_den=mix_den,
        log2_symbol_mass=log2_fraction(sym),
        log2_z=log2_fraction(z),
        valid_kraft=valid,
        note=note,
    )


def best_public_mixture(
    base: dict[int, Fraction],
    batch: dict[int, Fraction],
    atoms: int,
    child_records: int,
    denominator: int = 32,
) -> BatchRow:
    best: BatchRow | None = None
    for num in range(denominator + 1):
        masses = mix_mass(base, batch, num, denominator)
        candidate = row(
            "base/batch_mix",
            masses,
            atoms,
            child_records,
            mix_num=num,
            mix_den=denominator,
            note="best public mixture sweep",
        )
        if best is None or candidate.log2_z > best.log2_z:
            best = candidate
    if best is None:
        raise AssertionError("empty mixture sweep")
    return best


def coverage_for_gain(gain_bits: int) -> float:
    """Probability a fixed public batch family covers a uniform target once.

    If a batch saves G bits versus the raw target, it has 2^-G expected hit
    density. Multiple candidates give 1-exp(-2^-G), the same finite-capacity
    boundary as the all-open board.
    """

    return 1.0 - math.exp(-(2.0 ** (-gain_bits)))


def rows(atoms: int = 12) -> list[BatchRow]:
    base = mass_dict(h108.arity_symbol_masses("custom_record", 6, 12))
    result: list[BatchRow] = [
        row("base_custom_record", base, atoms, child_records=1, note="H108/H105 baseline"),
    ]
    for child_records in (2, 3, 4):
        batch = batch_mass(base, child_records)
        result.append(
            row(
                "batch_only",
                batch,
                atoms,
                child_records=child_records,
                note="common-cause as honest convolution",
            )
        )
        result.append(best_public_mixture(base, batch, atoms, child_records))
        for discount_bits in (1, 2, 3):
            discounted = scale_mass(batch, discount_bits)
            result.append(
                row(
                    "discounted_batch",
                    discounted,
                    atoms,
                    child_records=child_records,
                    discount_bits=discount_bits,
                    note="shared-overhead claim without mass removal",
                )
            )
    return result


def print_rows(result: list[BatchRow]) -> None:
    print("== common-cause batch witness audit ==")
    print("Exact Fraction recurrence over H108 custom_record base, B=1,N=12.")
    print(
        f"{'mode':<20} {'m':>2} {'disc':>4} {'mix':>7} "
        f"{'log2 sym':>10} {'log2 Z_N':>10} {'valid':>7} {'note'}"
    )
    for item in result:
        mix = "-" if item.mode != "base/batch_mix" else f"{item.mix_num}/{item.mix_den}"
        print(
            f"{item.mode:<20} {item.child_records:2d} {item.discount_bits:4d} "
            f"{mix:>7} {item.log2_symbol_mass:10.6f} {item.log2_z:10.6f} "
            f"{str(item.valid_kraft):>7} {item.note}"
        )
    print()


def print_coverage_table() -> None:
    print("== one-batch coverage sanity check ==")
    print("If one public batch saves G bits on an arbitrary A-bit target, coverage is 1-exp(-2^-G).")
    print(f"{'G saved':>7} {'coverage/pass':>14}")
    for gain in (0, 1, 2, 3, 4, 5):
        print(f"{gain:7d} {coverage_for_gain(gain):14.9f}")
    print()


def print_reading(result: list[BatchRow]) -> None:
    valid = [item for item in result if item.valid_kraft]
    best = max(valid, key=lambda item: item.log2_z)
    invalid = [item for item in result if not item.valid_kraft]
    print("== reading ==")
    print(
        "Honest common-cause batches are just Kraft-mass redistributions. "
        f"The best valid row is {best.mode}, m={best.child_records}, "
        f"mix={best.mix_num}/{best.mix_den}, with log2Z={best.log2_z:.6f}."
    )
    print(
        "Rows that claim shared-overhead savings without removing an equal "
        "amount of symbol mass are flagged invalid: their log2 symbol mass is "
        "positive, so they are overfull record grammars."
    )
    worst_invalid = max(invalid, key=lambda item: item.log2_z)
    print(
        f"The most tempting invalid row here reaches log2Z={worst_invalid.log2_z:.6f} "
        f"only with log2 symbol mass={worst_invalid.log2_symbol_mass:.6f}."
    )
    print(
        "Therefore a batch witness is live only if it supplies a new real "
        "joint source/fertility law. Under independent uniform hash outputs, "
        "it collapses to higher arity or an overfull-code artifact."
    )


def main() -> None:
    result = rows()
    print_rows(result)
    print_coverage_table()
    print_reading(result)


if __name__ == "__main__":
    main()
