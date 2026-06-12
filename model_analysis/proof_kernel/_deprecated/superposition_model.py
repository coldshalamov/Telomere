"""Encoder-only superposition model for retained Telomere candidates."""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

from costs import seed_records_with_cost_le


@dataclass(frozen=True)
class SuperpositionConfig:
    prune_delta_bits: int
    max_variants_per_position: int
    equal_size_allowed: bool
    bloat_tolerant_retained: bool


@dataclass(frozen=True)
class VariantStats:
    avg_variants: float
    weighted_score: float
    retained_by_excess: dict[int, float]
    state_growth_factor: float


def _expected_min_poisson(lam: float, cap: int) -> float:
    if cap <= 0 or lam <= 0:
        return 0.0
    if lam > 60:
        return float(cap)
    # E[min(X, cap)] = sum_{k=1..cap} P(X >= k)
    p0 = math.exp(-lam)
    cumulative = p0
    pk = p0
    total = 0.0
    for k in range(1, cap + 1):
        total += max(0.0, 1.0 - cumulative)
        pk *= lam / k
        cumulative += pk
    return min(float(cap), total)


@lru_cache(maxsize=None)
def _expected_records_at_exact_cost(entry_bits: int, record_cost_bits: int, depth_bits: int) -> float:
    if record_cost_bits < 0:
        return 0.0
    hi = seed_records_with_cost_le(1, record_cost_bits, depth_bits)
    lo = seed_records_with_cost_le(1, record_cost_bits - 1, depth_bits)
    count = max(0, hi - lo)
    if count == 0:
        return 0.0
    log_expected = math.log(count) - entry_bits * math.log(2.0)
    if log_expected > 60:
        return math.exp(60)
    if log_expected < -60:
        return 0.0
    return math.exp(log_expected)


@lru_cache(maxsize=None)
def _expected_bundle_records_at_exact_cost(
    span_bits: int,
    arity: int,
    record_cost_bits: int,
    depth_bits: int,
) -> float:
    if record_cost_bits < 0:
        return 0.0
    hi = seed_records_with_cost_le(arity, record_cost_bits, depth_bits)
    lo = seed_records_with_cost_le(arity, record_cost_bits - 1, depth_bits)
    count = max(0, hi - lo)
    if count == 0:
        return 0.0
    log_expected = math.log(count) - span_bits * math.log(2.0)
    if log_expected > 60:
        return math.exp(60)
    if log_expected < -60:
        return 0.0
    return math.exp(log_expected)


@lru_cache(maxsize=None)
def retained_variant_stats(entry_bits: int, depth_bits: int, config: SuperpositionConfig) -> VariantStats:
    """Expected retained variants and weighted opportunity score for one entry."""

    slots_left = float(max(0, int(config.max_variants_per_position) - 1))
    retained: dict[int, float] = {}
    if slots_left <= 0 or config.prune_delta_bits < 0:
        return VariantStats(1.0, 1.0, retained, 1.0)

    for excess in range(0, config.prune_delta_bits + 1):
        if excess == 0 and not config.equal_size_allowed:
            continue
        if excess > 0 and not config.bloat_tolerant_retained:
            continue
        lam = _expected_records_at_exact_cost(entry_bits, entry_bits + excess, depth_bits)
        take = min(slots_left, _expected_min_poisson(lam, math.ceil(slots_left)))
        if take > 1e-15:
            retained[excess] = take
            slots_left -= take
            if slots_left <= 0:
                break

    avg_retained = sum(retained.values())
    avg_retained = min(avg_retained, max(0, int(config.max_variants_per_position) - 1))
    weighted = 1.0 + sum(count * (2.0 ** (-excess)) for excess, count in retained.items())
    return VariantStats(
        avg_variants=1.0 + avg_retained,
        weighted_score=max(1.0, weighted),
        retained_by_excess=retained,
        state_growth_factor=1.0 + avg_retained,
    )


