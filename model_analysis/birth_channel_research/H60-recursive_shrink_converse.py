#!/usr/bin/env python3
"""H60 - recursive shrink converse and EOF one-to-one length ledger.

This ledger quantifies the "roughly all data" target for stateless recursive
lossless coding.

Prefix/public normalized codes obey the usual Kraft bound:

    fraction saving >= S bits <= 2^-S

EOF / file-length-delimited one-to-one codes are different for a single known
input length n. There are 2^n - 1 binary strings shorter than n, so one can
inject almost every n-bit input into a shorter output if n is known externally.
That is a real one-shot non-prefix effect.

The recursive catch is that the inverse codebook depends on the previous layer
length. If savings vary across passes, the decoder needs the intermediate
length path. Final length + root length + pass count leave:

    C(S-1, P-1)

positive-saving paths for total saving S over P passes. That path entropy is a
hidden channel unless derived by invariant or paid.
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass


@dataclass(frozen=True)
class FractionRow:
    n_bits: int
    saving_bits: int
    prefix_fraction: float
    eof_one_shot_fraction: float
    exact_length_fraction: float


@dataclass(frozen=True)
class RecursiveRow:
    passes: int
    total_saving: int
    path_bits: float
    net_after_path: float
    prefix_fraction: float
    eof_one_shot_fraction: float
    exact_one_bit_each_fraction: float


@dataclass(frozen=True)
class ExactTinyRow:
    n_bits: int
    passes: int
    saving_per_pass: int
    total_saving: int
    total_inputs: int
    prefix_count: int
    eof_count: int
    raw_fallback_count: int
    uncharged_best_of_count: int
    paid_best_of_count: int
    checksum_refereed_count: int
    checksum_bits_still_owed: float


@dataclass(frozen=True)
class PriorLiftRow:
    saving_bits: int
    desired_coverage: float
    max_uniform_coverage: float
    required_lift: float
    binary_kl_deficit_bits: float


def log2_comb(n: int, k: int) -> float:
    if k < 0 or k > n:
        return float("-inf")
    return (
        math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)
    ) / math.log(2.0)


def eof_fraction(n_bits: int, saving_bits: int) -> float:
    if saving_bits <= 0:
        return 1.0
    if saving_bits > n_bits:
        return 0.0
    # Count output strings of length <= n-saving.
    return (2.0 ** (1 - saving_bits)) - (2.0 ** (-n_bits))


def eof_count(n_bits: int, saving_bits: int) -> int:
    if saving_bits <= 0:
        return 2**n_bits
    if saving_bits > n_bits:
        return 0
    max_len = n_bits - saving_bits
    return (1 << (max_len + 1)) - 1


def fraction_rows(n_values: list[int], saving_values: list[int]) -> list[FractionRow]:
    rows: list[FractionRow] = []
    for n_bits in n_values:
        for saving in saving_values:
            rows.append(
                FractionRow(
                    n_bits=n_bits,
                    saving_bits=saving,
                    prefix_fraction=2.0 ** (-saving),
                    eof_one_shot_fraction=min(1.0, eof_fraction(n_bits, saving)),
                    exact_length_fraction=2.0 ** (-saving) if saving <= n_bits else 0.0,
                )
            )
    return rows


def recursive_rows(pass_values: list[int], saving_per_pass_values: list[float]) -> list[RecursiveRow]:
    rows: list[RecursiveRow] = []
    n_proxy = 1_000_000
    for passes in pass_values:
        for saving_per_pass in saving_per_pass_values:
            total = max(passes, int(round(passes * saving_per_pass)))
            path_bits = 0.0 if passes <= 1 else log2_comb(total - 1, passes - 1)
            rows.append(
                RecursiveRow(
                    passes=passes,
                    total_saving=total,
                    path_bits=path_bits,
                    net_after_path=total - path_bits,
                    prefix_fraction=2.0 ** (-total),
                    eof_one_shot_fraction=eof_fraction(n_proxy, total),
                    exact_one_bit_each_fraction=2.0 ** (-passes),
                )
            )
    return rows


def exact_tiny_row(
    n_bits: int,
    passes: int,
    saving_per_pass: int,
    raw_r: int,
    profiles: int,
    checksum_effective_bits: float,
) -> ExactTinyRow:
    total = 1 << n_bits
    total_saving = passes * saving_per_pass
    prefix_count = 0 if total_saving > n_bits else 1 << (n_bits - total_saving)
    eof_slots = min(total, eof_count(n_bits, total_saving))

    raw_bound = 0.0
    if raw_r > 0:
        denominator = (2.0**total_saving) - (2.0 ** (-raw_r))
        raw_bound = total * (1.0 - 2.0 ** (-raw_r)) / denominator
    raw_count = min(total, max(0, math.floor(raw_bound)))

    effective_profiles = max(1, profiles)
    uncharged = min(total, effective_profiles * prefix_count)
    paid = prefix_count
    referee_profiles = min(effective_profiles, int(2 ** math.floor(checksum_effective_bits)))
    checksum_count = min(total, referee_profiles * prefix_count)
    owed = max(0.0, math.log2(effective_profiles) - checksum_effective_bits)

    return ExactTinyRow(
        n_bits=n_bits,
        passes=passes,
        saving_per_pass=saving_per_pass,
        total_saving=total_saving,
        total_inputs=total,
        prefix_count=prefix_count,
        eof_count=eof_slots,
        raw_fallback_count=raw_count,
        uncharged_best_of_count=uncharged,
        paid_best_of_count=paid,
        checksum_refereed_count=checksum_count,
        checksum_bits_still_owed=owed,
    )


def binary_kl(c: float, p: float) -> float:
    if c <= 0.0:
        return -math.log2(1.0 - p) if p < 1.0 else float("inf")
    if c >= 1.0:
        return -math.log2(p) if p > 0.0 else float("inf")
    if p <= 0.0 or p >= 1.0:
        return float("inf")
    return c * math.log2(c / p) + (1.0 - c) * math.log2((1.0 - c) / (1.0 - p))


def prior_lift_rows(saving_values: list[int], desired_coverages: list[float]) -> list[PriorLiftRow]:
    rows: list[PriorLiftRow] = []
    for saving in saving_values:
        p = 2.0 ** (-saving)
        for coverage in desired_coverages:
            lift = coverage / p if p > 0.0 else float("inf")
            rows.append(
                PriorLiftRow(
                    saving_bits=saving,
                    desired_coverage=coverage,
                    max_uniform_coverage=p,
                    required_lift=lift,
                    binary_kl_deficit_bits=binary_kl(coverage, p),
                )
            )
    return rows


def fmt_prob(value: float) -> str:
    if value == 0.0:
        return "0"
    if value >= 0.001:
        return f"{value:.6f}"
    return f"{value:.3e}"


def render_fraction(rows: list[FractionRow]) -> list[str]:
    lines = [
        "## One-Shot Fraction Bounds",
        "",
        "| n bits | saving S | prefix bound | EOF one-shot bound | exact-length output bound |",
        "| ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row.n_bits} | {row.saving_bits} | "
            f"{fmt_prob(row.prefix_fraction)} | "
            f"{fmt_prob(row.eof_one_shot_fraction)} | "
            f"{fmt_prob(row.exact_length_fraction)} |"
        )
    return lines


def render_recursive(rows: list[RecursiveRow]) -> list[str]:
    lines = [
        "## Recursive Length-Path Ledger",
        "",
        "Rows assume every pass saves at least one bit and total saving is `S`.",
        "The decoder knows root length, final length, and pass count, but not the",
        "intermediate positive savings unless the path is stored or derived.",
        "",
        "| passes P | total saving S | length-path bits log2 C(S-1,P-1) | net S-path | prefix fraction | EOF one-shot fraction for final S | exact 1-bit/pass fraction |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row.passes} | {row.total_saving} | {row.path_bits:.6f} | "
            f"{row.net_after_path:.6f} | {fmt_prob(row.prefix_fraction)} | "
            f"{fmt_prob(row.eof_one_shot_fraction)} | "
            f"{fmt_prob(row.exact_one_bit_each_fraction)} |"
        )
    return lines


def render_exact_tiny(row: ExactTinyRow) -> list[str]:
    lines = [
        "## Exact Tiny Selector Ledger",
        "",
        f"Default sanity case: `n={row.n_bits}, P={row.passes}, "
        f"s={row.saving_per_pass}` so total saving `S={row.total_saving}`.",
        "",
        "| ledger | exact count | fraction | reading |",
        "| --- | ---: | ---: | --- |",
    ]
    entries = [
        ("prefix slots", row.prefix_count, "paid prefix/self-delimiting short outputs"),
        ("EOF one-to-one slots", row.eof_count, "non-prefix one-shot short outputs"),
        ("prefix raw fallback", row.raw_fallback_count, "success count after paying raw fallback length"),
        ("best-of profiles, selector free", row.uncharged_best_of_count, "apparent count if profile identity is hidden"),
        ("best-of profiles, selector paid", row.paid_best_of_count, "selector cost cancels the best-of multiplier"),
        (
            "checksum-refereed profiles",
            row.checksum_refereed_count,
            f"finite referee; {row.checksum_bits_still_owed:.3f} profile bits still owed",
        ),
    ]
    for label, count, reading in entries:
        lines.append(
            f"| {label} | {count} / {row.total_inputs} | "
            f"{count / row.total_inputs:.6f} | {reading} |"
        )
    return lines


def render_prior_lift(rows: list[PriorLiftRow]) -> list[str]:
    lines = [
        "## Required Source Lift For Roughly-All Claims",
        "",
        "If a paid uniform code saves `S` bits, the largest uniform winning set has",
        "measure `p=2^-S`. To make that set have source probability `c`, the source",
        "needs density lift `c/p` and at least binary-KL entropy deficit.",
        "",
        "| saving S | desired coverage c | max uniform p | required lift c/p | binary-KL deficit bits |",
        "| ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row.saving_bits} | {row.desired_coverage:.3f} | "
            f"{fmt_prob(row.max_uniform_coverage)} | "
            f"{row.required_lift:.6g} | {row.binary_kl_deficit_bits:.6f} |"
        )
    return lines


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-bits", type=int, nargs="+", default=[32, 128, 1024])
    parser.add_argument("--saving-bits", type=int, nargs="+", default=[1, 2, 4, 8])
    parser.add_argument("--passes", type=int, nargs="+", default=[2, 4, 8, 16, 64])
    parser.add_argument("--saving-per-pass", type=float, nargs="+", default=[1.0, 2.0, 4.0])
    parser.add_argument("--desired-coverage", type=float, nargs="+", default=[0.5, 0.9, 0.99])
    parser.add_argument("--prior-saving-bits", type=int, nargs="+", default=[1, 2, 4, 8, 128])
    parser.add_argument("--tiny-n", type=int, default=4)
    parser.add_argument("--tiny-passes", type=int, default=2)
    parser.add_argument("--tiny-saving-per-pass", type=int, default=1)
    parser.add_argument("--raw-r", type=int, default=3)
    parser.add_argument("--profiles", type=int, default=4)
    parser.add_argument("--checksum-effective-bits", type=float, default=1.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    lines = [
        "# H60 - Recursive Shrink Converse",
        "",
        "This is a counting ledger, not a compressor. It separates prefix/public-Q",
        "bounds from EOF one-to-one one-shot effects and charges the recursive",
        "intermediate-length path.",
        "",
        *render_fraction(fraction_rows(args.n_bits, args.saving_bits)),
        "",
        *render_recursive(recursive_rows(args.passes, args.saving_per_pass)),
        "",
        *render_exact_tiny(
            exact_tiny_row(
                args.tiny_n,
                args.tiny_passes,
                args.tiny_saving_per_pass,
                args.raw_r,
                args.profiles,
                args.checksum_effective_bits,
            )
        ),
        "",
        *render_prior_lift(prior_lift_rows(args.prior_saving_bits, args.desired_coverage)),
        "",
        "## Reading",
        "",
        "EOF/non-prefix one-to-one coding can compress almost every fixed-length",
        "input by at least one bit in a single layer if the old length is free.",
        "That does not give arbitrary stateless recursion. Once savings vary, the",
        "reverse decoder needs the intermediate length path. If savings are forced",
        "to exactly one bit per pass so the path is derivable, only a `2^-P`",
        "fraction can use exact-length one-bit outputs.",
        "",
        "Therefore a roughly-all-data recursive win needs either a public invariant",
        "that fixes the length path without lowering the eligible fraction, or a",
        "real non-uniform source/value law. Otherwise the bill is prefix/Kraft",
        "mass, length-path entropy, or an explicit selector.",
    ]
    print("\n".join(lines))


if __name__ == "__main__":
    main()
