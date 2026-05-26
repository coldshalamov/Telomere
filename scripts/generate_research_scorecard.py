#!/usr/bin/env python3
"""Generate a consolidated Telomere research scorecard."""

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
RESULTS_PATH = DOCS / "results.json"
SWEEPS_PATH = DOCS / "sweeps.json"
DEEP_SWEEPS_PATH = DOCS / "deep_sweeps.json"
TRANSFORM_SWEEPS_PATH = DOCS / "transform_sweeps.json"
TRANSFORM_PROBE_PATH = DOCS / "transform_probe.json"
TRANSFORM_VALIDATION_PATH = DOCS / "transform_validation.json"
PERIODIC_PROBE_PATH = DOCS / "periodic_transform_probe.json"
COMPOSED_PROBE_PATH = DOCS / "composed_transform_probe.json"
CORPUS_MATRIX_PATH = DOCS / "corpus_matrix.json"
CORPUS_GENERALIZATION_PATH = DOCS / "corpus_generalization_probe.json"
ACCELERATION_PATH = DOCS / "acceleration_report.json"
THEORY_PATH = DOCS / "theory.json"
MANIFOLD_PATH = DOCS / "manifold.json"
NEARMISS_FORECAST_PATH = DOCS / "nearmiss_forecast.json"
PREFIX_LADDER_PATH = DOCS / "prefix_ladder.json"
DEPTH3_PREFIX_PROBE_PATH = DOCS / "depth3_prefix_probe.json"
DEPTH3_COMPRESSION_FOLLOWUP_PATH = DOCS / "depth3_compression_followup.json"
LEAD_DEPTH3_PREFIX_PROBE_PATH = DOCS / "lead_depth3_prefix_probe.json"
LEAD_DEPTH3_COMPRESSION_FOLLOWUP_PATH = DOCS / "lead_depth3_compression_followup.json"
DEPTH3_FRONTIER_EXACT_DISCOVERY_PATH = DOCS / "depth3_frontier_exact_discovery.json"
DEPTH4_SHARD_PLAN_PATH = DOCS / "depth4_shard_plan.json"
DEPTH4_PILOT_SHARD_PATH = DOCS / "depth4_pilot_shard.json"
SEARCH_FRONTIER_GATE_PATH = DOCS / "search_frontier_gate.json"
MECHANISM_EXPERIMENT_RANKING_PATH = DOCS / "mechanism_experiment_ranking.json"
SEED_TABLE_PRESET_PROBE_PATH = DOCS / "seed_table_preset_probe.json"
EXACT_SHORT_HIT_BUNDLE_ECONOMICS_PATH = (
    DOCS / "exact_short_hit_bundle_economics.json"
)
WHOLE_STREAM_RESIDUAL_VECTOR_PROBE_PATH = (
    DOCS / "whole_stream_residual_vector_probe.json"
)
EXPANDER_SALT_ENSEMBLE_PATH = DOCS / "expander_salt_ensemble.json"
SCHEMA_NATIVE_PUBLIC_DICTIONARIES_PATH = (
    DOCS / "schema_native_public_dictionaries.json"
)
SCHEMA_NATIVE_PUBLIC_DICTIONARY_REPLICATION_PATH = (
    DOCS / "schema_native_public_dictionary_replication.json"
)
SUPERPOSITION_TELEMETRY_PATH = DOCS / "superposition_telemetry.json"
LONG_SPAN_BUNDLE_GATE_PATH = DOCS / "long_span_bundle_gate.json"
RECURSIVE_STRUCTURED_FIXTURES_PATH = DOCS / "recursive_structured_fixtures.json"
SCALE_PERFORMANCE_PATH = DOCS / "scale_performance_report.json"
UI_WORKFLOW_SMOKE_PATH = DOCS / "ui_workflow_smoke.json"
FIFTH_BYTE_RESIDUAL_PATH = DOCS / "fifth_byte_residual.json"
FIFTH_BYTE_STEERING_PATH = DOCS / "fifth_byte_steering.json"
CONTEXTUAL_STEERING_PATH = DOCS / "contextual_fifth_byte_steering.json"
STRUCTURAL_SEARCH_PATH = DOCS / "structural_transform_search.json"
BYTE_PERMUTATION_SEARCH_PATH = DOCS / "byte_permutation_transform_search.json"
BWT_MTF_PROBE_PATH = DOCS / "bwt_mtf_transform_probe.json"
GRAMMAR_CHANNEL_DISCOVERY_PATH = DOCS / "grammar_channel_match_discovery.json"
NUMERIC_VALUE_CHANNEL_DISCOVERY_PATH = DOCS / "numeric_value_channel_match_discovery.json"
HELDOUT_CORPUS_EXPANSION_PATH = DOCS / "heldout_corpus_expansion.json"
RECORD_CONTEXT_SEARCH_PATH = DOCS / "record_context_transform_search.json"
TOKEN_DICTIONARY_SEARCH_PATH = DOCS / "token_dictionary_transform_search.json"
AFFINE_SEARCH_PATH = DOCS / "affine_transform_search.json"
RESIDUAL_STEERING_PATH = DOCS / "seed_manifold_residual_steering.json"
SIDECAR_BREAK_EVEN_PATH = DOCS / "sidecar_break_even.json"
RESIDUAL_PAYLOAD_COMPRESSIBILITY_PATH = DOCS / "residual_payload_compressibility.json"
EXPERIMENTAL_SIDECAR_DESCRIPTOR_PATH = DOCS / "experimental_sidecar_descriptor.json"
SIDECAR_RECORD_OVERHEAD_PATH = DOCS / "sidecar_record_overhead.json"
PACKED_SIDECAR_DESCRIPTOR_PATH = DOCS / "packed_sidecar_descriptor.json"
PACKED_SIDECAR_CONTROLS_PATH = DOCS / "packed_sidecar_controls.json"
GENERALIZED_PACKED_SIDECAR_PATH = DOCS / "generalized_packed_sidecar.json"
PACKED_SIDECAR_REPLICATION_PATH = DOCS / "packed_sidecar_replication.json"
MATCH_DISCOVERY_PATH = DOCS / "match_discovery.json"
ALIGNMENT_ARITY_DISCOVERY_PATH = DOCS / "alignment_arity_discovery.json"
TRANSFORMED_MATCH_DISCOVERY_PATH = DOCS / "transformed_match_discovery.json"
LEAD_EXACT_DISCOVERY_PATH = DOCS / "lead_exact_discovery.json"
VIABILITY_PATH = DOCS / "viability.json"
SCORECARD_JSON = DOCS / "research_scorecard.json"
SCORECARD_MD = DOCS / "RESEARCH_SCORECARD.md"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def row_by_name(rows: list[dict[str, Any]], name: str) -> dict[str, Any]:
    for row in rows:
        if row["name"] == name:
            return row
    raise KeyError(name)


def row_by_key(rows: list[dict[str, Any]], key: str, value: Any) -> dict[str, Any]:
    for row in rows:
        if row[key] == value:
            return row
    raise KeyError(value)


