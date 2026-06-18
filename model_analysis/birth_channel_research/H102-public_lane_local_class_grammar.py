#!/usr/bin/env python3
"""H102 - public lane plus local class seed grammar.

H99/H101 priced visible seed parity: if the seed witness itself must reveal
even/odd readiness, accepting one class costs seed supply unless neutral
multiplicity discounts it.

There is a different construction:

    the public lane/position tells the decoder which epoch grammar applies
    the witness is a local rank inside that grammar's seed class

Then W witness bits name 2^W seeds in the selected class, not half of a global
2^W seed window. The class bit is not hidden in the seed. It is supplied by a
public lane invariant. This can make the seed-class cost zero, but only if the
ready/carry membership is public or otherwise paid.

This file is a ledger, not a compressor. It compares:

* visible seed class: class paid in match supply;
* public lane + local seed class: no class supply loss, but only public slots
  may be refreshed;
* content-selected lane: local class grammar plus arbitrary membership, which
  pays subset entropy.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Target:
    name: str
    records_per_atom: float
    margin_per_record: float


@dataclass(frozen=True)
class LedgerRow:
    target: Target
    q: float
    class_loss: float
    visible_seed_net: float
    public_lane_net: float
    content_lane_net: float
    content_lane_tax_per_record: float


TARGETS = [
    Target("H7 current", 0.008789, -1.357),
    Target("H9 current", 0.009765, -1.261),
    Target("H12 upper", 0.010987, -0.746),
    Target("hyp +0.28", 0.010000, 0.280),
    Target("hyp +1.00", 0.009765, 1.000),
    Target("hyp +2.00", 0.009765, 2.000),
]


def h2(p: float) -> float:
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -(p * math.log2(p) + (1.0 - p) * math.log2(1.0 - p))


def log2_binomial_stirling(n: int, k: int) -> float:
    if k < 0 or k > n:
        return float("inf")
    return (
        math.lgamma(n + 1) / math.log(2.0)
        - math.lgamma(k + 1) / math.log(2.0)
        - math.lgamma(n - k + 1) / math.log(2.0)
    )


def ledger_row(target: Target, q: float, class_loss: float) -> LedgerRow:
    visible = q * target.records_per_atom * (target.margin_per_record - class_loss)
    public_lane = q * target.records_per_atom * target.margin_per_record
    lane_tax = h2(q)
    content_lane = q * target.records_per_atom * target.margin_per_record - target.records_per_atom * lane_tax
    return LedgerRow(
        target=target,
        q=q,
        class_loss=class_loss,
        visible_seed_net=visible,
        public_lane_net=public_lane,
        content_lane_net=content_lane,
        content_lane_tax_per_record=lane_tax,
    )


def print_counting_sanity() -> None:
    print("== counting sanity ==")
    print("Ready/carry membership must be visible somewhere.")
    print(f"{'N':>8} {'R/N':>6} {'boundary/open':>14} {'subset/open':>13}")
    for n, q in ((1024, 0.5), (1024, 0.9), (1_000_000, 0.5), (1_000_000, 0.99)):
        r = round(n * q)
        boundary = math.log2(n + 1) / max(1, r)
        subset = log2_binomial_stirling(n, r) / max(1, r)
        print(f"{n:8d} {q:6.2f} {boundary:14.6f} {subset:13.6f}")
    print()


def print_seed_class_sanity() -> None:
    print("== seed-class grammar sanity ==")
    print("Visible global seed class pays supply. Public local grammar does not,")
    print("because W bits name 2^W seeds inside the public class.")
    print(f"{'W':>4} {'classes':>7} {'global seeds':>13} {'visible/class':>14} {'local/class':>13}")
    for width in (8, 16, 32):
        for classes in (2, 4):
            global_seeds = 2**width
            visible = global_seeds / classes
            local = global_seeds
            print(f"{width:4d} {classes:7d} {global_seeds:13.0f} {visible:14.0f} {local:13.0f}")
    print()


def print_net_table() -> None:
    print("== public-lane local-class net ==")
    print("q is public refreshed/open fraction. class_loss is paid only in visible-seed mode.")
    print(
        f"{'target':<12} {'q':>5} {'class':>7} {'visible':>10} "
        f"{'public':>10} {'content':>10} {'H(q)':>8}"
    )
    for target in TARGETS:
        for q in (1.0, 0.9, 0.5):
            for class_loss in (1.0, 0.830905, 0.260736):
                row = ledger_row(target, q, class_loss)
                print(
                    f"{target.name:<12} {q:5.2f} {class_loss:7.3f} "
                    f"{row.visible_seed_net:10.6f} {row.public_lane_net:10.6f} "
                    f"{row.content_lane_net:10.6f} {row.content_lane_tax_per_record:8.3f}"
                )
            print()
        print()


def print_thresholds() -> None:
    print("== positive conditions ==")
    print("Visible global seed class: margin_per_record > class_loss.")
    print("Public lane + local class grammar: margin_per_record > 0.")
    print("Content-selected lane + local class grammar: margin_per_record > H(q)/q.")
    print(f"{'q':>5} {'visible c=1':>13} {'public lane':>13} {'content lane':>14}")
    for q in (1.0, 0.99, 0.9, 0.75, 0.5):
        content = h2(q) / q if q > 0.0 else math.inf
        print(f"{q:5.2f} {1.0:13.6f} {0.0:13.6f} {content:14.6f}")
    print()


def print_reading() -> None:
    h9 = TARGETS[1]
    hyp = TARGETS[3]
    print("== reading ==")
    print(
        "A public lane can legitimately remove the per-record seed-class bill "
        "if the witness is a local rank inside the lane's seed class. That is "
        "not a reward hack because the lane, not the seed, carries readiness."
    )
    print(
        f"Current paid rows still fail because their base margins are negative; "
        f"H9 has public-lane net {ledger_row(h9, 1.0, 1.0).public_lane_net:.6f} "
        "bits/atom at q=1."
    )
    print(
        f"A separate collective mechanism worth about +0.28 bits/record would "
        f"survive public-lane local grammar: {ledger_row(hyp, 1.0, 1.0).public_lane_net:.6f} "
        "bits/atom at q=1 and no parity tax. The same mechanism would not "
        "survive visible global parity at a one-bit class cost."
    )
    print(
        "This is the cleanest surviving stateless decode shape: public two-epoch "
        "lanes for open/carry, class-local seed enumeration for fresh salts, "
        "and a separate paid witness mechanism that makes the forced rewrite "
        "margin positive."
    )


def main() -> None:
    print_counting_sanity()
    print_seed_class_sanity()
    print_net_table()
    print_thresholds()
    print_reading()


if __name__ == "__main__":
    main()
