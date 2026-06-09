"""Current-layer entry-state recurrence for the Telomere proof kernel."""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, replace

from costs import LITERAL_ENTRY_OVERHEAD_BITS
from hit_distribution import expected_gain_per_window, p_min_record_le
from refresh_model import RefreshRule
from selection_bounds import estimate_selection
from span_distribution import span_distributions
from superposition_model import SuperpositionConfig, retained_bundle_variant_stats, variant_scores_for_lengths


RechunkSchedule = int | tuple[int | None, ...] | None


@dataclass(frozen=True)
class EntryKey:
    length_bits: int
    kind: str
    variant_state: str = "main"


@dataclass
class EntryState:
    buckets: dict[EntryKey, float]
    original_raw_bits: float
    pass_index: int = 0
    accumulated_metadata_bits: float = 0.0

    @property
    def entry_count(self) -> float:
        return sum(self.buckets.values())

    @property
    def payload_bits(self) -> float:
        return sum(key.length_bits * count for key, count in self.buckets.items())

    @property
    def total_charged_bits(self) -> float:
        return self.payload_bits + self.accumulated_metadata_bits

    def length_pmf(self) -> dict[int, float]:
        n = self.entry_count
        if n <= 0:
            return {}
        pmf: dict[int, float] = defaultdict(float)
        for key, count in self.buckets.items():
            pmf[key.length_bits] += count / n
        return dict(pmf)

    def remove_proportionally(self, remove_count: float) -> "EntryState":
        n = self.entry_count
        if remove_count <= 0 or n <= 0:
            return self
        fraction = min(0.98, max(0.0, remove_count / n))
        return EntryState(
            {
                key: count * (1.0 - fraction)
                for key, count in self.buckets.items()
                if count * (1.0 - fraction) > 1e-12
            },
            self.original_raw_bits,
            self.pass_index,
            self.accumulated_metadata_bits,
        )

    def add_bucket(self, key: EntryKey, count: float) -> None:
        if count <= 0:
            return
        self.buckets[key] = self.buckets.get(key, 0.0) + count

    def wrap_raw_literals(self, literal_overhead_bits: int = LITERAL_ENTRY_OVERHEAD_BITS) -> "EntryState":
        wrapped: dict[EntryKey, float] = defaultdict(float)
        for key, count in self.buckets.items():
            if key.kind == "raw":
                wrapped[EntryKey(key.length_bits + literal_overhead_bits, "literal")] += count
            else:
                wrapped[key] += count
        return EntryState(dict(wrapped), self.original_raw_bits, self.pass_index, self.accumulated_metadata_bits)

    def rechunk(self, entry_bits: int | None) -> "EntryState":
        if entry_bits is None:
            return self
        if entry_bits <= 0:
            raise ValueError("rechunk entry_bits must be positive")
        return EntryState(
            {EntryKey(entry_bits, "rechunk"): self.payload_bits / entry_bits},
            self.original_raw_bits,
            self.pass_index,
            self.accumulated_metadata_bits,
        )


@dataclass(frozen=True)
class PassLedgerRow:
    pass_index: int
    depth_bits: int
    policy: str
    refresh_rule: str
    literal_overhead_bits: int
    bits_before: float
    bits_after: float
    metadata_bits: float
    net_delta_pct_current: float
    net_delta_pct_raw: float
    accepted_windows: float
    expected_gain_bits: float
    avg_variants_per_position: float
    max_window_multiplier: float
    optimistic_window_multiplier: float
    conservative_window_multiplier: float
    opportunity_discount_ratio: float
    variant_cap: int
    strict_seed_channels_per_entry: float
    equal_size_neutral_variants_per_entry: float
    retained_noncompressive_variants_per_entry: float
    bundled_variants_per_window: float
    phase_rechunk_derived_multiplier: float
    entry_count_before: float
    entry_count_after: float
    rechunk_entry_bits: int | None = None
    rechunk_residual_bits: float = 0.0
    rechunk_pad_bits: float = 0.0


