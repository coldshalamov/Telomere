#!/usr/bin/env python3
"""Ledger for position-as-status and ready-prefix decode geometry.

The user-proposed geometry ideas are real enough to price:

1. A boundary/delineation per pass is cheap if it is sufficient.
2. If the decoder also needs the subset of positions that moved to the prefix,
   the missing bill is an interval/bitmap entropy term.
3. A deterministic ready lane avoids subset bits but spends match supply by
   accepting records only in public lane slots.

This kernel only prices those channels. It does not run Telomere searches.
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass


@dataclass(frozen=True)
class GeometryRow:
    items: int
    record_fraction: float
    records: int
    boundary_bits_per_record: float
    subset_bits_per_record: float
    deterministic_lane_loss_bits: float
    subset_minus_boundary: float


def log2_comb(n: int, k: int) -> float:
    if k < 0 or k > n:
        return float("-inf")
    return (math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)) / math.log(2.0)


def row(items: int, record_fraction: float) -> GeometryRow:
    records = max(1, min(items, round(items * record_fraction)))
    actual_fraction = records / items
    boundary = math.log2(items + 1) / records
    subset = log2_comb(items, records) / records
    lane_loss = math.log2(1.0 / actual_fraction)
    return GeometryRow(
        items=items,
        record_fraction=actual_fraction,
        records=records,
        boundary_bits_per_record=boundary,
        subset_bits_per_record=subset,
        deterministic_lane_loss_bits=lane_loss,
        subset_minus_boundary=max(0.0, subset - boundary),
    )


def render(rows: list[GeometryRow]) -> str:
    lines = [
        "# Positional Geometry Ledger",
        "",
        "Boundary cost is the cheap ready-prefix dream: store one cut point.",
        "Subset cost is the honest stable-partition bill if the decoder must",
        "recover which positions were moved. Deterministic lane loss is the",
        "supply cost of requiring births only in a public position lane.",
        "",
        "| N items | record fraction r | records m | boundary bits/record | subset bits/record | hidden bits if boundary-only | deterministic lane supply loss/record |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in rows:
        lines.append(
            f"| {item.items} | {item.record_fraction:.6f} | {item.records} | "
            f"{item.boundary_bits_per_record:.6f} | {item.subset_bits_per_record:.6f} | "
            f"{item.subset_minus_boundary:.6f} | {item.deterministic_lane_loss_bits:.6f} |"
        )

    lines.extend(
        [
            "",
            "## Reading",
            "",
            "A ready-prefix boundary is attractive only when the pass semantics make",
            "the prefix order itself the previous-layer order, or when the moved",
            "positions are public. If the encoder selected arbitrary content-hit",
            "positions and then stable-partitioned them to the front, the decoder",
            "needs the original subset; the boundary alone is a hidden bitmap.",
            "",
            "A deterministic position lane can be metadata-free, but it spends the",
            "same currency as a sparse cover: only a fraction `r` of positions are",
            "eligible, costing about `log2(1/r)` match-supply bits per record.",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--items", type=int, nargs="+", default=[1024, 65536, 1000000])
    parser.add_argument("--fractions", type=float, nargs="+", default=[0.001, 0.01, 0.05, 0.1, 0.25, 0.5])
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = [row(items, fraction) for items in args.items for fraction in args.fractions]
    print(render(rows))


if __name__ == "__main__":
    main()
