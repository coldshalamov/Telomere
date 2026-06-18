#!/usr/bin/env python3
"""H99 - seed parity / rejection readiness ledger.

A fixed seed predicate such as "even seed only" can be used as a public class
channel:

    pass t uses seed class t mod C

The decoder can read the class from the seed witness. This is stateless and
parseable if the class schedule is public. It is not free: accepting only one
of C seed classes reduces match supply by C, or equivalently costs log2(C) bits
of search depth / witness opportunity per record.

This file prices that channel and checks the common trap:

    static seed parity can mark a birth class,
    but a carried record keeps the same parity forever.

So parity only identifies the birth pass if the number of live birth epochs is
within the class count, or if the remaining ambiguity is paid elsewhere.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Row:
    live_epochs: int
    class_bits: int
    classes: int
    seed_supply_loss_bits: float
    residual_birth_bits: float
    total_paid_bits: float
    net_from_2bit_match: float
    exact_birth: bool


def rows() -> list[Row]:
    out: list[Row] = []
    for live_epochs in (2, 4, 8, 16, 64, 256):
        for class_bits in (0, 1, 2, 3, 4, 6, 8):
            classes = 1 << class_bits
            seed_supply_loss = float(class_bits)
            residual = max(0.0, math.log2(live_epochs) - class_bits)
            total = seed_supply_loss + residual
            out.append(
                Row(
                    live_epochs=live_epochs,
                    class_bits=class_bits,
                    classes=classes,
                    seed_supply_loss_bits=seed_supply_loss,
                    residual_birth_bits=residual,
                    total_paid_bits=total,
                    net_from_2bit_match=2.0 - total,
                    exact_birth=classes >= live_epochs,
                )
            )
    return out


def print_rows(all_rows: list[Row]) -> None:
    print("== seed predicate readiness ledger ==")
    print("C=2^g seed classes. Total paid = seed-supply loss g + residual birth ambiguity.")
    print(
        f"{'P live':>6} {'g':>3} {'C':>6} {'supply':>8} {'resid':>8} "
        f"{'paid':>8} {'2b net':>8} {'exact?':>7}"
    )
    for row in all_rows:
        if row.class_bits not in {0, 1, 2, 3, 6, 8}:
            continue
        print(
            f"{row.live_epochs:6d} {row.class_bits:3d} {row.classes:6d} "
            f"{row.seed_supply_loss_bits:8.3f} {row.residual_birth_bits:8.3f} "
            f"{row.total_paid_bits:8.3f} {row.net_from_2bit_match:8.3f} "
            f"{str(row.exact_birth):>7}"
        )
    print()


def print_reading(all_rows: list[Row]) -> None:
    print("== reading ==")
    two_epoch = next(row for row in all_rows if row.live_epochs == 2 and row.class_bits == 1)
    many_epoch = next(row for row in all_rows if row.live_epochs == 64 and row.class_bits == 1)
    exact_64 = next(row for row in all_rows if row.live_epochs == 64 and row.class_bits == 6)
    print(
        f"Even/odd seeds are a legal two-epoch discriminator: paid cost "
        f"{two_epoch.total_paid_bits:.3f} bit/record, leaving "
        f"{two_epoch.net_from_2bit_match:.3f} bits from a hypothetical 2-bit record margin."
    )
    print(
        f"But across 64 live epochs, one parity bit leaves "
        f"{many_epoch.residual_birth_bits:.3f} bits/record of unresolved birth ambiguity; "
        f"the total paid channel is still {many_epoch.total_paid_bits:.3f} bits/record."
    )
    print(
        f"Making the class exact for 64 epochs needs g={exact_64.class_bits}, "
        f"which costs {exact_64.seed_supply_loss_bits:.3f} bits/record of match supply."
    )
    print(
        "So seed rejection can move readiness into the seed grammar, but it does "
        "not make readiness free. It is promising only for a bounded two-epoch "
        "or near-total exception design where the live ambiguity is already tiny."
    )


def main() -> None:
    all_rows = rows()
    print_rows(all_rows)
    print_reading(all_rows)


if __name__ == "__main__":
    main()