def initial_raw_state(entry_count: int, block_bits: int) -> EntryState:
    return EntryState(
        {EntryKey(block_bits, "raw"): float(entry_count)},
        original_raw_bits=float(entry_count * block_bits),
    )


def _variant_summary(
    state: EntryState,
    depth_bits: int,
    superposition: SuperpositionConfig,
    refresh: RefreshRule,
) -> tuple[dict[int, float], float, float, float, float, float]:
    lengths = list(state.length_pmf().keys())
    scores, stats = variant_scores_for_lengths(lengths, depth_bits, superposition, refresh.rho)
    pmf = state.length_pmf()
    avg_variants = sum(pmf[length] * stats[length].avg_variants for length in pmf)
    equal_size = sum(
        pmf[length] * stats[length].retained_by_excess.get(0, 0.0)
        for length in pmf
    )
    retained_bloat = sum(
        pmf[length] * sum(count for excess, count in stats[length].retained_by_excess.items() if excess > 0)
        for length in pmf
    )
    max_score = max(scores.values(), default=1.0)
    if avg_variants > superposition.max_variants_per_position + 1e-9:
        raise AssertionError(
            "earned variant expectation exceeded configured cap: "
            f"{avg_variants} > {superposition.max_variants_per_position}"
        )
    return scores, avg_variants, max_score, equal_size, retained_bloat, max(1.0, avg_variants)


def _discount_combo_multiplier(optimistic_multiplier: float, arity: int) -> float:
    """Discount independent-combo superposition for shared-entry correlation.

    The optimistic convolution multiplies retained-entry opportunity scores.
    A conservative no-double-counting proxy keeps only the linear marginal
    contribution implied by the per-entry geometric mean.
    """

    if optimistic_multiplier <= 1.0 or arity <= 1:
        return max(1.0, optimistic_multiplier)
    per_entry = optimistic_multiplier ** (1.0 / arity)
    return max(1.0, 1.0 + arity * (per_entry - 1.0))


