#!/usr/bin/env python3
"""H179 - reachable/generated regime tax.

Public developmental interpreters are real Telomere-like compression mechanisms:
a short root/program can unfold into a larger phenotype, and decode is
stateless. They do not, by themselves, solve arbitrary-content recursion.

If a public interpreter maps G root bits into P phenotype bits, the reachable
set fraction is at most

    rho <= 2 ** (G - P)

For uniform arbitrary data, naming "this file is in the reachable regime" costs
the same entropy deficit:

    source_tax >= P - G

This kernel keeps the generated-class win and the arbitrary-data tax in the same
table so generated positives are not mistaken for roughly-all-data positives.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass


@dataclass(frozen=True)
class Row:
    root_bits: int
    phenotype_bits: int
    records: int
    header_bits: int
    generated_gain: int
    reachable_tax: int
    uniform_net: int
    rho_log2: int


def run_row(root_bits: int, phenotype_bits: int, records: int, header_bits: int) -> Row:
    raw_bits = phenotype_bits * records
    generated_bits = root_bits + header_bits
    generated_gain = raw_bits - generated_bits
    reachable_tax = max(0, raw_bits - root_bits)
    return Row(
        root_bits=root_bits,
        phenotype_bits=phenotype_bits,
        records=records,
        header_bits=header_bits,
        generated_gain=generated_gain,
        reachable_tax=reachable_tax,
        uniform_net=generated_gain - reachable_tax,
        rho_log2=root_bits - raw_bits,
    )


def parse_int_list(raw: str, default: list[int]) -> list[int]:
    if not raw:
        return default
    return [int(part) for part in raw.split(",") if part]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root-bits", default="12,24,64")
    parser.add_argument("--phenotype-bits", type=int, default=128)
    parser.add_argument("--records", default="1,8,64")
    parser.add_argument("--header-bits", type=int, default=0)
    args = parser.parse_args()

    rows = [
        run_row(root_bits, args.phenotype_bits, records, args.header_bits)
        for root_bits in parse_int_list(args.root_bits, [12, 24, 64])
        for records in parse_int_list(args.records, [1, 8, 64])
    ]

    print("== H179 reachable/generated regime tax ==")
    print(
        "generated_gain is real inside the public reachable class; "
        "uniform_net subtracts the reachable-set source tax."
    )
    print(
        f"{'G root':>7} {'P chunk':>7} {'N':>5} {'header':>7} "
        f"{'log2 rho':>10} {'gen_gain':>10} {'tax':>10} {'uniform':>10}"
    )
    for row in rows:
        print(
            f"{row.root_bits:7d} {row.phenotype_bits:7d} {row.records:5d} "
            f"{row.header_bits:7d} {row.rho_log2:10d} {row.generated_gain:10d} "
            f"{row.reachable_tax:10d} {row.uniform_net:10d}"
        )

    print()
    print("== reading ==")
    print(
        "A generated/reachable positive is valid only for data drawn from that "
        "public regime. For arbitrary uniform data, the source tax cancels the "
        "root-vs-phenotype saving, leaving only header/framing cost."
    )


if __name__ == "__main__":
    main()
