#!/usr/bin/env python3
"""H43 - forced-rewrite / near-total-cover target surface.

The user keeps returning to the strongest stateless branch:

    rewrite every atom every pass

If every output unit is a record and every record opens, the birth/open/carry
problem disappears. H43 asks the next scientific question: what exact target
must this branch hit to become positive?

The important unit correction is that Telomere's familiar "about 2 bits per
match" can be discussed in two different regimes:

* current high-arity Total-Cover rows measure selected records; 2 bits/record
  at about 0.009 records/input atom is only about 0.018 bits/input atom;
* an all-atom forced rewrite target would need a paid margin per rewritten
  atom, which is a much stronger premise and gets a much looser exception
  budget.

H43 reports both so they cannot be accidentally mixed.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


def h2(p: float) -> float:
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -(p * math.log2(p) + (1.0 - p) * math.log2(1.0 - p))


def exception_ledger_bits_per_atom(eps: float, passes: int) -> float:
    """Near-total rewrite exception/pass assignment entropy rate.

    Newest/open cohort has mass 1-eps. The exception mass is split among older
    passes. This is the asymptotic multinomial rate:

        H2(eps) + eps log2(P-1)
    """

    if passes <= 1:
        return h2(eps)
    return h2(eps) + eps * math.log2(passes - 1)


def max_eps_for_budget(passes: int, budget_bits_per_atom: float) -> float:
    """Largest eps with exception ledger <= budget_bits_per_atom."""

    lo, hi = 0.0, 0.5
    for _ in range(90):
        mid = (lo + hi) / 2.0
        if exception_ledger_bits_per_atom(mid, passes) <= budget_bits_per_atom:
            lo = mid
        else:
            hi = mid
    return lo


def net_atom_margin(eps: float, passes: int, gain_per_rewritten_atom: float, fallback_overhead: float) -> float:
    return (
        (1.0 - eps) * gain_per_rewritten_atom
        - exception_ledger_bits_per_atom(eps, passes)
        - eps * fallback_overhead
    )


def break_even_eps_for_atom_margin(
    passes: int,
    gain_per_rewritten_atom: float,
    fallback_overhead: float,
) -> float:
    """Largest eps with positive atom-level margin under the optimistic model."""

    lo, hi = 0.0, 0.999999
    for _ in range(90):
        mid = (lo + hi) / 2.0
        if net_atom_margin(mid, passes, gain_per_rewritten_atom, fallback_overhead) > 0.0:
            lo = mid
        else:
            hi = mid
    return lo


def coverage_frontier_bits(block_bits: int, max_arity: int, eps: float) -> float:
    """Approximate D needed so an interior atom has some legal covering interval.

    For a k-atom interval, a seed frontier of 2^D hits with probability roughly
    1-exp(-2^(D-kB)). An interior atom lies in k intervals of arity k. The
    expected hit intensity covering the atom is:

        S = sum_k k * 2^(D-kB)

    and uncovered probability is approximately exp(-S). Solve for eps.

    This is a coverage-only target. It says nothing about whether the chosen
    interval is compressive after the witness stream is paid.
    """

    weight = sum(k * (2.0 ** (-(k * block_bits))) for k in range(1, max_arity + 1))
    return math.log2(math.log(1.0 / eps) / weight)


@dataclass(frozen=True)
class PaidTarget:
    name: str
    records_per_atom: float
    gain_per_atom: float
    missing_bits_per_record: float
    avg_arity: float

    @property
    def missing_bits_per_atom(self) -> float:
        return self.records_per_atom * self.missing_bits_per_record


TARGETS = [
    PaidTarget(
        "H7 raw first-hit delta",
        records_per_atom=0.008789,
        gain_per_atom=-0.011929,
        missing_bits_per_record=1.357,
        avg_arity=113.78,
    ),
    PaidTarget(
        "H9 fixed slack 0",
        records_per_atom=0.009765,
        gain_per_atom=-0.012314,
        missing_bits_per_record=1.261,
        avg_arity=102.40,  # approximate reciprocal of records/atom
    ),
    PaidTarget(
        "H12 perfect-credit UB",
        records_per_atom=0.010987,
        gain_per_atom=-0.008196,
        missing_bits_per_record=0.746,
        avg_arity=91.02,
    ),
]


def print_unit_table() -> None:
    print("== unit sanity: bits/record vs bits/input atom ==")
    print("High arity amortizes records, so a per-record win is much smaller per atom.")
    print(f"{'target':<24} {'rec/atom':>10} {'2b rec -> atom':>15} {'miss/rec':>9} {'miss/atom':>10}")
    for target in TARGETS:
        two_bit_atom = 2.0 * target.records_per_atom
        print(
            f"{target.name:<24} {target.records_per_atom:10.6f} "
            f"{two_bit_atom:15.6f} {target.missing_bits_per_record:9.3f} "
            f"{target.missing_bits_per_atom:10.6f}"
        )
    print()


def print_exception_budget_table() -> None:
    print("== max exception rate payable by current record-level surplus ==")
    print("eps is the non-rewritten/carry fraction. This assumes the exception")
    print("ledger is compared to high-arity records/atom. This is the right unit")
    print("for current H7/H9 measured rows; witness costs must still be paid.")
    print(
        f"{'target':<24} {'surplus/rec':>11} {'P':>6} "
        f"{'budget/atom':>12} {'max eps':>12}"
    )
    for target in TARGETS[:1]:
        for surplus_per_record in (0.5, 1.0, 1.357, 2.0, 4.0, 8.0):
            budget = target.records_per_atom * surplus_per_record
            for passes in (64, 256, 4096):
                eps = max_eps_for_budget(passes, budget)
                print(
                    f"{target.name:<24} {surplus_per_record:11.3f} "
                    f"{passes:6d} {budget:12.6f} {eps:12.8f}"
                )
    print()


def print_atom_margin_break_even_table() -> None:
    print("== optimistic all-atom rewrite margin ==")
    print("If a future mechanism really gives g paid bits per rewritten input atom,")
    print("near-total cover can tolerate much larger exception rates. This is not")
    print("the current H7/H9 unit; it is the all-block target unit.")
    print(f"{'g bits/atom':>11} {'fallback F':>10} {'P':>6} {'max eps':>10} {'coverage':>10}")
    for gain in (0.5, 1.0, 2.0):
        for fallback_overhead in (0.0, 1.0, 3.0, 8.0):
            for passes in (64, 256, 4096):
                eps = break_even_eps_for_atom_margin(passes, gain, fallback_overhead)
                print(
                    f"{gain:11.3f} {fallback_overhead:10.3f} {passes:6d} "
                    f"{eps:10.6f} {100.0 * (1.0 - eps):9.3f}%"
                )
    print()


def print_coverage_frontier_table() -> None:
    print("== frontier needed for coverage, not compression ==")
    print("D here only makes every atom likely to have at least one matching interval.")
    print("It can be much smaller than the D needed for a positive paid witness.")
    print(f"{'B':>4} {'K':>5} {'eps':>9} {'D bits':>10} {'span max bits':>13}")
    for block_bits in (4, 6, 8, 12, 24):
        for max_arity in (5, 16, 64, 128):
            if max_arity == 128 and block_bits == 24:
                continue
            for eps in (0.10, 0.01, 0.001):
                d_bits = coverage_frontier_bits(block_bits, max_arity, eps)
                print(
                    f"{block_bits:4d} {max_arity:5d} {eps:9.3f} "
                    f"{d_bits:10.3f} {block_bits * max_arity:13d}"
                )
    print()


def print_option_count_table() -> None:
    print("== local option-count dividend ==")
    print("An interior atom participates in 1+2+...+K intervals. In the most")
    print("optimistic independent-race view, choosing the best option is worth")
    print("about log2(M) bits before non-overlap and witness costs.")
    print(f"{'K':>5} {'options M':>10} {'ideal log2 M':>13}")
    for max_arity in (5, 8, 16, 24, 32, 48, 64, 96, 128):
        options = max_arity * (max_arity + 1) // 2
        print(f"{max_arity:5d} {options:10d} {math.log2(options):13.3f}")
    print()


def print_per_span_hit_table() -> None:
    print("== per-span hit frontier ==")
    print("For one specific k-atom span, D must sit near k*B just to get a hit.")
    print("This is the search-depth meaning of trying larger bundles.")
    print(f"{'B':>4} {'k':>5} {'span bits':>10} {'p=50% D':>10} {'p=90% D':>10} {'p=99% D':>10}")
    for block_bits, arity in ((4, 5), (4, 128), (8, 5), (8, 128), (24, 5)):
        span_bits = block_bits * arity
        d50 = span_bits + math.log2(-math.log(1.0 - 0.50))
        d90 = span_bits + math.log2(-math.log(1.0 - 0.90))
        d99 = span_bits + math.log2(-math.log(1.0 - 0.99))
        print(
            f"{block_bits:4d} {arity:5d} {span_bits:10d} "
            f"{d50:10.3f} {d90:10.3f} {d99:10.3f}"
        )
    print()


def print_forced_rewrite_equations() -> None:
    print("== forced-rewrite sign equation ==")
    print("For total cover, the sign is roughly:")
    print()
    print("  gain_atom = records_per_atom * margin_per_record - extra_atom_bills")
    print()
    print("where margin_per_record is after arity + seed witness are paid.")
    print("Current closest paid rows have negative margin:")
    for target in TARGETS:
        margin = target.gain_per_atom / target.records_per_atom
        print(f"  {target.name}: margin = {margin:.3f} bits/record")
    print()
    print("Therefore a coverage trick alone is insufficient in the current unit.")
    print("One of these must move:")
    print("  A. witness gap shrinks by about 1.2-1.4 bits/record;")
    print("  B. a public fertility/source law adds > that much value per record;")
    print("  C. record density rises while keeping positive per-record margin;")
    print("  D. exception fraction falls to the tiny eps allowed by the table above.")
    print()


def print_search_depth_interpretation() -> None:
    print("== search-depth interpretation ==")
    print("More D and larger K do two different jobs:")
    print("  coverage: ensure every atom has some interval match, often easy;")
    print("  compression: make the selected paid witness shorter than raw, still hard.")
    print()
    print("The all-block idea correctly removes birth/open entropy. The remaining")
    print("hard target is the paid witness margin, not the existence of any match.")
    print("The current best H7 row needs only 0.011929 bits/atom, but that is")
    print("1.357 bits/selected record because records are so sparse.")
    print()
    print("If a different all-block mechanism gives paid margin per rewritten atom,")
    print("use the atom-level break-even table instead; do not mix the units.")


def main() -> None:
    print_unit_table()
    print_exception_budget_table()
    print_atom_margin_break_even_table()
    print_coverage_frontier_table()
    print_option_count_table()
    print_per_span_hit_table()
    print_forced_rewrite_equations()
    print_search_depth_interpretation()


if __name__ == "__main__":
    main()