def run_pass(
    state: EntryState,
    arity_cap: int,
    depth_bits: int,
    policy: str,
    superposition: SuperpositionConfig,
    refresh: RefreshRule,
    literal_overhead_bits: int = LITERAL_ENTRY_OVERHEAD_BITS,
) -> tuple[EntryState, PassLedgerRow]:
    """Run one expectation pass over the current entry histogram."""

    bits_before = state.total_charged_bits
    entry_count = state.entry_count
    wrap_unmatched = any(key.kind == "raw" for key in state.buckets)
    scores, avg_variants, max_score, equal_size_variants, retained_bloat_variants, _earned = _variant_summary(
        state,
        depth_bits,
        superposition,
        refresh,
    )
    span_buckets = span_distributions(state.length_pmf(), scores, arity_cap)

    add_records: dict[int, float] = defaultdict(float)
    accepted_windows = 0.0
    expected_gain_bits = 0.0
    removed_entries = 0.0
    max_optimistic_multiplier = 1.0
    max_conservative_multiplier = 1.0
    max_discount_ratio = 1.0
    bundled_variant_mass = 0.0
    bundled_variant_weight = 0.0

    for arity in range(arity_cap, 0, -1):
        for span in span_buckets[arity]:
            bundle_stats = retained_bundle_variant_stats(span.span_bits, arity, depth_bits, superposition)
            bundle_credit = max(0.0, refresh.rho) * (
                bundle_stats.weighted_score - 1.0
            )
            optimistic_multiplier = span.opportunity_multiplier + bundle_credit
            conservative_multiplier = _discount_combo_multiplier(span.opportunity_multiplier, arity) + bundle_credit
            max_optimistic_multiplier = max(max_optimistic_multiplier, optimistic_multiplier)
            max_conservative_multiplier = max(max_conservative_multiplier, conservative_multiplier)
            if optimistic_multiplier > 1.0:
                max_discount_ratio = max(
                    max_discount_ratio,
                    optimistic_multiplier / max(conservative_multiplier, 1e-300),
                )
            bundled_variant_mass += span.probability * max(0.0, bundle_stats.avg_variants - 1.0)
            bundled_variant_weight += span.probability
            hit = p_min_record_le(
                span.span_bits - 1,
                span.span_bits,
                arity,
                depth_bits,
                conservative_multiplier,
            )
            if hit <= 0:
                continue
            selection = estimate_selection(entry_count, arity, hit, policy)
            expected_gain_window = expected_gain_per_window(
                span.span_bits,
                arity,
                depth_bits,
                conservative_multiplier,
            )
            denom = max(selection.candidate_windows * hit, 1e-300)
            scale = min(1.0, selection.accepted_windows / denom)
            bucket_windows = selection.candidate_windows * span.probability
            mass = bucket_windows * hit * scale
            if mass <= 0:
                continue
            gain_given_hit = expected_gain_window / hit
            record_len = max(1, round(span.span_bits - gain_given_hit))
            add_records[record_len] += mass
            accepted_windows += mass
            expected_gain_bits += mass * gain_given_hit
            removed_entries += mass * arity

    if removed_entries > entry_count * 0.98:
        downscale = (entry_count * 0.98) / max(removed_entries, 1e-300)
        add_records = defaultdict(float, {length: count * downscale for length, count in add_records.items()})
        accepted_windows *= downscale
        expected_gain_bits *= downscale
        removed_entries *= downscale

    next_state = state.remove_proportionally(removed_entries)
    if wrap_unmatched:
        next_state = next_state.wrap_raw_literals(literal_overhead_bits)

    next_state = EntryState(
        dict(next_state.buckets),
        state.original_raw_bits,
        pass_index=state.pass_index + 1,
        accumulated_metadata_bits=state.accumulated_metadata_bits + refresh.metadata_bits_per_pass,
    )
    for record_len, count in add_records.items():
        next_state.add_bucket(EntryKey(record_len, "seed"), count)

    bits_after = next_state.total_charged_bits
    net_delta = bits_before - bits_after
    row = PassLedgerRow(
        pass_index=state.pass_index + 1,
        depth_bits=depth_bits,
        policy=policy,
        refresh_rule=refresh.name,
        literal_overhead_bits=literal_overhead_bits if wrap_unmatched else 0,
        bits_before=bits_before,
        bits_after=bits_after,
        metadata_bits=refresh.metadata_bits_per_pass,
        net_delta_pct_current=100.0 * net_delta / bits_before if bits_before else 0.0,
        net_delta_pct_raw=100.0 * net_delta / state.original_raw_bits if state.original_raw_bits else 0.0,
        accepted_windows=accepted_windows,
        expected_gain_bits=expected_gain_bits,
        avg_variants_per_position=avg_variants,
        max_window_multiplier=max_conservative_multiplier,
        optimistic_window_multiplier=max(max_score**arity_cap, max_optimistic_multiplier),
        conservative_window_multiplier=max_conservative_multiplier,
        opportunity_discount_ratio=max_discount_ratio,
        variant_cap=superposition.max_variants_per_position,
        strict_seed_channels_per_entry=1.0,
        equal_size_neutral_variants_per_entry=equal_size_variants,
        retained_noncompressive_variants_per_entry=retained_bloat_variants,
        bundled_variants_per_window=(
            bundled_variant_mass / bundled_variant_weight
            if bundled_variant_weight > 0
            else 0.0
        ),
        phase_rechunk_derived_multiplier=(
            max(0.0, refresh.rho) * max(0.0, max_score - 1.0)
            if "rechunk" in refresh.name or "phase" in refresh.name or "permutation" in refresh.name
            else 0.0
        ),
        entry_count_before=entry_count,
        entry_count_after=next_state.entry_count,
    )
    return next_state, row


