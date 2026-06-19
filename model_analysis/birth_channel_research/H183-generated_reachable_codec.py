#!/usr/bin/env python3
"""H183 - generated/reachable recursive positive control.

This is the honest bounded/generated branch.

It proves a positive construction exists for a source-shaped reachable regime:
a fixed public developmental expander maps a short root to a much larger final
phenotype.  Decode is stateless: read the root witness and pass count, expand
deterministically, and compare the final bytes if desired.

It also prices why this does not solve arbitrary content.  If G root bits reach
N phenotype bits injectively, the reachable fraction is at most 2^(G-N).  For a
uniform arbitrary source, membership costs N-G bits, cancelling the root saving
apart from mode/header costs.
"""

from __future__ import annotations

import argparse
import hashlib
import math
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model_analysis.proof_kernel import costs


MODE_BITS = 1


def fmt(value: float) -> str:
    if math.isinf(value):
        return "inf" if value > 0 else "-inf"
    if math.isnan(value):
        return "nan"
    if value == 0.0:
        return "0"
    if abs(value) >= 10_000.0 or abs(value) < 0.0001:
        return f"{value:.3e}"
    return f"{value:.6f}"


def int_to_bytes(value: int, bit_width: int) -> bytes:
    return value.to_bytes((bit_width + 7) // 8, "big")


def expand_bits(label: bytes, out_bits: int) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) * 8 < out_bits:
        digest = hashlib.blake2b(digest_size=32)
        digest.update(label)
        digest.update(counter.to_bytes(8, "big"))
        out.extend(digest.digest())
        counter += 1
    extra_bits = len(out) * 8 - out_bits
    if extra_bits:
        out[-1] &= (0xFF << extra_bits) & 0xFF
    return bytes(out)


def develop(root: int, root_bits: int, passes: int, base_bits: int, growth: int) -> bytes:
    """Recursive public expander.

    Each pass increases the target phenotype width by ``growth`` and uses the
    previous state digest as the next state label.  The final output is the last
    state truncated to ``base_bits * growth**passes`` bits.
    """

    state_bits = base_bits
    state = expand_bits(b"H183-root\0" + int_to_bytes(root, root_bits), state_bits)
    for pass_index in range(1, passes + 1):
        state_bits *= growth
        state = expand_bits(b"H183-pass\0" + pass_index.to_bytes(4, "big") + state, state_bits)
    return state


def phenotype_bits(base_bits: int, growth: int, passes: int) -> int:
    return base_bits * (growth**passes)


def paid_root_bits(root_bits: int, passes: int, include_pass_count: bool) -> int:
    root_record = costs.record_cost_for_payload_width(1, root_bits)
    pass_header = costs.lotus_cost_for_value(passes) if include_pass_count else 0
    return MODE_BITS + root_record + pass_header


@dataclass(frozen=True)
class Row:
    root_bits: int
    base_bits: int
    growth: int
    passes: int
    out_bits: int
    paid_bits: int
    inside_gain: int
    reachable_tax: int
    uniform_net: int
    support_log2: int
    log2_len_ratio: float
    unique_roots: int
    roots_tested: int
    roundtrip_ok: bool


def run_row(root_bits: int, base_bits: int, growth: int, passes: int, include_pass_count: bool) -> Row:
    out_bits = phenotype_bits(base_bits, growth, passes)
    paid_bits = paid_root_bits(root_bits, passes, include_pass_count)
    inside_gain = out_bits - paid_bits
    reachable_tax = out_bits - root_bits
    uniform_net = inside_gain - reachable_tax
    roots = 1 << root_bits
    seen: set[bytes] = set()
    for root in range(roots):
        seen.add(develop(root, root_bits, passes, base_bits, growth))
    sample_root = min(roots - 1, roots // 3)
    phenotype = develop(sample_root, root_bits, passes, base_bits, growth)
    roundtrip_ok = phenotype == develop(sample_root, root_bits, passes, base_bits, growth)
    return Row(
        root_bits=root_bits,
        base_bits=base_bits,
        growth=growth,
        passes=passes,
        out_bits=out_bits,
        paid_bits=paid_bits,
        inside_gain=inside_gain,
        reachable_tax=reachable_tax,
        uniform_net=uniform_net,
        support_log2=root_bits - out_bits,
        log2_len_ratio=math.log2(paid_bits / out_bits),
        unique_roots=len(seen),
        roots_tested=roots,
        roundtrip_ok=roundtrip_ok,
    )


def default_rows(include_pass_count: bool) -> list[Row]:
    configs = [
        (8, 16, 2, 2),
        (8, 16, 2, 4),
        (12, 32, 2, 4),
        (12, 32, 2, 6),
        (16, 64, 2, 6),
    ]
    return [run_row(*config, include_pass_count=include_pass_count) for config in configs]


def print_table(rows: list[Row]) -> None:
    print("== H183 generated/reachable recursive positive control ==")
    print(
        "Paid bits use exact V1/J3D1 root record cost plus optional Lotus pass count. "
        "Uniform net subtracts reachable-set membership tax."
    )
    print(
        f"{'G':>4} {'base':>6} {'g':>3} {'P':>3} {'out':>8} {'paid':>6} "
        f"{'gain_in':>8} {'tax':>8} {'u_net':>7} {'log2sup':>8} "
        f"{'log2len':>9} {'unique':>9} {'rt':>4}"
    )
    for row in rows:
        print(
            f"{row.root_bits:4d} {row.base_bits:6d} {row.growth:3d} {row.passes:3d} "
            f"{row.out_bits:8d} {row.paid_bits:6d} {row.inside_gain:8d} "
            f"{row.reachable_tax:8d} {row.uniform_net:7d} {row.support_log2:8d} "
            f"{fmt(row.log2_len_ratio):>9} "
            f"{row.unique_roots:5d}/{row.roots_tested:<3d} {str(row.roundtrip_ok):>4}"
        )


def print_spec(include_pass_count: bool) -> None:
    print()
    print("== exact decode spec ==")
    print("Header: fixed mode tag for H183 generated regime.")
    print("Record: [arity=1][root witness] using exact V1/J3D1 cost.")
    if include_pass_count:
        print("Header also stores pass count as Lotus(value=P).")
    else:
        print("Pass count is fixed by the public bounded regime.")
    print("Decode: develop(root,G,P,base,growth) with the public BLAKE2b counter expander.")
    print("No carried records, open/carry map, birth-pass map, or final-position map is used.")


def print_theorem() -> None:
    print()
    print("== theorem ==")
    print("Inside the generated class, this is real stateless recursive compression.")
    print("For arbitrary uniform data, the reachable fraction is at most 2^(G-N),")
    print("so the membership tax N-G cancels the root-vs-phenotype gain.")
    print("This is a valid source-shaped/DNA-like branch, not an all-content solution.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixed-pass-count", action="store_true")
    args = parser.parse_args()
    include_pass_count = not args.fixed_pass_count

    rows = default_rows(include_pass_count)
    print_table(rows)
    print_spec(include_pass_count)
    print_theorem()


if __name__ == "__main__":
    main()
