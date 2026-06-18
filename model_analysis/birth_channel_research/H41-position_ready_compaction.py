#!/usr/bin/env python3
"""H41 - position / ready-prefix / compaction channel ledger.

This is the user's "maybe position tells the decoder what is ready" lane.
It prices four related tricks without hash-search luck:

1. ready records are moved to a prefix and a short boundary is stored;
2. records are grouped by birth/pass cohort and only cohort counts are stored;
3. final board positions or orbit phase are used as salt/birth witnesses;
4. records decode out of order and settle by a public canonical rule.

The useful constructive boundary is rare exceptions: if almost every atom is
rewritten, the paid ready/carry ledger is H(epsilon) per atom, not one tag per
atom. That is a real target for Total-Cover / Near-Total-Cover, but the entropy
does not disappear; it becomes small only when the non-rewritten set is small.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


def log2_choose(n: int, k: int) -> float:
    if k < 0 or k > n:
        return float("-inf")
    return (math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)) / math.log(2)


def log2_perm(n: int, k: int) -> float:
    if k < 0 or k > n:
        return float("-inf")
    return (math.lgamma(n + 1) - math.lgamma(n - k + 1)) / math.log(2)


def entropy(probs: list[float]) -> float:
    return -sum(p * math.log2(p) for p in probs if p > 0)


def binary_entropy(p: float) -> float:
    return entropy([p, 1.0 - p])


def log2_multinomial(counts: list[int]) -> float:
    n = sum(counts)
    return (math.lgamma(n + 1) - sum(math.lgamma(c + 1) for c in counts)) / math.log(2)


@dataclass(frozen=True)
class ReadyRow:
    n: int
    ready_fraction: float
    ready: int
    boundary_bits: float
    subset_bits: float
    bits_per_ready: float
    net_per_ready_if_two_bit_win: float


def ready_prefix_rows() -> list[ReadyRow]:
    rows: list[ReadyRow] = []
    for n in (1_000, 1_000_000):
        for r in (0.01, 0.10, 0.50, 0.75, 0.90, 0.99, 0.999):
            ready = max(1, min(n - 1, round(n * r)))
            boundary_bits = math.log2(n + 1)
            subset_bits = log2_choose(n, ready)
            bits_per_ready = subset_bits / ready
            rows.append(
                ReadyRow(
                    n=n,
                    ready_fraction=ready / n,
                    ready=ready,
                    boundary_bits=boundary_bits,
                    subset_bits=subset_bits,
                    bits_per_ready=bits_per_ready,
                    net_per_ready_if_two_bit_win=2.0 - bits_per_ready,
                )
            )
    return rows


@dataclass(frozen=True)
class CohortRow:
    n: int
    passes: int
    old_fraction: float
    counts_bits: float
    assignment_bits: float
    bits_per_atom: float
    net_per_atom_if_two_bit_win: float


def cohort_rows() -> list[CohortRow]:
    """Birth-pass cohorts sorted into runs.

    Counts are cheap. The assignment of original stream slots to cohorts is the
    hidden stable-unpartition unless cohort membership is public or almost all
    atoms are in one cohort.
    """

    rows: list[CohortRow] = []
    n = 1_000_000
    for passes in (8, 64, 256):
        # Equal cohorts: maximum entropy among P-way cohort ledgers.
        equal = [n // passes] * passes
        equal[-1] += n - sum(equal)
        counts_bits = log2_choose(n + passes - 1, passes - 1)
        assignment_bits = log2_multinomial(equal)
        rows.append(
            CohortRow(
                n=n,
                passes=passes,
                old_fraction=1.0 - (max(equal) / n),
                counts_bits=counts_bits,
                assignment_bits=assignment_bits,
                bits_per_atom=assignment_bits / n,
                net_per_atom_if_two_bit_win=2.0 - assignment_bits / n,
            )
        )

        # Near-total rewrite: newest cohort has 1-epsilon mass, older passes
        # split the exception mass. This is the one constructive opening.
        for eps in (0.10, 0.01, 0.001):
            newest = round(n * (1.0 - eps))
            old_total = n - newest
            counts = [old_total // (passes - 1)] * (passes - 1) + [newest]
            for i in range(old_total % (passes - 1)):
                counts[i] += 1
            assignment_bits = log2_multinomial(counts)
            rows.append(
                CohortRow(
                    n=n,
                    passes=passes,
                    old_fraction=eps,
                    counts_bits=counts_bits,
                    assignment_bits=assignment_bits,
                    bits_per_atom=assignment_bits / n,
                    net_per_atom_if_two_bit_win=2.0 - assignment_bits / n,
                )
            )
    return rows


@dataclass(frozen=True)
class BoardRow:
    q: int
    records: int
    coord_bits_per_record: float
    unordered_holes_per_record: float
    ordered_positions_per_record: float
    observed_after_compaction_capacity: float


def board_rows() -> list[BoardRow]:
    rows: list[BoardRow] = []
    for q, r in ((1_000_000, 100_000), (1_000_000, 900_000), (10_000_000, 100_000)):
        rows.append(
            BoardRow(
                q=q,
                records=r,
                coord_bits_per_record=math.log2(q),
                unordered_holes_per_record=log2_choose(q, r) / r,
                ordered_positions_per_record=log2_perm(q, r) / r,
                observed_after_compaction_capacity=0.0,
            )
        )
    return rows


def prefix_capacity_rows() -> list[tuple[int, int, int, float, float]]:
    """How many per-record birth choices can a single boundary carry?"""

    out: list[tuple[int, int, int, float, float]] = []
    for n in (1_000, 1_000_000):
        for ready in (10, 1_000, 100_000):
            if ready <= n:
                boundary = math.log2(n + 1)
                bits_per_ready = boundary / ready
                equivalent_passes = 2 ** bits_per_ready
                out.append((n, ready, round(boundary), bits_per_ready, equivalent_passes))
    return out


def self_destination_rows() -> list[tuple[int, int, int, int]]:
    """Demanding destination bits from the hash output spends match supply."""

    rows: list[tuple[int, int, int, int]] = []
    payload_bits = 64
    search_bits = 80
    for placement_bits in (0, 8, 16, 24, 32):
        log2_expected_hits = search_bits - payload_bits - placement_bits
        rows.append((payload_bits, search_bits, placement_bits, log2_expected_hits))
    return rows


def print_ready_prefix_table() -> None:
    print("== ready-prefix boundary vs hidden ready subset ==")
    print("Boundary-only is cheap only if ready membership is public. If the encoder")
    print("chose which slots were ready, the inverse stable partition costs log2 C(N,R).")
    print(f"{'N':>9} {'ready%':>8} {'R':>9} {'boundary':>10} {'subset/R':>10} {'net@2b':>9}")
    for row in ready_prefix_rows():
        if row.n == 1_000_000 or row.ready_fraction in (0.1, 0.5, 0.9):
            print(
                f"{row.n:9d} {100*row.ready_fraction:7.3f}% {row.ready:9d} "
                f"{row.boundary_bits:10.3f} {row.bits_per_ready:10.6f} "
                f"{row.net_per_ready_if_two_bit_win:9.6f}"
            )
    print()


def print_cohort_table() -> None:
    print("== birth/pass cohorts sorted into runs ==")
    print("Counts/delineations are cheap. Original slot-to-cohort assignment is the bill.")
    print("Near-total rewrite makes this bill small; equal cohorts cost about log2(P).")
    print(f"{'P':>5} {'old frac':>9} {'count bits':>11} {'assign bits/atom':>17} {'net@2b':>9}")
    for row in cohort_rows():
        print(
            f"{row.passes:5d} {row.old_fraction:9.3f} {row.counts_bits:11.3f} "
            f"{row.bits_per_atom:17.6f} {row.net_per_atom_if_two_bit_win:9.6f}"
        )
    print()


def print_board_table() -> None:
    print("== final board / coordinate observations ==")
    print("If the wire is compacted, final positions 0..R-1 carry no extra channel.")
    print("If board holes/coordinates are observable, their entropy is a paid position note.")
    print(f"{'Q':>10} {'R':>9} {'log2Q':>8} {'holes/R':>10} {'ordered/R':>10} {'compact cap':>11}")
    for row in board_rows():
        print(
            f"{row.q:10d} {row.records:9d} {row.coord_bits_per_record:8.3f} "
            f"{row.unordered_holes_per_record:10.6f} "
            f"{row.ordered_positions_per_record:10.6f} "
            f"{row.observed_after_compaction_capacity:11.3f}"
        )
    print()


def print_prefix_capacity_table() -> None:
    print("== single-boundary capacity ==")
    print("A boundary has log2(N+1) total bits. Spread over many records it cannot")
    print("name a per-record birth pass except in tiny R cases.")
    print(f"{'N':>9} {'R':>9} {'boundary':>9} {'bits/R':>10} {'equiv T':>10}")
    for n, ready, boundary, bits_per_ready, equivalent_passes in prefix_capacity_rows():
        print(
            f"{n:9d} {ready:9d} {boundary:9d} "
            f"{bits_per_ready:10.6f} {equivalent_passes:10.6f}"
        )
    print()


def print_orbit_hinge() -> None:
    print("== orbit / relative-position hinge ==")
    print("Single-speed public shuffle: final_pos = sigma^P(x), independent of birth t.")
    print("  Capacity about birth from position: 0 bits.")
    print("Freeze/slow-after-birth: final_pos = sigma^(P-t)(x), so phase can name t.")
    print("  But then position is a birth ledger: about log2(P) bits/record of board")
    print("  capacity, plus reverse decode must know live/frozen state to invert motion.")
    print("  If the final coordinates are not transmitted/observable, the channel is absent.")
    print()


def print_self_destination_table() -> None:
    print("== seed-derived destination / placement salt ==")
    print("If omitted placement bits are demanded from hash expansion, expected hits")
    print("fall by the same number of bits. This is match-supply payment.")
    print(f"{'payload':>8} {'search':>8} {'place':>8} {'log2 E_hits':>13}")
    for payload, search, placement, log_hits in self_destination_rows():
        print(f"{payload:8d} {search:8d} {placement:8d} {log_hits:13d}")
    print()


def main() -> None:
    print_ready_prefix_table()
    print_cohort_table()
    print_board_table()
    print_prefix_capacity_table()
    print_orbit_hinge()
    print_self_destination_table()
    print("SUMMARY:")
    print("  Position/compaction is excellent stateless decode machinery, not a free")
    print("  arbitrary subset channel. The constructive target is near-total cover:")
    print("  when exceptions are rare, H(exception) can be far below 2 bits/record.")


if __name__ == "__main__":
    main()
