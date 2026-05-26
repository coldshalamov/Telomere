#!/usr/bin/env python3
"""Generate a viability ledger from checked-in Telomere result artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
RESULTS_PATH = DOCS / "results.json"
SWEEPS_PATH = DOCS / "sweeps.json"
DEEP_SWEEPS_PATH = DOCS / "deep_sweeps.json"
TRANSFORM_SWEEPS_PATH = DOCS / "transform_sweeps.json"
CORPUS_MATRIX_PATH = DOCS / "corpus_matrix.json"
CORPUS_GENERALIZATION_PATH = DOCS / "corpus_generalization_probe.json"
COMPOSED_PROBE_PATH = DOCS / "composed_transform_probe.json"
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
VIABILITY_JSON = DOCS / "viability.json"
VIABILITY_MD = DOCS / "VIABILITY.md"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def artifact_hashes() -> dict[str, str]:
    return {
        "results_sha256": hashlib.sha256(RESULTS_PATH.read_bytes()).hexdigest(),
        "sweeps_sha256": hashlib.sha256(SWEEPS_PATH.read_bytes()).hexdigest(),
        "deep_sweeps_sha256": hashlib.sha256(DEEP_SWEEPS_PATH.read_bytes()).hexdigest(),
        "transform_sweeps_sha256": hashlib.sha256(TRANSFORM_SWEEPS_PATH.read_bytes()).hexdigest(),
        "corpus_matrix_sha256": hashlib.sha256(CORPUS_MATRIX_PATH.read_bytes()).hexdigest(),
        "corpus_generalization_probe_sha256": hashlib.sha256(
            CORPUS_GENERALIZATION_PATH.read_bytes()
        ).hexdigest(),
        "composed_transform_probe_sha256": hashlib.sha256(COMPOSED_PROBE_PATH.read_bytes()).hexdigest(),
        "depth3_prefix_probe_sha256": hashlib.sha256(
            DEPTH3_PREFIX_PROBE_PATH.read_bytes()
        ).hexdigest(),
        "depth3_compression_followup_sha256": hashlib.sha256(
            DEPTH3_COMPRESSION_FOLLOWUP_PATH.read_bytes()
        ).hexdigest(),
        "lead_depth3_prefix_probe_sha256": hashlib.sha256(
            LEAD_DEPTH3_PREFIX_PROBE_PATH.read_bytes()
        ).hexdigest(),
        "lead_depth3_compression_followup_sha256": hashlib.sha256(
            LEAD_DEPTH3_COMPRESSION_FOLLOWUP_PATH.read_bytes()
        ).hexdigest(),
        "depth3_frontier_exact_discovery_sha256": hashlib.sha256(
            DEPTH3_FRONTIER_EXACT_DISCOVERY_PATH.read_bytes()
        ).hexdigest(),
        "depth4_shard_plan_sha256": hashlib.sha256(
            DEPTH4_SHARD_PLAN_PATH.read_bytes()
        ).hexdigest(),
        "depth4_pilot_shard_sha256": hashlib.sha256(
            DEPTH4_PILOT_SHARD_PATH.read_bytes()
        ).hexdigest(),
        "search_frontier_gate_sha256": hashlib.sha256(
            SEARCH_FRONTIER_GATE_PATH.read_bytes()
        ).hexdigest(),
        "mechanism_experiment_ranking_sha256": hashlib.sha256(
            MECHANISM_EXPERIMENT_RANKING_PATH.read_bytes()
        ).hexdigest(),
        "seed_table_preset_probe_sha256": hashlib.sha256(
            SEED_TABLE_PRESET_PROBE_PATH.read_bytes()
        ).hexdigest(),
        "exact_short_hit_bundle_economics_sha256": hashlib.sha256(
            EXACT_SHORT_HIT_BUNDLE_ECONOMICS_PATH.read_bytes()
        ).hexdigest(),
        "whole_stream_residual_vector_probe_sha256": hashlib.sha256(
            WHOLE_STREAM_RESIDUAL_VECTOR_PROBE_PATH.read_bytes()
        ).hexdigest(),
        "expander_salt_ensemble_sha256": hashlib.sha256(
            EXPANDER_SALT_ENSEMBLE_PATH.read_bytes()
        ).hexdigest(),
        "schema_native_public_dictionaries_sha256": hashlib.sha256(
            SCHEMA_NATIVE_PUBLIC_DICTIONARIES_PATH.read_bytes()
        ).hexdigest(),
        "schema_native_public_dictionary_replication_sha256": hashlib.sha256(
            SCHEMA_NATIVE_PUBLIC_DICTIONARY_REPLICATION_PATH.read_bytes()
        ).hexdigest(),
        "superposition_telemetry_sha256": hashlib.sha256(
            SUPERPOSITION_TELEMETRY_PATH.read_bytes()
        ).hexdigest(),
        "long_span_bundle_gate_sha256": hashlib.sha256(
            LONG_SPAN_BUNDLE_GATE_PATH.read_bytes()
        ).hexdigest(),
        "recursive_structured_fixtures_sha256": hashlib.sha256(
            RECURSIVE_STRUCTURED_FIXTURES_PATH.read_bytes()
        ).hexdigest(),
        "scale_performance_report_sha256": hashlib.sha256(
            SCALE_PERFORMANCE_PATH.read_bytes()
        ).hexdigest(),
        "ui_workflow_smoke_sha256": hashlib.sha256(
            UI_WORKFLOW_SMOKE_PATH.read_bytes()
        ).hexdigest(),
        "contextual_fifth_byte_steering_sha256": hashlib.sha256(
            CONTEXTUAL_STEERING_PATH.read_bytes()
        ).hexdigest(),
        "structural_transform_search_sha256": hashlib.sha256(
            STRUCTURAL_SEARCH_PATH.read_bytes()
        ).hexdigest(),
        "byte_permutation_transform_search_sha256": hashlib.sha256(
            BYTE_PERMUTATION_SEARCH_PATH.read_bytes()
        ).hexdigest(),
        "bwt_mtf_transform_probe_sha256": hashlib.sha256(
            BWT_MTF_PROBE_PATH.read_bytes()
        ).hexdigest(),
        "grammar_channel_match_discovery_sha256": hashlib.sha256(
            GRAMMAR_CHANNEL_DISCOVERY_PATH.read_bytes()
        ).hexdigest(),
        "numeric_value_channel_match_discovery_sha256": hashlib.sha256(
            NUMERIC_VALUE_CHANNEL_DISCOVERY_PATH.read_bytes()
        ).hexdigest(),
        "heldout_corpus_expansion_sha256": hashlib.sha256(
            HELDOUT_CORPUS_EXPANSION_PATH.read_bytes()
        ).hexdigest(),
        "record_context_transform_search_sha256": hashlib.sha256(
            RECORD_CONTEXT_SEARCH_PATH.read_bytes()
        ).hexdigest(),
        "token_dictionary_transform_search_sha256": hashlib.sha256(
            TOKEN_DICTIONARY_SEARCH_PATH.read_bytes()
        ).hexdigest(),
        "affine_transform_search_sha256": hashlib.sha256(
            AFFINE_SEARCH_PATH.read_bytes()
        ).hexdigest(),
        "seed_manifold_residual_steering_sha256": hashlib.sha256(
            RESIDUAL_STEERING_PATH.read_bytes()
        ).hexdigest(),
        "sidecar_break_even_sha256": hashlib.sha256(
            SIDECAR_BREAK_EVEN_PATH.read_bytes()
        ).hexdigest(),
        "residual_payload_compressibility_sha256": hashlib.sha256(
            RESIDUAL_PAYLOAD_COMPRESSIBILITY_PATH.read_bytes()
        ).hexdigest(),
        "experimental_sidecar_descriptor_sha256": hashlib.sha256(
            EXPERIMENTAL_SIDECAR_DESCRIPTOR_PATH.read_bytes()
        ).hexdigest(),
        "sidecar_record_overhead_sha256": hashlib.sha256(
            SIDECAR_RECORD_OVERHEAD_PATH.read_bytes()
        ).hexdigest(),
        "packed_sidecar_descriptor_sha256": hashlib.sha256(
            PACKED_SIDECAR_DESCRIPTOR_PATH.read_bytes()
        ).hexdigest(),
        "packed_sidecar_controls_sha256": hashlib.sha256(
            PACKED_SIDECAR_CONTROLS_PATH.read_bytes()
        ).hexdigest(),
        "generalized_packed_sidecar_sha256": hashlib.sha256(
            GENERALIZED_PACKED_SIDECAR_PATH.read_bytes()
        ).hexdigest(),
        "packed_sidecar_replication_sha256": hashlib.sha256(
            PACKED_SIDECAR_REPLICATION_PATH.read_bytes()
        ).hexdigest(),
        "match_discovery_sha256": hashlib.sha256(
            MATCH_DISCOVERY_PATH.read_bytes()
        ).hexdigest(),
        "alignment_arity_discovery_sha256": hashlib.sha256(
            ALIGNMENT_ARITY_DISCOVERY_PATH.read_bytes()
        ).hexdigest(),
        "transformed_match_discovery_sha256": hashlib.sha256(
            TRANSFORMED_MATCH_DISCOVERY_PATH.read_bytes()
        ).hexdigest(),
        "lead_exact_discovery_sha256": hashlib.sha256(
            LEAD_EXACT_DISCOVERY_PATH.read_bytes()
        ).hexdigest(),
    }


def stable_projection(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if key != "generated_at"
    }


def row_by_name(rows: list[dict[str, Any]], name: str) -> dict[str, Any]:
    for row in rows:
        if row["name"] == name:
            return row
    raise KeyError(name)


def first_negative_density(sweep_rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    density_rows = [
        row
        for row in sweep_rows
        if row["group"] == "planted-density" and row["delta_bytes"] < 0
    ]
    return min(density_rows, key=lambda row: row["density_bytes"], default=None)


def largest_scale_row(sweep_rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    scale_rows = [row for row in sweep_rows if row["group"] == "memory-scaling"]
    return max(scale_rows, key=lambda row: row["input_bytes"], default=None)


def structured_control_rows(sweep_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        row
        for row in sweep_rows
        if row["group"] == "structured-search" or row["name"].startswith("structured-json-")
    ]


def status(ok: bool, caution: bool = False) -> str:
    if ok and not caution:
        return "proved"
    if ok and caution:
        return "qualified"
    return "open"


def build_ledger(
    results: dict[str, Any],
    sweeps: dict[str, Any],
    deep_sweeps: dict[str, Any],
    transform_sweeps: dict[str, Any],
    corpus_matrix: dict[str, Any],
    corpus_generalization: dict[str, Any],
    composed_probe: dict[str, Any],
    depth3_prefix_probe: dict[str, Any],
    depth3_followup: dict[str, Any],
    lead_depth3_prefix_probe: dict[str, Any],
    lead_depth3_followup: dict[str, Any],
    depth3_frontier_exact_discovery: dict[str, Any],
    depth4_shard_plan: dict[str, Any],
    depth4_pilot_shard: dict[str, Any],
    search_frontier_gate: dict[str, Any],
    mechanism_experiment_ranking: dict[str, Any],
    seed_table_preset_probe: dict[str, Any],
    exact_short_hit_bundle_economics: dict[str, Any],
    whole_stream_residual_vector_probe: dict[str, Any],
    expander_salt_ensemble: dict[str, Any],
    schema_native_public_dictionaries: dict[str, Any],
    schema_native_public_dictionary_replication: dict[str, Any],
    superposition_telemetry: dict[str, Any],
    long_span_bundle_gate: dict[str, Any],
    recursive_structured_fixtures: dict[str, Any],
    scale_performance: dict[str, Any],
    ui_workflow_smoke: dict[str, Any],
    contextual_steering: dict[str, Any],
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
) -> dict[str, Any]:
    result_rows = results["results"]
    sweep_rows = sweeps["results"]
    deep_rows = deep_sweeps["results"]
    transform_rows = transform_sweeps["results"]
    corpus_rows = corpus_matrix["results"]
    corpus_generalization_summary = corpus_generalization["summary"]
    composed_summary = composed_probe["summary"]
    depth3_prefix_summary = depth3_prefix_probe["summary"]
    depth3_followup_summary = depth3_followup["summary"]
    lead_depth3_prefix_summary = lead_depth3_prefix_probe["summary"]
    lead_depth3_followup_summary = lead_depth3_followup["summary"]
    depth3_frontier_summary = depth3_frontier_exact_discovery["summary"]
    depth4_gate = depth4_shard_plan["promotion_gate"]
    depth4_estimates = depth4_shard_plan["depth4_estimates"]
    depth4_pilot_summary = depth4_pilot_shard["summary"]
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

    random_null = row_by_name(result_rows, "streaming-random-null-1k")
    planted_arity2 = row_by_name(result_rows, "planted-sha256-arity2")
    indexed_span8 = row_by_name(result_rows, "indexed-planted-span8")
    streaming_span8 = row_by_name(result_rows, "streaming-planted-span8")
    span4 = row_by_name(sweep_rows, "span-4")
    span20 = row_by_name(sweep_rows, "span-20")
    offset1_pass1 = row_by_name(sweep_rows, "offset-1-passes-1")
    offset1_pass2 = row_by_name(sweep_rows, "offset-1-passes-2")
    offset1_pass4 = row_by_name(sweep_rows, "offset-1-passes-4")
    offset_span_step_rows = [
        row_by_name(sweep_rows, f"offset-{offset}-span-step-1")
        for offset in (1, 2, 3)
    ]
    seed2_depth1 = row_by_name(sweep_rows, "seed2-planted-depth1")
    seed2_depth2 = row_by_name(sweep_rows, "seed2-planted-depth2")
    structured_depth2 = row_by_name(sweep_rows, "structured-json-depth2-span8-step1-pass1")
    seed3_depth2 = row_by_name(deep_rows, "seed3-planted-depth2")
    seed3_depth3 = row_by_name(deep_rows, "seed3-planted-depth3")
    structured_depth3 = row_by_name(deep_rows, "structured-json-depth3-span8-step1-pass1")
    transform_identity = row_by_name(transform_rows, "structured-identity-depth2")
    transform_xor = row_by_name(transform_rows, "structured-xor-prev-depth2")
    transform_sub = row_by_name(transform_rows, "structured-sub-prev-depth2")
    transform_transpose = row_by_name(transform_rows, "structured-line-transpose-depth2")
    transform_token = row_by_name(transform_rows, "structured-static-token-depth2")
    structured = row_by_name(result_rows, "streaming-structured-json-control")
    kolyma = row_by_name(result_rows, "kolyma-pdf-streaming-control")
    structured_sweeps = structured_control_rows(sweep_rows)
    best_structured_sweep = min(
        structured_sweeps,
        key=lambda row: row["delta_bytes"],
        default=None,
    )
    best_corpus_matrix = min(
        corpus_rows,
        key=lambda row: (row["delta_pct"], row["delta_bytes"]),
        default=None,
    )
    density_break_even = first_negative_density(sweep_rows)
    scale = largest_scale_row(sweep_rows)
    scale_mib = f"{scale['input_bytes'] / (1024 * 1024):.0f} MiB" if scale else "no"

    entries = [
        {
            "level": 0,
            "claim": "Codec safety and deterministic decode are guarded by required tests and generated roundtrips.",
            "status": "qualified",
            "evidence": "Release gates require cargo test --all-targets plus generated compress/decompress scripts.",
            "limitation": "This ledger records the gate requirement; command output is verified separately by the release gate run.",
        },
        {
            "level": 1,
            "claim": "Planted short-seed data can produce negative delta.",
            "status": status(planted_arity2["delta_bytes"] < 0),
            "evidence": f"{planted_arity2['name']}: {planted_arity2['input_bytes']} -> {planted_arity2['output_bytes']} bytes ({planted_arity2['delta_pct']:.2f}%).",
            "limitation": "Planted data proves mechanism, not natural corpus prevalence.",
        },
        {
            "level": 2,
            "claim": "Indexed lookup and streaming lookup agree on the planted span8 fixture.",
            "status": status(indexed_span8["output_bytes"] == streaming_span8["output_bytes"]),
            "evidence": f"indexed/span8 and streaming/span8 both output {indexed_span8['output_bytes']} bytes.",
            "limitation": "Small fixture parity; deeper seed spaces still need larger parity matrices.",
        },
        {
            "level": 3,
            "claim": "Record overhead threshold is visible and span length matters.",
            "status": status(span4["delta_bytes"] > 0 and span20["delta_bytes"] < 0),
            "evidence": f"span-4 bloats by {span4['delta_bytes']} bytes; span-20 saves {-span20['delta_bytes']} bytes.",
            "limitation": "Generated spans only; not a general compression promise.",
        },
        {
            "level": 4,
            "claim": "Planted-density break-even is measured.",
            "status": status(density_break_even is not None),
            "evidence": (
                f"First negative density row is {density_break_even['name']} at "
                f"{density_break_even['density_bytes']} planted bytes."
                if density_break_even
                else "No negative density row found."
            ),
            "limitation": "Break-even depends on record format, span length, and corpus construction.",
        },
        {
            "level": 5,
            "claim": "Recursive v2 can create a second-pass win, but does not show open-ended convergence.",
            "status": status(
                offset1_pass1["delta_bytes"] > 0
                and offset1_pass2["delta_bytes"] < 0
                and offset1_pass4["output_bytes"] == offset1_pass2["output_bytes"],
                caution=True,
            ),
            "evidence": (
                f"offset-1 pass1 {offset1_pass1['output_bytes']} bytes, "
                f"pass2 {offset1_pass2['output_bytes']} bytes, "
                f"pass4 {offset1_pass4['output_bytes']} bytes."
            ),
            "limitation": "Current positive recursive evidence is an offset/control fixture.",
        },
        {
            "level": 6,
            "claim": "Sub-block span-step search can recover offset generated spans in one pass.",
            "status": status(
                offset1_pass1["telemetry"]["selected_count"] == 0
                and all(
                    row["telemetry"]["selected_count"] > 0 and row["delta_bytes"] < 0
                    for row in offset_span_step_rows
                ),
                caution=True,
            ),
            "evidence": (
                f"offset-1 block-step selected {offset1_pass1['telemetry']['selected_count']} spans; "
                "span-step-1 offsets 1, 2, and 3 output "
                + ", ".join(
                    f"{row['output_bytes']} bytes with {row['telemetry']['selected_count']} spans"
                    for row in offset_span_step_rows
                )
                + "."
            ),
            "limitation": "Byte-step search expands the candidate grid and cost; it is alignment evidence, not a natural-corpus result.",
        },
        {
            "level": 7,
            "claim": "Seed depth 2 expands the searchable space and is measured separately from normal fast tests.",
            "status": status(
                seed2_depth1["telemetry"]["selected_count"] == 0
                and seed2_depth1["delta_bytes"] > 0
                and seed2_depth2["telemetry"]["selected_count"] > 0
                and seed2_depth2["delta_bytes"] < 0
                and structured_depth2["delta_bytes"] > 0,
                caution=True,
            ),
            "evidence": (
                f"two-byte planted fixture depth1 {seed2_depth1['output_bytes']} bytes with "
                f"{seed2_depth1['telemetry']['selected_count']} spans; depth2 "
                f"{seed2_depth2['output_bytes']} bytes with {seed2_depth2['telemetry']['selected_count']} spans; "
                f"structured depth2 {structured_depth2['delta_pct']:.2f}% delta."
            ),
            "limitation": "Depth 2 proves wider search can unlock controlled seeds, but current structured depth-2 control still does not shrink.",
        },
        {
            "level": 8,
            "claim": "Seed depth 3 is measured as an opt-in deep-search artifact.",
            "status": status(
                seed3_depth2["telemetry"]["selected_count"] == 0
                and seed3_depth2["delta_bytes"] > 0
                and seed3_depth3["telemetry"]["selected_count"] > 0
                and seed3_depth3["delta_bytes"] < 0
                and structured_depth3["delta_bytes"] > 0,
                caution=True,
            ),
            "evidence": (
                f"three-byte planted fixture depth2 {seed3_depth2['output_bytes']} bytes with "
                f"{seed3_depth2['telemetry']['selected_count']} spans; depth3 "
                f"{seed3_depth3['output_bytes']} bytes with {seed3_depth3['telemetry']['selected_count']} spans; "
                f"structured depth3 {structured_depth3['delta_pct']:.2f}% delta."
            ),
            "limitation": "Depth 3 is only proven on tiny opt-in controls; current structured depth-3 control still does not shrink.",
        },
        {
            "level": 9,
            "claim": "Cheap generic reversible transforms do not create structured JSON seed-span wins yet.",
            "status": status(
                all(
                    row["telemetry"]["selected_count"] == 0 and row["effective_delta_bytes"] > 0
                    for row in (
                        transform_identity,
                        transform_xor,
                        transform_sub,
                        transform_transpose,
                    )
                ),
                caution=True,
            ),
            "evidence": (
                f"identity {transform_identity['effective_delta_pct']:.2f}%, "
                f"xor-prev {transform_xor['effective_delta_pct']:.2f}%, "
                f"sub-prev {transform_sub['effective_delta_pct']:.2f}%, "
                f"line-transpose {transform_transpose['effective_delta_pct']:.2f}%; "
                "all selected 0 spans."
            ),
            "limitation": "This covers only cheap byte-layout transforms on one generated JSON corpus.",
        },
        {
            "level": 10,
            "claim": "A static domain-token preconditioner can reduce effective JSON bytes, but it is transform gain rather than seed-span gain.",
            "status": status(
                transform_token["effective_delta_bytes"] < 0
                and transform_token["telemetry"]["selected_count"] == 0,
                caution=True,
            ),
            "evidence": (
                f"static-token effective delta {transform_token['effective_delta_pct']:.2f}% "
                f"with {transform_token['telemetry']['selected_count']} selected spans."
            ),
            "limitation": "This is a domain dictionary experiment, not current `.tlmr` format support and not evidence of natural seed matches.",
        },
        {
            "level": 11,
            "claim": "Structured and binary controls do not yet show natural-corpus wins.",
            "status": status(
                structured["delta_bytes"] > 0
                and kolyma["delta_bytes"] > 0
                and best_structured_sweep is not None
                and best_structured_sweep["delta_bytes"] > 0
                and best_corpus_matrix is not None
                and best_corpus_matrix["delta_bytes"] > 0
                and structured_depth3["delta_bytes"] > 0,
                caution=True,
            ),
            "evidence": (
                f"structured JSON {structured['delta_pct']:.2f}% delta; "
                f"best structured-search sweep "
                f"{best_structured_sweep['name'] if best_structured_sweep else 'missing'} "
                f"{best_structured_sweep['delta_pct']:.2f}% delta; "
                f"best broad corpus-matrix row "
                f"{best_corpus_matrix['name'] if best_corpus_matrix else 'missing'} "
                f"{best_corpus_matrix['delta_pct']:.2f}% delta with "
                f"{best_corpus_matrix['telemetry']['selected_count'] if best_corpus_matrix else 0} selected spans; "
                f"structured depth3 {structured_depth3['delta_pct']:.2f}% delta; "
                f"kolyma PDF {kolyma['delta_pct']:.4f}% delta."
                if best_structured_sweep and best_corpus_matrix
                else f"structured JSON {structured['delta_pct']:.2f}% delta; kolyma PDF {kolyma['delta_pct']:.4f}% delta."
            ),
            "limitation": "This is honest negative evidence across current seed-depth-1, seed-depth-2, broad generated corpus-matrix, and tiny opt-in seed-depth-3 structured searches; transformed wins remain open.",
        },
        {
            "level": 12,
            "claim": "Composing context/residual transforms with periodic masks does not yet cross the fifth-byte gate.",
            "status": "open",
            "evidence": (
                f"{composed_probe['candidate_count']} composed candidates selected "
                f"{composed_probe['selected_transform_count']} discovery leads; "
                f"held-out prefix>=5 uplift {composed_summary['heldout_prefix5_win_corpora']} corpora; "
                f"held-out exact hits {composed_summary['heldout_exact_hits']}."
            ),
            "limitation": "Composition is a bounded research probe, not current `.tlmr` format support.",
        },
        {
            "level": 13,
            "claim": "Depth-3 search can move a few held-out prefix frontiers, but exact hits are still absent.",
            "status": status(
                depth3_prefix_summary["heldout_rows_with_prefix5_uplift"] > 0,
                caution=True,
            ),
            "evidence": (
                f"{depth3_prefix_summary['enumerated_seed_count']} depth-3 seeds enumerated; "
                f"{depth3_prefix_summary['heldout_rows_with_prefix5_uplift']} held-out rows gained "
                f"prefix>=5 movement; exact hits {depth3_prefix_summary['heldout_exact_hits']}."
            ),
            "limitation": "Prefix movement is a search-frontier signal, not a `.tlmr` compression win until exact seed-span records beat overhead.",
        },
        {
            "level": 14,
            "claim": "The bounded depth-3 compression follow-up did not convert prefix movement into selected spans.",
            "status": "open",
            "evidence": (
                f"{depth3_followup_summary['promoted_prefix_rows']} physical input / "
                f"{depth3_followup_summary['logical_alias_rows']} logical aliases; "
                f"selected spans {depth3_followup_summary['total_depth3_selected_spans']}; "
                f"negative-delta rows {depth3_followup_summary['depth3_rows_with_negative_delta']}."
            ),
            "limitation": "This is a useful null on the current promoted rows, not a proof that all depth-3 search is barren.",
        },
        {
            "level": 15,
            "claim": "Context-conditioned fifth-byte steering does not yet beat the held-out promotion gate.",
            "status": "open",
            "evidence": (
                f"{contextual_summary['candidate_count']} contextual masks checked; "
                f"held-out prefix>=5 win rows {contextual_summary['cross_prefix5_win_rows']}; "
                f"exact-hit rows {contextual_summary['cross_exact_hit_rows']}; "
                f"null prefix>=5 win rows {contextual_summary['null_cross_prefix5_win_rows']}."
            ),
            "limitation": "This rejects one plausible steering family; it does not rule out richer reversible transforms.",
        },
        {
            "level": 16,
            "claim": "Bounded structural reversible transforms do not yet create held-out longer-prefix or exact seed-span wins.",
            "status": "open",
            "evidence": (
                f"{structural_summary['candidate_count']} structural candidates over "
                f"{structural_summary['validation_rows']} validation rows; held-out prefix>=5 win corpora "
                f"{structural_summary['heldout_prefix5_win_corpora']}; held-out exact hits "
                f"{structural_summary['heldout_exact_hits']}; shadow prefix>=5 win corpora "
                f"{structural_summary['shadow_prefix5_win_corpora']}; binary exact hits "
                f"{structural_summary['binary_exact_hits']}."
            ),
            "limitation": "This rejects the current bounded structural families, not all possible reversible preconditioners.",
        },
        {
            "level": 17,
            "claim": "Affine byte remaps can move held-out prefix-4 proximity broadly, but still do not cross the fifth-byte gate.",
            "status": "open",
            "evidence": (
                f"{affine_summary['searched_candidate_count']} affine candidates searched; "
                f"{affine_summary['heldout_prefix4_win_corpora']} held-out corpora had prefix>=4 uplift; "
                f"held-out prefix>=5 win corpora {affine_summary['heldout_prefix5_win_corpora']}; "
                f"held-out exact hits {affine_summary['heldout_exact_hits']}."
            ),
            "limitation": "Prefix-4 uplift is a steering signal, not a seed-span compression win.",
        },
        {
            "level": 18,
            "claim": "Residual sidecar steering can force some exact spans, but current span-8 economics still bloat.",
            "status": "open",
            "evidence": (
                f"{residual_summary['heldout_forced_rows']} held-out rows had forced exact spans; "
                f"{residual_summary['heldout_seed_contribution_positive_rows']} had positive seed contribution before sidecar cost; "
                f"held-out positive net-delta rows {residual_summary['heldout_positive_rows']}; "
                f"best held-out net delta {residual_summary['best_heldout_net_delta_bytes']} bytes."
            ),
            "limitation": "This measures span-8 suffix-residual sidecars only; it is not format support or a proof about all longer-span sidecars.",
        },
        {
            "level": 19,
            "claim": "Longer-span residual sidecars need stronger evidence than the current prefix frontier provides.",
            "status": "open",
            "evidence": (
                f"{sidecar_break_even_summary['row_count']} break-even rows; "
                f"minimum raw-suffix strict prefix "
                f"{sidecar_break_even_summary['minimum_raw_suffix_negative_prefix_len']}; "
                f"max observed held-out forced prefix "
                f"{sidecar_break_even_summary['max_observed_heldout_forced_prefix_len']}; "
                f"raw-suffix model-viable rows at observed prefix "
                f"{sidecar_break_even_summary['raw_suffix_viable_at_observed_prefix_rows']}; "
                f"sublinear model-viable rows at observed prefix "
                f"{sidecar_break_even_summary['sublinear_model_viable_at_observed_prefix_rows']}; "
                f"promoted rows {sidecar_break_even_summary['promoted_rows']}."
            ),
            "limitation": "This is math-only gating; sublinear residual models need measured, invertible payload compression before format or engine work.",
        },
        {
            "level": 20,
            "claim": "Measured residual payload coders expose one narrow held-out sidecar signal, but not general format support.",
            "status": "qualified",
            "evidence": (
                f"{residual_payload_summary['heldout_payload_rows']} held-out payload rows; "
                f"measured held-out negative rows "
                f"{residual_payload_summary['measured_heldout_negative_rows']}; "
                f"best measured case "
                f"{residual_payload_summary['best_measured_heldout_negative_case']}; "
                f"zlib best held-out net delta "
                f"{residual_payload_summary['best_heldout_net_delta_by_policy']['zlib_level9']} bytes; "
                f"quarter-rate held-out negative rows "
                f"{residual_payload_summary['heldout_negative_rows_by_policy']['quarter_rate_model']}."
            ),
            "limitation": "This promotes a narrow experimental payload descriptor follow-up; it is not `.tlmr` sidecar format support.",
        },
        {
            "level": 21,
            "claim": "The first experimental sidecar descriptor decodes, rejects corruption, and still bloats after full-stream overhead.",
            "status": "qualified",
            "evidence": (
                f"{experimental_sidecar_summary['prototype_rows']} descriptor rows; "
                f"decode verified rows {experimental_sidecar_summary['decode_verified_rows']}; "
                f"full-stream negative rows {experimental_sidecar_summary['full_stream_negative_rows']}; "
                f"best full-stream delta "
                f"{experimental_sidecar_summary['best_full_stream_delta_bytes']} bytes; "
                f"best local selected delta "
                f"{experimental_sidecar_summary['best_local_selected_delta_bytes']} bytes."
            ),
            "limitation": "This falsifies immediate sidecar format promotion for the current row; lower-overhead records or larger bundles remain open.",
        },
        {
            "level": 22,
            "claim": "Packed sidecar offset/seed-index budgets can make the promoted row full-stream negative on paper.",
            "status": "qualified",
            "evidence": (
                f"{sidecar_record_summary['layout_rows']} layout rows; "
                f"negative layout rows {sidecar_record_summary['negative_layout_rows']}; "
                f"best safe layout {sidecar_record_summary['best_safe_layout']} at "
                f"{sidecar_record_summary['best_safe_delta_bytes']} bytes; "
                f"best layout {sidecar_record_summary['best_layout']} at "
                f"{sidecar_record_summary['best_delta_bytes']} bytes."
            ),
            "limitation": "This is a budget model only; it needs an exact packed-table decoder before it becomes evidence for format work.",
        },
        {
            "level": 23,
            "claim": "A packed offset/seed-index sidecar descriptor can decode and produce full-stream negative delta on one promoted held-out row.",
            "status": "qualified",
            "evidence": (
                f"{packed_sidecar_summary['prototype_rows']} packed descriptor rows; "
                f"decode verified rows {packed_sidecar_summary['decode_verified_rows']}; "
                f"full-stream negative rows {packed_sidecar_summary['full_stream_negative_rows']}; "
                f"best coder {packed_sidecar_summary['best_coder']} at "
                f"{packed_sidecar_summary['best_delta_bytes']} bytes."
            ),
            "limitation": "This is one promoted held-out row and research-only descriptor evidence, not a general natural-corpus or `.tlmr` format claim.",
        },
        {
            "level": 24,
            "claim": "Packed sidecar controls show the descriptor signal is real but still narrow.",
            "status": "qualified",
            "evidence": (
                f"{packed_controls_summary['control_rows']} control rows; "
                f"encoded rows {packed_controls_summary['encoded_rows']}; "
                f"unique negative cases {packed_controls_summary['unique_negative_cases']}; "
                f"ordinary held-out negative cases "
                f"{packed_controls_summary['ordinary_heldout_negative_cases']}; "
                f"best delta {packed_controls_summary['best_delta_bytes']} bytes."
            ),
            "limitation": "Current packed descriptor assumptions skip most selected rows and have only one ordinary held-out negative case.",
        },
        {
            "level": 25,
            "claim": "Generalized packed offset and seed modes improve descriptor economics, but do not yet broaden ordinary held-out wins.",
            "status": "qualified",
            "evidence": (
                f"{generalized_packed_summary['row_count']} generalized rows; "
                f"encoded rows {generalized_packed_summary['encoded_rows']}; "
                f"unique encoded source rows "
                f"{generalized_packed_summary['unique_encoded_source_rows']}; "
                f"unique negative cases {generalized_packed_summary['unique_negative_cases']}; "
                f"ordinary held-out negative cases "
                f"{generalized_packed_summary['ordinary_heldout_negative_cases']}; "
                f"best-supported table bytes "
                f"{generalized_packed_summary['best_of_supported_modes_total_table_bytes']} "
                f"versus baseline "
                f"{generalized_packed_summary['baseline_delta_u16_global_u16_total_table_bytes']}."
            ),
            "limitation": "This improves descriptor applicability, not proof of broad natural-corpus viability.",
        },
        {
            "level": 26,
            "claim": "Frozen packed sidecar replication did not reproduce full-stream negative rows on unrelated held-out corpora.",
            "status": "open",
            "evidence": (
                f"{packed_replication_summary['corpus_count']} predeclared corpora; "
                f"{packed_replication_summary['source_case_count']} source cases; "
                f"{packed_replication_summary['descriptor_row_count']} descriptor rows; "
                f"decode verified rows {packed_replication_summary['decode_verified_rows']}; "
                f"full-stream negative rows "
                f"{packed_replication_summary['full_stream_negative_rows']}; "
                f"ordinary held-out negative groups "
                f"{packed_replication_summary['ordinary_heldout_negative_groups']}."
            ),
            "limitation": "This is falsification evidence for the current descriptor and transform set; it does not rule out future match-discovery or deeper-search approaches.",
        },
        {
            "level": 27,
            "claim": "Pre-sidecar match discovery did not find exact seed-span matches across the current validation and replication corpus matrix.",
            "status": "open",
            "evidence": (
                f"{match_discovery_summary['corpus_count']} corpora; "
                f"{match_discovery_summary['row_count']} rows; "
                f"{match_discovery_summary['target_span_count']} target spans scanned; "
                f"rows with prefix>=5 {match_discovery_summary['rows_with_prefix_ge_5']}; "
                f"rows with exact hits {match_discovery_summary['rows_with_exact_hits']}; "
                f"selected spans {match_discovery_summary['total_selected_spans']}."
            ),
            "limitation": "This covers seed depth 2, arity 1..5, and the current search policies; it does not rule out deeper seed windows, new corpora, or new reversible transforms.",
        },
        {
            "level": 28,
            "claim": "Alignment and arity discovery found only unprofitable short-span exact hits.",
            "status": "open",
            "evidence": (
                f"{alignment_summary['target_span_count']} target spans; "
                f"{alignment_summary['config_count']} supported configs; "
                f"skipped configs {alignment_summary['skipped_config_count']}; "
                f"rows with prefix>=5 {alignment_summary['rows_with_prefix_ge_5']}; "
                f"exact hits {alignment_summary['total_exact_hits']}; "
                f"positive exact hits {alignment_summary['total_positive_exact_hits']}; "
                f"selected spans {alignment_summary['total_selected_spans']}."
            ),
            "limitation": "This tests block size, step policy, phase, and arity at seed depth 2; it does not rule out deeper seed spaces or new reversible transforms.",
        },
        {
            "level": 29,
            "claim": "Frozen reversible transforms did not create selected exact seed-span rows.",
            "status": "open",
            "evidence": (
                f"{transformed_match_summary['target_span_count']} transformed target spans; "
                f"{transformed_match_summary['transform_count']} transforms; "
                f"rows with prefix>=5 {transformed_match_summary['rows_with_prefix_ge_5']}; "
                f"exact hits {transformed_match_summary['total_exact_hits']}; "
                f"selected spans {transformed_match_summary['total_selected_spans']}; "
                f"metadata-profitable rows {transformed_match_summary['metadata_profitable_rows']}."
            ),
            "limitation": "This covers the frozen transform-validation matrix at seed depth 2 and span length 8; it does not rule out new transform families or deeper seed spaces.",
        },
        {
            "level": 30,
            "claim": "Selected affine, periodic, and composed leads did not create exact seed-span rows.",
            "status": "open",
            "evidence": (
                f"{lead_exact_summary['target_span_count']} selected-lead target spans; "
                f"{lead_exact_summary['lead_count']} leads; "
                f"rows with prefix>=5 {lead_exact_summary['rows_with_prefix_ge_5']}; "
                f"exact hits {lead_exact_summary['total_exact_hits']}; "
                f"selected spans {lead_exact_summary['total_selected_spans']}; "
                f"metadata-profitable rows {lead_exact_summary['metadata_profitable_rows']}."
            ),
            "limitation": "This follows only already-selected affine, periodic, and composed leads; it is a falsifier for broadening current prefix-4 leads, not for all possible transforms.",
        },
        {
            "level": 31,
            "claim": f"Current CPU streaming scales to the generated {scale_mib} planted-density sweep.",
            "status": status(scale is not None and scale["delta_bytes"] < 0, caution=True),
            "evidence": (
                f"{scale['name']}: {scale['input_bytes']} -> {scale['output_bytes']} bytes, "
                f"{scale['compress_ms']} ms, peak {scale['peak_memory_mib']} MiB."
                if scale
                else "No scale row found."
            ),
            "limitation": f"{scale_mib} is useful local evidence, not production-scale archival proof.",
        },
        {
            "level": 32,
            "claim": "The generated scale-performance report makes bounded planted-density scaling interpretable but memory-heavy.",
            "status": "qualified"
            if scale_performance_summary["promotion_met"]
            else "open",
            "evidence": (
                f"{scale_performance_summary['row_count']} memory-scaling rows; "
                f"largest scale {scale_performance_summary['largest_scale_mib']} MiB; "
                f"largest peak memory "
                f"{scale_performance_summary['largest_peak_memory_mib']} MiB; "
                f"largest peak/estimated-table ratio "
                f"{scale_performance_summary['largest_peak_to_estimated_table_ratio']}; "
                f"plateau ratio spread "
                f"{scale_performance_summary['plateau_ratio_spread_pct']}%; "
                f"next double peak estimate "
                f"{scale_performance_summary['next_double_peak_memory_mib_at_current_ratio']} MiB."
            ),
            "limitation": "This is planted-density scale telemetry only; it does not prove natural-corpus compression or production memory behavior.",
        },
        {
            "level": 32,
            "claim": "The Tauri evidence ledger panel has static UI/bridge workflow coverage.",
            "status": "qualified" if ui_workflow_summary["promotion_met"] else "open",
            "evidence": (
                f"UI evidence keys {ui_workflow_summary['ui_evidence_key_count']}; "
                f"Tauri evidence fields "
                f"{ui_workflow_summary['tauri_evidence_field_count']}; "
                f"required cards {ui_workflow_summary['required_card_count']}; "
                f"missing Tauri fields "
                f"{len(ui_workflow_summary['missing_tauri_fields'])}; "
                f"missing mock fields "
                f"{len(ui_workflow_summary['missing_mock_fields'])}; "
                f"claim level {ui_workflow_summary['claim_level']}."
            ),
            "limitation": "This is static schema and artifact wiring coverage; it is not a full desktop browser smoke run.",
        },
        {
            "level": 33,
            "claim": "Selected-lead depth-3 compression follow-up stayed null after prefix movement.",
            "status": "open",
            "evidence": (
                f"Lead depth-3 prefix probe enumerated "
                f"{lead_depth3_prefix_summary['enumerated_seed_count']} seeds; "
                f"{lead_depth3_prefix_summary['rows_with_depth3_prefix5_uplift']} rows gained "
                f"prefix>=5 movement, exact hits "
                f"{lead_depth3_prefix_summary['total_depth3_exact_hits']}. "
                f"The follow-up ran {lead_depth3_followup_summary['promoted_prefix_rows']} physical input / "
                f"{lead_depth3_followup_summary['logical_alias_rows']} aliases with "
                f"{lead_depth3_followup_summary['total_depth3_selected_spans']} selected spans."
            ),
            "limitation": "Selected-lead prefix movement is still not a compression win without exact records selected by the compressor.",
        },
        {
            "level": 34,
            "claim": "Depth-3 frontier exact discovery found prefix movement only, not exact seed-span records.",
            "status": "open",
            "evidence": (
                f"{depth3_frontier_summary['frontier_rows']} frontier rows over "
                f"{depth3_frontier_summary['physical_payload_count']} physical payloads enumerated "
                f"{depth3_frontier_summary['enumerated_seed_count']} seeds; "
                f"prefix>=5 uplift rows {depth3_frontier_summary['rows_with_depth3_prefix5_uplift']}, "
                f"exact hits {depth3_frontier_summary['total_exact_hits']}, "
                f"selected spans {depth3_frontier_summary['total_selected_spans']}."
            ),
            "limitation": "This is the current gate against broad depth-3/depth-4 work; it can be reopened only by stronger exact-hit evidence.",
        },
        {
            "level": 34,
            "claim": "Depth-4 search is sharded and explicitly gated rather than a default next step.",
            "status": "open",
            "evidence": (
                f"Depth-4 plan status {depth4_gate['recommended_status']}; "
                f"estimated incremental full depth-4 time "
                f"{depth4_estimates['estimated_incremental_depth4_hours']} hours; "
                f"exact-8 probability on the current frontier "
                f"{depth4_estimates['exact8_probability_at_least_one']:.6g}."
            ),
            "limitation": "The plan makes depth-4 reproducible and sharded, but current evidence does not justify running all shards.",
        },
        {
            "level": 35,
            "claim": "Depth-4 pilot shards are bounded evidence gates, not production compression claims.",
            "status": "open",
            "evidence": (
                f"{depth4_pilot_summary['pilot_shard_count']} pilot shard enumerated "
                f"{depth4_pilot_summary['enumerated_seed_count']} four-byte seeds over "
                f"{depth4_pilot_summary['target_span_count']} frontier target spans; "
                f"prefix>=5 rows {depth4_pilot_summary['rows_with_depth4_prefix5']}; "
                f"prefix>=6 rows {depth4_pilot_summary['rows_with_depth4_prefix6']}; "
                f"exact hits {depth4_pilot_summary['total_exact_hits']}; "
                f"selected spans {depth4_pilot_summary['total_selected_spans']}."
            ),
            "limitation": "One shard is useful null evidence only; the remaining shards stay gated until stronger frontier evidence appears.",
        },
        {
            "level": 36,
            "claim": "The generated search-frontier gate blocks broad raw depth search from the current prefix-only frontier.",
            "status": "open",
            "evidence": (
                f"Gate status {search_gate_summary['recommended_status']}; "
                f"best non-planted forecast "
                f"{search_gate_summary['best_non_planted_gib_for_one_expected_hit']} GiB per expected exact hit; "
                f"depth-4 exact-8 probability "
                f"{search_gate_summary['depth4_exact8_probability']:.6g}; "
                f"selected span total {search_gate_summary['selected_span_total']}; "
                f"blocking gates {len(search_gate_summary['blocking_gates'])} of "
                f"{search_gate_summary['gate_count']}."
            ),
            "limitation": "This is a decision artifact assembled from current evidence, not a mathematical impossibility proof or a compression result.",
        },
        {
            "level": 37,
            "claim": "The generated mechanism-experiment ranking makes seed-table preset probing the next non-depth experiment.",
            "status": "open",
            "evidence": (
                f"Top lane {mechanism_ranking_summary['top_lane_id']}; "
                f"top next artifact {mechanism_ranking_summary['top_next_artifact']}; "
                f"ready lanes {mechanism_ranking_summary['ready_count']}; "
                f"gated lanes {mechanism_ranking_summary['gated_count']}; "
                f"blocked lanes {mechanism_ranking_summary['blocked_by_evidence_count']}; "
                f"selected spans {mechanism_ranking_summary['selected_span_total']}."
            ),
            "limitation": "This is generated evidence triage, not natural-corpus compression proof or format support.",
        },
        {
            "level": 38,
            "claim": "The generated long-span bundle gate blocks broad long-span sweeps from the current evidence base.",
            "status": "qualified" if long_span_gate_summary["promotion_met"] else "blocked-by-evidence",
            "evidence": (
                f"Gates met {long_span_gate_summary['gate_met_count']} of "
                f"{long_span_gate_summary['gate_count']}; "
                f"recommendation {long_span_gate_summary['recommendation']}; "
                f"best forecast "
                f"{long_span_gate_summary['best_non_planted_gib_for_one_expected_hit']} GiB; "
                f"selected spans {long_span_gate_summary['selected_span_total']}; "
                f"raw-suffix required prefix "
                f"{long_span_gate_summary['minimum_raw_suffix_negative_prefix_len']}; "
                f"max observed prefix "
                f"{long_span_gate_summary['max_observed_heldout_forced_prefix_len']}; "
                f"claim level {long_span_gate_summary['claim_level']}."
            ),
            "limitation": "This is a no-run gate assembled from current evidence; it should be regenerated if any prerequisite artifact changes.",
        },
        {
            "level": 38,
            "claim": "The generated seed-table preset probe did not yet promote a public Lotus preset.",
            "status": "open",
            "evidence": (
                f"Canonical selected spans {seed_table_summary['canonical_selected_spans']}; "
                f"ordinary held-out negative groups "
                f"{seed_table_summary['canonical_ordinary_heldout_negative_groups']}; "
                f"control negative groups {seed_table_summary['canonical_control_negative_groups']}; "
                f"SHA-256 baseline selected spans {seed_table_summary['sha256_selected_spans']}; "
                f"promotion met {seed_table_summary['promotion_met']}."
            ),
            "limitation": "This is a research-only seed-table/Lotus preset probe, not `.tlmr` format support or natural-corpus proof.",
        },
        {
            "level": 39,
            "claim": "The generated exact short-hit bundle economics artifact does not yet promote span-3 hit bundling.",
            "status": "open",
            "evidence": (
                f"Reconstructed exact hits {exact_short_summary['reconstructed_exact_hits']}; "
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
            "limitation": "This is an accounting artifact over frozen verified short hits, not new search, `.tlmr` support, or broad natural-corpus proof.",
        },
        {
            "level": 40,
            "claim": "The generated whole-stream residual vector probe closes the current residual-sidecar path as a broad compression claim.",
            "status": "open",
            "evidence": (
                f"Rows {whole_stream_summary['row_count']}; honest encoded rows "
                f"{whole_stream_summary['honest_encoded_rows']}; exact decode rows "
                f"{whole_stream_summary['decode_verified_rows']}; honest full-stream "
                f"negative rows {whole_stream_summary['honest_full_stream_negative_rows']}; "
                f"ordinary held-out negative groups "
                f"{whole_stream_summary['ordinary_heldout_negative_groups']}; "
                f"control negative groups {whole_stream_summary['control_negative_groups']}; "
                f"measured residual coding near entropy bound "
                f"{whole_stream_summary['measured_residual_coding_near_entropy_bound']}; "
                f"promotion met {whole_stream_summary['promotion_met']}."
            ),
            "limitation": "This is a whole-stream residual-vector falsification artifact, not `.tlmr` format support, compressed literal-stream evidence, or a new seed search.",
        },
        {
            "level": 41,
            "claim": "The generated expander salt ensemble did not beat the matched random-trial baseline.",
            "status": "open",
            "evidence": (
                f"Predeclared salts {expander_salt_summary['predeclared_salt_count']}; "
                f"salted exact hits {expander_salt_summary['salted_exact_hits']}; "
                f"salted expected exact hits "
                f"{expander_salt_summary['salted_expected_exact_hits']:.6g}; "
                f"random-trial multiplier exceeded "
                f"{expander_salt_summary['random_trial_multiplier_exceeded']}; "
                f"salted selected-span rows "
                f"{expander_salt_summary['salted_selected_span_rows']}; "
                f"full-stream negative rows "
                f"{expander_salt_summary['full_stream_negative_rows']}; "
                f"ordinary negative groups "
                f"{expander_salt_summary['ordinary_heldout_negative_groups']}; "
                f"control negative groups {expander_salt_summary['control_negative_groups']}; "
                f"promotion met {expander_salt_summary['promotion_met']}."
            ),
            "limitation": "This is a research-only predeclared salt/preset ensemble probe, not `.tlmr` format support or evidence for per-file trained expanders.",
        },
        {
            "level": 42,
            "claim": "The generated schema-native public dictionary probe found a narrow public-preset positive result.",
            "status": "qualified",
            "evidence": (
                f"Public entries {schema_native_summary['public_entry_count']}; "
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
            "limitation": "This is public dictionary-preset evidence on schema-shaped synthetic corpora, not current `.tlmr` format support or proof that SHA-256 seed expansion discovered natural structure.",
        },
        {
            "level": 43,
            "claim": "The schema-native public dictionary replication blocked promotion on paired shadow controls.",
            "status": "blocked-by-evidence"
            if not schema_replication_summary["promotion_met"]
            else "qualified",
            "evidence": (
                f"Replication corpora {schema_replication_summary['corpus_count']}; "
                f"standards selected spans "
                f"{schema_replication_summary['standards_selected_spans']}; "
                f"ordinary negative groups "
                f"{schema_replication_summary['standards_ordinary_negative_groups']}; "
                f"standards control negative groups "
                f"{schema_replication_summary['standards_control_negative_groups']}; "
                f"generic ordinary negative groups "
                f"{schema_replication_summary['generic_ordinary_negative_groups']}; "
                f"wrong-family ordinary negative groups "
                f"{schema_replication_summary['wrong_family_ordinary_negative_groups']}; "
                f"claim level {schema_replication_summary['claim_level']}; "
                f"promotion met {schema_replication_summary['promotion_met']}."
            ),
            "limitation": "This hardening artifact downgrades the public dictionary signal until paired shadow controls and externally sourced corpora separate cleanly.",
        },
        {
            "level": 44,
            "claim": "The generated superposition telemetry proves selector auditability on deterministic overlap fixtures.",
            "status": "qualified"
            if superposition_summary["promotion_met"]
            else "open",
            "evidence": (
                f"Fixtures {superposition_summary['fixture_count']}; "
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
            "limitation": "This is selector correctness and telemetry evidence only; it does not create new seed hits or prove natural-corpus compression.",
        },
        {
            "level": 45,
            "claim": "Recursive v2 later-layer gains remain unpromoted outside planted offset controls.",
            "status": "qualified"
            if recursive_structured_summary["promotion_met"]
            else "blocked-by-evidence",
            "evidence": (
                f"Fixtures {recursive_structured_summary['fixture_count']}; "
                f"ordinary structured fixtures "
                f"{recursive_structured_summary['ordinary_fixture_count']}; "
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
            "limitation": "This is real CLI v2 recursive evidence with metadata charged; it blocks broad recursive claims until at least two ordinary non-offset families improve on later layers.",
        },
        {
            "level": 43,
            "claim": "Corpus generalization controls did not produce exact seed-span rows.",
            "status": "open",
            "evidence": (
                f"{corpus_generalization_summary['control_count']} controls scanned "
                f"{corpus_generalization_summary['target_span_count']} spans; "
                f"prefix>=5 rows {corpus_generalization_summary['rows_with_prefix_ge_5']}; "
                f"exact hits {corpus_generalization_summary['total_exact_hits']}; "
                f"selected spans {corpus_generalization_summary['total_selected_spans']}."
            ),
            "limitation": "This reduces literal-token overfit risk but does not replace broader held-out natural corpus validation.",
        },
        {
            "level": 44,
            "claim": "Byte-permutation seed-manifold alignment did not yet produce exact seed-span rows.",
            "status": "open",
            "evidence": (
                f"{byte_permutation_summary['transform_count']} transforms over "
                f"{byte_permutation_summary['row_count']} rows scanned "
                f"{byte_permutation_summary['target_span_count']} spans; "
                f"prefix>=5 rows {byte_permutation_summary['rows_with_prefix_ge_5']}; "
                f"exact hits {byte_permutation_summary['total_exact_hits']}; "
                f"selected spans {byte_permutation_summary['total_selected_spans']}; "
                f"rows negative after metadata {byte_permutation_summary['rows_negative_after_metadata']}."
            ),
            "limitation": "This covers rank-based global and phase-local byte permutations only; grammar-channel transforms are tested separately.",
        },
        {
            "level": 45,
            "claim": "BWT/MTF classic preconditioners did not yet produce exact seed-span rows.",
            "status": "open",
            "evidence": (
                f"{bwt_mtf_summary['transform_count']} BWT/MTF/RLE transforms over "
                f"{bwt_mtf_summary['row_count']} rows scanned "
                f"{bwt_mtf_summary['target_span_count']} spans; "
                f"prefix>=5 rows {bwt_mtf_summary['rows_with_prefix_ge_5']}; "
                f"exact hits {bwt_mtf_summary['total_exact_hits']}; "
                f"selected spans {bwt_mtf_summary['total_selected_spans']}; "
                f"rows negative after metadata {bwt_mtf_summary['rows_negative_after_metadata']}; "
                f"shorter transformed payload rows {bwt_mtf_summary['rows_with_shorter_transformed_payload']}."
            ),
            "limitation": "This covers bounded block BWT, MTF, and zero-run packing only; transform-only shortening is not counted as Lotus evidence.",
        },
        {
            "level": 46,
            "claim": "Grammar/channel discovery did not yet produce exact seed-span rows.",
            "status": "open",
            "evidence": (
                f"{grammar_channel_summary['channel_count']} channels over "
                f"{grammar_channel_summary['row_count']} rows scanned "
                f"{grammar_channel_summary['target_span_count']} spans; "
                f"prefix>=5 rows {grammar_channel_summary['rows_with_prefix_ge_5']}; "
                f"exact hits {grammar_channel_summary['total_exact_hits']}; "
                f"selected spans {grammar_channel_summary['total_selected_spans']}; "
                f"rows negative after metadata {grammar_channel_summary['rows_negative_after_metadata']}."
            ),
            "limitation": "This covers first-pass grammar channels with charged literal sidecars only; richer parsers may need a new artifact.",
        },
        {
            "level": 47,
            "claim": "Numeric value-channel discovery did not yet produce exact seed-span rows.",
            "status": "open",
            "evidence": (
                f"{numeric_value_channel_summary['channel_count']} numeric value channels over "
                f"{numeric_value_channel_summary['row_count']} rows parsed "
                f"{numeric_value_channel_summary['parsed_value_count']} values and scanned "
                f"{numeric_value_channel_summary['target_span_count']} spans; "
                f"prefix>=5 rows {numeric_value_channel_summary['rows_with_prefix_ge_5']}; "
                f"exact hits {numeric_value_channel_summary['total_exact_hits']}; "
                f"selected spans {numeric_value_channel_summary['total_selected_spans']}; "
                f"rows negative after metadata {numeric_value_channel_summary['rows_negative_after_metadata']}."
            ),
            "limitation": "This covers bounded parsed numeric value streams with exact reconstruction metadata charged; timestamp/vector numeric channels remain future research.",
        },
        {
            "level": 48,
            "claim": "Held-out corpus expansion broadened deterministic corpus coverage but did not change the raw seed frontier.",
            "status": "qualified",
            "evidence": (
                f"{heldout_expansion_summary['corpus_count']} frozen replication corpora, "
                f"{heldout_expansion_summary['ordinary_corpus_count']} ordinary and "
                f"{heldout_expansion_summary['control_corpus_count']} controls, scanned "
                f"{heldout_expansion_summary['target_span_count']} raw spans; "
                f"missing from corpus matrix {heldout_expansion_summary['missing_corpus_matrix_count']}; "
                f"prefix>=5 rows {heldout_expansion_summary['rows_with_prefix_ge_5']}; "
                f"exact-hit rows {heldout_expansion_summary['rows_with_exact_hits']}; "
                f"selected-span rows {heldout_expansion_summary['rows_with_selected_spans']}."
            ),
            "limitation": "This is a separate frontier artifact; it intentionally does not stale the expensive transform-validation or corpus-matrix hash chain.",
        },
        {
            "level": 49,
            "claim": "Record/context-aware transforms did not yet produce exact seed-span rows.",
            "status": "open",
            "evidence": (
                f"{record_context_summary['transform_count']} transforms over "
                f"{record_context_summary['row_count']} rows scanned "
                f"{record_context_summary['target_span_count']} spans; "
                f"prefix>=5 rows {record_context_summary['rows_with_prefix_ge_5']}; "
                f"exact hits {record_context_summary['total_exact_hits']}; "
                f"selected spans {record_context_summary['total_selected_spans']}; "
                f"rows negative after metadata {record_context_summary['rows_negative_after_metadata']}."
            ),
            "limitation": "This covers the current line/field/fixed-width/delta descriptor families only, not every possible record-aware transform.",
        },
        {
            "level": 50,
            "claim": "Token/dictionary transforms did not yet produce exact seed-span rows.",
            "status": "open",
            "evidence": (
                f"{token_dictionary_summary['transform_count']} transforms over "
                f"{token_dictionary_summary['row_count']} rows scanned "
                f"{token_dictionary_summary['target_span_count']} spans; "
                f"prefix>=5 rows {token_dictionary_summary['rows_with_prefix_ge_5']}; "
                f"exact hits {token_dictionary_summary['total_exact_hits']}; "
                f"selected spans {token_dictionary_summary['total_selected_spans']}; "
                f"rows negative after metadata {token_dictionary_summary['rows_negative_after_metadata']}."
            ),
            "limitation": "This covers lexeme dictionary and token-order streams only; richer grammar coders remain open research.",
        },
    ]

    verdict = "research-viable, not production-proven"
    open_questions = [
        "Turn promising preconditioners into a versioned reversible format layer, or reject them as non-Telomere transform-only gains.",
        "Find repeatable natural or transformed structured-corpus seed-span wins beyond the current seed-depth-1, seed-depth-2, and opt-in seed-depth-3 controls.",
        "Find a transform family that survives held-out composition testing into prefix>=5 or exact seed-span hits.",
        "Design transform families beyond the current bounded structural permutations and residuals, or retire this lane if new families keep returning null.",
        "Find new independent match-discovery leads beyond the current depth-2 arity 1..5 validation and replication matrix.",
        "Use depth-3 frontier exact discovery as the gate before any broad depth-3 or opt-in depth-4 search.",
        "Use the depth-4 shard plan only for pilot shards until the promotion gate is met.",
        "Use the generated search-frontier gate as the go/no-go source before any broad raw depth or full depth-4 execution.",
        "Use the generated mechanism-experiment ranking to prioritize seed-table preset probing before raw-depth escalation or format promotion.",
        "Use the generated long-span bundle gate before running long-span sweeps or optimizing bundle packing.",
        "Use the generated seed-table preset probe as null evidence before spending further on public corpus-shaped Lotus presets.",
        "Use the generated exact short-hit bundle economics artifact as null evidence before spending further on span-3 hit bundling.",
        "Use the generated recursive structured fixtures as the gate before claiming recursive convergence beyond planted offset controls.",
        "Use the generated scale-performance report before extending planted-density runs beyond the current 16 MiB memory-heavy sweep.",
        "Keep the generated UI workflow smoke in lockstep with any Tauri evidence DTO or ledger-panel changes.",
        "Move beyond alignment/arity tuning only after a lane produces profitable exact hits or repeatable prefix>=5 movement.",
        "Do not promote the frozen transform-validation matrix without exact selected spans after transform metadata is charged.",
        "Stop broadening selected affine/periodic/composed prefix-4 leads unless a new lead crosses prefix>=5 or exact-hit thresholds.",
        "Find a new lead before spending on broad depth-3 sweeps; the bounded follow-up on current promoted rows found zero selected spans.",
        "Use the generated vocabulary-disjoint shadow corpora and binary TLV/varint controls before trusting literal-token-driven prefix wins.",
        "Treat the corpus generalization null as a reason to implement record-aware transforms before broadening expensive corpus discovery.",
        "Treat the BWT/MTF null as evidence that classic entropy preconditioners do not automatically create Lotus seed-span hits.",
        "Treat the grammar/channel null as a reason to design stronger parser-backed channels before increasing seed depth.",
        "Treat the numeric value-channel null as evidence against simple parsed-value streams before adding format support.",
        "Use the held-out corpus expansion as a promotion gate before mutating the expensive corpus matrix or transform-validation matrix.",
        "Treat the record/context transform null as a reason to find stronger record descriptors before spending on format support.",
        "Treat the token/dictionary transform null as evidence against simple lexeme dictionaries without stronger grammar models.",
        "Extend seed-depth-3 economics beyond tiny controls only after runtime and memory stay bounded.",
        "Replace research-only GPU fallback with real OpenCL only if it beats CPU streaming under parity tests.",
        f"Push generated scale sweeps past {scale_mib} after memory telemetry and chunking are acceptable.",
    ]

    for level, entry in enumerate(entries):
        entry["level"] = level

    return {
        "generated_by": "scripts/generate_viability.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "artifact_hashes": artifact_hashes(),
        "verdict": verdict,
        "entries": entries,
        "open_questions": open_questions,
    }


def write_viability(payload: dict[str, Any]) -> None:
    VIABILITY_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Telomere Viability Ledger",
        "",
        "Generated by `scripts/generate_viability.py` from checked-in result artifacts.",
        "This document separates proved mechanisms from open research claims.",
        "",
        f"Verdict: **{payload['verdict']}**.",
        "",
        "| level | status | claim | evidence | limitation |",
        "| ---: | --- | --- | --- | --- |",
    ]
    for entry in payload["entries"]:
        lines.append(
            "| {level} | {status} | {claim} | {evidence} | {limitation} |".format(
                **entry
            )
        )

    lines.extend(["", "## Open Questions", ""])
    lines.extend(f"- {question}" for question in payload["open_questions"])
    lines.extend(
        [
            "",
            "## Source Artifacts",
            "",
            f"- `docs/results.json` SHA-256: `{payload['artifact_hashes']['results_sha256']}`",
            f"- `docs/sweeps.json` SHA-256: `{payload['artifact_hashes']['sweeps_sha256']}`",
            f"- `docs/deep_sweeps.json` SHA-256: `{payload['artifact_hashes']['deep_sweeps_sha256']}`",
            f"- `docs/transform_sweeps.json` SHA-256: `{payload['artifact_hashes']['transform_sweeps_sha256']}`",
            f"- `docs/corpus_matrix.json` SHA-256: `{payload['artifact_hashes']['corpus_matrix_sha256']}`",
            f"- `docs/corpus_generalization_probe.json` SHA-256: `{payload['artifact_hashes']['corpus_generalization_probe_sha256']}`",
            f"- `docs/composed_transform_probe.json` SHA-256: `{payload['artifact_hashes']['composed_transform_probe_sha256']}`",
            f"- `docs/depth3_prefix_probe.json` SHA-256: `{payload['artifact_hashes']['depth3_prefix_probe_sha256']}`",
            f"- `docs/depth3_compression_followup.json` SHA-256: `{payload['artifact_hashes']['depth3_compression_followup_sha256']}`",
            f"- `docs/lead_depth3_prefix_probe.json` SHA-256: `{payload['artifact_hashes']['lead_depth3_prefix_probe_sha256']}`",
            f"- `docs/lead_depth3_compression_followup.json` SHA-256: `{payload['artifact_hashes']['lead_depth3_compression_followup_sha256']}`",
            f"- `docs/depth3_frontier_exact_discovery.json` SHA-256: `{payload['artifact_hashes']['depth3_frontier_exact_discovery_sha256']}`",
            f"- `docs/depth4_shard_plan.json` SHA-256: `{payload['artifact_hashes']['depth4_shard_plan_sha256']}`",
            f"- `docs/depth4_pilot_shard.json` SHA-256: `{payload['artifact_hashes']['depth4_pilot_shard_sha256']}`",
            f"- `docs/search_frontier_gate.json` SHA-256: `{payload['artifact_hashes']['search_frontier_gate_sha256']}`",
            f"- `docs/mechanism_experiment_ranking.json` SHA-256: `{payload['artifact_hashes']['mechanism_experiment_ranking_sha256']}`",
            f"- `docs/seed_table_preset_probe.json` SHA-256: `{payload['artifact_hashes']['seed_table_preset_probe_sha256']}`",
            f"- `docs/exact_short_hit_bundle_economics.json` SHA-256: `{payload['artifact_hashes']['exact_short_hit_bundle_economics_sha256']}`",
            f"- `docs/whole_stream_residual_vector_probe.json` SHA-256: `{payload['artifact_hashes']['whole_stream_residual_vector_probe_sha256']}`",
            f"- `docs/expander_salt_ensemble.json` SHA-256: `{payload['artifact_hashes']['expander_salt_ensemble_sha256']}`",
            f"- `docs/schema_native_public_dictionaries.json` SHA-256: `{payload['artifact_hashes']['schema_native_public_dictionaries_sha256']}`",
            f"- `docs/schema_native_public_dictionary_replication.json` SHA-256: `{payload['artifact_hashes']['schema_native_public_dictionary_replication_sha256']}`",
            f"- `docs/superposition_telemetry.json` SHA-256: `{payload['artifact_hashes']['superposition_telemetry_sha256']}`",
            f"- `docs/long_span_bundle_gate.json` SHA-256: `{payload['artifact_hashes']['long_span_bundle_gate_sha256']}`",
            f"- `docs/recursive_structured_fixtures.json` SHA-256: `{payload['artifact_hashes']['recursive_structured_fixtures_sha256']}`",
            f"- `docs/scale_performance_report.json` SHA-256: `{payload['artifact_hashes']['scale_performance_report_sha256']}`",
            f"- `docs/ui_workflow_smoke.json` SHA-256: `{payload['artifact_hashes']['ui_workflow_smoke_sha256']}`",
            f"- `docs/contextual_fifth_byte_steering.json` SHA-256: `{payload['artifact_hashes']['contextual_fifth_byte_steering_sha256']}`",
            f"- `docs/structural_transform_search.json` SHA-256: `{payload['artifact_hashes']['structural_transform_search_sha256']}`",
            f"- `docs/byte_permutation_transform_search.json` SHA-256: `{payload['artifact_hashes']['byte_permutation_transform_search_sha256']}`",
            f"- `docs/bwt_mtf_transform_probe.json` SHA-256: `{payload['artifact_hashes']['bwt_mtf_transform_probe_sha256']}`",
            f"- `docs/grammar_channel_match_discovery.json` SHA-256: `{payload['artifact_hashes']['grammar_channel_match_discovery_sha256']}`",
            f"- `docs/numeric_value_channel_match_discovery.json` SHA-256: `{payload['artifact_hashes']['numeric_value_channel_match_discovery_sha256']}`",
            f"- `docs/heldout_corpus_expansion.json` SHA-256: `{payload['artifact_hashes']['heldout_corpus_expansion_sha256']}`",
            f"- `docs/record_context_transform_search.json` SHA-256: `{payload['artifact_hashes']['record_context_transform_search_sha256']}`",
            f"- `docs/token_dictionary_transform_search.json` SHA-256: `{payload['artifact_hashes']['token_dictionary_transform_search_sha256']}`",
            f"- `docs/affine_transform_search.json` SHA-256: `{payload['artifact_hashes']['affine_transform_search_sha256']}`",
            f"- `docs/seed_manifold_residual_steering.json` SHA-256: `{payload['artifact_hashes']['seed_manifold_residual_steering_sha256']}`",
            f"- `docs/sidecar_break_even.json` SHA-256: `{payload['artifact_hashes']['sidecar_break_even_sha256']}`",
            f"- `docs/residual_payload_compressibility.json` SHA-256: `{payload['artifact_hashes']['residual_payload_compressibility_sha256']}`",
            f"- `docs/experimental_sidecar_descriptor.json` SHA-256: `{payload['artifact_hashes']['experimental_sidecar_descriptor_sha256']}`",
            f"- `docs/sidecar_record_overhead.json` SHA-256: `{payload['artifact_hashes']['sidecar_record_overhead_sha256']}`",
            f"- `docs/packed_sidecar_descriptor.json` SHA-256: `{payload['artifact_hashes']['packed_sidecar_descriptor_sha256']}`",
            f"- `docs/packed_sidecar_controls.json` SHA-256: `{payload['artifact_hashes']['packed_sidecar_controls_sha256']}`",
            f"- `docs/generalized_packed_sidecar.json` SHA-256: `{payload['artifact_hashes']['generalized_packed_sidecar_sha256']}`",
            f"- `docs/packed_sidecar_replication.json` SHA-256: `{payload['artifact_hashes']['packed_sidecar_replication_sha256']}`",
            f"- `docs/match_discovery.json` SHA-256: `{payload['artifact_hashes']['match_discovery_sha256']}`",
            f"- `docs/alignment_arity_discovery.json` SHA-256: `{payload['artifact_hashes']['alignment_arity_discovery_sha256']}`",
            f"- `docs/transformed_match_discovery.json` SHA-256: `{payload['artifact_hashes']['transformed_match_discovery_sha256']}`",
            f"- `docs/lead_exact_discovery.json` SHA-256: `{payload['artifact_hashes']['lead_exact_discovery_sha256']}`",
        ]
    )
    VIABILITY_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_payload_from_files() -> dict[str, Any]:
    return build_ledger(
        load_json(RESULTS_PATH),
        load_json(SWEEPS_PATH),
        load_json(DEEP_SWEEPS_PATH),
        load_json(TRANSFORM_SWEEPS_PATH),
        load_json(CORPUS_MATRIX_PATH),
        load_json(CORPUS_GENERALIZATION_PATH),
        load_json(COMPOSED_PROBE_PATH),
        load_json(DEPTH3_PREFIX_PROBE_PATH),
        load_json(DEPTH3_COMPRESSION_FOLLOWUP_PATH),
        load_json(LEAD_DEPTH3_PREFIX_PROBE_PATH),
        load_json(LEAD_DEPTH3_COMPRESSION_FOLLOWUP_PATH),
        load_json(DEPTH3_FRONTIER_EXACT_DISCOVERY_PATH),
        load_json(DEPTH4_SHARD_PLAN_PATH),
        load_json(DEPTH4_PILOT_SHARD_PATH),
        load_json(SEARCH_FRONTIER_GATE_PATH),
        load_json(MECHANISM_EXPERIMENT_RANKING_PATH),
        load_json(SEED_TABLE_PRESET_PROBE_PATH),
        load_json(EXACT_SHORT_HIT_BUNDLE_ECONOMICS_PATH),
        load_json(WHOLE_STREAM_RESIDUAL_VECTOR_PROBE_PATH),
        load_json(EXPANDER_SALT_ENSEMBLE_PATH),
        load_json(SCHEMA_NATIVE_PUBLIC_DICTIONARIES_PATH),
        load_json(SCHEMA_NATIVE_PUBLIC_DICTIONARY_REPLICATION_PATH),
        load_json(SUPERPOSITION_TELEMETRY_PATH),
        load_json(LONG_SPAN_BUNDLE_GATE_PATH),
        load_json(RECURSIVE_STRUCTURED_FIXTURES_PATH),
        load_json(SCALE_PERFORMANCE_PATH),
        load_json(UI_WORKFLOW_SMOKE_PATH),
        load_json(CONTEXTUAL_STEERING_PATH),
        load_json(STRUCTURAL_SEARCH_PATH),
        load_json(BYTE_PERMUTATION_SEARCH_PATH),
        load_json(BWT_MTF_PROBE_PATH),
        load_json(GRAMMAR_CHANNEL_DISCOVERY_PATH),
        load_json(NUMERIC_VALUE_CHANNEL_DISCOVERY_PATH),
        load_json(HELDOUT_CORPUS_EXPANSION_PATH),
        load_json(RECORD_CONTEXT_SEARCH_PATH),
        load_json(TOKEN_DICTIONARY_SEARCH_PATH),
        load_json(AFFINE_SEARCH_PATH),
        load_json(RESIDUAL_STEERING_PATH),
        load_json(SIDECAR_BREAK_EVEN_PATH),
        load_json(RESIDUAL_PAYLOAD_COMPRESSIBILITY_PATH),
        load_json(EXPERIMENTAL_SIDECAR_DESCRIPTOR_PATH),
        load_json(SIDECAR_RECORD_OVERHEAD_PATH),
        load_json(PACKED_SIDECAR_DESCRIPTOR_PATH),
        load_json(PACKED_SIDECAR_CONTROLS_PATH),
        load_json(GENERALIZED_PACKED_SIDECAR_PATH),
        load_json(PACKED_SIDECAR_REPLICATION_PATH),
        load_json(MATCH_DISCOVERY_PATH),
        load_json(ALIGNMENT_ARITY_DISCOVERY_PATH),
        load_json(TRANSFORMED_MATCH_DISCOVERY_PATH),
        load_json(LEAD_EXACT_DISCOVERY_PATH),
    )


def check_viability() -> None:
    if not VIABILITY_JSON.exists() or not VIABILITY_MD.exists():
        raise SystemExit("generated viability files are missing")
    payload = load_json(VIABILITY_JSON)
    if payload.get("generated_by") != "scripts/generate_viability.py":
        raise SystemExit("viability.json has wrong generated_by marker")
    if payload.get("artifact_hashes") != artifact_hashes():
        raise SystemExit("viability artifact hashes are stale")
    expected = stable_projection(build_payload_from_files())
    current = stable_projection(payload)
    if current != expected:
        raise SystemExit("viability.json is stale; regenerate it")
    levels = [entry.get("level") for entry in payload.get("entries", [])]
    if levels != list(range(len(levels))):
        raise SystemExit("viability levels must be unique, contiguous, and ordered")
    text = VIABILITY_MD.read_text(encoding="utf-8")
    for source_name, digest in payload["artifact_hashes"].items():
        if digest not in text:
            raise SystemExit(f"VIABILITY.md missing source hash: {source_name}")
    for phrase in (
        "research-viable, not production-proven",
        "Structured and binary controls",
        "Bounded structural reversible transforms",
        "Affine byte remaps",
        "Residual sidecar steering",
        "Longer-span residual sidecars",
        "Measured residual payload coders",
        "experimental sidecar descriptor",
        "Packed sidecar offset",
        "packed offset/seed-index sidecar descriptor",
        "Packed sidecar controls",
        "Generalized packed offset and seed modes",
        "Frozen packed sidecar replication",
        "Pre-sidecar match discovery",
        "Alignment and arity discovery",
        "Frozen reversible transforms",
        "Corpus generalization controls did not produce exact seed-span rows",
        "BWT/MTF classic preconditioners did not yet produce exact seed-span rows",
        "Selected affine, periodic, and composed leads",
        "Selected-lead depth-3 compression follow-up stayed null",
        "Depth-3 frontier exact discovery found prefix movement only",
        "Depth-4 search is sharded and explicitly gated",
        "generated search-frontier gate blocks broad raw depth search",
        "generated mechanism-experiment ranking",
        "generated seed-table preset probe",
        "generated exact short-hit bundle economics",
        "generated whole-stream residual vector probe",
        "generated expander salt ensemble",
        "generated schema-native public dictionary probe",
        "schema-native public dictionary replication blocked promotion",
        "generated superposition telemetry proves selector auditability",
        "generated long-span bundle gate blocks broad long-span sweeps",
        "Recursive v2 later-layer gains remain unpromoted outside planted offset controls",
        "generated scale-performance report makes bounded planted-density scaling interpretable",
        "Tauri evidence ledger panel has static UI/bridge workflow coverage",
        "Grammar/channel discovery did not yet produce exact seed-span rows",
        "Numeric value-channel discovery did not yet produce exact seed-span rows",
        "Held-out corpus expansion broadened deterministic corpus coverage",
        "Record/context-aware transforms did not yet produce exact seed-span rows",
        "Token/dictionary transforms did not yet produce exact seed-span rows",
    ):
        if phrase not in text:
            raise SystemExit(f"VIABILITY.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate generated viability files")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.check:
        check_viability()
        return
    write_viability(build_payload_from_files())


if __name__ == "__main__":
    main()
