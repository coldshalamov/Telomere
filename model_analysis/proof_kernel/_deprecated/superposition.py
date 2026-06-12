"""Compatibility wrapper for ``superposition_model.py``."""

from superposition_model import (
    SuperpositionConfig,
    VariantStats,
    retained_bundle_variant_stats,
    retained_variant_stats,
    sweep_configs,
    variant_scores_for_lengths,
)

__all__ = [
    "SuperpositionConfig",
    "VariantStats",
    "retained_bundle_variant_stats",
    "retained_variant_stats",
    "sweep_configs",
    "variant_scores_for_lengths",
]
