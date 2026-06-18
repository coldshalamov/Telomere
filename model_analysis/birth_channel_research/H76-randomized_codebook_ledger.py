#!/usr/bin/env python3
"""H76 - randomized / best-of codebook ledger.

This prices the loophole:

    "Use randomness or huge compute to try many public codebooks/profiles and
    choose the one that compresses this file."

If the codebook/profile is fixed public before the file, it is just a public Q
and obeys the uniform conservation law. If the encoder chooses among M profiles
after seeing the file, profile identity is a selector. A checksum/referee can
hide only a finite number of selector bits.

Unpriced best-of-M can increase the apparent winning fraction by M:

    c_free <= min(1, M * 2^-S)

Paying log2(M) selector bits reduces net saving by log2(M), returning the same
uniform coverage bound for the requested net saving.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


def base_prefix_coverage(saving_bits: float) -> float:
    if saving_bits <= 0.0:
        return 1.0
    return 2.0 ** (-saving_bits)


def base_eof_coverage(saving_bits: float) -> float:
    if saving_bits <= 0.0:
        return 1.0
    return min(1.0, 2.0 ** (1.0 - saving_bits))


def free_best_of_coverage(saving_bits: float, profiles: int, eof: bool) -> float:
    base = base_eof_coverage(saving_bits) if eof else base_prefix_coverage(saving_bits)
    return min(1.0, profiles * base)


def paid_best_of_coverage(net_saving_bits: float, profiles: int, eof: bool) -> float:
    selector_bits = math.ceil(math.log2(max(1, profiles)))
    gross_saving = net_saving_bits + selector_bits
    base = base_eof_coverage(gross_saving) if eof else base_prefix_coverage(gross_saving)
    return min(1.0, profiles * base)


def referee_best_of_coverage(saving_bits: float, profiles: int, referee_bits: int, eof: bool) -> float:
    visible_profiles = min(profiles, 1 << referee_bits)
    base = base_eof_coverage(saving_bits) if eof else base_prefix_coverage(saving_bits)
    return min(1.0, visible_profiles * base)


def profiles_needed_for_coverage(coverage: float, saving_bits: float, eof: bool) -> int:
    base = base_eof_coverage(saving_bits) if eof else base_prefix_coverage(saving_bits)
    if base <= 0.0:
        return math.inf  # type: ignore[return-value]
    return math.ceil(coverage / base)


@dataclass(frozen=True)
class BestOfRow:
    saving_bits: int
    profiles: int
    free_prefix: float
    paid_prefix: float
    free_eof: float
    paid_eof: float


@dataclass(frozen=True)
class NeedRow:
    coverage: float
    passes: int
    saving_per_pass_bits: float
    total_saving_bits: float
    prefix_profiles_needed: int
    eof_profiles_needed: int
    selector_bits_prefix: float
    selector_bits_eof: float


@dataclass(frozen=True)
class RefereeRow:
    saving_bits: int
    profiles: int
    referee_bits: int
    free_prefix: float
    referee_prefix: float
    bits_still_owed: float


def best_of_rows() -> list[BestOfRow]:
    rows: list[BestOfRow] = []
    for saving in (4, 16, 64):
        for profiles in (1, 16, 256, 65536):
            rows.append(
                BestOfRow(
                    saving_bits=saving,
                    profiles=profiles,
                    free_prefix=free_best_of_coverage(saving, profiles, eof=False),
                    paid_prefix=paid_best_of_coverage(saving, profiles, eof=False),
                    free_eof=free_best_of_coverage(saving, profiles, eof=True),
                    paid_eof=paid_best_of_coverage(saving, profiles, eof=True),
                )
            )
    return rows


def need_rows() -> list[NeedRow]:
    rows: list[NeedRow] = []
    for coverage in (0.90, 0.99):
        for passes in (4, 16, 64):
            for saving_per_pass in (1.0, 2.0):
                total = passes * saving_per_pass
                p_need = profiles_needed_for_coverage(coverage, total, eof=False)
                e_need = profiles_needed_for_coverage(coverage, total, eof=True)
                rows.append(
                    NeedRow(
                        coverage=coverage,
                        passes=passes,
                        saving_per_pass_bits=saving_per_pass,
                        total_saving_bits=total,
                        prefix_profiles_needed=p_need,
                        eof_profiles_needed=e_need,
                        selector_bits_prefix=math.log2(p_need),
                        selector_bits_eof=math.log2(e_need),
                    )
                )
    return rows


def referee_rows() -> list[RefereeRow]:
    rows: list[RefereeRow] = []
    for saving in (16, 64):
        for profiles in (256, 65536, 1 << 32):
            for referee_bits in (8, 16):
                rows.append(
                    RefereeRow(
                        saving_bits=saving,
                        profiles=profiles,
                        referee_bits=referee_bits,
                        free_prefix=free_best_of_coverage(saving, profiles, eof=False),
                        referee_prefix=referee_best_of_coverage(saving, profiles, referee_bits, eof=False),
                        bits_still_owed=max(0.0, math.log2(profiles) - referee_bits),
                    )
                )
    return rows


def fmt_prob(value: float) -> str:
    if value == 0.0:
        return "0"
    if value >= 0.001:
        return f"{value:.6f}"
    return f"{value:.3e}"


def print_best_of_rows() -> None:
    print("== best-of-M profile coverage ==")
    print("Paid rows target the same net saving S after selector bits.")
    print(
        f"{'S':>5} {'M':>10} {'prefix free':>13} {'prefix paid':>13} "
        f"{'EOF free':>11} {'EOF paid':>11}"
    )
    for row in best_of_rows():
        print(
            f"{row.saving_bits:5d} {row.profiles:10d} "
            f"{fmt_prob(row.free_prefix):>13} {fmt_prob(row.paid_prefix):>13} "
            f"{fmt_prob(row.free_eof):>11} {fmt_prob(row.paid_eof):>11}"
        )
    print()


def print_need_rows() -> None:
    print("== profiles needed for claimed roughly-all recursion ==")
    print("Selector bits needed are approximately the total saving being hidden.")
    print(
        f"{'coverage':>8} {'P':>5} {'s/pass':>7} {'S':>7} "
        f"{'M prefix':>13} {'sel bits':>10} {'M EOF':>13} {'sel bits':>10}"
    )
    for row in need_rows():
        if row.coverage == 0.90:
            print(
                f"{row.coverage:8.2f} {row.passes:5d} "
                f"{row.saving_per_pass_bits:7.2f} {row.total_saving_bits:7.1f} "
                f"{row.prefix_profiles_needed:13d} {row.selector_bits_prefix:10.3f} "
                f"{row.eof_profiles_needed:13d} {row.selector_bits_eof:10.3f}"
            )
    print()


def print_referee_rows() -> None:
    print("== finite checksum/referee budget ==")
    print("A C-bit referee exposes at most C selector bits.")
    print(
        f"{'S':>5} {'M':>12} {'C':>5} {'free prefix':>13} "
        f"{'referee prefix':>15} {'owed bits':>10}"
    )
    for row in referee_rows():
        if row.saving_bits == 64:
            print(
                f"{row.saving_bits:5d} {row.profiles:12d} {row.referee_bits:5d} "
                f"{fmt_prob(row.free_prefix):>13} "
                f"{fmt_prob(row.referee_prefix):>15} {row.bits_still_owed:10.3f}"
            )
    print()


def print_reading() -> None:
    print("== reading ==")
    print("Randomness helps only by naming a public distribution before the file")
    print("or by selecting a profile after seeing the file. The first is public Q")
    print("and obeys KL conservation; the second is selector metadata. Compute can")
    print("find the best profile, but decode needs to know which profile unless the")
    print("choice is visible in the output length, in which case it is already paid.")


def main() -> None:
    print_best_of_rows()
    print_need_rows()
    print_referee_rows()
    print_reading()


if __name__ == "__main__":
    main()