def artifact_hashes() -> dict[str, str]:
    return {
        "results_sha256": sha256(RESULTS_PATH),
        "sweeps_sha256": sha256(SWEEPS_PATH),
        "deep_sweeps_sha256": sha256(DEEP_SWEEPS_PATH),
        "transform_sweeps_sha256": sha256(TRANSFORM_SWEEPS_PATH),
        "transform_probe_sha256": sha256(TRANSFORM_PROBE_PATH),
        "transform_validation_sha256": sha256(TRANSFORM_VALIDATION_PATH),
        "periodic_transform_probe_sha256": sha256(PERIODIC_PROBE_PATH),
        "composed_transform_probe_sha256": sha256(COMPOSED_PROBE_PATH),
        "corpus_matrix_sha256": sha256(CORPUS_MATRIX_PATH),
        "corpus_generalization_probe_sha256": sha256(CORPUS_GENERALIZATION_PATH),
        "acceleration_report_sha256": sha256(ACCELERATION_PATH),
        "theory_sha256": sha256(THEORY_PATH),
        "manifold_sha256": sha256(MANIFOLD_PATH),
        "nearmiss_forecast_sha256": sha256(NEARMISS_FORECAST_PATH),
        "prefix_ladder_sha256": sha256(PREFIX_LADDER_PATH),
        "depth3_prefix_probe_sha256": sha256(DEPTH3_PREFIX_PROBE_PATH),
        "depth3_compression_followup_sha256": sha256(DEPTH3_COMPRESSION_FOLLOWUP_PATH),
        "lead_depth3_prefix_probe_sha256": sha256(LEAD_DEPTH3_PREFIX_PROBE_PATH),
        "lead_depth3_compression_followup_sha256": sha256(
            LEAD_DEPTH3_COMPRESSION_FOLLOWUP_PATH
        ),
        "depth3_frontier_exact_discovery_sha256": sha256(
            DEPTH3_FRONTIER_EXACT_DISCOVERY_PATH
        ),
        "depth4_shard_plan_sha256": sha256(DEPTH4_SHARD_PLAN_PATH),
        "depth4_pilot_shard_sha256": sha256(DEPTH4_PILOT_SHARD_PATH),
        "search_frontier_gate_sha256": sha256(SEARCH_FRONTIER_GATE_PATH),
        "mechanism_experiment_ranking_sha256": sha256(
            MECHANISM_EXPERIMENT_RANKING_PATH
        ),
        "seed_table_preset_probe_sha256": sha256(SEED_TABLE_PRESET_PROBE_PATH),
        "exact_short_hit_bundle_economics_sha256": sha256(
            EXACT_SHORT_HIT_BUNDLE_ECONOMICS_PATH
        ),
        "whole_stream_residual_vector_probe_sha256": sha256(
            WHOLE_STREAM_RESIDUAL_VECTOR_PROBE_PATH
        ),
        "expander_salt_ensemble_sha256": sha256(EXPANDER_SALT_ENSEMBLE_PATH),
        "schema_native_public_dictionaries_sha256": sha256(
            SCHEMA_NATIVE_PUBLIC_DICTIONARIES_PATH
        ),
        "schema_native_public_dictionary_replication_sha256": sha256(
            SCHEMA_NATIVE_PUBLIC_DICTIONARY_REPLICATION_PATH
        ),
        "superposition_telemetry_sha256": sha256(SUPERPOSITION_TELEMETRY_PATH),
        "long_span_bundle_gate_sha256": sha256(LONG_SPAN_BUNDLE_GATE_PATH),
        "recursive_structured_fixtures_sha256": sha256(
            RECURSIVE_STRUCTURED_FIXTURES_PATH
        ),
        "scale_performance_report_sha256": sha256(SCALE_PERFORMANCE_PATH),
        "ui_workflow_smoke_sha256": sha256(UI_WORKFLOW_SMOKE_PATH),
        "fifth_byte_residual_sha256": sha256(FIFTH_BYTE_RESIDUAL_PATH),
        "fifth_byte_steering_sha256": sha256(FIFTH_BYTE_STEERING_PATH),
        "contextual_fifth_byte_steering_sha256": sha256(CONTEXTUAL_STEERING_PATH),
        "structural_transform_search_sha256": sha256(STRUCTURAL_SEARCH_PATH),
        "byte_permutation_transform_search_sha256": sha256(
            BYTE_PERMUTATION_SEARCH_PATH
        ),
        "bwt_mtf_transform_probe_sha256": sha256(BWT_MTF_PROBE_PATH),
        "grammar_channel_match_discovery_sha256": sha256(
            GRAMMAR_CHANNEL_DISCOVERY_PATH
        ),
        "numeric_value_channel_match_discovery_sha256": sha256(
            NUMERIC_VALUE_CHANNEL_DISCOVERY_PATH
        ),
        "heldout_corpus_expansion_sha256": sha256(HELDOUT_CORPUS_EXPANSION_PATH),
        "record_context_transform_search_sha256": sha256(RECORD_CONTEXT_SEARCH_PATH),
        "token_dictionary_transform_search_sha256": sha256(
            TOKEN_DICTIONARY_SEARCH_PATH
        ),
        "affine_transform_search_sha256": sha256(AFFINE_SEARCH_PATH),
        "seed_manifold_residual_steering_sha256": sha256(RESIDUAL_STEERING_PATH),
        "sidecar_break_even_sha256": sha256(SIDECAR_BREAK_EVEN_PATH),
        "residual_payload_compressibility_sha256": sha256(
            RESIDUAL_PAYLOAD_COMPRESSIBILITY_PATH
        ),
        "experimental_sidecar_descriptor_sha256": sha256(
            EXPERIMENTAL_SIDECAR_DESCRIPTOR_PATH
        ),
        "sidecar_record_overhead_sha256": sha256(SIDECAR_RECORD_OVERHEAD_PATH),
        "packed_sidecar_descriptor_sha256": sha256(PACKED_SIDECAR_DESCRIPTOR_PATH),
        "packed_sidecar_controls_sha256": sha256(PACKED_SIDECAR_CONTROLS_PATH),
        "generalized_packed_sidecar_sha256": sha256(
            GENERALIZED_PACKED_SIDECAR_PATH
        ),
        "packed_sidecar_replication_sha256": sha256(
            PACKED_SIDECAR_REPLICATION_PATH
        ),
        "match_discovery_sha256": sha256(MATCH_DISCOVERY_PATH),
        "alignment_arity_discovery_sha256": sha256(ALIGNMENT_ARITY_DISCOVERY_PATH),
        "transformed_match_discovery_sha256": sha256(TRANSFORMED_MATCH_DISCOVERY_PATH),
        "lead_exact_discovery_sha256": sha256(LEAD_EXACT_DISCOVERY_PATH),
        "viability_sha256": sha256(VIABILITY_PATH),
    }


def stable_projection(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if key != "generated_at"
    }


