#!/usr/bin/env python3
"""
H36 - developmental attractor / canalization ledger.

Idea:

    A public developmental system maps short genotypes through attractor
    dynamics into larger phenotypes. Decode is stateless: read genotype/recipe,
    run the public dynamics, emit the phenotype.

This is the closest biology-shaped mechanism: DNA-like unfolding, canalized
attractors, neutral basins, and regulatory expansion. The question is whether it
can cover roughly all arbitrary targets without paying the inverse branch or a
source prior.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, log2
import random


@dataclass(frozen=True)
class SupportRow:
    phenotype_bits: int
    genotype_bits: int
    coverage_log2: int
    net_if_reachable: int
    all_data: bool


def support_rows() -> list[SupportRow]:
    rows: list[SupportRow] = []
    for phenotype_bits in (16, 64, 128):
        for genotype_bits in (8, 16, 32, 64, 128, 160):
            if genotype_bits > phenotype_bits + 32:
                continue
            rows.append(
                SupportRow(
                    phenotype_bits=phenotype_bits,
                    genotype_bits=genotype_bits,
                    coverage_log2=min(0, genotype_bits - phenotype_bits),
                    net_if_reachable=phenotype_bits - genotype_bits,
                    all_data=genotype_bits >= phenotype_bits,
                )
            )
    return rows


@dataclass(frozen=True)
class AttractorResidualRow:
    state_bits: int
    attractor_bits: int
    residual_bits: int
    coverage_log2: int
    total_cost: int
    net_if_reachable: int
    all_data: bool


def attractor_residual_rows() -> list[AttractorResidualRow]:
    rows: list[AttractorResidualRow] = []
    for state_bits in (32, 64, 128):
        for attractor_bits in (0, 8, 16, 32):
            if attractor_bits > state_bits:
                continue
            full_branch_bits = state_bits - attractor_bits
            for residual_bits in (0, full_branch_bits // 2, full_branch_bits):
                total = attractor_bits + residual_bits
                rows.append(
                    AttractorResidualRow(
                        state_bits=state_bits,
                        attractor_bits=attractor_bits,
                        residual_bits=residual_bits,
                        coverage_log2=min(0, residual_bits - full_branch_bits),
                        total_cost=total,
                        net_if_reachable=state_bits - total,
                        all_data=residual_bits >= full_branch_bits,
                    )
                )
    return rows


def entropy(probabilities: list[float]) -> float:
    return -sum(p * log2(p) for p in probabilities if p > 0.0)


def cross_entropy(p: list[float], q: list[float]) -> float:
    return -sum(pi * log2(qi) for pi, qi in zip(p, q) if pi > 0.0)


@dataclass(frozen=True)
class BasinProfileRow:
    name: str
    phenotype_bits: int
    genotype_bits: int
    support: int
    source_entropy: float
    source_gain_pure: float
    source_gain_mixture: float
    uniform_penalty_mixture: float
    uniform_cross_entropy_pure: float | None


def random_profile(
    phenotype_bits: int, genotype_bits: int, seed: int
) -> tuple[list[float], int]:
    rng = random.Random(seed)
    target_count = 1 << phenotype_bits
    counts = [0] * target_count
    for _ in range(1 << genotype_bits):
        counts[rng.randrange(target_count)] += 1
    total = float(1 << genotype_bits)
    q = [c / total for c in counts]
    return q, sum(1 for c in counts if c)


def zipf_profile(phenotype_bits: int, exponent: float) -> tuple[list[float], int]:
    target_count = 1 << phenotype_bits
    weights = [1.0 / ((i + 1) ** exponent) for i in range(target_count)]
    total = sum(weights)
    return [w / total for w in weights], target_count


def basin_profile_rows() -> list[BasinProfileRow]:
    rows: list[BasinProfileRow] = []
    configs: list[tuple[str, int, int, list[float], int]] = []
    for phenotype_bits, genotype_bits in ((8, 8), (8, 10), (8, 12), (8, 16)):
        q, support = random_profile(phenotype_bits, genotype_bits, 36000 + genotype_bits)
        configs.append((f"random-map-g{genotype_bits}", phenotype_bits, genotype_bits, q, support))
    for exponent in (0.5, 1.0, 1.5):
        q, support = zipf_profile(8, exponent)
        configs.append((f"zipf-basin-s{exponent:.1f}", 8, 8, q, support))

    for name, phenotype_bits, genotype_bits, q, support in configs:
        target_count = 1 << phenotype_bits
        u = [1.0 / target_count] * target_count
        alpha = 0.5
        mixture = [(1.0 - alpha) * ui + alpha * qi for ui, qi in zip(u, q)]
        source_h = entropy(q)
        source_gain_pure = phenotype_bits - source_h
        source_gain_mixture = phenotype_bits - cross_entropy(q, mixture)
        uniform_penalty_mixture = cross_entropy(u, mixture) - phenotype_bits
        if support == target_count and all(qi > 0.0 for qi in q):
            uniform_cross_entropy_pure = cross_entropy(u, q)
        else:
            uniform_cross_entropy_pure = None
        rows.append(
            BasinProfileRow(
                name=name,
                phenotype_bits=phenotype_bits,
                genotype_bits=genotype_bits,
                support=support,
                source_entropy=source_h,
                source_gain_pure=source_gain_pure,
                source_gain_mixture=source_gain_mixture,
                uniform_penalty_mixture=uniform_penalty_mixture,
                uniform_cross_entropy_pure=uniform_cross_entropy_pure,
            )
        )
    return rows


@dataclass(frozen=True)
class RegulatoryPairRow:
    current_bits: int
    future_bits: int
    genotype_bits: int
    pair_coverage_log2: int
    source_gain: int
    uniform_all_data: bool


def regulatory_pair_rows() -> list[RegulatoryPairRow]:
    rows: list[RegulatoryPairRow] = []
    for current_bits, future_bits in ((8, 8), (16, 16), (32, 32)):
        raw = current_bits + future_bits
        for genotype_bits in (current_bits, raw - 4, raw, raw + 8):
            rows.append(
                RegulatoryPairRow(
                    current_bits=current_bits,
                    future_bits=future_bits,
                    genotype_bits=genotype_bits,
                    pair_coverage_log2=min(0, genotype_bits - raw),
                    source_gain=raw - genotype_bits,
                    uniform_all_data=genotype_bits >= raw,
                )
            )
    return rows


def print_support_table() -> None:
    print("== genotype support bound ==")
    print(
        "A public developmental decoder with g genotype bits can name at most "
        "2^g phenotypes. Roughly-all-data n-bit coverage needs g >= n."
    )
    print(
        f"{'phenotype':>9} {'genotype':>9} {'log2 cover':>11} "
        f"{'net if hit':>11} {'all data?':>10}"
    )
    for row in support_rows():
        if row.phenotype_bits in (64, 128) and row.genotype_bits in (32, 64, 128, 160):
            print(
                f"{row.phenotype_bits:9d} {row.genotype_bits:9d} "
                f"{row.coverage_log2:11d} {row.net_if_reachable:11d} "
                f"{str(row.all_data):>10}"
            )
    print()


def print_attractor_table() -> None:
    print("== attractor plus inverse-branch residual ==")
    print(
        "Attractor dynamics erase branch information. Lossless arbitrary decode "
        "needs attractor id plus the inverse branch inside its basin."
    )
    print(
        f"{'state':>6} {'attractor':>9} {'residual':>9} {'log2 cover':>11} "
        f"{'cost':>7} {'net':>7} {'all data?':>10}"
    )
    for row in attractor_residual_rows():
        if row.state_bits in (64, 128) and row.attractor_bits in (8, 32):
            print(
                f"{row.state_bits:6d} {row.attractor_bits:9d} "
                f"{row.residual_bits:9d} {row.coverage_log2:11d} "
                f"{row.total_cost:7d} {row.net_if_reachable:7d} "
                f"{str(row.all_data):>10}"
            )
    print()


def print_basin_profile_table() -> None:
    print("== basin prior: source gain vs uniform penalty ==")
    print(
        "A basin distribution Q can compress data drawn from Q. Uniform targets "
        "pay cross-entropy or need raw escape; the gain is source-shaped."
    )
    print(
        f"{'profile':>17} {'support':>8} {'H(Q)':>8} {'src gain':>9} "
        f"{'mix src':>9} {'mix U pen':>10} {'pure U CE':>10}"
    )
    for row in basin_profile_rows():
        pure = (
            f"{row.uniform_cross_entropy_pure:10.3f}"
            if row.uniform_cross_entropy_pure is not None
            and isfinite(row.uniform_cross_entropy_pure)
            else f"{'infinite':>10}"
        )
        print(
            f"{row.name:>17} {row.support:8d} {row.source_entropy:8.3f} "
            f"{row.source_gain_pure:9.3f} {row.source_gain_mixture:9.3f} "
            f"{row.uniform_penalty_mixture:10.3f} {pure}"
        )
    print()


def print_regulatory_pair_table() -> None:
    print("== regulatory current+future pair ==")
    print(
        "A genotype can name current and future observables together, but "
        "uniform pair coverage still needs genotype bits >= raw pair bits."
    )
    print(
        f"{'current':>8} {'future':>8} {'genotype':>9} "
        f"{'log2 cover':>11} {'source gain':>12} {'all data?':>10}"
    )
    for row in regulatory_pair_rows():
        if row.current_bits in (16, 32):
            print(
                f"{row.current_bits:8d} {row.future_bits:8d} "
                f"{row.genotype_bits:9d} {row.pair_coverage_log2:11d} "
                f"{row.source_gain:12d} {str(row.uniform_all_data):>10}"
            )
    print()


def main() -> None:
    print_support_table()
    print_attractor_table()
    print_basin_profile_table()
    print_regulatory_pair_table()
    print("CONCLUSION:")
    print(
        "Developmental attractors are a plausible Telomere-shaped source prior: "
        "a public genotype can unfold into current and future observables, and "
        "data drawn from that developmental distribution can be shorter. For "
        "roughly all uniform targets, support and inverse-branch counting still "
        "force the stored genotype/residual to carry n bits. Biology gives a "
        "real non-uniform/canalized source model, not a free uniform all-data "
        "escape."
    )


if __name__ == "__main__":
    main()
