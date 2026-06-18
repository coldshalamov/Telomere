#!/usr/bin/env python3
"""H78 - master no-go audit for structure-free maintained recursion.

This is the compact theorem checker for the current boundary.

Given desired coverage c, passes P, and saving per pass s, it reports the
maximum allowed coverage / finite K for any stateless, lossless, content-blind
scheme after all visible state is charged.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


def prefix_coverage(total_saving_bits: float) -> float:
    if total_saving_bits <= 0.0:
        return 1.0
    return 2.0 ** (-total_saving_bits)


def eof_coverage(total_saving_bits: float, n_bits: int) -> float:
    if total_saving_bits <= 0.0:
        return 1.0
    return max(0.0, min(1.0, (2.0 ** (1.0 - total_saving_bits)) - (2.0 ** (-n_bits))))


def prefix_max_total_saving(coverage: float) -> float:
    return max(0.0, -math.log2(coverage))


def eof_max_total_saving(coverage: float, n_bits: int) -> float:
    return max(0.0, 1.0 - math.log2(coverage + (2.0 ** (-n_bits))))


def max_k(coverage: float, saving_per_pass: float, n_bits: int, eof: bool) -> int:
    total = eof_max_total_saving(coverage, n_bits) if eof else prefix_max_total_saving(coverage)
    if saving_per_pass <= 0.0:
        return math.inf  # type: ignore[return-value]
    return math.floor(total / saving_per_pass)


@dataclass(frozen=True)
class AuditRow:
    n_bits: int
    coverage: float
    passes: int
    saving_per_pass_bits: float
    total_saving_bits: float
    prefix_allowed_coverage: float
    eof_allowed_coverage: float
    prefix_max_k: int
    eof_max_k: int
    prefix_avg_saving_allowed: float
    eof_avg_saving_allowed: float


def rows() -> list[AuditRow]:
    result: list[AuditRow] = []
    for n_bits in (128, 4096):
        for coverage in (0.90, 0.99):
            for passes in (1, 4, 16, 64, 1024):
                for saving_per_pass in (1.0, 2.0):
                    total = passes * saving_per_pass
                    result.append(
                        AuditRow(
                            n_bits=n_bits,
                            coverage=coverage,
                            passes=passes,
                            saving_per_pass_bits=saving_per_pass,
                            total_saving_bits=total,
                            prefix_allowed_coverage=prefix_coverage(total),
                            eof_allowed_coverage=eof_coverage(total, n_bits),
                            prefix_max_k=max_k(coverage, saving_per_pass, n_bits, eof=False),
                            eof_max_k=max_k(coverage, saving_per_pass, n_bits, eof=True),
                            prefix_avg_saving_allowed=prefix_max_total_saving(coverage) / passes,
                            eof_avg_saving_allowed=eof_max_total_saving(coverage, n_bits) / passes,
                        )
                    )
    return result


def fmt_prob(value: float) -> str:
    if value == 0.0:
        return "0"
    if value >= 0.001:
        return f"{value:.6f}"
    return f"{value:.3e}"


def print_rows() -> None:
    print("== master no-go audit ==")
    print("Rows show the allowed coverage for the claimed total saving S=P*s.")
    print(
        f"{'n':>6} {'c':>6} {'P':>6} {'s/pass':>7} {'S':>8} "
        f"{'prefix cov':>12} {'EOF cov':>12} {'K prefix':>9} {'K EOF':>7}"
    )
    for row in rows():
        if row.n_bits == 4096 and row.coverage == 0.90 and row.saving_per_pass_bits == 1.0:
            print(
                f"{row.n_bits:6d} {row.coverage:6.2f} {row.passes:6d} "
                f"{row.saving_per_pass_bits:7.2f} {row.total_saving_bits:8.1f} "
                f"{fmt_prob(row.prefix_allowed_coverage):>12} "
                f"{fmt_prob(row.eof_allowed_coverage):>12} "
                f"{row.prefix_max_k:9d} {row.eof_max_k:7d}"
            )
    print()


def print_average_rows() -> None:
    print("== average saving per pass allowed at fixed coverage ==")
    print(f"{'c':>6} {'P':>6} {'prefix avg':>12} {'EOF avg':>12}")
    for coverage in (0.90, 0.99):
        for passes in (16, 64, 1024):
            prefix_avg = prefix_max_total_saving(coverage) / passes
            eof_avg = eof_max_total_saving(coverage, 4096) / passes
            print(f"{coverage:6.2f} {passes:6d} {prefix_avg:12.6f} {eof_avg:12.6f}")
    print()


def print_theorem() -> None:
    print("== theorem statement ==")
    print("If a stateless lossless content-blind scheme compresses coverage c of")
    print("n-bit uniform inputs by total saving S after all visible state is")
    print("charged, then:")
    print("  prefix/self-delimiting: c <= 2^-S")
    print("  EOF one-shot generous:  c <= 2^(1-S) - 2^-n")
    print()
    print("For maintained s>0 bits/pass over arbitrary P, S=P*s grows while c")
    print("is fixed away from zero. The bound fails for large P. The only")
    print("remaining constructive relaxation is a predeclared non-uniform public")
    print("source/fertility law with uniform negative controls.")


def main() -> None:
    print_rows()
    print_average_rows()
    print_theorem()


if __name__ == "__main__":
    main()
