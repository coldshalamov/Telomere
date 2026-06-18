#!/usr/bin/env python3
"""H82 - native syntax support-capacity ledger.

After H81, the remaining target is "native compact syntax that is fertile".
The simplest version is: make the visible record language only emit strings in
a public fertile class F.

H82 prices that support restriction. If F has uniform mass f and source mass q,
then:

    support tax              = -log2(f)
    class-membership dividend = log2(q/f)
    forced-subset net         = log2(q) <= 0

So a public valid-subset syntax cannot be positive from membership alone. It
can still be useful as decode geometry, but the breakthrough would need graded
within-syntax value, not merely "valid strings are fertile strings".
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


@dataclass(frozen=True)
class SupportRow:
    name: str
    fraction: float
    q_mass: float
    support_tax_bits: float
    membership_dividend_bits: float
    forced_subset_net_bits: float
    mu_f: float


def row_for_indices(domain, name: str, indices: list[int]) -> SupportRow:
    class_row = _h80.row_for_indices(domain, indices)
    f = class_row.fraction
    q = class_row.q_mass
    support_tax = -math.log2(f)
    dividend = math.log2(q / f)
    return SupportRow(
        name=name,
        fraction=f,
        q_mass=q,
        support_tax_bits=support_tax,
        membership_dividend_bits=dividend,
        forced_subset_net_bits=dividend - support_tax,
        mu_f=class_row.mu_f,
    )


def rows(domain) -> list[SupportRow]:
    result = [
        row_for_indices(domain, "top2.5", _h80.top_class_indices(domain.scores, 0.025)),
        row_for_indices(domain, "top10", _h80.top_class_indices(domain.scores, 0.10)),
        row_for_indices(domain, "top25", _h80.top_class_indices(domain.scores, 0.25)),
        row_for_indices(domain, "F_positive", _h80.positive_class_indices(domain.scores)),
        row_for_indices(domain, "top50", _h80.top_class_indices(domain.scores, 0.50)),
        row_for_indices(domain, "bottom25", _h80.bottom_class_indices(domain.scores, 0.25)),
    ]
    return result


def print_rows(rows: list[SupportRow]) -> None:
    print("== public syntax support-capacity ledger ==")
    print(
        "Forced-subset net is membership_dividend - support_tax = log2(Q(F)). "
        "It cannot be positive unless Q(F)>1, so membership alone cannot pay."
    )
    print(
        f"{'class':<12} {'f=U(F)':>9} {'Q(F)':>9} {'tax':>8} "
        f"{'dividend':>9} {'net':>9} {'mu_F':>9}"
    )
    for row in rows:
        print(
            f"{row.name:<12} {row.fraction:9.4f} {row.q_mass:9.4f} "
            f"{row.support_tax_bits:8.3f} {row.membership_dividend_bits:9.3f} "
            f"{row.forced_subset_net_bits:9.3f} {row.mu_f:9.3f}"
        )
    print()


def print_reading() -> None:
    print("== reading ==")
    print(
        "A native syntax cannot win merely by declaring fertile strings valid. "
        "For top25/F_positive, Q puts about 78% of mass in the class, but the "
        "capacity tax is about two bits, leaving a membership-only net around "
        "-0.35 bits. This does not rule out a graded record language whose "
        "actual code lengths and visible syntax are jointly fertile; it rules "
        "out support membership as the missing free channel."
    )


def main() -> None:
    domain = _h80.exact_domain()
    print_rows(rows(domain))
    print_reading()


if __name__ == "__main__":
    main()
