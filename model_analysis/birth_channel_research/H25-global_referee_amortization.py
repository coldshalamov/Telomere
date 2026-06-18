#!/usr/bin/env python3
"""Global referee/checksum amortization ledger.

Trial decode plus a checksum can be a real finite resource: a C-bit referee can
select one reading out of about 2^C candidates. The question is whether this
amortizes birth/open/pass/status information across many records.

If each record leaves M candidate readings after structural pruning, R records
leave about M^R joint readings. A checksum with false-accept probability
epsilon must satisfy:

    C >= R * log2(M) + log2(1/epsilon)

So fixed C buys a finite reach, but scaling requires the same per-record bits.
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass


@dataclass(frozen=True)
class RefereeRow:
    passes: int
    structural_bits: float
    checksum_bits: int
    safety_bits: float
    candidates_per_record: float
    referee_bits_per_record: float
    max_records_at_checksum: float
    cost_at_1000_records: float
    log2_false_accepts_at_1000_records: float


def candidates_per_record(passes: int, structural_bits: float) -> float:
    """Expected candidate multiplicity after an E-bit structural filter."""

    if passes <= 1:
        return 1.0
    q = 2.0 ** (-structural_bits)
    return 1.0 + (passes - 1) * q


def row(passes: int, structural_bits: float, checksum_bits: int, safety_bits: float, scale_records: int) -> RefereeRow:
    m = candidates_per_record(passes, structural_bits)
    per = math.log2(m)
    budget = max(0.0, checksum_bits - safety_bits)
    max_records = math.inf if per <= 0.0 else budget / per
    required = scale_records * per + safety_bits
    # log2 expected false accepts if only checksum_bits are available.
    log2_false_accepts = scale_records * per - checksum_bits
    return RefereeRow(
        passes=passes,
        structural_bits=structural_bits,
        checksum_bits=checksum_bits,
        safety_bits=safety_bits,
        candidates_per_record=m,
        referee_bits_per_record=per,
        max_records_at_checksum=max_records,
        cost_at_1000_records=required,
        log2_false_accepts_at_1000_records=log2_false_accepts,
    )


def fmt(value: float) -> str:
    if math.isinf(value):
        return "inf"
    if value == 0.0:
        return "0"
    if abs(value) >= 1_000_000 or abs(value) < 0.001:
        return f"{value:.3e}"
    return f"{value:.6g}"


def render(rows: list[RefereeRow], scale_records: int) -> str:
    lines = [
        "# Global Referee Amortization Ledger",
        "",
        "A checksum/referee is a finite global selector. It is useful below its",
        "candidate capacity and becomes the same per-record bill above it.",
        "",
        f"`scale_records = {scale_records}` for the required-width and false-accept columns.",
        "",
        "| passes T | structural E bits | checksum C | candidates/record M | bits/record log2 M | max records under C | required bits at scale | log2 expected false accepts at scale with C |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in rows:
        lines.append(
            f"| {item.passes} | {item.structural_bits:.3f} | {item.checksum_bits} | "
            f"{fmt(item.candidates_per_record)} | {fmt(item.referee_bits_per_record)} | "
            f"{fmt(item.max_records_at_checksum)} | {fmt(item.cost_at_1000_records)} | "
            f"{fmt(item.log2_false_accepts_at_1000_records)} |"
        )

    lines.extend(
        [
            "",
            "## Reading",
            "",
            "For singles, `E=0`, so `M=T` and the bill is exactly `log2(T)`",
            "bits per record. For length-pinned bundles, `E>0` gives a finite",
            "free-looking window while `T << 2^E`; once `T` exceeds that knee,",
            "the per-record bill approaches `log2(T)-E`.",
            "",
            "A fixed checksum can validate small demonstrations because the",
            "candidate entropy is below the checksum width. It cannot maintain",
            "arbitrary-pass/stateless decode across growing files unless the",
            "checksum/referee grows with the candidate entropy.",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--passes", type=int, nargs="+", default=[4, 16, 64, 256, 1024, 65536])
    parser.add_argument("--structural-bits", type=float, nargs="+", default=[0.0, 2.5, 9.36, 12.59, 18.20])
    parser.add_argument("--checksum-bits", type=int, nargs="+", default=[64, 128, 256])
    parser.add_argument("--safety-bits", type=float, default=32.0)
    parser.add_argument("--scale-records", type=int, default=1000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = [
        row(passes, structural, checksum, args.safety_bits, args.scale_records)
        for checksum in args.checksum_bits
        for structural in args.structural_bits
        for passes in args.passes
    ]
    print(render(rows, args.scale_records))


if __name__ == "__main__":
    main()