@lru_cache(maxsize=None)
def retained_bundle_variant_stats(
    span_bits: int,
    arity: int,
    depth_bits: int,
    config: SuperpositionConfig,
) -> VariantStats:
    """Retained whole-window variants that are not decomposed per entry."""

    slots_left = float(max(0, int(config.max_variants_per_position) - 1))
    retained: dict[int, float] = {}
    if slots_left <= 0 or config.prune_delta_bits < 0:
        return VariantStats(1.0, 1.0, retained, 1.0)

    for excess in range(0, config.prune_delta_bits + 1):
        if excess == 0 and not config.equal_size_allowed:
            continue
        if excess > 0 and not config.bloat_tolerant_retained:
            continue
        lam = _expected_bundle_records_at_exact_cost(
            span_bits,
            arity,
            span_bits + excess,
            depth_bits,
        )
        take = min(slots_left, _expected_min_poisson(lam, math.ceil(slots_left)))
        if take > 1e-15:
            retained[excess] = take
            slots_left -= take
            if slots_left <= 0:
                break

    avg_retained = sum(retained.values())
    avg_retained = min(avg_retained, max(0, int(config.max_variants_per_position) - 1))
    weighted = 1.0 + sum(count * (2.0 ** (-excess)) for excess, count in retained.items())
    return VariantStats(
        avg_variants=1.0 + avg_retained,
        weighted_score=max(1.0, weighted),
        retained_by_excess=retained,
        state_growth_factor=1.0 + avg_retained,
    )


def variant_scores_for_lengths(
    lengths: list[int],
    depth_bits: int,
    config: SuperpositionConfig,
    refresh_rho: float = 1.0,
) -> tuple[dict[int, float], dict[int, VariantStats]]:
    scores: dict[int, float] = {}
    stats: dict[int, VariantStats] = {}
    for length in sorted(set(lengths)):
        stat = retained_variant_stats(length, depth_bits, config)
        score = 1.0 + max(0.0, refresh_rho) * (stat.weighted_score - 1.0)
        scores[length] = score
        stats[length] = stat
    return scores, stats


def sweep_configs() -> list[SuperpositionConfig]:
    configs: set[SuperpositionConfig] = set()
    for delta in (0, 1, 2, 4, 8, 16, 32, 64):
        for max_variants in (1, 2, 3, 4, 8, 16):
            for equal_size in (False, True):
                for bloat in (False, True):
                    if max_variants == 1 and (delta != 0 or equal_size or bloat):
                        continue
                    configs.add(SuperpositionConfig(delta, max_variants, equal_size, bloat))
    return sorted(
        configs,
        key=lambda cfg: (
            cfg.prune_delta_bits,
            cfg.max_variants_per_position,
            cfg.equal_size_allowed,
            cfg.bloat_tolerant_retained,
        ),
    )


def validate_sweep_configs(configs: list[SuperpositionConfig] | None = None) -> dict[str, list[int | bool]]:
    configs = configs or sweep_configs()
    observed = {
        "prune_delta_bits": sorted({cfg.prune_delta_bits for cfg in configs}),
        "max_variants_per_position": sorted({cfg.max_variants_per_position for cfg in configs}),
        "equal_size_allowed": sorted({cfg.equal_size_allowed for cfg in configs}),
        "bloat_tolerant_retained": sorted({cfg.bloat_tolerant_retained for cfg in configs}),
    }
    expected = {
        "prune_delta_bits": [0, 1, 2, 4, 8, 16, 32, 64],
        "max_variants_per_position": [1, 2, 3, 4, 8, 16],
        "equal_size_allowed": [False, True],
        "bloat_tolerant_retained": [False, True],
    }
    for key, values in expected.items():
        if observed[key] != values:
            raise AssertionError(f"superposition sweep {key} mismatch: {observed[key]} != {values}")
    for cfg in configs:
        stats = retained_variant_stats(34, 121, cfg)
        if stats.avg_variants > cfg.max_variants_per_position + 1e-9:
            raise AssertionError(f"variant cap exceeded for {cfg}: {stats.avg_variants}")
    return observed


if __name__ == "__main__":
    cfg = SuperpositionConfig(8, 4, True, True)
    print(retained_variant_stats(34, 64, cfg))
