"""Current-layer entry-state recurrence with computed freshness.

Two corrections over the previous kernel revision, both required by the
operating contract:

1. **Freshness is modeled, not assumed.** The seed search is deterministic,
   so a window whose content and search depth are unchanged since its last
   search yields nothing new. Per pass, candidate windows split into a fresh
   mass (full M trials; replacement cascade, neutral swaps, permutation
   adjacency, or chunk-boundary shift) and a stale mass (only the incremental
   depth slice, zero on a flat depth schedule). The computed per-pass refresh
   coefficient is reported in the ledger.

2. **Chunk layers charge their discrimination channel.** A rechunked layer
   mixes records with verbatim chunks; the Kraft-complete record alphabet
   cannot self-discriminate and replacement positions are content-dependent.
   Channels: ``explicit_flag`` (1 bit per element, flags enlarge spans),
   ``implicit_selector`` (decode-by-replay; per-fire stuffing escapes charged
   from the exact Kraft ledger in ``implicit_selector.py``), or
   ``uncharged_diagnostic`` (the previous, undecodable accounting — kept only
   to quantify the old error; always fails the audit gate).
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, replace

from costs import LITERAL_ENTRY_OVERHEAD_BITS, min_record_bits
from hit_distribution import p_min_record_le, p_min_record_le_incremental
from implicit_selector import escape_economics
from refresh_model import RefreshRule
from selection_bounds import estimate_selection
from span_distribution import span_distributions
from superposition_model import (
    SuperpositionConfig,
    _expected_records_at_exact_cost,
    retained_bundle_variant_stats,
    variant_scores_for_lengths,
)


RechunkSchedule = int | tuple[int | None, ...] | None

RECHUNK_CHANNELS = ("records_only", "explicit_flag", "implicit_selector", "uncharged_diagnostic")


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
    changed_fraction: float = 1.0  # fraction of entries with new content last pass
    prev_depth_bits: int = 0  # deepest seed depth already searched on stale content
    layer_mode: str = "records"  # "records" or "chunks"
    rechunk_channel: str = "records_only"

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
        return replace(
            self,
            buckets={
                key: count * (1.0 - fraction)
                for key, count in self.buckets.items()
                if count * (1.0 - fraction) > 1e-12
            },
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
        return replace(self, buckets=dict(wrapped))

    def rechunk(self, entry_bits: int | None, channel: str = "uncharged_diagnostic") -> "EntryState":
        if entry_bits is None:
            return self
        if entry_bits <= 0:
            raise ValueError("rechunk entry_bits must be positive")
        if channel not in RECHUNK_CHANNELS or channel == "records_only":
            raise ValueError(f"chunk layers need a discrimination channel, got {channel!r}")
        chunk_count = self.payload_bits / entry_bits
        if channel == "explicit_flag":
            # Each element carries its 1-bit flag on the wire; spans and entry
            # sizes include it so the accounting is automatic.
            buckets = {EntryKey(entry_bits + 1, "chunk_flagged"): chunk_count}
        else:
            buckets = {EntryKey(entry_bits, "chunk"): chunk_count}
        return replace(
            self,
            buckets=buckets,
            layer_mode="chunks",
            rechunk_channel=channel,
            # Boundary phase shifts make chunk windows fresh provided at least
            # one upstream replacement changed the stream; the recurrence sets
            # this per pass.
            changed_fraction=1.0,
            prev_depth_bits=0,
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
    # Freshness accounting (new).
    fresh_fraction_arity1: float = 1.0
    fresh_fraction_multi: float = 1.0
    refresh_coefficient: float = 1.0  # window-mass-weighted fresh fraction
    neutral_swap_mass: float = 0.0
    incremental_depth_bits: int = 0  # delta-D available to stale windows
    stale_gain_bits: float = 0.0
    # Discrimination channel accounting (new).
    rechunk_channel: str = "records_only"
    discrimination_bits: float = 0.0  # flags or stuffing charged this pass
    escape_fire_rate_per_chunk: float = 0.0
    decode_replay_expansions: float = 0.0
    uncharged_passthrough: bool = False


def initial_raw_state(entry_count: int, block_bits: int) -> EntryState:
    return EntryState(
        {EntryKey(block_bits, "raw"): float(entry_count)},
        original_raw_bits=float(entry_count * block_bits),
    )


def _variant_summary(
    state: EntryState,
    depth_bits: int,
    superposition: SuperpositionConfig,
) -> tuple[dict[int, float], float, float, float, float]:
    lengths = list(state.length_pmf().keys())
    scores, stats = variant_scores_for_lengths(lengths, depth_bits, superposition, 1.0)
    pmf = state.length_pmf()
    avg_variants = sum(pmf[length] * stats[length].avg_variants for length in pmf)
    equal_size = sum(pmf[length] * stats[length].retained_by_excess.get(0, 0.0) for length in pmf)
    retained_bloat = sum(
        pmf[length] * sum(count for excess, count in stats[length].retained_by_excess.items() if excess > 0)
        for length in pmf
    )
    if avg_variants > superposition.max_variants_per_position + 1e-9:
        raise AssertionError(
            "earned variant expectation exceeded configured cap: "
            f"{avg_variants} > {superposition.max_variants_per_position}"
        )
    return scores, avg_variants, max(scores.values(), default=1.0), equal_size, retained_bloat


def _discount_combo_multiplier(optimistic_multiplier: float, arity: int) -> float:
    if optimistic_multiplier <= 1.0 or arity <= 1:
        return max(1.0, optimistic_multiplier)
    per_entry = optimistic_multiplier ** (1.0 / arity)
    return max(1.0, 1.0 + arity * (per_entry - 1.0))


def _neutral_swap_rate(state: EntryState, depth_bits: int) -> float:
    """Probability a content-fresh entry finds an equal-size arity-1 record."""

    pmf = state.length_pmf()
    rate = 0.0
    for length, prob in pmf.items():
        if length < min_record_bits(1):
            continue
        lam = _expected_records_at_exact_cost(length, length, depth_bits)
        rate += prob * -math.expm1(-lam)
    return rate


def _marked_window_stats(
    span_bits: int,
    arity: int,
    depth_bits: int,
    multiplier: float,
    record_extra_bits: int,
    prev_depth_bits: int,
    fresh: bool,
) -> tuple[float, float]:
    """(hit probability, expected net gain per window) for one channel.

    ``record_extra_bits`` charges the per-record disambiguation bit on
    flag/implicit chunk layers. Net gain g requires record cost
    r <= span - g - extra.
    """

    max_gain = span_bits - record_extra_bits - min_record_bits(min(arity, 5))
    if max_gain < 1:
        return 0.0, 0.0
    if fresh:
        hit = p_min_record_le(
            span_bits - 1 - record_extra_bits, span_bits, arity, depth_bits, multiplier
        )
        if hit <= 0:
            return 0.0, 0.0
        egain = 0.0
        for gain in range(1, max_gain + 1):
            egain += p_min_record_le(
                span_bits - gain - record_extra_bits, span_bits, arity, depth_bits, multiplier
            )
        return hit, egain
    # Stale window: only the new depth slice provides untried seeds, and
    # retained-variant combos were already searched, so no multiplier.
    hit = p_min_record_le_incremental(
        span_bits - 1 - record_extra_bits, span_bits, arity, depth_bits, prev_depth_bits, 1.0
    )
    if hit <= 0:
        return 0.0, 0.0
    egain = 0.0
    for gain in range(1, max_gain + 1):
        egain += p_min_record_le_incremental(
            span_bits - gain - record_extra_bits, span_bits, arity, depth_bits, prev_depth_bits, 1.0
        )
    return hit, egain


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
    chunk_layer = state.layer_mode == "chunks"
    channel = state.rechunk_channel if chunk_layer else "records_only"
    record_extra_bits = 1 if channel in ("explicit_flag", "implicit_selector") else 0

    scores, avg_variants, max_score, equal_size_variants, retained_bloat_variants = _variant_summary(
        state, depth_bits, superposition
    )
    span_buckets = span_distributions(state.length_pmf(), scores, arity_cap)

    # --- freshness fractions -------------------------------------------------
    u_prev = max(0.0, min(1.0, state.changed_fraction))
    incremental_depth = max(0, depth_bits - state.prev_depth_bits) if state.prev_depth_bits else 0
    swap_rate = _neutral_swap_rate(state, depth_bits) if refresh.neutral_swaps else 0.0
    swap_mass = entry_count * u_prev * swap_rate

    if chunk_layer:
        # Boundary phase shift from any upstream replacement refreshes chunk
        # windows; modeled fresh when the previous pass changed the stream.
        fresh_1 = 1.0 if u_prev > 0 else 0.0
        fresh_multi = fresh_1
    else:
        fresh_1 = u_prev
        fresh_multi = 1.0 if refresh.permutes_entries else 1.0 - (1.0 - u_prev) ** 2

    def fresh_fraction(arity: int) -> float:
        if arity == 1:
            return fresh_1
        if chunk_layer:
            return fresh_multi
        if refresh.permutes_entries:
            return 1.0
        return 1.0 - (1.0 - u_prev) ** arity

    add_records: dict[int, float] = defaultdict(float)
    accepted_windows = 0.0
    expected_gain_bits = 0.0
    stale_gain_bits = 0.0
    removed_entries = 0.0
    max_optimistic_multiplier = 1.0
    max_conservative_multiplier = 1.0
    max_discount_ratio = 1.0
    bundled_variant_mass = 0.0
    bundled_variant_weight = 0.0
    refresh_coeff_num = 0.0
    refresh_coeff_den = 0.0

    for arity in range(arity_cap, 0, -1):
        f_fresh = fresh_fraction(arity)
        for span in span_buckets[arity]:
            bundle_stats = retained_bundle_variant_stats(span.span_bits, arity, depth_bits, superposition)
            bundle_credit = bundle_stats.weighted_score - 1.0
            optimistic_multiplier = span.opportunity_multiplier + bundle_credit
            conservative_multiplier = (
                _discount_combo_multiplier(span.opportunity_multiplier, arity) + bundle_credit
            )
            # Floor onto a 1e-3 grid: keeps lru caches warm across passes and
            # only ever under-counts charged opportunity (conservative).
            conservative_multiplier = max(1.0, math.floor(conservative_multiplier * 1000.0) / 1000.0)
            max_optimistic_multiplier = max(max_optimistic_multiplier, optimistic_multiplier)
            max_conservative_multiplier = max(max_conservative_multiplier, conservative_multiplier)
            if optimistic_multiplier > 1.0:
                max_discount_ratio = max(
                    max_discount_ratio,
                    optimistic_multiplier / max(conservative_multiplier, 1e-300),
                )
            bundled_variant_mass += span.probability * max(0.0, bundle_stats.avg_variants - 1.0)
            bundled_variant_weight += span.probability

            hit_fresh, egain_fresh = _marked_window_stats(
                span.span_bits, arity, depth_bits, conservative_multiplier,
                record_extra_bits, state.prev_depth_bits, fresh=True,
            )
            hit_stale, egain_stale = _marked_window_stats(
                span.span_bits, arity, depth_bits, 1.0,
                record_extra_bits, state.prev_depth_bits, fresh=False,
            )
            hit = f_fresh * hit_fresh + (1.0 - f_fresh) * hit_stale
            egain = f_fresh * egain_fresh + (1.0 - f_fresh) * egain_stale
            refresh_coeff_num += span.probability * f_fresh
            refresh_coeff_den += span.probability
            if hit <= 0:
                continue
            selection = estimate_selection(entry_count, arity, hit, policy)
            denom = max(selection.candidate_windows * hit, 1e-300)
            scale = min(1.0, selection.accepted_windows / denom)
            bucket_windows = selection.candidate_windows * span.probability
            mass = bucket_windows * hit * scale
            if mass <= 0:
                continue
            gain_given_hit = egain / hit
            record_len = max(1, round(span.span_bits - gain_given_hit))
            add_records[record_len] += mass
            accepted_windows += mass
            expected_gain_bits += mass * gain_given_hit
            stale_gain_bits += bucket_windows * (1.0 - f_fresh) * egain_stale * scale
            removed_entries += mass * arity

    if removed_entries > entry_count * 0.98:
        downscale = (entry_count * 0.98) / max(removed_entries, 1e-300)
        add_records = defaultdict(float, {length: count * downscale for length, count in add_records.items()})
        accepted_windows *= downscale
        expected_gain_bits *= downscale
        stale_gain_bits *= downscale
        removed_entries *= downscale

    # --- discrimination channel charges --------------------------------------
    discrimination_bits = 0.0
    escape_fire_rate = 0.0
    replay_expansions = 0.0
    uncharged = False
    if chunk_layer:
        remaining_chunks = max(0.0, entry_count - removed_entries)
        if channel == "implicit_selector":
            eco = escape_economics(
                max(1, int(round(state.payload_bits / max(entry_count, 1.0)))),
                arity_cap,
                depth_bits,
            )
            escape_fire_rate = eco.fire_mass_per_chunk
            discrimination_bits = remaining_chunks * eco.stuff_bits_per_chunk + accepted_windows * 1.0
            replay_expansions = remaining_chunks * eco.fire_mass_per_chunk + accepted_windows
        elif channel == "explicit_flag":
            # Flags ride inside the (c+1)-bit chunk entries and the +1 record
            # marker is inside record_extra_bits; nothing extra here.
            discrimination_bits = 0.0
        elif channel == "uncharged_diagnostic":
            uncharged = True

    next_state = state.remove_proportionally(removed_entries)
    if wrap_unmatched:
        next_state = next_state.wrap_raw_literals(literal_overhead_bits)

    next_buckets = dict(next_state.buckets)
    for record_len, count in add_records.items():
        key = EntryKey(record_len, "seed")
        next_buckets[key] = next_buckets.get(key, 0.0) + count
    if discrimination_bits > 0:
        key = EntryKey(1, "stuff")
        next_buckets[key] = next_buckets.get(key, 0.0) + discrimination_bits

    entry_count_after = sum(next_buckets.values())
    records_added = sum(add_records.values())
    if wrap_unmatched or (chunk_layer and accepted_windows >= 1.0):
        changed_next = 1.0
    else:
        survivors = max(entry_count_after, 1.0)
        changed_next = max(
            0.0,
            min(
                1.0,
                (records_added + swap_mass * (1.0 - removed_entries / max(entry_count, 1.0))) / survivors,
            ),
        )

    next_state = EntryState(
        next_buckets,
        state.original_raw_bits,
        pass_index=state.pass_index + 1,
        accumulated_metadata_bits=state.accumulated_metadata_bits + refresh.metadata_bits_per_pass,
        changed_fraction=changed_next,
        prev_depth_bits=max(state.prev_depth_bits, depth_bits),
        layer_mode="records" if not chunk_layer else state.layer_mode,
        rechunk_channel="records_only" if not chunk_layer else state.rechunk_channel,
    )

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
            bundled_variant_mass / bundled_variant_weight if bundled_variant_weight > 0 else 0.0
        ),
        phase_rechunk_derived_multiplier=0.0,
        entry_count_before=entry_count,
        entry_count_after=entry_count_after,
        fresh_fraction_arity1=fresh_1,
        fresh_fraction_multi=fresh_multi,
        refresh_coefficient=(refresh_coeff_num / refresh_coeff_den if refresh_coeff_den > 0 else 0.0),
        neutral_swap_mass=swap_mass,
        incremental_depth_bits=incremental_depth,
        stale_gain_bits=stale_gain_bits,
        rechunk_channel=channel,
        discrimination_bits=discrimination_bits,
        escape_fire_rate_per_chunk=escape_fire_rate,
        decode_replay_expansions=replay_expansions,
        uncharged_passthrough=uncharged,
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
    rechunk_channel: str = "explicit_flag",
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
        rechunk_channel,
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
    rechunk_channel: str = "explicit_flag",
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
        if current_rechunk_bits is not None:
            state = state.rechunk(current_rechunk_bits, rechunk_channel)
            # The rechunk belongs to the pass that emitted this layer. Any wire
            # growth it causes (explicit flags) must land in THIS row's ledger,
            # not in the gap between rows.
            new_bits_after = state.total_charged_bits
            inflation = max(0.0, new_bits_after - row.bits_after)
            row = replace(
                row,
                bits_after=new_bits_after,
                net_delta_pct_current=(
                    100.0 * (row.bits_before - new_bits_after) / row.bits_before
                    if row.bits_before
                    else 0.0
                ),
                net_delta_pct_raw=(
                    100.0 * (row.bits_before - new_bits_after) / state.original_raw_bits
                    if state.original_raw_bits
                    else 0.0
                ),
                entry_count_after=state.entry_count,
                rechunk_entry_bits=current_rechunk_bits,
                rechunk_residual_bits=residual_bits,
                rechunk_pad_bits=0.0,
                discrimination_bits=row.discrimination_bits + inflation,
            )
        rows.append(row)
    return state, rows


def validate_state_recurrence() -> dict[str, float | int]:
    from refresh_model import by_name

    state = initial_raw_state(10_000, 16)
    no_variants = SuperpositionConfig(0, 1, False, False)
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


def validate_staleness() -> dict[str, float]:
    """no_refresh on a flat depth schedule must decay toward cascade-only."""

    from refresh_model import by_name

    no_variants = SuperpositionConfig(0, 1, False, False)
    _final, rows = run_profile(
        100_000,
        8,
        5,
        32,
        6,
        "greedy_largest_gain",
        no_variants,
        by_name("no_refresh"),
        initial_literal_overhead_bits=8,
    )
    late = [row.refresh_coefficient for row in rows[2:]]
    if late and max(late) > 0.5:
        raise AssertionError(f"no_refresh stayed implausibly fresh: {late}")
    fresh_perm = run_profile(
        100_000,
        8,
        5,
        32,
        6,
        "greedy_largest_gain",
        no_variants,
        by_name("deterministic_entry_permutation"),
        initial_literal_overhead_bits=8,
    )[1]
    if fresh_perm[3].fresh_fraction_multi < 0.999:
        raise AssertionError("permutation must keep multi-entry windows fresh")
    return {
        "no_refresh_late_coefficient_max": max(late) if late else 0.0,
        "permutation_multi_fresh": fresh_perm[3].fresh_fraction_multi,
    }
