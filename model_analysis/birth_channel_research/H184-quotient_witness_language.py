#!/usr/bin/env python3
"""H184 - quotient/coset witness language accounting.

This kernel tests a tempting witness-entropy escape:

    Store only a seed quotient/coset, not the exact seed.  Let the decoder
    derive the exact member from public constraints, a checksum, or a layer-wide
    selector tape.

There are only three honest cases:

1. canonical member:
   the decoder picks one public member of each coset.  This is stateless, but
   it throws away q seed bits of match supply.

2. selector/referee:
   the coset contains 2^q possible seed expansions.  A local selector or global
   referee must identify the chosen one, costing q bits per record plus safety.

3. public fixed width / layer tape:
   a whole layer stores raw payload ranks after a public width declaration.
   This can remove repeated Lotus width headers, but it is exactly value/count
   separation; it does not increase witness mass.  H176 is the recursive
   trellis version of this generous case.
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


LN2 = math.log(2.0)


def parse_int_list(values: list[str], default: list[int]) -> list[int]:
    if not values:
        return default
    out: list[int] = []
    for value in values:
        out.extend(int(part) for part in value.split(",") if part)
    return out


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


def required_referee_bits(hidden_bits: float, target_unique: float) -> int:
    if not 0.0 < target_unique < 1.0:
        raise ValueError("target_unique must be in (0,1)")
    return math.ceil(hidden_bits - math.log2(-math.log(target_unique)))


@dataclass(frozen=True)
class CosetRow:
    arity: int
    payload_width: int
    hidden_bits: int
    records: int
    direct_bits: int
    quotient_bits: int
    selector_bits: int
    local_paid_bits: int
    local_delta: int
    canonical_supply_tax: int
    referee_bits_99: int
    referee_paid_bits: int
    referee_delta: int
    decode_work_log2: int
    verdict: str


@dataclass(frozen=True)
class WidthRow:
    arity: int
    payload_width: int
    records: int
    v1_bits: int
    raw_width_bits: int
    width_header_bits: int
    layer_paid_per_record: float
    savings_per_record: float
    tier_overhead: int
    verdict: str


def coset_row(arity: int, payload_width: int, hidden_bits: int, records: int, target_unique: float) -> CosetRow:
    if hidden_bits >= payload_width:
        raise ValueError("hidden bits must be smaller than payload width")
    direct_bits = costs.record_cost_for_payload_width(arity, payload_width)
    quotient_width = payload_width - hidden_bits
    quotient_bits = costs.record_cost_for_payload_width(arity, quotient_width)
    selector_bits = hidden_bits
    local_paid_bits = quotient_bits + selector_bits
    local_delta = direct_bits - local_paid_bits
    canonical_supply_tax = hidden_bits
    hidden_layer_bits = hidden_bits * records
    referee_bits = required_referee_bits(hidden_layer_bits, target_unique)
    referee_paid = quotient_bits * records + referee_bits
    direct_layer = direct_bits * records
    referee_delta = direct_layer - referee_paid
    if local_delta > 0:
        verdict = "tier overhead saved; selector still paid"
    elif local_delta == 0:
        verdict = "selector exactly cancels quotient"
    else:
        verdict = "split is worse than direct"
    return CosetRow(
        arity=arity,
        payload_width=payload_width,
        hidden_bits=hidden_bits,
        records=records,
        direct_bits=direct_bits,
        quotient_bits=quotient_bits,
        selector_bits=selector_bits,
        local_paid_bits=local_paid_bits,
        local_delta=local_delta,
        canonical_supply_tax=canonical_supply_tax,
        referee_bits_99=referee_bits,
        referee_paid_bits=referee_paid,
        referee_delta=referee_delta,
        decode_work_log2=hidden_layer_bits,
        verdict=verdict,
    )


def width_row(arity: int, payload_width: int, records: int) -> WidthRow:
    v1_bits = costs.record_cost_for_payload_width(arity, payload_width)
    raw_width_bits = costs.arity_cost(arity) + payload_width
    width_header_bits = costs.lotus_cost_for_value(payload_width)
    layer_paid = raw_width_bits + width_header_bits / records
    savings = v1_bits - layer_paid
    tier_overhead = costs.j3d1_cost_for_payload_width(payload_width) - payload_width
    if savings > 0.0:
        verdict = "valid layer-packing saving, no supply boost"
    elif abs(savings) < 1e-12:
        verdict = "break-even"
    else:
        verdict = "header amortization too small"
    return WidthRow(
        arity=arity,
        payload_width=payload_width,
        records=records,
        v1_bits=v1_bits,
        raw_width_bits=raw_width_bits,
        width_header_bits=width_header_bits,
        layer_paid_per_record=layer_paid,
        savings_per_record=savings,
        tier_overhead=tier_overhead,
        verdict=verdict,
    )


def print_coset_table(args: argparse.Namespace) -> None:
    widths = parse_int_list(args.payload_width, [8, 16, 32, 64, 128, 256, 508])
    hidden_values = parse_int_list(args.hidden_bits, [1, 2, 4, 8, 16, 32, 64])
    records_values = parse_int_list(args.records, [8, 32, 128])

    print("== H184 quotient/coset witness accounting ==")
    print(
        "direct is exact V1/J3D1. quotient stores W-q bits; selector/referee must recover q hidden bits."
    )
    print(
        f"{'a':>3} {'W':>5} {'q':>4} {'R':>5} {'direct':>7} {'quot':>7} "
        f"{'sel':>5} {'local':>7} {'dLocal':>7} {'canonTax':>8} "
        f"{'ref99':>7} {'dRef':>7} {'work2':>7} {'verdict':<42}"
    )
    for width in widths:
        for hidden in hidden_values:
            if hidden >= width:
                continue
            for records in records_values:
                row = coset_row(args.arity, width, hidden, records, args.target_unique)
                print(
                    f"{row.arity:3d} {row.payload_width:5d} {row.hidden_bits:4d} "
                    f"{row.records:5d} {row.direct_bits:7d} {row.quotient_bits:7d} "
                    f"{row.selector_bits:5d} {row.local_paid_bits:7d} "
                    f"{row.local_delta:7d} {row.canonical_supply_tax:8d} "
                    f"{row.referee_bits_99:7d} {row.referee_delta:7d} "
                    f"{row.decode_work_log2:7d} "
                    f"{row.verdict:<42}"
                )


def print_width_table(args: argparse.Namespace) -> None:
    widths = parse_int_list(args.payload_width, [8, 16, 32, 64, 128, 256, 508])
    records_values = parse_int_list(args.records, [8, 32, 128])

    print()
    print("== public width / layer-rank packing ceiling ==")
    print(
        "This is the honest custom witness mode: declare width once, then store raw ranks."
    )
    print(
        f"{'a':>3} {'W':>5} {'R':>5} {'v1/rec':>7} {'raw/rec':>7} "
        f"{'wHead':>7} {'paid/rec':>9} {'save/rec':>9} {'tier':>5} {'verdict':<38}"
    )
    for width in widths:
        for records in records_values:
            row = width_row(args.arity, width, records)
            print(
                f"{row.arity:3d} {row.payload_width:5d} {row.records:5d} "
                f"{row.v1_bits:7d} {row.raw_width_bits:7d} "
                f"{row.width_header_bits:7d} {fmt(row.layer_paid_per_record):>9} "
                f"{fmt(row.savings_per_record):>9} {row.tier_overhead:5d} "
                f"{row.verdict:<38}"
            )


def print_theorem() -> None:
    print()
    print("== theorem ==")
    print("A quotient witness does not reduce seed entropy by itself.")
    print("Canonical coset members lose q bits of match supply.")
    print("Noncanonical coset members need q selector/referee bits per record plus safety.")
    print("If those bits are a checksum instead of a selector tape, decode has")
    print("to explore about 2^(qR) candidate low-bit assignments for R records.")
    print("Public layer width can remove repeated Lotus width headers, but this")
    print("is a valid packing optimization only; it does not raise witness supply")
    print("or evade the H177/H182 row-mass bound.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--arity", type=int, default=1)
    parser.add_argument("--payload-width", action="append", default=[])
    parser.add_argument("--hidden-bits", action="append", default=[])
    parser.add_argument("--records", action="append", default=[])
    parser.add_argument("--target-unique", type=float, default=0.99)
    args = parser.parse_args()

    print_coset_table(args)
    print_width_table(args)
    print_theorem()


if __name__ == "__main__":
    main()