def normalize_rechunk_schedule(rechunk_bits: RechunkSchedule) -> tuple[int | None, ...]:
    if isinstance(rechunk_bits, tuple):
        if not rechunk_bits:
            raise ValueError("rechunk schedule must not be empty")
        return rechunk_bits
    return (rechunk_bits,)


def rechunk_bits_for_pass(rechunk_bits: RechunkSchedule, pass_i: int) -> int | None:
    schedule = normalize_rechunk_schedule(rechunk_bits)
    return schedule[min(pass_i, len(schedule) - 1)]


def rechunk_residual_bits(payload_bits: float, entry_bits: int | None) -> float:
    if entry_bits is None:
        return 0.0
    if entry_bits <= 0:
        raise ValueError("rechunk entry_bits must be positive")
    if payload_bits <= 0:
        return 0.0
    full = math.floor(payload_bits / entry_bits)
    residual = payload_bits - full * entry_bits
    if residual <= 1e-6 or residual >= entry_bits - 1e-6:
        return 0.0
    return max(0.0, residual)


def run_profile(
    entry_count: int,
    block_bits: int,
    arity_cap: int,
    depth_bits: int,
    passes: int,
    policy: str,
    superposition: SuperpositionConfig,
    refresh: RefreshRule,
    initial_literal_overhead_bits: int = LITERAL_ENTRY_OVERHEAD_BITS,
    rechunk_bits: RechunkSchedule = None,
) -> tuple[EntryState, list[PassLedgerRow]]:
    return run_scheduled_profile(
        entry_count,
        block_bits,
        arity_cap,
        (depth_bits,),
        passes,
        policy,
        superposition,
        refresh,
        initial_literal_overhead_bits,
        rechunk_bits,
    )


def run_scheduled_profile(
    entry_count: int,
    block_bits: int,
    arity_cap: int,
    depth_schedule_bits: tuple[int, ...],
    passes: int,
    policy: str,
    superposition: SuperpositionConfig,
    refresh: RefreshRule,
    initial_literal_overhead_bits: int = LITERAL_ENTRY_OVERHEAD_BITS,
    rechunk_bits: RechunkSchedule = None,
) -> tuple[EntryState, list[PassLedgerRow]]:
    if not depth_schedule_bits:
        raise ValueError("depth_schedule_bits must not be empty")
    state = initial_raw_state(entry_count, block_bits)
    rows: list[PassLedgerRow] = []
    for pass_i in range(passes):
        depth_bits = depth_schedule_bits[min(pass_i, len(depth_schedule_bits) - 1)]
        literal_overhead_bits = initial_literal_overhead_bits if pass_i == 0 else LITERAL_ENTRY_OVERHEAD_BITS
        state, row = run_pass(
            state,
            arity_cap,
            depth_bits,
            policy,
            superposition,
            refresh,
            literal_overhead_bits,
        )
        current_rechunk_bits = rechunk_bits_for_pass(rechunk_bits, pass_i)
        residual_bits = rechunk_residual_bits(state.payload_bits, current_rechunk_bits)
        state = state.rechunk(current_rechunk_bits)
        if current_rechunk_bits is not None:
            row = replace(
                row,
                entry_count_after=state.entry_count,
                rechunk_entry_bits=current_rechunk_bits,
                rechunk_residual_bits=residual_bits,
                rechunk_pad_bits=0.0,
            )
        rows.append(row)
    return state, rows


def validate_state_recurrence() -> dict[str, float | int]:
    state = initial_raw_state(10_000, 16)
    no_variants = SuperpositionConfig(0, 1, False, False)
    from refresh_model import by_name

    final, rows = run_profile(
        10_000,
        16,
        2,
        16,
        2,
        "left_to_right",
        no_variants,
        by_name("no_refresh"),
    )
    if not rows or final.entry_count <= 0:
        raise AssertionError("empty state recurrence")
    if rows[0].bits_after <= 0:
        raise AssertionError("invalid first pass bit count")
    return {
        "passes": len(rows),
        "entry_count_after": final.entry_count,
        "bits_after": final.total_charged_bits,
    }
