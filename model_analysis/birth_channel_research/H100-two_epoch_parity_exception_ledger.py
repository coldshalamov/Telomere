#!/usr/bin/env python3
"""H100 - two-epoch parity / near-total exception ledger.

H99 left one live opening: seed-class parity is not a free many-pass birth
channel, but it is a paid two-epoch discriminator. H100 asks whether that
bounded discriminator is cheap enough to matter if the codec enforces:

    live records are either current epoch or previous epoch, never older.

The decoder then knows, from pass parity and the seed class, which records open
and which records carry. That is stateless only if the two-epoch invariant is
true. This file prices the invariant as a target ledger, not a compression run.

Definitions:

    r       selected records per input atom
    m       base paid margin before seed-class restriction, bits/record
    q       fraction of output record slots born/refreshed in this pass
    c       seed-class bits; c=1 is even/odd

Two-epoch seed class net, record-slot model:

    net_bits_per_atom = q * r * (m - c)

Old record slots are visible by their previous seed class and carry for one
pass only. If they live longer than one pass, parity aliases and the hidden
birth channel returns.

For comparison, H100 also prints:

    ideal current/old marker:
        q*r*m - r*H2(1-q)

    many-epoch atom exception ledger:
        q*r*m - [H2(eps) + eps*log2(P-1)]

The first is an unrealistically cheap record-slot marker. The second is the old
many-pass atom-exception bill from H43. The seed-parity channel is between
them: stateless and local, but paid as match-supply loss on each new record.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Target:
    name: str
    records_per_atom: float
    margin_per_record: float


TARGETS = [
    Target("H7 current", 0.008789, -1.357),
    Target("H9 current", 0.009765, -1.261),
    Target("H12 upper", 0.010987, -0.746),
    Target("hyp +1.0", 0.009765, 1.000),
    Target("hyp +1.5", 0.009765, 1.500),
    Target("hyp +2.0", 0.009765, 2.000),
]


def h2(p: float) -> float:
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -(p * math.log2(p) + (1.0 - p) * math.log2(1.0 - p))


def parity_net(target: Target, q: float, class_bits: float) -> float:
    return q * target.records_per_atom * (target.margin_per_record - class_bits)


def ideal_record_marker_net(target: Target, q: float) -> float:
    eps = 1.0 - q
    return q * target.records_per_atom * target.margin_per_record - target.records_per_atom * h2(eps)


def many_epoch_atom_net(target: Target, q: float, passes: int) -> float:
    eps = 1.0 - q
    ledger = h2(eps) + (eps * math.log2(passes - 1) if passes > 1 else 0.0)
    return q * target.records_per_atom * target.margin_per_record - ledger


def required_margin_parity(class_bits: float) -> float:
    return class_bits


def required_margin_marker(q: float) -> float:
    if q <= 0.0:
        return math.inf
    return h2(1.0 - q) / q


def required_margin_many_epoch(target: Target, q: float, passes: int) -> float:
    if q <= 0.0 or target.records_per_atom <= 0.0:
        return math.inf
    eps = 1.0 - q
    ledger = h2(eps) + (eps * math.log2(passes - 1) if passes > 1 else 0.0)
    return ledger / (q * target.records_per_atom)


def residual_age_entropy_uniform(live_ages: int, class_bits: int) -> float:
    """H(age | age mod 2^class_bits) for uniform live ages 0..live_ages-1."""

    classes = 1 << class_bits
    counts = [0] * classes
    for age in range(live_ages):
        counts[age % classes] += 1
    return sum((count / live_ages) * math.log2(count) for count in counts if count)


def print_net_table() -> None:
    print("== two-epoch seed-class net ==")
    print("q is the fraction of record slots born/refreshed this pass; c=1 is parity.")
    print(
        f"{'target':<12} {'q':>6} {'m rec':>8} {'r/atom':>8} "
        f"{'parity':>10} {'ideal mark':>10} {'P256 atom':>10}"
    )
    for target in TARGETS:
        for q in (1.00, 0.99, 0.95, 0.90, 0.75, 0.50):
            print(
                f"{target.name:<12} {q:6.2f} {target.margin_per_record:8.3f} "
                f"{target.records_per_atom:8.6f} {parity_net(target, q, 1.0):10.6f} "
                f"{ideal_record_marker_net(target, q):10.6f} "
                f"{many_epoch_atom_net(target, q, 256):10.6f}"
            )
        print()


def print_threshold_table() -> None:
    print("== required base margin per record ==")
    print("This is the margin before paying the readiness channel.")
    print(
        f"{'q':>6} {'parity c1':>10} {'ideal rec mark':>14} "
        f"{'H7 P256 atom':>14} {'H9 P256 atom':>14}"
    )
    h7 = TARGETS[0]
    h9 = TARGETS[1]
    for q in (1.00, 0.99, 0.95, 0.90, 0.75, 0.50):
        print(
            f"{q:6.2f} {required_margin_parity(1.0):10.3f} "
            f"{required_margin_marker(q):14.3f} "
            f"{required_margin_many_epoch(h7, q, 256):14.3f} "
            f"{required_margin_many_epoch(h9, q, 256):14.3f}"
        )
    print()


def print_residual_age_table() -> None:
    print("== residual age entropy ==")
    print("Exact H(age | age mod C) for uniform live ages; L=2,c=1 is the bounded target.")
    print(f"{'live L':>7} {'c':>3} {'C':>5} {'residual bits/record':>21}")
    for live_ages in (2, 3, 4, 8, 16, 64, 256):
        for class_bits in (1, 2, 3, 6, 8):
            print(
                f"{live_ages:7d} {class_bits:3d} {1 << class_bits:5d} "
                f"{residual_age_entropy_uniform(live_ages, class_bits):21.6f}"
            )
        print()


def print_reading() -> None:
    h12 = TARGETS[2]
    hyp2 = TARGETS[-1]
    print("== reading ==")
    print(
        f"Current nearest paid rows do not survive parity. Even the H12 upper row "
        f"would be {parity_net(h12, 1.0, 1.0):.6f} bits/atom at q=1 because its "
        f"base margin is {h12.margin_per_record:.3f} bits/record before the "
        "1-bit seed-class loss."
    )
    print(
        f"A real +2 bits/record mechanism would survive two-epoch parity at the "
        f"H9 record density: {parity_net(hyp2, 1.0, 1.0):.6f} bits/atom at q=1 "
        f"and {parity_net(hyp2, 0.9, 1.0):.6f} bits/atom at q=0.9."
    )
    print(
        "Therefore two-epoch parity is not the missing witness improvement, but "
        "it is a plausible stateless readiness layer after some other mechanism "
        "creates more than 1 paid bit/record of base margin and enforces maximum "
        "record lifetime <=1 pass."
    )
    print(
        "If records can live for more than one pass, the parity classes alias and "
        "H99's log2(P) birth ambiguity returns."
    )


def main() -> None:
    print_net_table()
    print_threshold_table()
    print_residual_age_table()
    print_reading()


if __name__ == "__main__":
    main()
