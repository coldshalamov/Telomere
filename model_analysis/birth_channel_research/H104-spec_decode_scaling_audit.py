#!/usr/bin/env python3
"""H104 - SPEC_V1 trial-decode scaling audit.

Current SPEC_V1 says position salts are self-presenting and the decoder uses
"keep what decodes" with a fixed checksum referee. The proof artifacts show
small round trips. GOLDEN_CONFIG/MATH_MODEL_V1 also say trial-decode ambiguity
is the open scaling bill.

This kernel reconciles those claims without running a huge DFS:

* keep-what-decodes is a valid finite decoder when the checksum/referee can
  isolate the true reading;
* a syntactic arity-1 record carried across T reverse walks has T possible
  structurally valid opening times under position salt;
* R such records give S = T^R readings before the checksum;
* a fixed C-bit checksum can referee only finite R*log2(T) bits of ambiguity.

It is a scaling audit, not a rejection of the toy round-trip proofs.
"""

from __future__ import annotations

import math


def h2(p: float) -> float:
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -(p * math.log2(p) + (1.0 - p) * math.log2(1.0 - p))


def survivor_bits(records: int, passes: int) -> float:
    if records <= 0 or passes <= 1:
        return 0.0
    return records * math.log2(passes)


def max_records_for_referee(passes: int, checksum_bits: int, safety_bits: int = 0) -> float:
    effective = checksum_bits - safety_bits
    if effective <= 0:
        return 0.0
    if passes <= 1:
        return math.inf
    return effective / math.log2(passes)


def collision_risk_bits(survivor_log2: float, checksum_bits: int) -> float:
    """Union-bound expected false checksum winners as log2 expectation."""

    return survivor_log2 - checksum_bits


def print_referee_table() -> None:
    print("== fixed-checksum referee capacity ==")
    print("Rmax is the number of independent carried records a C-bit checksum can referee.")
    print(f"{'T passes':>8} {'log2T':>8} {'Rmax C64':>10} {'Rmax C64-32safe':>16} {'net@2b/rec':>11}")
    for passes in (2, 4, 8, 16, 32, 64, 256, 4096):
        l2 = math.log2(passes)
        r64 = max_records_for_referee(passes, 64)
        r32 = max_records_for_referee(passes, 64, 32)
        net = 2.0 - l2
        print(f"{passes:8d} {l2:8.3f} {r64:10.3f} {r32:16.3f} {net:11.3f}")
    print()


def print_scale_examples() -> None:
    print("== survivor growth examples ==")
    print("S = T^R readings before checksum for carried arity-1 records.")
    print(f"{'T':>6} {'R':>8} {'log2 S':>12} {'log2 false@C64':>16} {'64-bit enough?':>15}")
    for passes, records in (
        (16, 10),
        (16, 100),
        (64, 10),
        (64, 100),
        (64, 1_000),
        (256, 100),
        (4096, 100),
    ):
        bits = survivor_bits(records, passes)
        false_bits = collision_risk_bits(bits, 64)
        enough = "yes" if bits <= 64 else "no"
        print(f"{passes:6d} {records:8d} {bits:12.3f} {false_bits:16.3f} {enough:>15}")
    print()


def print_near_total_exception_table() -> None:
    print("== near-total exception reading ==")
    print("If only eps fraction of records carry ambiguously, referee bits per atom are")
    print("H(eps)+eps*log2(T-1). This is H41/H43-style exception pricing.")
    print(f"{'T':>6} {'eps':>8} {'bits/atom':>12} {'records C64 covers @N=1e6':>25}")
    for passes in (64, 256, 4096):
        for eps in (0.1, 0.01, 0.001):
            bits = h2(eps) + eps * math.log2(passes - 1)
            covered_atoms = 64 / bits if bits > 0.0 else math.inf
            print(f"{passes:6d} {eps:8.3f} {bits:12.6f} {covered_atoms:25.1f}")
        print()


def print_reading() -> None:
    print("== reading ==")
    print(
        "The small proof artifacts can both be true and incomplete for scale: "
        "they demonstrate that a checksum-refereed keep-what-decodes rule can "
        "find the right reading in small cases, not that the number of readings "
        "stays bounded for arbitrary files and passes."
    )
    print(
        "Position salt is self-presenting only for a record opened on the reverse "
        "step corresponding to its birth state. If the record is carried through "
        "later states, opening it at a wrong state still yields a syntactically "
        "valid item stream in the arity-1 worst case; only the final checksum "
        "distinguishes the bytes."
    )
    print(
        "Therefore fixed-checksum trial decode is a finite referee budget, not "
        "an unbounded free birth channel. To make arbitrary-pass stateless "
        "recursion scale, the design still needs one of: total-cover/all-open, "
        "public two-epoch lanes with mandatory refresh, or a proved invariant "
        "that bounds survivor readings independently of record count."
    )


def main() -> None:
    print_referee_table()
    print_scale_examples()
    print_near_total_exception_table()
    print_reading()


if __name__ == "__main__":
    main()
