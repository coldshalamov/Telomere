#!/usr/bin/env python3
"""H197 - bounded referee / hidden-lane overfull closure.

This kernel tests the last H195-adjacent escape hatch suggested by bounded
ambiguity: let the encoder use an overfull ambiguous witness family, then rely
on a small checksum/referee to make stateless decode unique.

It separates three quantities:

    apparent saving from omitting a selector,
    exact selector entropy for lossless decode,
    checksum/referee bits needed for high-probability uniqueness.

The result is a closure certificate, not a codec proposal.  Exact selectors tie;
checksums need the same log candidate count plus a reliability margin.
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


def parse_int_list(values: list[str], default: list[int]) -> list[int]:
    if not values:
        return default
    out: list[int] = []
    for value in values:
        out.extend(int(part) for part in value.split(",") if part)
    return out


def q_single_lane(max_payload_width: int) -> float:
    total = 0.0
    for payload_width in range(1, max_payload_width + 1):
        count = costs.payload_width_count_exact(payload_width)
        record_bits = costs.record_cost_for_payload_width(1, payload_width)
        total += count * 2.0 ** (-record_bits)
    return total


def checksum_bits_for_uniqueness(log2_candidates: float, target_unique: float) -> float:
    """Return c such that one true candidate among M has P(no false) >= target.

    False candidates pass an ideal c-bit referee with probability 2^-c.
    Exact condition: (1 - 2^-c)^(M-1) >= target.
    For large M, use exp(-(M-1)2^-c).
    """

    if log2_candidates <= 0.0:
        return 0.0
    if not 0.0 < target_unique < 1.0:
        raise ValueError("target_unique must be between 0 and 1")
    # M-1 ~= 2^logM.  The approximation is exact enough for the scaling bill
    # and avoids constructing huge integers.
    return log2_candidates - math.log2(-math.log(target_unique))


@dataclass(frozen=True)
class ToyRow:
    raw_bits: int
    visible_bits: int
    copies: int
    apparent_gain: int
    selector_bits: int
    exact_net: int
    checksum_bits_99: float
    checksum_net_99: float


def toy_row(raw_bits: int, visible_bits: int, copies: int, target_unique: float) -> ToyRow:
    hidden_per = raw_bits - visible_bits
    apparent_gain = hidden_per * copies
    selector_bits = hidden_per * copies
    checksum_bits = checksum_bits_for_uniqueness(selector_bits, target_unique)
    checksum_net = apparent_gain - checksum_bits
    return ToyRow(
        raw_bits=raw_bits,
        visible_bits=visible_bits,
        copies=copies,
        apparent_gain=apparent_gain,
        selector_bits=selector_bits,
        exact_net=apparent_gain - selector_bits,
        checksum_bits_99=checksum_bits,
        checksum_net_99=checksum_net,
    )


@dataclass(frozen=True)
class LaneRow:
    max_payload_width: int
    lanes: int
    q_single: float
    q_paid: float
    q_hidden: float
    apparent_surplus: float
    lane_selector_bits: int
    exact_net: float
    checksum_bits_99: float
    checksum_net_99: float
    records_per_64bit_referee: float


def lane_row(max_payload_width: int, lanes: int, target_unique: float) -> LaneRow:
    q = q_single_lane(max_payload_width)
    lane_bits = 0 if lanes <= 1 else math.ceil(math.log2(lanes))
    q_paid = lanes * q * 2.0 ** (-lane_bits)
    q_hidden = lanes * q
    apparent_surplus = math.log2(q_hidden) if q_hidden > 0.0 else -math.inf
    checksum_bits = checksum_bits_for_uniqueness(lane_bits, target_unique)
    records_per_64 = 64.0 / lane_bits if lane_bits > 0 else math.inf
    return LaneRow(
        max_payload_width=max_payload_width,
        lanes=lanes,
        q_single=q,
        q_paid=q_paid,
        q_hidden=q_hidden,
        apparent_surplus=apparent_surplus,
        lane_selector_bits=lane_bits,
        exact_net=apparent_surplus - lane_bits,
        checksum_bits_99=checksum_bits,
        checksum_net_99=apparent_surplus - checksum_bits,
        records_per_64bit_referee=records_per_64,
    )


def print_toy_table(args: argparse.Namespace) -> None:
    copies_values = parse_int_list(args.copies, [1, 8, 32, 128])
    print("== exact coalescence toy ==")
    print(
        f"{'raw':>4} {'vis':>4} {'R':>5} {'appGain':>8} {'selector':>9} "
        f"{'exactNet':>9} {'c@u':>10} {'chkNet':>10}"
    )
    for copies in copies_values:
        row = toy_row(args.raw_bits, args.visible_bits, copies, args.target_unique)
        print(
            f"{row.raw_bits:4d} {row.visible_bits:4d} {row.copies:5d} "
            f"{row.apparent_gain:8d} {row.selector_bits:9d} {row.exact_net:9d} "
            f"{fmt(row.checksum_bits_99):>10} {fmt(row.checksum_net_99):>10}"
        )


def print_lane_table(args: argparse.Namespace) -> None:
    widths = parse_int_list(args.max_payload_width, [4, 8, 16])
    lanes_values = parse_int_list(args.lanes, [16, 20, 32, 64, 256])
    print()
    print("== hidden-lane H195 overfull bill ==")
    print(
        f"{'Wmax':>5} {'lanes':>6} {'q1':>9} {'qPaid':>9} {'qHidden':>9} "
        f"{'surplus':>9} {'laneBits':>8} {'exactNet':>10} "
        f"{'c@u':>10} {'chkNet':>10} {'R@64':>8}"
    )
    best: LaneRow | None = None
    for width in widths:
        for lanes in lanes_values:
            row = lane_row(width, lanes, args.target_unique)
            if best is None or row.exact_net > best.exact_net:
                best = row
            print(
                f"{row.max_payload_width:5d} {row.lanes:6d} "
                f"{fmt(row.q_single):>9} {fmt(row.q_paid):>9} "
                f"{fmt(row.q_hidden):>9} {fmt(row.apparent_surplus):>9} "
                f"{row.lane_selector_bits:8d} {fmt(row.exact_net):>10} "
                f"{fmt(row.checksum_bits_99):>10} {fmt(row.checksum_net_99):>10} "
                f"{fmt(row.records_per_64bit_referee):>8}"
            )
    if best is not None:
        print()
        print(
            "best hidden-lane exact net: "
            f"{fmt(best.exact_net)} at W={best.max_payload_width},lanes={best.lanes}"
        )


def print_theorem(args: argparse.Namespace) -> None:
    margin = -math.log2(-math.log(args.target_unique))
    print()
    print("== theorem ==")
    print("Overfull ambiguity can create apparent surplus only by leaving")
    print("multiple possible decodes. Exact lossless decode needs the missing")
    print("selector entropy back. A checksum/referee that targets uniqueness")
    print(f"{args.target_unique:.6f} needs about log2(M)+{fmt(margin)} bits,")
    print("so fixed referee bits buy only a bounded finite toy.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-bits", type=int, default=2)
    parser.add_argument("--visible-bits", type=int, default=1)
    parser.add_argument("--copies", action="append", default=[])
    parser.add_argument("--max-payload-width", action="append", default=[])
    parser.add_argument("--lanes", action="append", default=[])
    parser.add_argument("--target-unique", type=float, default=0.99)
    args = parser.parse_args()

    if args.visible_bits > args.raw_bits:
        raise SystemExit("--visible-bits cannot exceed --raw-bits")
    print("== H197 bounded referee / hidden-lane overfull closure ==")
    print_toy_table(args)
    print_lane_table(args)
    print_theorem(args)


if __name__ == "__main__":
    main()
