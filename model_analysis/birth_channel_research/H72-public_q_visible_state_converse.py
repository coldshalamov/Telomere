#!/usr/bin/env python3
"""H72 - public-Q / visible-state / selector-budget converse.

This kernel prices a common family of proposed escapes:

* choose the best public model/profile/cover after seeing the file;
* let a checksum/referee select the right decoding;
* hide the selected cover in a final board / visible arrangement;
* claim the decoder can infer the state, so no selector is stored.

The counting check is simple. For n-bit uniform inputs and a desired final
saving S, there are only so many short outputs. Splitting a short output into

    [visible state][payload]

does not increase the number of short outputs. A multiplier from profiles,
checksums, or board arrangements helps only when its identity is not counted.
If the identity is present in the compressed file, it spends log2(multiplier)
bits and cancels the multiplier in the uniform count.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


def log2_int(value: int) -> float:
    return math.log2(max(1, value))


def prefix_slots(n_bits: int, saving_bits: int) -> int:
    if saving_bits < 0:
        return 1 << n_bits
    if saving_bits > n_bits:
        return 0
    return 1 << (n_bits - saving_bits)


def eof_slots(n_bits: int, saving_bits: int) -> int:
    if saving_bits <= 0:
        return 1 << n_bits
    if saving_bits > n_bits:
        return 0
    max_len = n_bits - saving_bits
    return (1 << (max_len + 1)) - 1


def cap(total: int, count: int) -> int:
    return max(0, min(total, count))


@dataclass(frozen=True)
class SelectorRow:
    n_bits: int
    saving_bits: int
    total_inputs: int
    prefix_count: int
    eof_count: int
    multiplier_name: str
    multiplier: int
    free_prefix_count: int
    paid_prefix_count: int
    free_eof_count: int
    paid_eof_count: int


@dataclass(frozen=True)
class RefereeRow:
    n_bits: int
    saving_bits: int
    profiles: int
    referee_bits: int
    total_inputs: int
    unrefereed_count: int
    free_referee_count: int
    charged_referee_count: int
    profiles_left_unpriced_bits: float


@dataclass(frozen=True)
class PublicQRow:
    q_name: str
    expected_excess_bits: float
    uniform_verdict: str
    source_verdict: str


def selector_row(n_bits: int, saving_bits: int, multiplier_name: str, multiplier: int) -> SelectorRow:
    total = 1 << n_bits
    prefix = prefix_slots(n_bits, saving_bits)
    eof = eof_slots(n_bits, saving_bits)
    selector_bits = math.ceil(log2_int(multiplier))
    return SelectorRow(
        n_bits=n_bits,
        saving_bits=saving_bits,
        total_inputs=total,
        prefix_count=prefix,
        eof_count=eof,
        multiplier_name=multiplier_name,
        multiplier=multiplier,
        free_prefix_count=cap(total, multiplier * prefix),
        paid_prefix_count=cap(total, multiplier * prefix_slots(n_bits, saving_bits + selector_bits)),
        free_eof_count=cap(total, multiplier * eof),
        paid_eof_count=cap(total, multiplier * eof_slots(n_bits, saving_bits + selector_bits)),
    )


def referee_row(n_bits: int, saving_bits: int, profiles: int, referee_bits: int) -> RefereeRow:
    total = 1 << n_bits
    base = prefix_slots(n_bits, saving_bits)
    visible_profiles = min(profiles, 1 << referee_bits)
    return RefereeRow(
        n_bits=n_bits,
        saving_bits=saving_bits,
        profiles=profiles,
        referee_bits=referee_bits,
        total_inputs=total,
        unrefereed_count=base,
        free_referee_count=cap(total, visible_profiles * base),
        charged_referee_count=cap(total, (1 << referee_bits) * prefix_slots(n_bits, saving_bits + referee_bits)),
        profiles_left_unpriced_bits=max(0.0, log2_int(profiles) - referee_bits),
    )


def public_q_rows() -> list[PublicQRow]:
    return [
        PublicQRow(
            q_name="uniform raw code",
            expected_excess_bits=0.0,
            uniform_verdict="baseline",
            source_verdict="no source lift",
        ),
        PublicQRow(
            q_name="H58 frozen bucket Q",
            expected_excess_bits=0.229195,
            uniform_verdict="positive excess under uniform",
            source_verdict="can cross only if source visits high-Q states enough",
        ),
        PublicQRow(
            q_name="H59 raw/Q mixture T1",
            expected_excess_bits=0.053411,
            uniform_verdict="positive held-out excess under uniform",
            source_verdict="smallest current source-shaped target",
        ),
    ]


def fmt_count(count: int, total: int) -> str:
    return f"{count}/{total} ({count / total:.6f})"


def print_selector_table() -> None:
    print("== selector / visible-state multiplier audit ==")
    print("If multiplier identity is paid inside the short output, it cancels.")
    print(
        f"{'n':>4} {'S':>4} {'multiplier':<16} {'M':>8} "
        f"{'prefix base':>20} {'prefix free':>20} {'prefix paid':>20} "
        f"{'EOF base':>20} {'EOF free':>20} {'EOF paid':>20}"
    )
    for name, multiplier in (
        ("profiles", 16),
        ("board states", 1024),
        ("cover shapes", 4096),
    ):
        row = selector_row(16, 4, name, multiplier)
        print(
            f"{row.n_bits:4d} {row.saving_bits:4d} {row.multiplier_name:<16} "
            f"{row.multiplier:8d} {fmt_count(row.prefix_count, row.total_inputs):>20} "
            f"{fmt_count(row.free_prefix_count, row.total_inputs):>20} "
            f"{fmt_count(row.paid_prefix_count, row.total_inputs):>20} "
            f"{fmt_count(row.eof_count, row.total_inputs):>20} "
            f"{fmt_count(row.free_eof_count, row.total_inputs):>20} "
            f"{fmt_count(row.paid_eof_count, row.total_inputs):>20}"
        )
    print()


def print_referee_table() -> None:
    print("== checksum/referee finite-budget audit ==")
    print("A finite referee can choose among finite profiles; charged bits cancel.")
    print(
        f"{'n':>4} {'S':>4} {'profiles':>9} {'C bits':>7} "
        f"{'base':>18} {'free referee':>18} {'charged':>18} {'owed bits':>10}"
    )
    for profiles in (4, 16, 256, 4096):
        for referee_bits in (1, 4, 8):
            row = referee_row(16, 4, profiles, referee_bits)
            print(
                f"{row.n_bits:4d} {row.saving_bits:4d} {row.profiles:9d} "
                f"{row.referee_bits:7d} {fmt_count(row.unrefereed_count, row.total_inputs):>18} "
                f"{fmt_count(row.free_referee_count, row.total_inputs):>18} "
                f"{fmt_count(row.charged_referee_count, row.total_inputs):>18} "
                f"{row.profiles_left_unpriced_bits:10.3f}"
            )
    print()


def print_public_q_table() -> None:
    print("== public Q expected-excess audit ==")
    print("For uniform U, E_U[-log2 Q(X)] = n + KL(U||Q) >= n.")
    print(f"{'Q':<24} {'excess bits':>12} {'uniform':<36} {'source-shaped reading':<48}")
    for row in public_q_rows():
        print(
            f"{row.q_name:<24} {row.expected_excess_bits:12.6f} "
            f"{row.uniform_verdict:<36} {row.source_verdict:<48}"
        )
    print()


def print_reading() -> None:
    print("== reading ==")
    print("Final boards, cover shapes, checksums, and best-of public profiles are")
    print("not rejected by name. They are rejected only when their identity is a")
    print("free multiplier on the number of short outputs. If the decoder observes")
    print("the state in the compressed file, those state bits are part of the file")
    print("length. If it does not, they are hidden metadata. Public Q remains the")
    print("clean formulation: it can define which strings are favored, but under")
    print("uniform data its expected excess is nonnegative.")


def main() -> None:
    print_selector_table()
    print_referee_table()
    print_public_q_table()
    print_reading()


if __name__ == "__main__":
    main()