def best_row(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    return min(rows, key=lambda row: row[key])


def build_scorecard() -> dict[str, Any]:
    results = load_json(RESULTS_PATH)
    sweeps = load_json(SWEEPS_PATH)
    deep_sweeps = load_json(DEEP_SWEEPS_PATH)
    transform_sweeps = load_json(TRANSFORM_SWEEPS_PATH)
    transform_probe = load_json(TRANSFORM_PROBE_PATH)
    transform_validation = load_json(TRANSFORM_VALIDATION_PATH)
    periodic_probe = load_json(PERIODIC_PROBE_PATH)
    composed_probe = load_json(COMPOSED_PROBE_PATH)
    corpus_matrix = load_json(CORPUS_MATRIX_PATH)
    corpus_generalization = load_json(CORPUS_GENERALIZATION_PATH)
    acceleration = load_json(ACCELERATION_PATH)
    theory = load_json(THEORY_PATH)
    manifold = load_json(MANIFOLD_PATH)
    nearmiss_forecast = load_json(NEARMISS_FORECAST_PATH)
    prefix_ladder = load_json(PREFIX_LADDER_PATH)
    depth3_prefix = load_json(DEPTH3_PREFIX_PROBE_PATH)
    depth3_followup = load_json(DEPTH3_COMPRESSION_FOLLOWUP_PATH)
    lead_depth3_prefix = load_json(LEAD_DEPTH3_PREFIX_PROBE_PATH)
    lead_depth3_followup = load_json(LEAD_DEPTH3_COMPRESSION_FOLLOWUP_PATH)
    depth3_frontier = load_json(DEPTH3_FRONTIER_EXACT_DISCOVERY_PATH)
    depth4_shard_plan = load_json(DEPTH4_SHARD_PLAN_PATH)
    depth4_pilot = load_json(DEPTH4_PILOT_SHARD_PATH)
    search_frontier_gate = load_json(SEARCH_FRONTIER_GATE_PATH)
    mechanism_experiment_ranking = load_json(MECHANISM_EXPERIMENT_RANKING_PATH)
    seed_table_preset_probe = load_json(SEED_TABLE_PRESET_PROBE_PATH)
    exact_short_hit_bundle_economics = load_json(
        EXACT_SHORT_HIT_BUNDLE_ECONOMICS_PATH
    )
    whole_stream_residual_vector_probe = load_json(
        WHOLE_STREAM_RESIDUAL_VECTOR_PROBE_PATH
    )
    expander_salt_ensemble = load_json(EXPANDER_SALT_ENSEMBLE_PATH)
    schema_native_public_dictionaries = load_json(
        SCHEMA_NATIVE_PUBLIC_DICTIONARIES_PATH
    )
    schema_native_public_dictionary_replication = load_json(
        SCHEMA_NATIVE_PUBLIC_DICTIONARY_REPLICATION_PATH
    )
    superposition_telemetry = load_json(SUPERPOSITION_TELEMETRY_PATH)
    long_span_bundle_gate = load_json(LONG_SPAN_BUNDLE_GATE_PATH)
    recursive_structured_fixtures = load_json(RECURSIVE_STRUCTURED_FIXTURES_PATH)
    scale_performance = load_json(SCALE_PERFORMANCE_PATH)
    ui_workflow_smoke = load_json(UI_WORKFLOW_SMOKE_PATH)
    fifth_byte = load_json(FIFTH_BYTE_RESIDUAL_PATH)
    fifth_steering = load_json(FIFTH_BYTE_STEERING_PATH)
    contextual_steering = load_json(CONTEXTUAL_STEERING_PATH)
    structural_search = load_json(STRUCTURAL_SEARCH_PATH)
    byte_permutation_search = load_json(BYTE_PERMUTATION_SEARCH_PATH)
    bwt_mtf_probe = load_json(BWT_MTF_PROBE_PATH)
    grammar_channel_discovery = load_json(GRAMMAR_CHANNEL_DISCOVERY_PATH)
    numeric_value_channel_discovery = load_json(NUMERIC_VALUE_CHANNEL_DISCOVERY_PATH)
    heldout_corpus_expansion = load_json(HELDOUT_CORPUS_EXPANSION_PATH)
    record_context_search = load_json(RECORD_CONTEXT_SEARCH_PATH)
    token_dictionary_search = load_json(TOKEN_DICTIONARY_SEARCH_PATH)
    affine_search = load_json(AFFINE_SEARCH_PATH)
    residual_steering = load_json(RESIDUAL_STEERING_PATH)
    sidecar_break_even = load_json(SIDECAR_BREAK_EVEN_PATH)
    residual_payload_compressibility = load_json(RESIDUAL_PAYLOAD_COMPRESSIBILITY_PATH)
    experimental_sidecar_descriptor = load_json(EXPERIMENTAL_SIDECAR_DESCRIPTOR_PATH)
    sidecar_record_overhead = load_json(SIDECAR_RECORD_OVERHEAD_PATH)
    packed_sidecar_descriptor = load_json(PACKED_SIDECAR_DESCRIPTOR_PATH)
    packed_sidecar_controls = load_json(PACKED_SIDECAR_CONTROLS_PATH)
    generalized_packed_sidecar = load_json(GENERALIZED_PACKED_SIDECAR_PATH)
    packed_sidecar_replication = load_json(PACKED_SIDECAR_REPLICATION_PATH)
    match_discovery = load_json(MATCH_DISCOVERY_PATH)
    alignment_arity_discovery = load_json(ALIGNMENT_ARITY_DISCOVERY_PATH)
    transformed_match_discovery = load_json(TRANSFORMED_MATCH_DISCOVERY_PATH)
    lead_exact_discovery = load_json(LEAD_EXACT_DISCOVERY_PATH)
    viability = load_json(VIABILITY_PATH)

    result_rows = results["results"]
    sweep_rows = sweeps["results"]
    deep_rows = deep_sweeps["results"]
    transform_rows = transform_sweeps["results"]
    corpus_rows = corpus_matrix["results"]

    viability_entries = viability["entries"]
    viability_status_counts = Counter(entry["status"] for entry in viability_entries)

    raw_structured_rows = [
        row_by_name(result_rows, "streaming-structured-json-control"),
        *[row for row in sweep_rows if row["name"].startswith("structured-json-")],
        row_by_name(deep_rows, "structured-json-depth3-span8-step1-pass1"),
        *corpus_rows,
    ]
    best_raw_structured = best_row(raw_structured_rows, "delta_pct")
    best_transform = best_row(transform_rows, "effective_delta_bytes")
    scale_rows = [row for row in sweep_rows if row["group"] == "memory-scaling"]
    largest_scale = max(scale_rows, key=lambda row: row["input_bytes"])
    seed3 = row_by_name(deep_rows, "seed3-planted-depth3")
    frontier_depth3 = row_by_key(theory["minimum_profitable_frontier"], "max_seed_len", 3)
    best_manifold = row_by_name(
        manifold["results"],
        manifold["summary"]["best_non_planted_case"],
    )
    planted_manifold = row_by_name(manifold["results"], "planted-span8-positive")
    probe_best_prefix4 = transform_probe["top_prefix_ge_4"][0]
    validation_summary = transform_validation["summary"]
    periodic_summary = periodic_probe["summary"]
    composed_summary = composed_probe["summary"]
    nearmiss_summary = nearmiss_forecast["summary"]
    ladder_summary = prefix_ladder["summary"]
    depth3_summary = depth3_prefix["summary"]
    depth3_followup_summary = depth3_followup["summary"]
    lead_depth3_prefix_summary = lead_depth3_prefix["summary"]
    lead_depth3_followup_summary = lead_depth3_followup["summary"]
    depth3_frontier_summary = depth3_frontier["summary"]
    depth4_gate = depth4_shard_plan["promotion_gate"]
    depth4_estimates = depth4_shard_plan["depth4_estimates"]
    depth4_pilot_summary = depth4_pilot["summary"]
    search_gate_summary = search_frontier_gate["summary"]
    mechanism_ranking_summary = mechanism_experiment_ranking["summary"]
    seed_table_summary = seed_table_preset_probe["summary"]
    exact_short_summary = exact_short_hit_bundle_economics["summary"]
    whole_stream_summary = whole_stream_residual_vector_probe["summary"]
    expander_salt_summary = expander_salt_ensemble["summary"]
    schema_native_summary = schema_native_public_dictionaries["summary"]
    schema_replication_summary = schema_native_public_dictionary_replication["summary"]
    superposition_summary = superposition_telemetry["summary"]
    long_span_gate_summary = long_span_bundle_gate["summary"]
    recursive_structured_summary = recursive_structured_fixtures["summary"]
    scale_performance_summary = scale_performance["summary"]
    ui_workflow_summary = ui_workflow_smoke["summary"]
    fifth_summary = fifth_byte["summary"]
    steering_summary = fifth_steering["summary"]
    contextual_summary = contextual_steering["summary"]
    structural_summary = structural_search["summary"]
    byte_permutation_summary = byte_permutation_search["summary"]
    bwt_mtf_summary = bwt_mtf_probe["summary"]
    grammar_channel_summary = grammar_channel_discovery["summary"]
    numeric_value_channel_summary = numeric_value_channel_discovery["summary"]
    heldout_expansion_summary = heldout_corpus_expansion["summary"]
    record_context_summary = record_context_search["summary"]
    token_dictionary_summary = token_dictionary_search["summary"]
    affine_summary = affine_search["summary"]
    residual_summary = residual_steering["summary"]
    sidecar_break_even_summary = sidecar_break_even["summary"]
    residual_payload_summary = residual_payload_compressibility["summary"]
    experimental_sidecar_summary = experimental_sidecar_descriptor["summary"]
    sidecar_record_summary = sidecar_record_overhead["summary"]
    packed_sidecar_summary = packed_sidecar_descriptor["summary"]
    packed_controls_summary = packed_sidecar_controls["summary"]
    generalized_packed_summary = generalized_packed_sidecar["summary"]
    packed_replication_summary = packed_sidecar_replication["summary"]
    match_discovery_summary = match_discovery["summary"]
    alignment_summary = alignment_arity_discovery["summary"]
    transformed_match_summary = transformed_match_discovery["summary"]
    lead_exact_summary = lead_exact_discovery["summary"]
    corpus_generalization_summary = corpus_generalization["summary"]

    cards = [
        {
            "area": "Codec and format safety",
            "status": "proved",
            "evidence": "Viability level 0 plus full generated artifact checks.",
            "next": "Keep golden vectors and corrupt-input tests tied to any format change.",
        },
        {
            "area": "Planted generative mechanism",
            "status": "proved",
            "evidence": (
                f"v1 planted arity2 {row_by_name(result_rows, 'planted-sha256-arity2')['delta_pct']:.2f}%; "
                f"streaming span8 {row_by_name(result_rows, 'streaming-planted-span8')['delta_pct']:.2f}%."
            ),
            "next": "Move beyond planted controls only when corpus evidence supports it.",
        },
        {
            "area": "Search farther / seed depth",
            "status": "qualified",
            "evidence": (
                f"depth3 planted {seed3['delta_pct']:.2f}% with "
                f"{seed3['telemetry']['selected_count']} selected spans in {seed3['compress_ms']} ms."
            ),
            "next": "Extend depth3 only with bounded runtime and memory controls.",
        },
        {
            "area": "Depth-3 prefix frontier",
            "status": "qualified",
            "evidence": (
                f"{depth3_summary['enumerated_seed_count']} seeds enumerated; "
                f"{depth3_summary['heldout_rows_with_prefix5_uplift']} held-out rows gained "
                f"prefix>=5 movement, with {depth3_summary['heldout_exact_hits']} exact hits. "
                f"The bounded compression follow-up ran {depth3_followup_summary['promoted_prefix_rows']} "
                f"physical inputs / {depth3_followup_summary['logical_alias_rows']} aliases and found "
                f"{depth3_followup_summary['total_depth3_selected_spans']} selected spans."
            ),
            "next": "Keep broad depth-3 sweeps gated until a transform/corpus lead creates exact hits or selected spans.",
        },
        {
            "area": "Selected-lead depth-3 follow-up",
            "status": "open",
            "evidence": (
                f"lead prefix probe enumerated {lead_depth3_prefix_summary['enumerated_seed_count']} seeds; "
                f"{lead_depth3_prefix_summary['rows_with_depth3_prefix5_uplift']} rows gained prefix>=5, "
                f"{lead_depth3_prefix_summary['total_depth3_exact_hits']} exact hits. "
                f"The CLI compression follow-up ran {lead_depth3_followup_summary['promoted_prefix_rows']} "
                f"physical input / {lead_depth3_followup_summary['logical_alias_rows']} aliases and found "
                f"{lead_depth3_followup_summary['total_depth3_selected_spans']} selected spans."
            ),
            "next": "Do not broaden selected-lead depth-3 compression until exact records appear.",
        },
        {
            "area": "Depth-3 frontier exact discovery",
            "status": "open",
            "evidence": (
                f"{depth3_frontier_summary['frontier_rows']} frontier rows / "
                f"{depth3_frontier_summary['physical_payload_count']} payloads enumerated "
                f"{depth3_frontier_summary['enumerated_seed_count']} seeds; "
                f"prefix>=5 uplift rows {depth3_frontier_summary['rows_with_depth3_prefix5_uplift']}, "
                f"exact hits {depth3_frontier_summary['total_exact_hits']}, "
                f"selected spans {depth3_frontier_summary['total_selected_spans']}."
            ),
            "next": "Keep depth 4 opt-in and sharded until this gate finds prefix>=6, exact hits, or selected spans.",
        },
        {
            "area": "Depth-4 shard plan",
            "status": "open",
            "evidence": (
                f"status {depth4_gate['recommended_status']}; "
                f"estimated incremental depth-4 time "
                f"{depth4_estimates['estimated_incremental_depth4_hours']} hours; "
                f"frontier exact-8 probability "
                f"{depth4_estimates['exact8_probability_at_least_one']:.6g}."
            ),
            "next": "Run only pilot shards unless a new lead satisfies the promotion gate.",
        },
        {
            "area": "Depth-4 pilot shard",
            "status": "open",
            "evidence": (
                f"{depth4_pilot_summary['pilot_shard_count']} shard enumerated "
                f"{depth4_pilot_summary['enumerated_seed_count']} seeds over "
                f"{depth4_pilot_summary['target_span_count']} target spans; "
                f"prefix>=5 rows {depth4_pilot_summary['rows_with_depth4_prefix5']}, "
                f"prefix>=6 rows {depth4_pilot_summary['rows_with_depth4_prefix6']}, "
                f"exact hits {depth4_pilot_summary['total_exact_hits']}, "
                f"selected spans {depth4_pilot_summary['total_selected_spans']}."
            ),
            "next": "Keep the remaining 255 shards gated until prefix>=6, exact hits, or selected spans appear.",
        },
        {
            "area": "Search frontier gate",
            "status": "open",
            "evidence": (
                f"status {search_gate_summary['recommended_status']}; "
                f"best forecast {search_gate_summary['best_non_planted_gib_for_one_expected_hit']} GiB "
                f"per expected exact hit; depth-4 exact-8 probability "
                f"{search_gate_summary['depth4_exact8_probability']:.6g}; "
                f"selected spans {search_gate_summary['selected_span_total']}; "
                f"gate checks met {search_gate_summary['gate_met_count']} of "
                f"{search_gate_summary['gate_count']}."
            ),
            "next": "Use this artifact as the go/no-go source before broad raw depth search, full depth-4 shards, corpus-matrix promotion, or format-transform promotion.",
        },
        {
            "area": "Mechanism experiment ranking",
            "status": "open",
            "evidence": (
                f"top lane {mechanism_ranking_summary['top_lane_id']}; "
                f"next artifact {mechanism_ranking_summary['top_next_artifact']}; "
                f"ready {mechanism_ranking_summary['ready_count']}, "
                f"gated {mechanism_ranking_summary['gated_count']}, "
                f"blocked {mechanism_ranking_summary['blocked_by_evidence_count']}; "
                f"natural-corpus compression proven "
                f"{mechanism_ranking_summary['natural_corpus_compression_proven']}."
            ),
            "next": "Run the generated seed-table preset probe before raw-depth escalation, format promotion, descriptor packing, or hardware acceleration.",
        },
        {
            "area": "Seed-table preset probe",
            "status": "open",
            "evidence": (
                f"canonical selected spans {seed_table_summary['canonical_selected_spans']}; "
                f"ordinary held-out negative groups "
                f"{seed_table_summary['canonical_ordinary_heldout_negative_groups']}; "
                f"control negative groups {seed_table_summary['canonical_control_negative_groups']}; "
                f"SHA-256 baseline selected spans {seed_table_summary['sha256_selected_spans']}; "
                f"promotion met {seed_table_summary['promotion_met']}."
            ),
            "next": "Treat the public seed-table preset as current null/insufficient evidence; move to the next ranked mechanism or redesign the preset only with stricter controls.",
        },
        {
            "area": "Exact short-hit bundle economics",
            "status": "open",
            "evidence": (
                f"reconstructed exact hits {exact_short_summary['reconstructed_exact_hits']}; "
                f"zero-overhead best delta "
                f"{exact_short_summary['zero_overhead_best_delta_bytes']} bytes; "
                f"full-stream negative rows "
                f"{exact_short_summary['full_stream_negative_rows']}; "
                f"ordinary negative groups "
                f"{exact_short_summary['full_stream_ordinary_negative_groups']}; "
                f"control negative groups "
                f"{exact_short_summary['full_stream_control_negative_groups']}; "
                f"control density comparable "
                f"{exact_short_summary['control_density']['control_density_comparable']}; "
                f"promotion met {exact_short_summary['promotion_met']}."
            ),
            "next": "Treat span-3 hit bundling as blocked by controls unless a future exact-hit artifact changes density or produces longer profitable spans.",
        },
        {
            "area": "Whole-stream residual vector probe",
            "status": "open",
            "evidence": (
                f"honest encoded rows {whole_stream_summary['honest_encoded_rows']}; "
                f"exact decode rows {whole_stream_summary['decode_verified_rows']}; "
                f"honest full-stream negative rows "
                f"{whole_stream_summary['honest_full_stream_negative_rows']}; "
                f"ordinary held-out negative groups "
                f"{whole_stream_summary['ordinary_heldout_negative_groups']}; "
                f"control negative groups {whole_stream_summary['control_negative_groups']}; "
                f"best honest delta {whole_stream_summary['best_honest_delta_bytes']} bytes; "
                f"promotion met {whole_stream_summary['promotion_met']}."
            ),
            "next": "Treat the residual-sidecar family as falsified for broad promotion until a materially different source of seed-span structure appears.",
        },
        {
            "area": "Expander salt ensemble",
            "status": "open",
            "evidence": (
                f"predeclared salts {expander_salt_summary['predeclared_salt_count']}; "
                f"salted exact hits {expander_salt_summary['salted_exact_hits']}; "
                f"salted expected exact hits "
                f"{expander_salt_summary['salted_expected_exact_hits']:.6g}; "
                f"random-trial multiplier exceeded "
                f"{expander_salt_summary['random_trial_multiplier_exceeded']}; "
                f"selected-span rows {expander_salt_summary['salted_selected_span_rows']}; "
                f"full-stream negative rows "
                f"{expander_salt_summary['full_stream_negative_rows']}; "
                f"promotion met {expander_salt_summary['promotion_met']}."
            ),
            "next": "Treat salted expander presets as null until a predeclared ensemble beats equivalent random trials with full-stream wins.",
        },
        {
            "area": "Schema-native public dictionary probe",
            "status": "qualified",
            "evidence": (
                f"public entries {schema_native_summary['public_entry_count']}; "
                f"family selected spans {schema_native_summary['family_selected_spans']}; "
                f"ordinary held-out negative groups "
                f"{schema_native_summary['family_ordinary_heldout_negative_groups']}; "
                f"family control negative groups "
                f"{schema_native_summary['family_control_negative_groups']}; "
                f"wrong-schema negative groups "
                f"{schema_native_summary['wrong_schema_ordinary_negative_groups']}; "
                f"same-size random negative groups "
                f"{schema_native_summary['random_table_ordinary_negative_groups']}; "
                f"shadow negative groups "
                f"{schema_native_summary['shadow_ordinary_negative_groups']}; "
                f"beats generic baseline "
                f"{schema_native_summary['beats_generic_dictionary_baseline']}; "
                f"promotion met {schema_native_summary['promotion_met']}."
            ),
            "next": "Harden this as public dictionary-preset evidence only; do not present it as current `.tlmr` format support or proof of hash-manifold compression.",
        },
        {
            "area": "Schema-native public dictionary replication",
            "status": "qualified"
            if schema_replication_summary["promotion_met"]
            else "blocked-by-evidence",
            "evidence": (
                f"replication corpora {schema_replication_summary['corpus_count']}; "
                f"standards selected spans "
                f"{schema_replication_summary['standards_selected_spans']}; "
                f"ordinary negative groups "
                f"{schema_replication_summary['standards_ordinary_negative_groups']}; "
                f"standards control negative groups "
                f"{schema_replication_summary['standards_control_negative_groups']}; "
                f"generic ordinary negative groups "
                f"{schema_replication_summary['generic_ordinary_negative_groups']}; "
                f"claim level {schema_replication_summary['claim_level']}; "
                f"promotion met {schema_replication_summary['promotion_met']}."
            ),
            "next": "Keep the original schema dictionary result qualified but do not promote registry or format work until paired shadow controls stay null.",
        },
        {
            "area": "Superposition telemetry",
            "status": "qualified"
            if superposition_summary["promotion_met"]
            else "open",
            "evidence": (
                f"fixtures {superposition_summary['fixture_count']}; "
                f"candidates {superposition_summary['candidate_count']}; "
                f"retained alternatives "
                f"{superposition_summary['retained_alternative_count']}; "
                f"weighted extra savings "
                f"{superposition_summary['weighted_extra_savings']}; "
                f"weighted-beats-greedy fixtures "
                f"{superposition_summary['weighted_beats_greedy_fixture_count']}; "
                f"unexplained discards "
                f"{superposition_summary['unexplained_discard_count']}; "
                f"promotion met {superposition_summary['promotion_met']}."
            ),
            "next": "Treat this as selector auditability; only build more lattice machinery if future hit-discovery artifacts produce candidates worth selecting.",
        },
        {
            "area": "Long-span bundle gate",
            "status": "qualified"
            if long_span_gate_summary["promotion_met"]
            else "blocked-by-evidence",
            "evidence": (
                f"gates met {long_span_gate_summary['gate_met_count']} of "
                f"{long_span_gate_summary['gate_count']}; "
                f"recommendation {long_span_gate_summary['recommendation']}; "
                f"best forecast "
                f"{long_span_gate_summary['best_non_planted_gib_for_one_expected_hit']} GiB; "
                f"selected spans {long_span_gate_summary['selected_span_total']}; "
                f"raw-suffix prefix "
                f"{long_span_gate_summary['max_observed_heldout_forced_prefix_len']}/"
                f"{long_span_gate_summary['minimum_raw_suffix_negative_prefix_len']}; "
                f"claim level {long_span_gate_summary['claim_level']}."
            ),
            "next": "Do not run broad long-span bundle sweeps until search-frontier, selected-span, raw-suffix, and control gates pass.",
        },
        {
            "area": "Recursive structured fixtures",
            "status": "qualified"
            if recursive_structured_summary["promotion_met"]
            else "blocked-by-evidence",
            "evidence": (
                f"fixtures {recursive_structured_summary['fixture_count']}; "
                f"ordinary later-win families "
                f"{recursive_structured_summary['ordinary_later_win_families']}; "
                f"planted offset later-win families "
                f"{recursive_structured_summary['planted_offset_later_win_families']}; "
                f"first-pass control win families "
                f"{recursive_structured_summary['first_pass_control_win_families']}; "
                f"all decoded exactly "
                f"{recursive_structured_summary['all_decoded_exact']}; "
                f"claim level {recursive_structured_summary['claim_level']}; "
                f"promotion met {recursive_structured_summary['promotion_met']}."
            ),
            "next": "Keep recursive v2 as format-capable but scientifically unpromoted until ordinary non-offset later-layer wins replicate.",
        },
        {
            "area": "Scale performance",
            "status": "qualified"
            if scale_performance_summary["promotion_met"]
            else "open",
            "evidence": (
                f"largest scale {scale_performance_summary['largest_scale_mib']} MiB; "
                f"peak memory {scale_performance_summary['largest_peak_memory_mib']} MiB; "
                f"peak/table ratio "
                f"{scale_performance_summary['largest_peak_to_estimated_table_ratio']}; "
                f"plateau ratio spread "
                f"{scale_performance_summary['plateau_ratio_spread_pct']}%; "
                f"next doubled peak estimate "
                f"{scale_performance_summary['next_double_peak_memory_mib_at_current_ratio']} MiB."
            ),
            "next": "Treat scale as interpretable but memory-heavy; do not extend planted-density size without chunked target-table or memory-ratio work.",
        },
        {
            "area": "UI workflow smoke",
            "status": "qualified" if ui_workflow_summary["promotion_met"] else "open",
            "evidence": (
                f"UI evidence keys {ui_workflow_summary['ui_evidence_key_count']}; "
                f"Tauri fields "
                f"{ui_workflow_summary['tauri_evidence_field_count']}; "
                f"required cards {ui_workflow_summary['required_card_count']}; "
                f"missing Tauri fields "
                f"{len(ui_workflow_summary['missing_tauri_fields'])}; "
                f"missing mock fields "
                f"{len(ui_workflow_summary['missing_mock_fields'])}; "
                f"claim level {ui_workflow_summary['claim_level']}."
            ),
            "next": "Keep this static schema smoke plus Tauri command tests green before broadening desktop UI claims.",
        },
        {
            "area": "Raw structured corpus",
            "status": "open",
            "evidence": (
                f"best raw structured row {best_raw_structured['name']} "
                f"{best_raw_structured['delta_pct']:.2f}% with "
                f"{best_raw_structured['telemetry']['selected_count'] if 'telemetry' in best_raw_structured else 0} selected spans."
            ),
            "next": "Theory report says current exact-prefix expectation is near zero; test different mechanisms or much larger search.",
        },
        {
            "area": "Corpus generalization probe",
            "status": "open",
            "evidence": (
                f"{corpus_generalization_summary['control_count']} controls scanned "
                f"{corpus_generalization_summary['target_span_count']} target spans; "
                f"prefix>=5 rows {corpus_generalization_summary['rows_with_prefix_ge_5']}, "
                f"exact hits {corpus_generalization_summary['total_exact_hits']}, "
                f"selected spans {corpus_generalization_summary['total_selected_spans']}."
            ),
            "next": "Use this null to prioritize new record-aware transform families over broad corpus-matrix expansion.",
        },
        {
            "area": "Held-out corpus expansion",
            "status": "qualified",
            "evidence": (
                f"{heldout_expansion_summary['corpus_count']} frozen replication corpora, "
                f"{heldout_expansion_summary['ordinary_corpus_count']} ordinary and "
                f"{heldout_expansion_summary['control_corpus_count']} controls, are outside both "
                f"the corpus matrix ({heldout_expansion_summary['missing_corpus_matrix_count']} missing) "
                f"and transform validation ({heldout_expansion_summary['missing_transform_validation_count']} missing). "
                f"Raw frontier rows with prefix>=5 {heldout_expansion_summary['rows_with_prefix_ge_5']}; "
                f"exact hits {heldout_expansion_summary['total_exact_hits']}; "
                f"selected spans {heldout_expansion_summary['total_selected_spans']}."
            ),
            "next": "Promote these corpora into the expensive matrices only if a follow-up creates ordinary held-out prefix>=5 movement or exact selected spans while controls stay null.",
        },
        {
            "area": "Hit-rate theory",
            "status": "qualified",
            "evidence": (
                f"{theory['conclusion']} At depth {frontier_depth3['max_seed_len']}, "
                f"minimum profitable span {frontier_depth3['minimum_profitable_span_len']} "
                f"still leaves {frontier_depth3['gap_bits_at_minimum_profitable_span']:.2f} gap bits."
            ),
            "next": "Use the model to choose future span lengths, seed depths, and corpus sizes before running expensive sweeps.",
        },
        {
            "area": "Manifold proximity",
            "status": "open",
            "evidence": (
                f"best non-planted case {best_manifold['name']} has "
                f"{best_manifold['prefix_ge_4_count']} prefix>=4 spans and "
                f"{best_manifold['exact_span_hits']} exact hits. Prefix>=3 best is "
                f"{manifold['summary']['best_non_planted_prefix_ge_3_case']} with "
                f"{manifold['summary']['best_non_planted_prefix_ge_3_count']} spans; "
                f"planted control has "
                f"{planted_manifold['exact_span_hits']} exact hits."
            ),
            "next": "Search for transforms or corpora whose prefix-proximity telemetry separates from random controls before spending on deeper search.",
        },
        {
            "area": "Transform/preconditioner path",
            "status": "qualified",
            "evidence": (
                f"best transform {best_transform['name']} effective "
                f"{best_transform['effective_delta_pct']:.2f}% with "
                f"{best_transform['telemetry']['selected_count']} selected spans."
            ),
            "next": "Do not count transform-only gains as Telomere wins unless a future format records them.",
        },
        {
            "area": "Transform probe",
            "status": "open",
            "evidence": (
                f"{transform_probe['summary']['best_prefix_ge_4']} produced "
                f"{probe_best_prefix4['prefix_ge_4_count']} prefix>=4 spans but "
                f"{transform_probe['summary']['best_exact_hits']} exact hits across "
                f"{transform_probe['probe_count']} reversible probes."
            ),
            "next": "Validate any shallow prefix-lift transform on held-out corpora before adding format-level transform metadata.",
        },
        {
            "area": "Transform validation",
            "status": "open",
            "evidence": (
                f"held-out prefix>=4 uplift in "
                f"{validation_summary['heldout_prefix4_win_corpora']} corpora; "
                f"held-out exact hits {validation_summary['heldout_exact_hits']}."
            ),
            "next": "Treat non-generalizing transform leads as overfit unless held-out exact hits or repeatable prefix ladders appear.",
        },
        {
            "area": "Structural transform search",
            "status": "open",
            "evidence": (
                f"{structural_summary['candidate_count']} reversible structural candidates over "
                f"{structural_summary['validation_rows']} validation rows; held-out prefix>=5 win corpora "
                f"{structural_summary['heldout_prefix5_win_corpora']}; held-out exact hits "
                f"{structural_summary['heldout_exact_hits']}; shadow prefix>=5 win corpora "
                f"{structural_summary['shadow_prefix5_win_corpora']}; binary exact hits "
                f"{structural_summary['binary_exact_hits']}."
            ),
            "next": "Keep structural transforms as null-control evidence unless held-out prefix>=5 uplift or exact seed-span hits appear.",
        },
        {
            "area": "Byte permutation transform search",
            "status": "open",
            "evidence": (
                f"{byte_permutation_summary['transform_count']} byte-permutation candidates over "
                f"{byte_permutation_summary['row_count']} rows; prefix>=5 rows "
                f"{byte_permutation_summary['rows_with_prefix_ge_5']}; exact hits "
                f"{byte_permutation_summary['total_exact_hits']}; selected spans "
                f"{byte_permutation_summary['total_selected_spans']}; rows negative after metadata "
                f"{byte_permutation_summary['rows_negative_after_metadata']}."
            ),
            "next": "Treat finite seed-byte distribution alignment as null until phase maps produce prefix>=5 or exact hits.",
        },
        {
            "area": "BWT/MTF transform probe",
            "status": "open",
            "evidence": (
                f"{bwt_mtf_summary['transform_count']} BWT/MTF/RLE candidates over "
                f"{bwt_mtf_summary['row_count']} rows; prefix>=5 rows "
                f"{bwt_mtf_summary['rows_with_prefix_ge_5']}; exact hits "
                f"{bwt_mtf_summary['total_exact_hits']}; selected spans "
                f"{bwt_mtf_summary['total_selected_spans']}; rows negative after metadata "
                f"{bwt_mtf_summary['rows_negative_after_metadata']}; shorter transformed payload rows "
                f"{bwt_mtf_summary['rows_with_shorter_transformed_payload']}."
            ),
            "next": "Treat classic preconditioner shortening as transform-only evidence unless exact seed-span hits survive metadata.",
        },
        {
            "area": "Grammar channel match discovery",
            "status": "open",
            "evidence": (
                f"{grammar_channel_summary['channel_count']} reversible grammar channels over "
                f"{grammar_channel_summary['row_count']} rows; prefix>=5 rows "
                f"{grammar_channel_summary['rows_with_prefix_ge_5']}; exact hits "
                f"{grammar_channel_summary['total_exact_hits']}; selected spans "
                f"{grammar_channel_summary['total_selected_spans']}; rows negative after metadata "
                f"{grammar_channel_summary['rows_negative_after_metadata']}."
            ),
            "next": "Treat first-pass grammar channels as null until a parser-backed channel yields held-out/control-safe prefix>=5 or exact hits.",
        },
        {
            "area": "Numeric value-channel match discovery",
            "status": "open",
            "evidence": (
                f"{numeric_value_channel_summary['channel_count']} numeric value channels over "
                f"{numeric_value_channel_summary['row_count']} rows; parsed values "
                f"{numeric_value_channel_summary['parsed_value_count']}; prefix>=5 rows "
                f"{numeric_value_channel_summary['rows_with_prefix_ge_5']}; exact hits "
                f"{numeric_value_channel_summary['total_exact_hits']}; selected spans "
                f"{numeric_value_channel_summary['total_selected_spans']}; rows negative after metadata "
                f"{numeric_value_channel_summary['rows_negative_after_metadata']}."
            ),
            "next": "Treat parsed numeric value streams as null until exact seed-span hits survive full reconstruction metadata.",
        },
        {
            "area": "Record context transform search",
            "status": "open",
            "evidence": (
                f"{record_context_summary['transform_count']} record/context candidates over "
                f"{record_context_summary['row_count']} rows; prefix>=5 rows "
                f"{record_context_summary['rows_with_prefix_ge_5']}; exact hits "
                f"{record_context_summary['total_exact_hits']}; selected spans "
                f"{record_context_summary['total_selected_spans']}; rows negative after metadata "
                f"{record_context_summary['rows_negative_after_metadata']}."
            ),
            "next": "Treat record-aware transforms as null evidence until metadata-positive exact seed spans appear.",
        },
        {
            "area": "Token dictionary transform search",
            "status": "open",
            "evidence": (
                f"{token_dictionary_summary['transform_count']} token/dictionary candidates over "
                f"{token_dictionary_summary['row_count']} rows; prefix>=5 rows "
                f"{token_dictionary_summary['rows_with_prefix_ge_5']}; exact hits "
                f"{token_dictionary_summary['total_exact_hits']}; selected spans "
                f"{token_dictionary_summary['total_selected_spans']}; rows negative after metadata "
                f"{token_dictionary_summary['rows_negative_after_metadata']}."
            ),
            "next": "Do not promote token dictionaries unless exact seed-span hits survive dictionary metadata.",
        },
        {
            "area": "Affine transform search",
            "status": "open",
            "evidence": (
                f"{affine_summary['searched_candidate_count']} affine/phase-affine candidates searched; "
                f"{affine_summary['selected_candidate_count']} candidates validated over "
                f"{affine_summary['validation_rows']} rows; held-out prefix>=4 win corpora "
                f"{affine_summary['heldout_prefix4_win_corpora']}; held-out prefix>=5 win corpora "
                f"{affine_summary['heldout_prefix5_win_corpora']}; held-out exact hits "
                f"{affine_summary['heldout_exact_hits']}; binary exact hits "
                f"{affine_summary['binary_exact_hits']}."
            ),
            "next": "Treat prefix-4 uplift as a steering clue only; test residual-sidecar economics before depth-3 escalation.",
        },
        {
            "area": "Seed-manifold residual steering",
            "status": "open",
            "evidence": (
                f"{residual_summary['candidate_count']} residual-sidecar schemes over "
                f"{residual_summary['validation_rows']} validation rows; held-out forced rows "
                f"{residual_summary['heldout_forced_rows']}; held-out rows with positive seed contribution "
                f"{residual_summary['heldout_seed_contribution_positive_rows']}; held-out positive net-delta rows "
                f"{residual_summary['heldout_positive_rows']}; best held-out net delta "
                f"{residual_summary['best_heldout_net_delta_bytes']} bytes."
            ),
            "next": "Do not promote sidecar steering unless residual bytes plus metadata beat literal storage on held-out rows.",
        },
        {
            "area": "Sidecar break-even",
            "status": "open",
            "evidence": (
                f"{sidecar_break_even_summary['row_count']} break-even rows; "
                f"raw-suffix strict gain starts at prefix "
                f"{sidecar_break_even_summary['minimum_raw_suffix_negative_prefix_len']}; "
                f"max observed held-out forced prefix "
                f"{sidecar_break_even_summary['max_observed_heldout_forced_prefix_len']}; "
                f"raw-suffix viable rows at observed prefix "
                f"{sidecar_break_even_summary['raw_suffix_viable_at_observed_prefix_rows']}; "
                f"sublinear-model viable rows at observed prefix "
                f"{sidecar_break_even_summary['sublinear_model_viable_at_observed_prefix_rows']}; "
                f"promoted rows {sidecar_break_even_summary['promoted_rows']}."
            ),
            "next": "Measure residual payload compressibility before testing more sidecar families; sublinear rows are hypotheses, not compression wins.",
        },
        {
            "area": "Residual payload compressibility",
            "status": "qualified",
            "evidence": (
                f"{residual_payload_summary['heldout_payload_rows']} held-out payload rows; "
                f"measured held-out negative rows "
                f"{residual_payload_summary['measured_heldout_negative_rows']}; "
                f"best measured held-out case "
                f"{residual_payload_summary['best_measured_heldout_negative_case']}; "
                f"zlib held-out best "
                f"{residual_payload_summary['best_heldout_net_delta_by_policy']['zlib_level9']} bytes; "
                f"LZMA held-out best "
                f"{residual_payload_summary['best_heldout_net_delta_by_policy']['lzma_preset9']} bytes."
            ),
            "next": "Prototype an experimental payload descriptor only for this narrow signal, with decode proof and controls before any format proposal.",
        },
        {
            "area": "Experimental sidecar descriptor",
            "status": "qualified",
            "evidence": (
                f"{experimental_sidecar_summary['prototype_rows']} prototype rows; "
                f"decode verified rows {experimental_sidecar_summary['decode_verified_rows']}; "
                f"full-stream negative rows {experimental_sidecar_summary['full_stream_negative_rows']}; "
                f"best full-stream delta "
                f"{experimental_sidecar_summary['best_full_stream_delta_bytes']} bytes; "
                f"best local selected delta "
                f"{experimental_sidecar_summary['best_local_selected_delta_bytes']} bytes."
            ),
            "next": "Do not promote sidecar format support until record overhead or span bundles turn the decoded prototype negative as a full stream.",
        },
        {
            "area": "Sidecar record overhead",
            "status": "qualified",
            "evidence": (
                f"{sidecar_record_summary['layout_rows']} layout rows; "
                f"negative rows {sidecar_record_summary['negative_layout_rows']}; "
                f"best safe layout {sidecar_record_summary['best_safe_layout']} "
                f"{sidecar_record_summary['best_safe_delta_bytes']} bytes."
            ),
            "next": "Prototype the packed offset/seed-index decoder before treating this budget as format evidence.",
        },
        {
            "area": "Packed sidecar descriptor",
            "status": "qualified",
            "evidence": (
                f"{packed_sidecar_summary['prototype_rows']} prototype rows; "
                f"decode verified rows {packed_sidecar_summary['decode_verified_rows']}; "
                f"full-stream negative rows {packed_sidecar_summary['full_stream_negative_rows']}; "
                f"best coder {packed_sidecar_summary['best_coder']} "
                f"{packed_sidecar_summary['best_delta_bytes']} bytes."
            ),
            "next": "Treat as a narrow signal; validate controls and additional held-out corpora before any `.tlmr` proposal.",
        },
        {
            "area": "Packed sidecar controls",
            "status": "qualified",
            "evidence": (
                f"{packed_controls_summary['control_rows']} control rows; "
                f"encoded rows {packed_controls_summary['encoded_rows']}; "
                f"unique negative cases {packed_controls_summary['unique_negative_cases']}; "
                f"ordinary held-out negative cases "
                f"{packed_controls_summary['ordinary_heldout_negative_cases']}; "
                f"best delta {packed_controls_summary['best_delta_bytes']} bytes."
            ),
            "next": "Generalize the packed layout beyond u8-delta rows and replicate on more ordinary held-out cases before format work.",
        },
        {
            "area": "Generalized packed sidecar",
            "status": "qualified",
            "evidence": (
                f"{generalized_packed_summary['encoded_rows']} encoded rows from "
                f"{generalized_packed_summary['unique_encoded_source_rows']} unique source rows; "
                f"unique negative cases {generalized_packed_summary['unique_negative_cases']}; "
                f"ordinary held-out negative cases "
                f"{generalized_packed_summary['ordinary_heldout_negative_cases']}; "
                f"best-supported table bytes "
                f"{generalized_packed_summary['best_of_supported_modes_total_table_bytes']} "
                f"versus baseline "
                f"{generalized_packed_summary['baseline_delta_u16_global_u16_total_table_bytes']}."
            ),
            "next": "Do not change `.tlmr`; descriptor packing alone needs replication before it is a format lane.",
        },
        {
            "area": "Packed sidecar replication",
            "status": "open",
            "evidence": (
                f"{packed_replication_summary['corpus_count']} frozen corpora; "
                f"{packed_replication_summary['source_case_count']} source cases; "
                f"{packed_replication_summary['descriptor_row_count']} descriptor rows; "
                f"full-stream negative rows "
                f"{packed_replication_summary['full_stream_negative_rows']}; "
                f"ordinary held-out negative groups "
                f"{packed_replication_summary['ordinary_heldout_negative_groups']}."
            ),
            "next": "Shift the sidecar lane back to match discovery; do not spend more on descriptor packing until independent held-out matches exist.",
        },
        {
            "area": "Match discovery",
            "status": "open",
            "evidence": (
                f"{match_discovery_summary['corpus_count']} corpora; "
                f"{match_discovery_summary['row_count']} rows; "
                f"{match_discovery_summary['target_span_count']} target spans; "
                f"rows with prefix>=5 {match_discovery_summary['rows_with_prefix_ge_5']}; "
                f"rows with exact hits {match_discovery_summary['rows_with_exact_hits']}; "
                f"selected spans {match_discovery_summary['total_selected_spans']}."
            ),
            "next": "Try alignment/arity and deeper search only where a new predeclared lead moves prefix ladders or exact hits.",
        },
        {
            "area": "Alignment and arity discovery",
            "status": "open",
            "evidence": (
                f"{alignment_summary['target_span_count']} target spans; "
                f"{alignment_summary['config_count']} supported configs; "
                f"rows with prefix>=5 {alignment_summary['rows_with_prefix_ge_5']}; "
                f"exact hits {alignment_summary['total_exact_hits']}; "
                f"positive exact hits {alignment_summary['total_positive_exact_hits']}; "
                f"selected spans {alignment_summary['total_selected_spans']}."
            ),
            "next": "Do not spend on more alignment tuning unless it produces profitable hits or repeatable prefix>=5 movement.",
        },
        {
            "area": "Transformed match discovery",
            "status": "open",
            "evidence": (
                f"{transformed_match_summary['target_span_count']} transformed target spans; "
                f"{transformed_match_summary['transform_count']} frozen transforms; "
                f"rows with prefix>=5 {transformed_match_summary['rows_with_prefix_ge_5']}; "
                f"exact hits {transformed_match_summary['total_exact_hits']}; "
                f"selected spans {transformed_match_summary['total_selected_spans']}; "
                f"metadata-profitable rows {transformed_match_summary['metadata_profitable_rows']}."
            ),
            "next": "Treat the current frozen transforms as null evidence until a new family creates exact selected spans after metadata.",
        },
        {
            "area": "Lead exact discovery",
            "status": "open",
            "evidence": (
                f"{lead_exact_summary['target_span_count']} selected-lead target spans; "
                f"{lead_exact_summary['lead_count']} leads; "
                f"rows with prefix>=5 {lead_exact_summary['rows_with_prefix_ge_5']}; "
                f"exact hits {lead_exact_summary['total_exact_hits']}; "
                f"selected spans {lead_exact_summary['total_selected_spans']}; "
                f"metadata-profitable rows {lead_exact_summary['metadata_profitable_rows']}."
            ),
            "next": "Do not broaden existing prefix-4 leads; move to new transform families or bounded deeper-seed exact discovery.",
        },
        {
            "area": "Periodic transform probe",
            "status": "open",
            "evidence": (
                f"{periodic_probe['candidate_count']} bounded periodic masks selected "
                f"{periodic_probe['selected_transform_count']} discovery leads; held-out "
                f"prefix>=5 uplift in {periodic_summary['heldout_prefix5_win_corpora']} corpora; "
                f"held-out exact hits {periodic_summary['heldout_exact_hits']}."
            ),
            "next": "Promote deeper search only if periodic or related transforms produce prefix>=5 uplift or exact seed-span hits.",
        },
        {
            "area": "Composed transform probe",
            "status": "open",
            "evidence": (
                f"{composed_probe['candidate_count']} context+periodic compositions selected "
                f"{composed_probe['selected_transform_count']} discovery leads; held-out "
                f"prefix>=5 uplift in {composed_summary['heldout_prefix5_win_corpora']} corpora; "
                f"held-out exact hits {composed_summary['heldout_exact_hits']}."
            ),
            "next": "Composition is not a promotion path unless it creates held-out prefix>=5 or exact seed-span events.",
        },
        {
            "area": "Near-miss forecast",
            "status": "open",
            "evidence": (
                f"best non-planted case {nearmiss_summary['best_non_planted_case']} "
                f"expects {nearmiss_summary['best_non_planted_expected_exact_hits']:.3e} "
                f"exact hits in observed bytes."
            ),
            "next": "Use near-miss forecasts to decide whether a transform lead deserves deeper seed or larger-corpus runs.",
        },
        {
            "area": "Prefix ladder",
            "status": "open",
            "evidence": (
                f"{ladder_summary['heldout_rows_with_prefix4']} held-out/control rows reach prefix>=4; "
                f"{ladder_summary['heldout_rows_with_prefix5']} reach prefix>=5; "
                f"best prefix-4 case {ladder_summary['best_prefix4_case']} has "
                f"{ladder_summary['best_prefix4_count']} prefix>=4 spans."
            ),
            "next": "Target fifth-byte survival before promoting deeper exact search.",
        },
        {
            "area": "Fifth-byte residual",
            "status": "open",
            "evidence": (
                f"{fifth_summary['rows_analyzed']} prefix-4 lead rows analyzed; "
                f"best robust XOR residual coverage "
                f"{fifth_summary['robust_best_xor_residual_coverage']:.2%}; "
                f"best robust add residual coverage "
                f"{fifth_summary['robust_best_add_residual_coverage']:.2%}."
            ),
            "next": "Do not build format transforms from fifth-byte residuals unless coverage becomes concentrated on held-out rows.",
        },
        {
            "area": "Fifth-byte steering",
            "status": "open",
            "evidence": (
                f"{steering_summary['candidate_count']} residual-derived masks checked across "
                f"{steering_summary['heldout_cross_rows']} held-out cross-corpus rows; "
                f"prefix>=4 win rows {steering_summary['cross_prefix4_win_rows']}; "
                f"prefix>=5 win rows {steering_summary['cross_prefix5_win_rows']}; "
                f"exact-hit rows {steering_summary['cross_exact_hit_rows']}."
            ),
            "next": "Residual masks are not a promotion path unless they generalize into cross-corpus prefix>=5 or exact hits.",
        },
        {
            "area": "Contextual fifth-byte steering",
            "status": "open",
            "evidence": (
                f"{contextual_summary['candidate_count']} context-conditioned masks checked across "
                f"{contextual_summary['heldout_cross_rows']} held-out cross-corpus rows; "
                f"prefix>=5 win rows {contextual_summary['cross_prefix5_win_rows']}; "
                f"exact-hit rows {contextual_summary['cross_exact_hit_rows']}; "
                f"null-control prefix>=5 win rows {contextual_summary['null_cross_prefix5_win_rows']}."
            ),
            "next": "Do not promote context-conditioned fifth-byte steering unless it beats null controls on held-out prefix>=5 or exact hits.",
        },
        {
            "area": "Scale economics",
            "status": "qualified",
            "evidence": (
                f"{largest_scale['name']} {largest_scale['input_bytes']} -> "
                f"{largest_scale['output_bytes']} bytes, peak {largest_scale['peak_memory_mib']} MiB."
            ),
            "next": (
                f"Push beyond {largest_scale['input_bytes'] / (1024 * 1024):.0f} MiB "
                "only after candidate telemetry and memory stay controlled."
            ),
        },
        {
            "area": "Production acceleration",
            "status": "open",
            "evidence": (
                f"acceleration status {acceleration['detected']['status']}; "
                f"real kernel detected {acceleration['detected']['real_kernel_detected']}."
            ),
            "next": "Add real OpenCL/CUDA only behind CPU parity and benchmark gates.",
        },
    ]

    return {
        "generated_by": "scripts/generate_research_scorecard.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "verdict": viability["verdict"],
        "overall_status": "not production-proven",
        "viability_status_counts": dict(viability_status_counts),
        "scorecard_status_counts": dict(Counter(card["status"] for card in cards)),
        "artifact_hashes": artifact_hashes(),
        "cards": cards,
        "open_questions": viability["open_questions"],
    }


def write_scorecard(payload: dict[str, Any]) -> None:
    SCORECARD_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Telomere Research Scorecard",
        "",
        "Generated by `scripts/generate_research_scorecard.py` from the checked-in result artifacts.",
        "This is the top-level proof map for the research program.",
        "",
        f"Overall research status: **{payload['overall_status']}**.",
        f"Viability verdict: **{payload['verdict']}**.",
        "",
        "## Viability Status Counts",
        "",
    ]
    for status, count in sorted(payload["viability_status_counts"].items()):
        lines.append(f"- `{status}`: {count}")

    lines.extend(["", "## Scorecard Status Counts", ""])
    for status, count in sorted(payload["scorecard_status_counts"].items()):
        lines.append(f"- `{status}`: {count}")

    lines.extend(
        [
            "",
            "## Scorecard",
            "",
            "| area | status | evidence | next |",
            "| --- | --- | --- | --- |",
        ]
    )
    for card in payload["cards"]:
        lines.append(
            "| {area} | {status} | {evidence} | {next} |".format(**card)
        )

    lines.extend(["", "## Open Questions", ""])
    lines.extend(f"- {question}" for question in payload["open_questions"])

    lines.extend(["", "## Source Artifacts", ""])
    for name, digest in payload["artifact_hashes"].items():
        lines.append(f"- `{name}`: `{digest}`")

    SCORECARD_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_scorecard() -> None:
    if not SCORECARD_JSON.exists() or not SCORECARD_MD.exists():
        raise SystemExit("generated research scorecard files are missing")
    payload = load_json(SCORECARD_JSON)
    if payload.get("generated_by") != "scripts/generate_research_scorecard.py":
        raise SystemExit("research_scorecard.json has wrong generated_by marker")
    if payload.get("artifact_hashes") != artifact_hashes():
        raise SystemExit("research scorecard artifact hashes are stale")
    expected = stable_projection(build_scorecard())
    current = stable_projection(payload)
    if current != expected:
        raise SystemExit("research_scorecard.json is stale; regenerate it")
    text = SCORECARD_MD.read_text(encoding="utf-8")
    for phrase in (
        "Overall research status",
        "not production-proven",
        "Raw structured corpus",
        "Corpus generalization probe",
        "Held-out corpus expansion",
        "Depth-3 prefix frontier",
        "Selected-lead depth-3 follow-up",
        "Depth-3 frontier exact discovery",
        "Depth-4 shard plan",
        "Depth-4 pilot shard",
        "Search frontier gate",
        "Mechanism experiment ranking",
        "Seed-table preset probe",
        "Exact short-hit bundle economics",
        "Whole-stream residual vector probe",
        "Expander salt ensemble",
        "Schema-native public dictionary probe",
        "Schema-native public dictionary replication",
        "Superposition telemetry",
        "Long-span bundle gate",
        "Recursive structured fixtures",
        "Scale performance",
        "UI workflow smoke",
        "Transform/preconditioner path",
        "Periodic transform probe",
        "Structural transform search",
        "Byte permutation transform search",
        "BWT/MTF transform probe",
        "Grammar channel match discovery",
        "Numeric value-channel match discovery",
        "Record context transform search",
        "Token dictionary transform search",
        "Affine transform search",
        "Seed-manifold residual steering",
        "Sidecar break-even",
        "Residual payload compressibility",
        "Experimental sidecar descriptor",
        "Sidecar record overhead",
        "Packed sidecar descriptor",
        "Packed sidecar controls",
        "Generalized packed sidecar",
        "Packed sidecar replication",
        "Match discovery",
        "Alignment and arity discovery",
        "Transformed match discovery",
        "Lead exact discovery",
        "Composed transform probe",
        "Prefix ladder",
        "Fifth-byte residual",
        "Fifth-byte steering",
        "Contextual fifth-byte steering",
    ):
        if phrase not in text:
            raise SystemExit(f"RESEARCH_SCORECARD.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate generated scorecard files")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.check:
        check_scorecard()
        return
    write_scorecard(build_scorecard())


if __name__ == "__main__":
    main()
