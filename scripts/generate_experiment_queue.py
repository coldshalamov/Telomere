#!/usr/bin/env python3
"""Generate the next Telomere research experiment queue from current evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
SCORECARD_JSON = DOCS / "research_scorecard.json"
NEARMISS_JSON = DOCS / "nearmiss_forecast.json"
PREFIX_LADDER_JSON = DOCS / "prefix_ladder.json"
DEPTH3_PREFIX_JSON = DOCS / "depth3_prefix_probe.json"
DEPTH3_FOLLOWUP_JSON = DOCS / "depth3_compression_followup.json"
LEAD_DEPTH3_PREFIX_JSON = DOCS / "lead_depth3_prefix_probe.json"
LEAD_DEPTH3_FOLLOWUP_JSON = DOCS / "lead_depth3_compression_followup.json"
DEPTH3_FRONTIER_JSON = DOCS / "depth3_frontier_exact_discovery.json"
DEPTH4_SHARD_PLAN_JSON = DOCS / "depth4_shard_plan.json"
DEPTH4_PILOT_SHARD_JSON = DOCS / "depth4_pilot_shard.json"
SEARCH_FRONTIER_GATE_JSON = DOCS / "search_frontier_gate.json"
LONG_SPAN_BUNDLE_GATE_JSON = DOCS / "long_span_bundle_gate.json"
MECHANISM_EXPERIMENT_RANKING_JSON = DOCS / "mechanism_experiment_ranking.json"
SEED_TABLE_PRESET_PROBE_JSON = DOCS / "seed_table_preset_probe.json"
EXACT_SHORT_HIT_BUNDLE_ECONOMICS_JSON = (
    DOCS / "exact_short_hit_bundle_economics.json"
)
WHOLE_STREAM_RESIDUAL_VECTOR_PROBE_JSON = (
    DOCS / "whole_stream_residual_vector_probe.json"
)
EXPANDER_SALT_ENSEMBLE_JSON = DOCS / "expander_salt_ensemble.json"
SCHEMA_NATIVE_PUBLIC_DICTIONARIES_JSON = (
    DOCS / "schema_native_public_dictionaries.json"
)
SCHEMA_NATIVE_PUBLIC_DICTIONARY_REPLICATION_JSON = (
    DOCS / "schema_native_public_dictionary_replication.json"
)
SUPERPOSITION_TELEMETRY_JSON = DOCS / "superposition_telemetry.json"
RECURSIVE_STRUCTURED_FIXTURES_JSON = DOCS / "recursive_structured_fixtures.json"
SCALE_PERFORMANCE_JSON = DOCS / "scale_performance_report.json"
BOUNDED_STREAMING_MEMORY_JSON = DOCS / "bounded_streaming_memory_gate.json"
UI_WORKFLOW_SMOKE_JSON = DOCS / "ui_workflow_smoke.json"
FIFTH_BYTE_JSON = DOCS / "fifth_byte_residual.json"
FIFTH_STEERING_JSON = DOCS / "fifth_byte_steering.json"
CONTEXTUAL_STEERING_JSON = DOCS / "contextual_fifth_byte_steering.json"
TRANSFORM_VALIDATION_JSON = DOCS / "transform_validation.json"
CORPUS_GENERALIZATION_JSON = DOCS / "corpus_generalization_probe.json"
PERIODIC_PROBE_JSON = DOCS / "periodic_transform_probe.json"
COMPOSED_PROBE_JSON = DOCS / "composed_transform_probe.json"
STRUCTURAL_SEARCH_JSON = DOCS / "structural_transform_search.json"
BYTE_PERMUTATION_SEARCH_JSON = DOCS / "byte_permutation_transform_search.json"
BWT_MTF_PROBE_JSON = DOCS / "bwt_mtf_transform_probe.json"
GRAMMAR_CHANNEL_DISCOVERY_JSON = DOCS / "grammar_channel_match_discovery.json"
NUMERIC_VALUE_CHANNEL_DISCOVERY_JSON = (
    DOCS / "numeric_value_channel_match_discovery.json"
)
HELDOUT_CORPUS_EXPANSION_JSON = DOCS / "heldout_corpus_expansion.json"
RECORD_CONTEXT_SEARCH_JSON = DOCS / "record_context_transform_search.json"
TOKEN_DICTIONARY_SEARCH_JSON = DOCS / "token_dictionary_transform_search.json"
AFFINE_SEARCH_JSON = DOCS / "affine_transform_search.json"
RESIDUAL_STEERING_JSON = DOCS / "seed_manifold_residual_steering.json"
SIDECAR_BREAK_EVEN_JSON = DOCS / "sidecar_break_even.json"
RESIDUAL_PAYLOAD_COMPRESSIBILITY_JSON = DOCS / "residual_payload_compressibility.json"
EXPERIMENTAL_SIDECAR_DESCRIPTOR_JSON = DOCS / "experimental_sidecar_descriptor.json"
SIDECAR_RECORD_OVERHEAD_JSON = DOCS / "sidecar_record_overhead.json"
PACKED_SIDECAR_DESCRIPTOR_JSON = DOCS / "packed_sidecar_descriptor.json"
PACKED_SIDECAR_CONTROLS_JSON = DOCS / "packed_sidecar_controls.json"
GENERALIZED_PACKED_SIDECAR_JSON = DOCS / "generalized_packed_sidecar.json"
PACKED_SIDECAR_REPLICATION_JSON = DOCS / "packed_sidecar_replication.json"
MATCH_DISCOVERY_JSON = DOCS / "match_discovery.json"
ALIGNMENT_ARITY_DISCOVERY_JSON = DOCS / "alignment_arity_discovery.json"
TRANSFORMED_MATCH_DISCOVERY_JSON = DOCS / "transformed_match_discovery.json"
LEAD_EXACT_DISCOVERY_JSON = DOCS / "lead_exact_discovery.json"
VIABILITY_JSON = DOCS / "viability.json"
ACCELERATION_JSON = DOCS / "acceleration_report.json"
GOAL_AUDIT_JSON = DOCS / "goal_audit.json"
SWEEPS_JSON = DOCS / "sweeps.json"
QUEUE_JSON = DOCS / "experiment_queue.json"
QUEUE_MD = DOCS / "EXPERIMENT_QUEUE.md"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_hashes() -> dict[str, str]:
    return {
        "research_scorecard_sha256": sha256(SCORECARD_JSON),
        "nearmiss_forecast_sha256": sha256(NEARMISS_JSON),
        "prefix_ladder_sha256": sha256(PREFIX_LADDER_JSON),
        "depth3_prefix_probe_sha256": sha256(DEPTH3_PREFIX_JSON),
        "depth3_compression_followup_sha256": sha256(DEPTH3_FOLLOWUP_JSON),
        "lead_depth3_prefix_probe_sha256": sha256(LEAD_DEPTH3_PREFIX_JSON),
        "lead_depth3_compression_followup_sha256": sha256(LEAD_DEPTH3_FOLLOWUP_JSON),
        "depth3_frontier_exact_discovery_sha256": sha256(DEPTH3_FRONTIER_JSON),
        "depth4_shard_plan_sha256": sha256(DEPTH4_SHARD_PLAN_JSON),
        "depth4_pilot_shard_sha256": sha256(DEPTH4_PILOT_SHARD_JSON),
        "search_frontier_gate_sha256": sha256(SEARCH_FRONTIER_GATE_JSON),
        "long_span_bundle_gate_sha256": sha256(LONG_SPAN_BUNDLE_GATE_JSON),
        "mechanism_experiment_ranking_sha256": sha256(
            MECHANISM_EXPERIMENT_RANKING_JSON
        ),
        "seed_table_preset_probe_sha256": sha256(SEED_TABLE_PRESET_PROBE_JSON),
        "exact_short_hit_bundle_economics_sha256": sha256(
            EXACT_SHORT_HIT_BUNDLE_ECONOMICS_JSON
        ),
        "whole_stream_residual_vector_probe_sha256": sha256(
            WHOLE_STREAM_RESIDUAL_VECTOR_PROBE_JSON
        ),
        "expander_salt_ensemble_sha256": sha256(EXPANDER_SALT_ENSEMBLE_JSON),
        "schema_native_public_dictionaries_sha256": sha256(
            SCHEMA_NATIVE_PUBLIC_DICTIONARIES_JSON
        ),
        "schema_native_public_dictionary_replication_sha256": sha256(
            SCHEMA_NATIVE_PUBLIC_DICTIONARY_REPLICATION_JSON
        ),
        "superposition_telemetry_sha256": sha256(SUPERPOSITION_TELEMETRY_JSON),
        "recursive_structured_fixtures_sha256": sha256(
            RECURSIVE_STRUCTURED_FIXTURES_JSON
        ),
        "scale_performance_report_sha256": sha256(SCALE_PERFORMANCE_JSON),
        "bounded_streaming_memory_gate_sha256": sha256(BOUNDED_STREAMING_MEMORY_JSON),
        "ui_workflow_smoke_sha256": sha256(UI_WORKFLOW_SMOKE_JSON),
        "fifth_byte_residual_sha256": sha256(FIFTH_BYTE_JSON),
        "fifth_byte_steering_sha256": sha256(FIFTH_STEERING_JSON),
        "contextual_fifth_byte_steering_sha256": sha256(CONTEXTUAL_STEERING_JSON),
        "corpus_generalization_probe_sha256": sha256(CORPUS_GENERALIZATION_JSON),
        "transform_validation_sha256": sha256(TRANSFORM_VALIDATION_JSON),
        "periodic_transform_probe_sha256": sha256(PERIODIC_PROBE_JSON),
        "composed_transform_probe_sha256": sha256(COMPOSED_PROBE_JSON),
        "structural_transform_search_sha256": sha256(STRUCTURAL_SEARCH_JSON),
        "byte_permutation_transform_search_sha256": sha256(BYTE_PERMUTATION_SEARCH_JSON),
        "bwt_mtf_transform_probe_sha256": sha256(BWT_MTF_PROBE_JSON),
        "grammar_channel_match_discovery_sha256": sha256(GRAMMAR_CHANNEL_DISCOVERY_JSON),
        "numeric_value_channel_match_discovery_sha256": sha256(
            NUMERIC_VALUE_CHANNEL_DISCOVERY_JSON
        ),
        "heldout_corpus_expansion_sha256": sha256(HELDOUT_CORPUS_EXPANSION_JSON),
        "record_context_transform_search_sha256": sha256(RECORD_CONTEXT_SEARCH_JSON),
        "token_dictionary_transform_search_sha256": sha256(TOKEN_DICTIONARY_SEARCH_JSON),
        "affine_transform_search_sha256": sha256(AFFINE_SEARCH_JSON),
        "seed_manifold_residual_steering_sha256": sha256(RESIDUAL_STEERING_JSON),
        "sidecar_break_even_sha256": sha256(SIDECAR_BREAK_EVEN_JSON),
        "residual_payload_compressibility_sha256": sha256(
            RESIDUAL_PAYLOAD_COMPRESSIBILITY_JSON
        ),
        "experimental_sidecar_descriptor_sha256": sha256(
            EXPERIMENTAL_SIDECAR_DESCRIPTOR_JSON
        ),
        "sidecar_record_overhead_sha256": sha256(SIDECAR_RECORD_OVERHEAD_JSON),
        "packed_sidecar_descriptor_sha256": sha256(PACKED_SIDECAR_DESCRIPTOR_JSON),
        "packed_sidecar_controls_sha256": sha256(PACKED_SIDECAR_CONTROLS_JSON),
        "generalized_packed_sidecar_sha256": sha256(GENERALIZED_PACKED_SIDECAR_JSON),
        "packed_sidecar_replication_sha256": sha256(PACKED_SIDECAR_REPLICATION_JSON),
        "match_discovery_sha256": sha256(MATCH_DISCOVERY_JSON),
        "alignment_arity_discovery_sha256": sha256(ALIGNMENT_ARITY_DISCOVERY_JSON),
        "transformed_match_discovery_sha256": sha256(TRANSFORMED_MATCH_DISCOVERY_JSON),
        "lead_exact_discovery_sha256": sha256(LEAD_EXACT_DISCOVERY_JSON),
        "viability_sha256": sha256(VIABILITY_JSON),
        "acceleration_report_sha256": sha256(ACCELERATION_JSON),
        "goal_audit_sha256": sha256(GOAL_AUDIT_JSON),
        "sweeps_sha256": sha256(SWEEPS_JSON),
    }


def stable_projection(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if key != "generated_at"
    }


def largest_scale_row(sweeps: dict[str, Any]) -> dict[str, Any] | None:
    scale_rows = [
        row for row in sweeps.get("results", []) if row.get("group") == "memory-scaling"
    ]
    return max(scale_rows, key=lambda row: row["input_bytes"], default=None)


def queue_items(
    scorecard: dict[str, Any],
    nearmiss: dict[str, Any],
    prefix_ladder: dict[str, Any],
    depth3_prefix: dict[str, Any],
    depth3_followup: dict[str, Any],
    lead_depth3_prefix: dict[str, Any],
    lead_depth3_followup: dict[str, Any],
    depth3_frontier: dict[str, Any],
    depth4_shard_plan: dict[str, Any],
    depth4_pilot_shard: dict[str, Any],
    search_frontier_gate: dict[str, Any],
    long_span_bundle_gate: dict[str, Any],
    mechanism_experiment_ranking: dict[str, Any],
    seed_table_preset_probe: dict[str, Any],
    exact_short_hit_bundle_economics: dict[str, Any],
    whole_stream_residual_vector_probe: dict[str, Any],
    expander_salt_ensemble: dict[str, Any],
    schema_native_public_dictionaries: dict[str, Any],
    schema_native_public_dictionary_replication: dict[str, Any],
    superposition_telemetry: dict[str, Any],
    recursive_structured_fixtures: dict[str, Any],
    scale_performance: dict[str, Any],
    bounded_streaming_memory: dict[str, Any],
    ui_workflow_smoke: dict[str, Any],
    fifth_byte: dict[str, Any],
    fifth_steering: dict[str, Any],
    contextual_steering: dict[str, Any],
    corpus_generalization: dict[str, Any],
    transform_validation: dict[str, Any],
    periodic_probe: dict[str, Any],
    composed_probe: dict[str, Any],
    structural_search: dict[str, Any],
    byte_permutation_search: dict[str, Any],
    bwt_mtf_probe: dict[str, Any],
    grammar_channel_discovery: dict[str, Any],
    numeric_value_channel_discovery: dict[str, Any],
    heldout_corpus_expansion: dict[str, Any],
    record_context_search: dict[str, Any],
    token_dictionary_search: dict[str, Any],
    affine_search: dict[str, Any],
    residual_steering: dict[str, Any],
    sidecar_break_even: dict[str, Any],
    residual_payload_compressibility: dict[str, Any],
    experimental_sidecar_descriptor: dict[str, Any],
    sidecar_record_overhead: dict[str, Any],
    packed_sidecar_descriptor: dict[str, Any],
    packed_sidecar_controls: dict[str, Any],
    generalized_packed_sidecar: dict[str, Any],
    packed_sidecar_replication: dict[str, Any],
    match_discovery: dict[str, Any],
    alignment_arity_discovery: dict[str, Any],
    transformed_match_discovery: dict[str, Any],
    lead_exact_discovery: dict[str, Any],
    viability: dict[str, Any],
    acceleration: dict[str, Any],
    goal_audit: dict[str, Any],
    sweeps: dict[str, Any],
) -> list[dict[str, Any]]:
    best_nearmiss = nearmiss["summary"]
    ladder = prefix_ladder["summary"]
    depth3 = depth3_prefix["summary"]
    depth3_actual = depth3_followup["summary"]
    lead_depth3 = lead_depth3_prefix["summary"]
    lead_depth3_actual = lead_depth3_followup["summary"]
    depth3_frontier_summary = depth3_frontier["summary"]
    depth4_gate = depth4_shard_plan["promotion_gate"]
    depth4_estimates = depth4_shard_plan["depth4_estimates"]
    depth4_pilot = depth4_pilot_shard["summary"]
    search_gate = search_frontier_gate["summary"]
    long_span_gate = long_span_bundle_gate["summary"]
    mechanism_ranking = mechanism_experiment_ranking["summary"]
    seed_table = seed_table_preset_probe["summary"]
    exact_short = exact_short_hit_bundle_economics["summary"]
    whole_stream = whole_stream_residual_vector_probe["summary"]
    expander_salt = expander_salt_ensemble["summary"]
    schema_native = schema_native_public_dictionaries["summary"]
    schema_replication = schema_native_public_dictionary_replication["summary"]
    superposition = superposition_telemetry["summary"]
    recursive_structured = recursive_structured_fixtures["summary"]
    scale_performance_summary = scale_performance["summary"]
    bounded_memory = bounded_streaming_memory["summary"]
    ui_workflow_summary = ui_workflow_smoke["summary"]
    rankings = mechanism_experiment_ranking["rankings"]
    consumed_lanes = set()
    if not seed_table["promotion_met"]:
        consumed_lanes.add("seed-table-preset-probe")
    if not exact_short["promotion_met"]:
        consumed_lanes.add("exact-short-hit-bundle-economics")
    if not whole_stream["promotion_met"]:
        consumed_lanes.add("whole-stream-residual-vector-probe")
    if not expander_salt["promotion_met"]:
        consumed_lanes.add("expander-salt-ensemble")
    consumed_lanes.add("schema-native-public-dictionaries")
    if superposition["promotion_met"]:
        consumed_lanes.add("candidate-lattice-telemetry")
    if not recursive_structured["promotion_met"]:
        consumed_lanes.add("recursive-structured-fixtures")
    mechanism_ready = next(
        (
            row
            for row in rankings
            if row["status"] == "ready" and row["lane_id"] not in consumed_lanes
        ),
        None,
    )
    mechanism_top = mechanism_ready or next(
        (row for row in rankings if row["status"] == "gated"),
        rankings[0],
    )
    fifth = fifth_byte["summary"]
    steering = fifth_steering["summary"]
    contextual = contextual_steering["summary"]
    generalization = corpus_generalization["summary"]
    validation = transform_validation["summary"]
    periodic = periodic_probe["summary"]
    composed = composed_probe["summary"]
    structural = structural_search["summary"]
    byte_permutation = byte_permutation_search["summary"]
    bwt_mtf = bwt_mtf_probe["summary"]
    grammar_channel = grammar_channel_discovery["summary"]
    numeric_value_channel = numeric_value_channel_discovery["summary"]
    heldout_expansion = heldout_corpus_expansion["summary"]
    record_context = record_context_search["summary"]
    token_dictionary = token_dictionary_search["summary"]
    affine = affine_search["summary"]
    residual = residual_steering["summary"]
    sidecar = sidecar_break_even["summary"]
    residual_payload = residual_payload_compressibility["summary"]
    experimental_sidecar = experimental_sidecar_descriptor["summary"]
    sidecar_record = sidecar_record_overhead["summary"]
    packed_sidecar = packed_sidecar_descriptor["summary"]
    packed_controls = packed_sidecar_controls["summary"]
    generalized_packed = generalized_packed_sidecar["summary"]
    packed_replication = packed_sidecar_replication["summary"]
    match_discovery_summary = match_discovery["summary"]
    alignment_summary = alignment_arity_discovery["summary"]
    transformed_match_summary = transformed_match_discovery["summary"]
    lead_exact_summary = lead_exact_discovery["summary"]
    acceleration_status = acceleration["detected"]["status"]
    open_questions = viability["open_questions"]
    audit_counts = goal_audit["status_counts"]
    scale = largest_scale_row(sweeps)
    scale_mib = f"{scale['input_bytes'] / (1024 * 1024):.0f} MiB" if scale else "no"
    scale_telemetry = scale.get("telemetry", {}) if scale else {}
    scale_target_table_mib = scale_telemetry.get(
        "tier_estimated_target_table_mib_total", 0
    )
    scale_peak_mib = scale.get("peak_memory_mib") if scale else None
    scale_peak_ratio = (
        scale_peak_mib / scale_target_table_mib
        if scale_peak_mib is not None and scale_target_table_mib
        else None
    )
    scale_ratio_text = (
        f" with peak/estimated-table ratio {scale_peak_ratio:.2f}"
        if scale_peak_ratio is not None
        else ""
    )
    long_span_status = (
        "ready" if long_span_gate["promotion_met"] else "blocked-by-evidence"
    )
    top_action = (
        "Use the generated long-span bundle gate as the source of truth; "
        f"do not run broad long-span sweeps while it reports "
        f"{long_span_gate['gate_met_count']} of {long_span_gate['gate_count']} "
        "gates met."
        if not long_span_gate["promotion_met"]
        else (
            "The generated long-span bundle gate is open; replace this gate "
            "with a narrowly scoped sweep artifact before any broad compute run."
        )
    )

    return [
        {
            "rank": 1,
            "lane": "long-span-bundle-gate",
            "status": long_span_status,
            "parallel_group": "corpus-transform",
            "action": top_action,
            "why_now": (
                f"MECHANISM_EXPERIMENT_RANKING ranks {mechanism_ranking['top_lane_id']} "
                f"as the top lane, with {mechanism_ranking['ready_count']} ready lanes, "
                f"{mechanism_ranking['gated_count']} gated lanes, "
                f"{mechanism_ranking['blocked_by_evidence_count']} blocked lanes, and "
                f"natural-corpus compression proven "
                f"{mechanism_ranking['natural_corpus_compression_proven']}. "
                f"SEED_TABLE_PRESET_PROBE then found "
                f"{seed_table['canonical_selected_spans']} canonical selected spans, "
                f"{seed_table['canonical_ordinary_heldout_negative_groups']} ordinary "
                f"held-out negative groups, {seed_table['canonical_control_negative_groups']} "
                f"control negative groups, and promotion met {seed_table['promotion_met']}; "
                f"EXACT_SHORT_HIT_BUNDLE_ECONOMICS then reconstructed "
                f"{exact_short['reconstructed_exact_hits']} verified short hits, "
                f"found a zero-overhead lower bound of "
                f"{exact_short['zero_overhead_best_delta_bytes']} bytes, "
                f"{exact_short['full_stream_negative_rows']} full-stream negative rows, "
                f"{exact_short['full_stream_control_negative_groups']} control negative groups, "
                f"short-hit density comparable "
                f"{exact_short['control_density']['control_density_comparable']}, "
                f"and promotion met {exact_short['promotion_met']}; "
                f"WHOLE_STREAM_RESIDUAL_VECTOR_PROBE then tested global residual entropy "
                f"and bitplane/vector channels over "
                f"{whole_stream['honest_encoded_rows']} honest encoded rows, "
                f"found {whole_stream['honest_full_stream_negative_rows']} honest "
                f"full-stream negative rows, "
                f"{whole_stream['ordinary_heldout_negative_groups']} ordinary held-out "
                f"negative groups, {whole_stream['control_negative_groups']} control "
                f"negative groups, controls null "
                f"{whole_stream['control_negative_groups'] == 0}, measured residual coding "
                f"near entropy bound "
                f"{whole_stream['measured_residual_coding_near_entropy_bound']}, "
                f"and promotion met {whole_stream['promotion_met']}; "
                f"EXPANDER_SALT_ENSEMBLE then tested "
                f"{expander_salt['predeclared_salt_count']} predeclared expander salts, "
                f"found {expander_salt['salted_exact_hits']} salted exact hits "
                f"against {expander_salt['salted_expected_exact_hits']:.6g} expected, "
                f"random-trial multiplier exceeded "
                f"{expander_salt['random_trial_multiplier_exceeded']}, "
                f"{expander_salt['salted_selected_span_rows']} selected-span rows, "
                f"{expander_salt['full_stream_negative_rows']} full-stream negative rows, "
                f"{expander_salt['control_negative_groups']} control negative groups, "
                f"and promotion met {expander_salt['promotion_met']}; "
                f"SCHEMA_NATIVE_PUBLIC_DICTIONARIES then tested "
                f"{schema_native['public_entry_count']} frozen public entries across "
                f"{schema_native['mode_count']} modes, found "
                f"{schema_native['family_selected_spans']} family selected spans, "
                f"{schema_native['family_ordinary_heldout_negative_groups']} ordinary "
                f"held-out negative groups, {schema_native['family_control_negative_groups']} "
                f"family control negative groups, "
                f"{schema_native['wrong_schema_ordinary_negative_groups']} wrong-schema "
                f"negative groups, {schema_native['random_table_ordinary_negative_groups']} "
                f"same-size random negative groups, "
                f"{schema_native['shadow_ordinary_negative_groups']} shadow negative groups, "
                f"beats generic dictionary baseline "
                f"{schema_native['beats_generic_dictionary_baseline']}, and promotion met "
                f"{schema_native['promotion_met']}; "
                f"SCHEMA_NATIVE_PUBLIC_DICTIONARY_REPLICATION then tested "
                f"{schema_replication['corpus_count']} frozen replication corpora, found "
                f"{schema_replication['standards_selected_spans']} standards selected spans, "
                f"{schema_replication['standards_ordinary_negative_groups']} ordinary "
                f"negative groups, {schema_replication['standards_control_negative_groups']} "
                f"standards control negative groups, "
                f"{schema_replication['generic_ordinary_negative_groups']} generic "
                f"ordinary negative groups, claim level "
                f"{schema_replication['claim_level']}, and promotion met "
                f"{schema_replication['promotion_met']}; "
                f"SUPERPOSITION_TELEMETRY then tested "
                f"{superposition['fixture_count']} deterministic fixtures with "
                f"{superposition['candidate_count']} candidates, retained "
                f"{superposition['retained_alternative_count']} alternatives, "
                f"found {superposition['weighted_extra_savings']} weighted extra "
                f"savings over greedy, explained "
                f"{superposition['explained_discard_count']} discarded candidates "
                f"with {superposition['unexplained_discard_count']} unexplained "
                f"discards, and promotion met {superposition['promotion_met']}; "
                f"RECURSIVE_STRUCTURED_FIXTURES then tested "
                f"{recursive_structured['fixture_count']} CLI-verified fixtures, found "
                f"{recursive_structured['ordinary_later_win_families']} ordinary later-win "
                f"families, {recursive_structured['planted_offset_later_win_families']} "
                f"planted offset later-win families, claim level "
                f"{recursive_structured['claim_level']}, and promotion met "
                f"{recursive_structured['promotion_met']}; "
                f"LONG_SPAN_BUNDLE_GATE then consolidated these signals into "
                f"{long_span_gate['gate_met_count']} of {long_span_gate['gate_count']} "
                f"gates met, recommendation {long_span_gate['recommendation']}, "
                f"selected-span frontier {long_span_gate['selected_span_total']}, "
                f"best non-planted forecast "
                f"{long_span_gate['best_non_planted_gib_for_one_expected_hit']:.3g} GiB, "
                f"raw-suffix observed prefix "
                f"{long_span_gate['max_observed_heldout_forced_prefix_len']} vs required "
                f"{long_span_gate['minimum_raw_suffix_negative_prefix_len']}, "
                f"short-hit control groups "
                f"{long_span_gate['exact_short_control_negative_groups']}, "
                f"schema replication claim {long_span_gate['schema_replication_claim_level']}, "
                f"and claim level {long_span_gate['claim_level']}; "
                f"the queue therefore blocks broad long-span bundle sweeps. "
                f"Best near miss {best_nearmiss['best_non_planted_case']} still expects "
                f"{best_nearmiss['best_non_planted_expected_exact_hits']:.3e} exact hits in observed bytes, "
                f"and periodic masks currently show prefix>=5 uplift in "
                f"{periodic['heldout_prefix5_win_corpora']} held-out corpora, "
                f"composed context+periodic probes show prefix>=5 uplift in "
                f"{composed['heldout_prefix5_win_corpora']} held-out corpora and "
                f"{composed['heldout_exact_hits']} held-out exact hits, "
                f"while the ladder diagnostic shows "
                f"{ladder['heldout_rows_with_prefix5']} held-out/control rows at prefix>=5. "
                f"The fifth-byte residual diagnostic tops out at "
                f"{fifth['robust_best_xor_residual_coverage']:.1%} robust XOR coverage, "
                f"and residual-derived steering masks produced "
                f"{steering['cross_prefix5_win_rows']} cross-corpus prefix>=5 win rows; "
                f"contextual steering checked {contextual['candidate_count']} masks and produced "
                f"{contextual['cross_prefix5_win_rows']} prefix>=5 win rows. "
                f"Corpus generalization controls scanned "
                f"{generalization['target_span_count']} spans across "
                f"{generalization['control_count']} controls and found "
                f"{generalization['rows_with_prefix_ge_5']} prefix>=5 rows and "
                f"{generalization['total_exact_hits']} exact hits. "
                f"Vocabulary-disjoint transform validation produced "
                f"{validation['shadow_prefix5_win_corpora']} shadow prefix>=5 win corpora and "
                f"{validation['binary_exact_hits']} binary exact hits. "
                f"The bounded structural search checked {structural['candidate_count']} candidates over "
                f"{structural['validation_rows']} rows and found "
                f"{structural['heldout_prefix5_win_corpora']} held-out prefix>=5 win corpora, "
                f"{structural['heldout_exact_hits']} held-out exact hits, and "
                f"{structural['binary_exact_hits']} binary exact hits. "
                f"The byte-permutation transform search checked "
                f"{byte_permutation['transform_count']} candidates over "
                f"{byte_permutation['row_count']} rows and found "
                f"{byte_permutation['rows_with_prefix_ge_5']} prefix>=5 rows, "
                f"{byte_permutation['total_exact_hits']} exact hits, "
                f"{byte_permutation['total_selected_spans']} selected spans, and "
                f"{byte_permutation['rows_negative_after_metadata']} rows negative after metadata. "
                f"The BWT/MTF classic-preconditioner probe checked "
                f"{bwt_mtf['transform_count']} candidates over "
                f"{bwt_mtf['row_count']} rows and found "
                f"{bwt_mtf['rows_with_prefix_ge_5']} prefix>=5 rows, "
                f"{bwt_mtf['total_exact_hits']} exact hits, "
                f"{bwt_mtf['total_selected_spans']} selected spans, "
                f"{bwt_mtf['rows_negative_after_metadata']} rows negative after metadata, and "
                f"{bwt_mtf['rows_with_shorter_transformed_payload']} shorter transformed-payload rows that are transform-only diagnostics. "
                f"The grammar/channel match discovery checked "
                f"{grammar_channel['channel_count']} channels over "
                f"{grammar_channel['row_count']} rows and found "
                f"{grammar_channel['rows_with_prefix_ge_5']} prefix>=5 rows, "
                f"{grammar_channel['total_exact_hits']} exact hits, "
                f"{grammar_channel['total_selected_spans']} selected spans, and "
                f"{grammar_channel['rows_negative_after_metadata']} rows negative after metadata. "
                f"The numeric value-channel search then parsed "
                f"{numeric_value_channel['parsed_value_count']} values across "
                f"{numeric_value_channel['row_count']} rows and found "
                f"{numeric_value_channel['rows_with_prefix_ge_5']} prefix>=5 rows, "
                f"{numeric_value_channel['total_exact_hits']} exact hits, "
                f"{numeric_value_channel['total_selected_spans']} selected spans, and "
                f"{numeric_value_channel['rows_negative_after_metadata']} rows negative after metadata. "
                f"The held-out corpus expansion then audited "
                f"{heldout_expansion['corpus_count']} frozen replication corpora outside the "
                f"canonical matrix, scanned {heldout_expansion['target_span_count']} raw spans, "
                f"and found {heldout_expansion['rows_with_prefix_ge_5']} prefix>=5 rows, "
                f"{heldout_expansion['rows_with_exact_hits']} exact-hit rows, and "
                f"{heldout_expansion['rows_with_selected_spans']} selected-span rows. "
                f"The record/context transform search checked "
                f"{record_context['transform_count']} candidates over "
                f"{record_context['row_count']} rows and found "
                f"{record_context['rows_with_prefix_ge_5']} prefix>=5 rows, "
                f"{record_context['total_exact_hits']} exact hits, "
                f"{record_context['total_selected_spans']} selected spans, and "
                f"{record_context['rows_negative_after_metadata']} rows negative after metadata. "
                f"The token/dictionary transform search checked "
                f"{token_dictionary['transform_count']} candidates over "
                f"{token_dictionary['row_count']} rows and found "
                f"{token_dictionary['rows_with_prefix_ge_5']} prefix>=5 rows, "
                f"{token_dictionary['total_exact_hits']} exact hits, "
                f"{token_dictionary['total_selected_spans']} selected spans, and "
                f"{token_dictionary['rows_negative_after_metadata']} rows negative after metadata. "
                f"Affine remaps searched {affine['searched_candidate_count']} candidates and found "
                f"{affine['heldout_prefix4_win_corpora']} held-out prefix>=4 win corpora, but "
                f"{affine['heldout_prefix5_win_corpora']} held-out prefix>=5 win corpora and "
                f"{affine['heldout_exact_hits']} held-out exact hits. "
                f"Residual-sidecar steering found {residual['heldout_forced_rows']} held-out forced rows "
                f"and {residual['heldout_seed_contribution_positive_rows']} rows with positive seed contribution, "
                f"but {residual['heldout_positive_rows']} held-out positive net-delta rows; best held-out net delta "
                f"{residual['best_heldout_net_delta_bytes']} bytes. "
                f"The longer-span sidecar break-even report shows raw-suffix strict gain starts at prefix "
                f"{sidecar['minimum_raw_suffix_negative_prefix_len']}, current held-out forced prefixes stop at "
                f"{sidecar['max_observed_heldout_forced_prefix_len']}, raw-suffix viable rows at observed prefix "
                f"{sidecar['raw_suffix_viable_at_observed_prefix_rows']}, and sublinear-model viable rows "
                f"{sidecar['sublinear_model_viable_at_observed_prefix_rows']}. "
                f"Residual payload compressibility then found "
                f"{residual_payload['measured_heldout_negative_rows']} measured held-out negative row; "
                f"best measured case {residual_payload['best_measured_heldout_negative_case']} with "
                f"zlib best delta "
                f"{residual_payload['best_heldout_net_delta_by_policy']['zlib_level9']} bytes. "
                f"The experimental descriptor decoded {experimental_sidecar['decode_verified_rows']} rows "
                f"and rejected corrupt inputs, but full-stream negative rows stayed "
                f"{experimental_sidecar['full_stream_negative_rows']} with best full delta "
                f"{experimental_sidecar['best_full_stream_delta_bytes']} bytes. "
                f"The sidecar record-overhead budget found "
                f"{sidecar_record['negative_layout_rows']} negative layout rows; best safe layout "
                f"{sidecar_record['best_safe_layout']} reaches "
                f"{sidecar_record['best_safe_delta_bytes']} bytes. "
                f"The packed sidecar descriptor then decoded "
                f"{packed_sidecar['decode_verified_rows']} rows, rejected corruption, and found "
                f"{packed_sidecar['full_stream_negative_rows']} full-stream negative rows with best delta "
                f"{packed_sidecar['best_delta_bytes']} bytes. "
                f"Controls encoded {packed_controls['encoded_rows']} of "
                f"{packed_controls['control_rows']} rows, found "
                f"{packed_controls['unique_negative_cases']} unique negative cases and "
                f"{packed_controls['ordinary_heldout_negative_cases']} ordinary held-out negative case. "
                f"The generalized packed sidecar offset and seed modes encoded "
                f"{generalized_packed['unique_encoded_source_rows']} unique source rows and "
                f"{generalized_packed['encoded_rows']} mode/coder rows, but ordinary held-out "
                f"negative cases stayed at "
                f"{generalized_packed['ordinary_heldout_negative_cases']}. "
                f"The packed sidecar replication control-matrix then tested "
                f"{packed_replication['corpus_count']} frozen corpora, "
                f"{packed_replication['source_case_count']} source cases, and "
                f"{packed_replication['descriptor_row_count']} descriptor rows, producing "
                f"{packed_replication['full_stream_negative_rows']} full-stream negative rows "
                f"and {packed_replication['ordinary_heldout_negative_groups']} ordinary held-out "
                f"negative groups. Match discovery scanned "
                f"{match_discovery_summary['target_span_count']} target spans across "
                f"{match_discovery_summary['corpus_count']} corpora, with "
                f"{match_discovery_summary['rows_with_prefix_ge_5']} rows at prefix>=5, "
                f"{match_discovery_summary['rows_with_exact_hits']} rows with exact hits, "
                f"{match_discovery_summary['rows_with_selected_spans']} rows with selected spans, "
                f"and {match_discovery_summary['ordinary_heldout_selected_groups']} ordinary held-out "
                f"selected groups. Alignment/arity discovery then scanned "
                f"{alignment_summary['target_span_count']} target spans across "
                f"{alignment_summary['row_count']} rows, with "
                f"{alignment_summary['rows_with_prefix_ge_5']} rows at prefix>=5, "
                f"{alignment_summary['total_exact_hits']} exact hits, "
                f"{alignment_summary['total_positive_exact_hits']} positive exact hits, "
                f"and {alignment_summary['total_selected_spans']} selected spans. "
                f"Transformed match discovery applied "
                f"{transformed_match_summary['transform_count']} frozen transforms over "
                f"{transformed_match_summary['target_span_count']} target spans and found "
                f"{transformed_match_summary['rows_with_prefix_ge_5']} prefix>=5 rows, "
                f"{transformed_match_summary['total_exact_hits']} exact hits, "
                f"{transformed_match_summary['total_selected_spans']} selected spans, and "
                f"{transformed_match_summary['metadata_profitable_rows']} metadata-profitable rows. "
                f"Selected-lead exact discovery then scanned "
                f"{lead_exact_summary['target_span_count']} transformed target spans across "
                f"{lead_exact_summary['lead_count']} selected affine/periodic/composed leads and found "
                f"{lead_exact_summary['rows_with_prefix_ge_5']} prefix>=5 rows, "
                f"{lead_exact_summary['total_exact_hits']} exact hits, "
                f"{lead_exact_summary['total_selected_spans']} selected spans, and "
                f"{lead_exact_summary['metadata_profitable_rows']} metadata-profitable rows. "
                "Blind scale-up is not justified."
            ),
            "promotion_gate": "Open this lane only when LONG_SPAN_BUNDLE_GATE reports every prerequisite gate met or an intentional override is documented with new evidence.",
            "stop_rule": long_span_gate["stop_rule"],
            "suggested_artifact": (
                "Use `docs/LONG_SPAN_BUNDLE_GATE.md`; only replace this with a "
                "sweep artifact after the generated gate passes."
            ),
        },
        {
            "rank": 2,
            "lane": "heldout-corpora",
            "status": "gated",
            "parallel_group": "corpus-transform",
            "action": "Keep replication corpora in a separate frontier artifact unless the team intentionally accepts the expensive matrix-regeneration cascade.",
            "why_now": (
                f"The held-out expansion found {heldout_expansion['corpus_count']} deterministic "
                f"replication corpora missing from both the corpus matrix and transform validation, "
                f"including {heldout_expansion['ordinary_corpus_count']} ordinary corpora and "
                f"{heldout_expansion['control_corpus_count']} controls. Raw seed-frontier scanning "
                f"covered {heldout_expansion['target_span_count']} spans and found "
                f"{heldout_expansion['rows_with_prefix_ge_5']} prefix>=5 rows, "
                f"{heldout_expansion['rows_with_exact_hits']} exact-hit rows, and "
                f"{heldout_expansion['rows_with_selected_spans']} selected-span rows. "
                f"Current held-out transform validation still has prefix>=4 uplift in "
                f"{validation['heldout_prefix4_win_corpora']} corpora and "
                f"{validation['heldout_exact_hits']} exact hits."
            ),
            "promotion_gate": "Promote into canonical matrices only for accepted coverage expansion or after unrelated ordinary groups produce prefix>=5 movement, exact hits, or selected spans while controls stay null.",
            "stop_rule": "Keep the separate artifact as the source of truth while raw prefix>=5, exact-hit, and selected-span rows remain zero.",
            "suggested_artifact": "Use `docs/HELDOUT_CORPUS_EXPANSION.md`; schedule matrix integration only with an explicit regeneration budget.",
        },
        {
            "rank": 3,
            "lane": "search-depth",
            "status": "gated",
            "parallel_group": "compute-economics",
            "action": "Keep broad depth-3 structured sweeps gated after the bounded compression follow-up returned null.",
            "why_now": (
                f"The depth-3 prefix probe enumerated {depth3['enumerated_seed_count']} seeds and found "
                f"{depth3['heldout_rows_with_prefix5_uplift']} held-out prefix>=5 uplift rows but "
                f"{depth3['heldout_exact_hits']} exact hits. The bounded follow-up ran "
                f"{depth3_actual['promoted_prefix_rows']} physical inputs / "
                f"{depth3_actual['logical_alias_rows']} aliases and found "
                f"{depth3_actual['total_depth3_selected_spans']} selected spans. "
                f"The selected-lead depth-3 probe found "
                f"{lead_depth3['rows_with_depth3_prefix5_uplift']} prefix>=5 uplift rows, "
                f"{lead_depth3['total_depth3_exact_hits']} exact hits, and the lead compression follow-up found "
                f"{lead_depth3_actual['total_depth3_selected_spans']} selected spans. "
                f"Depth-3 frontier exact discovery then checked "
                f"{depth3_frontier_summary['frontier_rows']} frozen frontier rows / "
                f"{depth3_frontier_summary['physical_payload_count']} payloads, with "
                f"{depth3_frontier_summary['rows_with_depth3_prefix5_uplift']} prefix>=5 uplift rows, "
                f"{depth3_frontier_summary['total_exact_hits']} exact hits, and "
                f"{depth3_frontier_summary['total_selected_spans']} selected spans. "
                f"The depth-4 shard plan is {depth4_gate['recommended_status']}, estimates "
                f"{depth4_estimates['estimated_incremental_depth4_hours']} hours for the full "
                f"4-byte bucket at the depth-3 frontier rate, and gives exact-8 probability "
                f"{depth4_estimates['exact8_probability_at_least_one']:.6g} on the current frontier. "
                f"The pilot shard enumerated {depth4_pilot['enumerated_seed_count']} four-byte seeds "
                f"and found {depth4_pilot['rows_with_depth4_prefix5']} prefix>=5 rows, "
                f"{depth4_pilot['rows_with_depth4_prefix6']} prefix>=6 rows, "
                f"{depth4_pilot['total_exact_hits']} exact hits, and "
                f"{depth4_pilot['total_selected_spans']} selected spans. "
                f"Best non-planted forecast still needs about "
                f"{best_nearmiss['best_non_planted_gib_for_one_expected_hit']:.3e} GiB "
                "for one expected exact hit under the random-suffix model. "
                f"The generated search frontier gate is {search_gate['recommended_status']} with "
                f"{search_gate['gate_met_count']} of {search_gate['gate_count']} gates met, "
                f"{search_gate['selected_span_total']} selected spans, and "
                f"{search_gate['depth4_exact8_probability']:.6g} depth-4 exact-8 probability."
            ),
            "promotion_gate": "Promote broader depth-3 or opt-in depth-4 work only if a new lead finds prefix>=6 movement, exact hits, selected spans, negative delta, or forecast scale below 1 GiB for one expected exact hit.",
            "stop_rule": "Abort deeper search if frontier exact discovery remains prefix-only with no exact hits.",
            "suggested_artifact": "Use `docs/SEARCH_FRONTIER_GATE.md` as the broad go/no-go gate before any raw depth or full depth-4 proposal.",
        },
        {
            "rank": 4,
            "lane": "scale-performance",
            "status": "qualified"
            if scale_performance_summary["promotion_met"]
            else "ready",
            "parallel_group": "compute-economics",
            "action": "Interpret the current bounded planted-density scale sweeps before extending size.",
            "why_now": (
                f"The current {scale_mib} planted-density sweep is useful performance "
                "evidence but not natural-corpus proof; it now preserves seed expansions, "
                "target windows, lookup counts, and target-table byte estimates"
                f"{scale_ratio_text}. SCALE_PERFORMANCE reports plateau ratio spread "
                f"{scale_performance_summary['plateau_ratio_spread_pct']}%, "
                f"largest peak memory "
                f"{scale_performance_summary['largest_peak_memory_mib']} MiB, and "
                f"next-double peak estimate "
                f"{scale_performance_summary['next_double_peak_memory_mib_at_current_ratio']} MiB. "
                f"BOUNDED_STREAMING_MEMORY_GATE reports {bounded_memory['gate_status']}, "
                f"target-table preflight present {bounded_memory['target_table_preflight_present']}, "
                f"full RSS containment {bounded_memory['full_rss_containment']}, and "
                f"chunked target tables {bounded_memory['chunked_target_tables_implemented']}."
            ),
            "promotion_gate": "Peak memory and runtime scale predictably without changing roundtrip or telemetry correctness, with full RSS containment or chunked target tables for promoted workloads.",
            "stop_rule": "Stop scaling if peak working set grows faster than search-work and target-table telemetry explains, or if target-table estimates exceed the configured memory limit.",
            "suggested_artifact": "Use `docs/SCALE_PERFORMANCE.md` and `docs/BOUNDED_STREAMING_MEMORY_GATE.md`; extend bounded sizes only if the current ratio stays explainable or chunked tables reduce memory.",
        },
        {
            "rank": 5,
            "lane": "format-transforms",
            "status": "blocked-by-evidence",
            "parallel_group": "format-policy",
            "action": "Do not add transform metadata to `.tlmr` yet.",
            "why_now": "Current transform wins are transform-only or shallow prefix effects with zero selected seed spans.",
            "promotion_gate": "Only draft a format extension after a reversible transform produces repeatable exact seed-span wins.",
            "stop_rule": "Reject format work if exact hits remain absent after held-out validation.",
            "suggested_artifact": "Keep ADR-0001 policy in force.",
        },
        {
            "rank": 6,
            "lane": "gpu-acceleration",
            "status": "blocked-by-evidence",
            "parallel_group": "acceleration",
            "action": "Do not implement production GPU acceleration until CPU evidence identifies a worthwhile target workload.",
            "why_now": f"Acceleration report status is `{acceleration_status}` and current non-planted exact-hit forecasts are weak.",
            "promotion_gate": "A CPU workload shows repeatable exact hits but is too slow, then GPU parity and benchmark work becomes valuable.",
            "stop_rule": "Stop GPU work if it cannot beat CPU streaming on the promoted workload under parity tests.",
            "suggested_artifact": "Keep `docs/ACCELERATION.md` as the GPU promotion gate.",
        },
        {
            "rank": 7,
            "lane": "tauri-workflow",
            "status": "qualified" if ui_workflow_summary["promotion_met"] else "ready",
            "parallel_group": "operator-ui",
            "action": "Keep the Tauri evidence dashboard covered by generated static UI/bridge smoke checks.",
            "why_now": (
                "The research program now has generated scorecard, forecasts, "
                "validation, acceleration gates, and UI_WORKFLOW_SMOKE reports "
                f"{ui_workflow_summary['ui_evidence_key_count']} UI evidence keys, "
                f"{ui_workflow_summary['tauri_evidence_field_count']} Tauri fields, "
                f"{ui_workflow_summary['required_card_count']} required cards, and "
                f"claim level {ui_workflow_summary['claim_level']}."
            ),
            "promotion_gate": "UI smoke tests can read and render generated artifact summaries plus per-layer telemetry without desktop-only assumptions.",
            "stop_rule": "Stop UI expansion if it encourages unsupported compression claims or hides null results.",
            "suggested_artifact": "Use `docs/UI_WORKFLOW_SMOKE.md`; add live desktop/browser smoke only when UI behavior changes beyond static schema wiring.",
        },
        {
            "rank": 8,
            "lane": "research-audit",
            "status": "qualified",
            "parallel_group": "meta-research",
            "action": "Keep the open-question list synchronized with generated evidence after each new experiment family.",
            "why_now": (
                f"The current viability ledger has {len(open_questions)} open questions, "
                f"and the generated goal audit has {audit_counts.get('open', 0)} open "
                f"requirements, {goal_audit.get('unresolved_count', 0)} unresolved "
                f"evidence gates, {audit_counts.get('blocked-by-evidence', 0)} "
                f"blocked-by-evidence requirements, and "
                f"{audit_counts.get('qualified', 0)} qualified requirements. "
                "The scorecard, goal audit, UI workflow smoke, and this queue have "
                "all been regenerated from current checked-in evidence."
            ),
            "promotion_gate": "Every open question points to a generated artifact, command gate, or explicit stop rule.",
            "stop_rule": "Stop adding new experiment families when they do not change the scorecard or queue.",
            "suggested_artifact": "Regenerate `docs/VIABILITY.md`, `docs/RESEARCH_SCORECARD.md`, `docs/GOAL_AUDIT.md`, and this queue after every artifact family.",
        },
    ]


def build_report() -> dict[str, Any]:
    scorecard = load_json(SCORECARD_JSON)
    nearmiss = load_json(NEARMISS_JSON)
    prefix_ladder = load_json(PREFIX_LADDER_JSON)
    depth3_prefix = load_json(DEPTH3_PREFIX_JSON)
    depth3_followup = load_json(DEPTH3_FOLLOWUP_JSON)
    lead_depth3_prefix = load_json(LEAD_DEPTH3_PREFIX_JSON)
    lead_depth3_followup = load_json(LEAD_DEPTH3_FOLLOWUP_JSON)
    depth3_frontier = load_json(DEPTH3_FRONTIER_JSON)
    depth4_shard_plan = load_json(DEPTH4_SHARD_PLAN_JSON)
    depth4_pilot_shard = load_json(DEPTH4_PILOT_SHARD_JSON)
    search_frontier_gate = load_json(SEARCH_FRONTIER_GATE_JSON)
    long_span_bundle_gate = load_json(LONG_SPAN_BUNDLE_GATE_JSON)
    mechanism_experiment_ranking = load_json(MECHANISM_EXPERIMENT_RANKING_JSON)
    seed_table_preset_probe = load_json(SEED_TABLE_PRESET_PROBE_JSON)
    exact_short_hit_bundle_economics = load_json(
        EXACT_SHORT_HIT_BUNDLE_ECONOMICS_JSON
    )
    whole_stream_residual_vector_probe = load_json(
        WHOLE_STREAM_RESIDUAL_VECTOR_PROBE_JSON
    )
    expander_salt_ensemble = load_json(EXPANDER_SALT_ENSEMBLE_JSON)
    schema_native_public_dictionaries = load_json(SCHEMA_NATIVE_PUBLIC_DICTIONARIES_JSON)
    schema_native_public_dictionary_replication = load_json(
        SCHEMA_NATIVE_PUBLIC_DICTIONARY_REPLICATION_JSON
    )
    superposition_telemetry = load_json(SUPERPOSITION_TELEMETRY_JSON)
    recursive_structured_fixtures = load_json(RECURSIVE_STRUCTURED_FIXTURES_JSON)
    scale_performance = load_json(SCALE_PERFORMANCE_JSON)
    bounded_streaming_memory = load_json(BOUNDED_STREAMING_MEMORY_JSON)
    ui_workflow_smoke = load_json(UI_WORKFLOW_SMOKE_JSON)
    fifth_byte = load_json(FIFTH_BYTE_JSON)
    fifth_steering = load_json(FIFTH_STEERING_JSON)
    contextual_steering = load_json(CONTEXTUAL_STEERING_JSON)
    corpus_generalization = load_json(CORPUS_GENERALIZATION_JSON)
    transform_validation = load_json(TRANSFORM_VALIDATION_JSON)
    periodic_probe = load_json(PERIODIC_PROBE_JSON)
    composed_probe = load_json(COMPOSED_PROBE_JSON)
    structural_search = load_json(STRUCTURAL_SEARCH_JSON)
    byte_permutation_search = load_json(BYTE_PERMUTATION_SEARCH_JSON)
    bwt_mtf_probe = load_json(BWT_MTF_PROBE_JSON)
    grammar_channel_discovery = load_json(GRAMMAR_CHANNEL_DISCOVERY_JSON)
    numeric_value_channel_discovery = load_json(NUMERIC_VALUE_CHANNEL_DISCOVERY_JSON)
    heldout_corpus_expansion = load_json(HELDOUT_CORPUS_EXPANSION_JSON)
    record_context_search = load_json(RECORD_CONTEXT_SEARCH_JSON)
    token_dictionary_search = load_json(TOKEN_DICTIONARY_SEARCH_JSON)
    affine_search = load_json(AFFINE_SEARCH_JSON)
    residual_steering = load_json(RESIDUAL_STEERING_JSON)
    sidecar_break_even = load_json(SIDECAR_BREAK_EVEN_JSON)
    residual_payload_compressibility = load_json(RESIDUAL_PAYLOAD_COMPRESSIBILITY_JSON)
    experimental_sidecar_descriptor = load_json(EXPERIMENTAL_SIDECAR_DESCRIPTOR_JSON)
    sidecar_record_overhead = load_json(SIDECAR_RECORD_OVERHEAD_JSON)
    packed_sidecar_descriptor = load_json(PACKED_SIDECAR_DESCRIPTOR_JSON)
    packed_sidecar_controls = load_json(PACKED_SIDECAR_CONTROLS_JSON)
    generalized_packed_sidecar = load_json(GENERALIZED_PACKED_SIDECAR_JSON)
    packed_sidecar_replication = load_json(PACKED_SIDECAR_REPLICATION_JSON)
    match_discovery = load_json(MATCH_DISCOVERY_JSON)
    alignment_arity_discovery = load_json(ALIGNMENT_ARITY_DISCOVERY_JSON)
    transformed_match_discovery = load_json(TRANSFORMED_MATCH_DISCOVERY_JSON)
    lead_exact_discovery = load_json(LEAD_EXACT_DISCOVERY_JSON)
    viability = load_json(VIABILITY_JSON)
    acceleration = load_json(ACCELERATION_JSON)
    goal_audit = load_json(GOAL_AUDIT_JSON)
    sweeps = load_json(SWEEPS_JSON)
    items = queue_items(
        scorecard,
        nearmiss,
        prefix_ladder,
        depth3_prefix,
        depth3_followup,
        lead_depth3_prefix,
        lead_depth3_followup,
        depth3_frontier,
        depth4_shard_plan,
        depth4_pilot_shard,
        search_frontier_gate,
        long_span_bundle_gate,
        mechanism_experiment_ranking,
        seed_table_preset_probe,
        exact_short_hit_bundle_economics,
        whole_stream_residual_vector_probe,
        expander_salt_ensemble,
        schema_native_public_dictionaries,
        schema_native_public_dictionary_replication,
        superposition_telemetry,
        recursive_structured_fixtures,
        scale_performance,
        bounded_streaming_memory,
        ui_workflow_smoke,
        fifth_byte,
        fifth_steering,
        contextual_steering,
        corpus_generalization,
        transform_validation,
        periodic_probe,
        composed_probe,
        structural_search,
        byte_permutation_search,
        bwt_mtf_probe,
        grammar_channel_discovery,
        numeric_value_channel_discovery,
        heldout_corpus_expansion,
        record_context_search,
        token_dictionary_search,
        affine_search,
        residual_steering,
        sidecar_break_even,
        residual_payload_compressibility,
        experimental_sidecar_descriptor,
        sidecar_record_overhead,
        packed_sidecar_descriptor,
        packed_sidecar_controls,
        generalized_packed_sidecar,
        packed_sidecar_replication,
        match_discovery,
        alignment_arity_discovery,
        transformed_match_discovery,
        lead_exact_discovery,
        viability,
        acceleration,
        goal_audit,
        sweeps,
    )
    scale = largest_scale_row(sweeps)
    scale_mib = f"{scale['input_bytes'] / (1024 * 1024):.0f} MiB" if scale else "no"
    ready_count = sum(1 for item in items if item["status"] == "ready")
    status_counts = dict(Counter(item["status"] for item in items))
    top_ready_lane = next(
        (item["lane"] for item in items if item["status"] == "ready"),
        "none",
    )
    return {
        "generated_by": "scripts/generate_experiment_queue.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "artifact_hashes": artifact_hashes(),
        "overall_status": scorecard["overall_status"],
        "verdict": scorecard["verdict"],
        "items": items,
        "summary": {
            "status_counts": status_counts,
            "ready_count": ready_count,
            "gated_count": status_counts.get("gated", 0),
            "blocked_by_evidence_count": status_counts.get("blocked-by-evidence", 0),
            "qualified_count": status_counts.get("qualified", 0),
            "top_ready_lane": top_ready_lane,
            "current_scale_mib": scale_mib,
            "conclusion": (
                "No ready ungated experiments remain; do not spend on gated compute "
                "or production GPU until evidence improves."
                if ready_count == 0
                else "Run ready experiments first; do not spend on gated compute or production GPU until evidence improves."
            ),
        },
    }


def write_report(payload: dict[str, Any]) -> None:
    QUEUE_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Telomere Experiment Queue",
        "",
        "Generated by `scripts/generate_experiment_queue.py` from current evidence artifacts.",
        "This queue turns null results, near misses, and proved mechanisms into explicit next actions.",
        "",
        f"Overall status: **{payload['overall_status']}**.",
        f"Verdict: **{payload['verdict']}**.",
        "",
        "## Summary",
        "",
        f"- Ready experiments: `{payload['summary']['ready_count']}`",
        f"- Gated experiments: `{payload['summary']['gated_count']}`",
        f"- Blocked by evidence: `{payload['summary']['blocked_by_evidence_count']}`",
        f"- Qualified experiments: `{payload['summary']['qualified_count']}`",
        f"- Top ready lane: `{payload['summary']['top_ready_lane']}`",
        "",
        "Status counts: "
        + ", ".join(
            f"`{status}` {count}"
            for status, count in sorted(payload["summary"]["status_counts"].items())
        )
        + ".",
        "",
        payload["summary"]["conclusion"],
        "",
        "## Queue",
        "",
        "| rank | lane | status | parallel group | action | promotion gate | stop rule |",
        "| ---: | --- | --- | --- | --- | --- | --- |",
    ]
    for item in payload["items"]:
        lines.append(
            "| {rank} | {lane} | {status} | {parallel_group} | {action} | {promotion_gate} | {stop_rule} |".format(
                **item
            )
        )

    lines.extend(["", "## Execution Notes", ""])
    for item in payload["items"]:
        lines.append(f"- `{item['lane']}`: {item['why_now']} Suggested artifact: {item['suggested_artifact']}")
    QUEUE_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not QUEUE_JSON.exists() or not QUEUE_MD.exists():
        raise SystemExit("generated experiment queue files are missing")
    payload = load_json(QUEUE_JSON)
    if payload.get("generated_by") != "scripts/generate_experiment_queue.py":
        raise SystemExit("experiment_queue.json has wrong generated_by marker")
    if payload.get("artifact_hashes") != artifact_hashes():
        raise SystemExit("experiment_queue.json artifact hashes are stale")
    if not payload.get("items"):
        raise SystemExit("experiment_queue.json contains no queue items")
    expected = stable_projection(build_report())
    current = stable_projection(payload)
    if current != expected:
        raise SystemExit("experiment_queue.json is stale; regenerate it")
    summary_counts = payload.get("summary", {}).get("status_counts", {})
    if sum(summary_counts.values()) != len(payload["items"]):
        raise SystemExit("experiment_queue status counts do not match item count")
    expected_scale = (
        f"{largest_scale_row(load_json(SWEEPS_JSON))['input_bytes'] / (1024 * 1024):.0f} MiB"
        if largest_scale_row(load_json(SWEEPS_JSON))
        else "no"
    )
    if payload.get("summary", {}).get("current_scale_mib") != expected_scale:
        raise SystemExit("experiment_queue.json scale summary is stale")
    text = QUEUE_MD.read_text(encoding="utf-8")
    if f"current {expected_scale} planted-density sweep" not in text:
        raise SystemExit("EXPERIMENT_QUEUE.md scale claim is stale")
    for phrase in (
        "Ready experiments",
        "Qualified experiments",
        "Status counts",
        "Blocked by evidence",
        "unresolved evidence gates",
        "promotion gate",
        "stop rule",
        "do not spend on gated compute",
        "bounded structural search",
        "byte-permutation transform search",
        "BWT/MTF classic-preconditioner probe",
        "grammar/channel match discovery",
        "numeric value-channel search",
        "held-out corpus expansion",
        "record/context transform search",
        "token/dictionary transform search",
        "Affine remaps",
        "Residual-sidecar steering",
        "longer-span sidecar break-even",
        "Residual payload compressibility",
        "experimental descriptor",
        "sidecar record-overhead",
        "packed sidecar descriptor",
        "control-matrix",
        "generalized packed sidecar",
        "packed sidecar replication",
        "Match discovery scanned",
        "Alignment/arity discovery then scanned",
        "Transformed match discovery applied",
        "Selected-lead exact discovery then scanned",
        "selected-lead depth-3 probe",
        "generated search frontier gate",
        "LONG_SPAN_BUNDLE_GATE",
        "MECHANISM_EXPERIMENT_RANKING",
        "SEED_TABLE_PRESET_PROBE",
        "EXACT_SHORT_HIT_BUNDLE_ECONOMICS",
        "WHOLE_STREAM_RESIDUAL_VECTOR_PROBE",
        "EXPANDER_SALT_ENSEMBLE",
        "SCHEMA_NATIVE_PUBLIC_DICTIONARIES",
        "SCHEMA_NATIVE_PUBLIC_DICTIONARY_REPLICATION",
        "SUPERPOSITION_TELEMETRY",
        "RECURSIVE_STRUCTURED_FIXTURES",
        "SCALE_PERFORMANCE",
        "wrong-schema",
        "same-size random",
        "predeclared expander salts",
        "random-trial multiplier",
        "global residual entropy",
        "bitplane/vector channels",
        "measured residual coding",
        "controls null",
        "zero-overhead lower bound",
        "short-hit density",
        "full-stream negative",
        "Depth-3 frontier exact discovery",
        "depth-4 shard plan",
        "pilot shard enumerated",
        "Corpus generalization controls",
        "ordinary held-out",
        "SEARCH_FRONTIER_GATE",
    ):
        if phrase not in text:
            raise SystemExit(f"EXPERIMENT_QUEUE.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate generated experiment queue")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.check:
        check_report()
        return
    write_report(build_report())


if __name__ == "__main__":
    main()
