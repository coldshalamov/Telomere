#!/usr/bin/env python3
"""Lightweight documentation consistency checks for the current Telomere docs."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import generate_results
import generate_deep_sweeps
import generate_corpus_matrix
import generate_corpus_generalization_probe
import generate_acceleration_report
import generate_affine_transform_search
import generate_alignment_arity_discovery
import generate_byte_permutation_transform_search
import generate_bwt_mtf_transform_probe
import generate_experiment_queue
import generate_experimental_sidecar_descriptor
import generate_fifth_byte_residual
import generate_fifth_byte_steering
import generate_goal_audit
import generate_grammar_channel_match_discovery
import generate_generalized_packed_sidecar
import generate_heldout_corpus_expansion
import generate_lead_exact_discovery
import generate_manifold_report
import generate_match_discovery
import generate_nearmiss_forecast
import generate_numeric_value_channel_match_discovery
import generate_packed_sidecar_descriptor
import generate_packed_sidecar_controls
import generate_packed_sidecar_replication
import generate_periodic_transform_probe
import generate_composed_transform_probe
import generate_contextual_fifth_byte_steering
import generate_depth3_compression_followup
import generate_depth3_frontier_exact_discovery
import generate_depth3_prefix_probe
import generate_depth4_pilot_shard
import generate_depth4_shard_plan
import generate_lead_depth3_compression_followup
import generate_lead_depth3_prefix_probe
import generate_prefix_ladder
import generate_research_scorecard
import generate_research_decision
import generate_research_frontier
import generate_natural_corpus_proof_matrix
import generate_natural_corpus_reopen_manifest
import generate_external_corpus_accession
import generate_production_proof_matrix
import generate_research_team_protocol
import generate_goal_completion_audit
import generate_blocked_requirement_dispatch
import generate_research_hypotheses
import generate_research_team_packet
import generate_research_agent_prompts
import generate_research_agent_result_intake
import generate_claim_boundary_audit
import generate_residual_payload_compressibility
import generate_search_frontier_gate
import generate_mechanism_experiment_ranking
import generate_seed_table_preset_probe
import generate_exact_short_hit_bundle_economics
import generate_whole_stream_residual_vector_probe
import generate_expander_salt_ensemble
import generate_seed_table_fasta_ablation
import generate_schema_native_public_dictionaries
import generate_schema_native_public_dictionary_replication
import generate_public_preset_promotion_gate
import generate_public_preset_control_audit
import generate_public_preset_control_ablation
import generate_public_preset_ablation_projection
import generate_public_preset_control_rerun
import generate_public_preset_codeword_sweep
import generate_seed_table_preset_replay
import generate_superposition_telemetry
import generate_lattice_selection_heldout_probe
import generate_long_span_bundle_gate
import generate_mechanism_closure_audit
import generate_next_mechanism_designs
import generate_frozen_rank_coded_span_generator
import generate_frozen_rank_source_candidates
import generate_recursive_structured_fixtures
import generate_scale_performance_report
import generate_bounded_streaming_memory_gate
import generate_streaming_economics_gate
import generate_ui_workflow_smoke
import generate_seed_manifold_residual_steering
import generate_sidecar_break_even
import generate_sidecar_record_overhead
import generate_record_context_transform_search
import generate_structural_transform_search
import generate_sweeps
import generate_theory_report
import generate_token_dictionary_transform_search
import generate_transformed_match_discovery
import generate_transform_sweeps
import generate_transform_probe
import generate_transform_validation
import generate_viability


ROOT = Path(__file__).resolve().parents[1]


REQUIRED_FILES = [
    "README.md",
    "docs/ARCHITECTURE.md",
    "docs/FORMAT.md",
    "docs/RESULTS.md",
    "docs/results.json",
    "docs/SWEEPS.md",
    "docs/sweeps.json",
    "docs/DEEP_SWEEPS.md",
    "docs/deep_sweeps.json",
    "docs/TRANSFORM_SWEEPS.md",
    "docs/transform_sweeps.json",
    "docs/TRANSFORM_PROBE.md",
    "docs/transform_probe.json",
    "docs/TRANSFORM_VALIDATION.md",
    "docs/transform_validation.json",
    "docs/STRUCTURAL_TRANSFORM_SEARCH.md",
    "docs/structural_transform_search.json",
    "docs/BYTE_PERMUTATION_TRANSFORM_SEARCH.md",
    "docs/byte_permutation_transform_search.json",
    "docs/BWT_MTF_TRANSFORM_PROBE.md",
    "docs/bwt_mtf_transform_probe.json",
    "docs/GRAMMAR_CHANNEL_MATCH_DISCOVERY.md",
    "docs/grammar_channel_match_discovery.json",
    "docs/NUMERIC_VALUE_CHANNEL_MATCH_DISCOVERY.md",
    "docs/numeric_value_channel_match_discovery.json",
    "docs/HELDOUT_CORPUS_EXPANSION.md",
    "docs/heldout_corpus_expansion.json",
    "docs/RECORD_CONTEXT_TRANSFORM_SEARCH.md",
    "docs/record_context_transform_search.json",
    "docs/TOKEN_DICTIONARY_TRANSFORM_SEARCH.md",
    "docs/token_dictionary_transform_search.json",
    "docs/AFFINE_TRANSFORM_SEARCH.md",
    "docs/affine_transform_search.json",
    "docs/SEED_MANIFOLD_RESIDUAL_STEERING.md",
    "docs/seed_manifold_residual_steering.json",
    "docs/SIDECAR_BREAK_EVEN.md",
    "docs/sidecar_break_even.json",
    "docs/RESIDUAL_PAYLOAD_COMPRESSIBILITY.md",
    "docs/residual_payload_compressibility.json",
    "docs/EXPERIMENTAL_SIDECAR_DESCRIPTOR.md",
    "docs/experimental_sidecar_descriptor.json",
    "docs/SIDECAR_RECORD_OVERHEAD.md",
    "docs/sidecar_record_overhead.json",
    "docs/PACKED_SIDECAR_DESCRIPTOR.md",
    "docs/packed_sidecar_descriptor.json",
    "docs/PACKED_SIDECAR_CONTROLS.md",
    "docs/packed_sidecar_controls.json",
    "docs/GENERALIZED_PACKED_SIDECAR.md",
    "docs/generalized_packed_sidecar.json",
    "docs/PACKED_SIDECAR_REPLICATION.md",
    "docs/packed_sidecar_replication.json",
    "docs/MATCH_DISCOVERY.md",
    "docs/match_discovery.json",
    "docs/ALIGNMENT_ARITY_DISCOVERY.md",
    "docs/alignment_arity_discovery.json",
    "docs/TRANSFORMED_MATCH_DISCOVERY.md",
    "docs/transformed_match_discovery.json",
    "docs/LEAD_EXACT_DISCOVERY.md",
    "docs/lead_exact_discovery.json",
    "docs/LEAD_DEPTH3_PREFIX_PROBE.md",
    "docs/lead_depth3_prefix_probe.json",
    "docs/LEAD_DEPTH3_COMPRESSION_FOLLOWUP.md",
    "docs/lead_depth3_compression_followup.json",
    "docs/DEPTH3_FRONTIER_EXACT_DISCOVERY.md",
    "docs/depth3_frontier_exact_discovery.json",
    "docs/DEPTH4_SHARD_PLAN.md",
    "docs/depth4_shard_plan.json",
    "docs/DEPTH4_PILOT_SHARD.md",
    "docs/depth4_pilot_shard.json",
    "docs/SEARCH_FRONTIER_GATE.md",
    "docs/search_frontier_gate.json",
    "docs/MECHANISM_EXPERIMENT_RANKING.md",
    "docs/mechanism_experiment_ranking.json",
    "docs/SEED_TABLE_PRESET_PROBE.md",
    "docs/seed_table_preset_probe.json",
    "docs/SEED_TABLE_PRESET_REPLAY.md",
    "docs/seed_table_preset_replay.json",
    "docs/SEED_TABLE_FASTA_ABLATION.md",
    "docs/seed_table_fasta_ablation.json",
    "docs/EXACT_SHORT_HIT_BUNDLE_ECONOMICS.md",
    "docs/exact_short_hit_bundle_economics.json",
    "docs/WHOLE_STREAM_RESIDUAL_VECTOR_PROBE.md",
    "docs/whole_stream_residual_vector_probe.json",
    "docs/EXPANDER_SALT_ENSEMBLE.md",
    "docs/expander_salt_ensemble.json",
    "docs/SCHEMA_NATIVE_PUBLIC_DICTIONARIES.md",
    "docs/schema_native_public_dictionaries.json",
    "docs/SCHEMA_NATIVE_PUBLIC_DICTIONARY_REPLICATION.md",
    "docs/schema_native_public_dictionary_replication.json",
    "docs/PUBLIC_PRESET_PROMOTION_GATE.md",
    "docs/public_preset_promotion_gate.json",
    "docs/PUBLIC_PRESET_CONTROL_AUDIT.md",
    "docs/public_preset_control_audit.json",
    "docs/PUBLIC_PRESET_CONTROL_ABLATION.md",
    "docs/public_preset_control_ablation.json",
    "docs/PUBLIC_PRESET_ABLATION_PROJECTION.md",
    "docs/public_preset_ablation_projection.json",
    "docs/PUBLIC_PRESET_CONTROL_RERUN.md",
    "docs/public_preset_control_rerun.json",
    "docs/PUBLIC_PRESET_CODEWORD_SWEEP.md",
    "docs/public_preset_codeword_sweep.json",
    "docs/LONG_SPAN_BUNDLE_GATE.md",
    "docs/long_span_bundle_gate.json",
    "docs/MECHANISM_CLOSURE_AUDIT.md",
    "docs/mechanism_closure_audit.json",
    "docs/NEXT_MECHANISM_DESIGNS.md",
    "docs/next_mechanism_designs.json",
    "docs/FROZEN_RANK_CODED_SPAN_GENERATOR.md",
    "docs/frozen_rank_coded_span_generator.json",
    "docs/FROZEN_RANK_SOURCE_CANDIDATES.md",
    "docs/frozen_rank_source_candidates.json",
    "docs/SUPERPOSITION_TELEMETRY.md",
    "docs/superposition_telemetry.json",
    "docs/LATTICE_SELECTION_HELDOUT_PROBE.md",
    "docs/lattice_selection_heldout_probe.json",
    "docs/RECURSIVE_STRUCTURED_FIXTURES.md",
    "docs/recursive_structured_fixtures.json",
    "docs/SCALE_PERFORMANCE.md",
    "docs/scale_performance_report.json",
    "docs/BOUNDED_STREAMING_MEMORY_GATE.md",
    "docs/bounded_streaming_memory_gate.json",
    "docs/STREAMING_ECONOMICS_GATE.md",
    "docs/streaming_economics_gate.json",
    "docs/UI_WORKFLOW_SMOKE.md",
    "docs/ui_workflow_smoke.json",
    "docs/PERIODIC_TRANSFORM_PROBE.md",
    "docs/periodic_transform_probe.json",
    "docs/COMPOSED_TRANSFORM_PROBE.md",
    "docs/composed_transform_probe.json",
    "docs/CORPUS_MATRIX.md",
    "docs/corpus_matrix.json",
    "docs/CORPUS_GENERALIZATION_PROBE.md",
    "docs/corpus_generalization_probe.json",
    "docs/ACCELERATION.md",
    "docs/acceleration_report.json",
    "docs/THEORY.md",
    "docs/theory.json",
    "docs/MANIFOLD.md",
    "docs/manifold.json",
    "docs/NEARMISS_FORECAST.md",
    "docs/nearmiss_forecast.json",
    "docs/PREFIX_LADDER.md",
    "docs/prefix_ladder.json",
    "docs/DEPTH3_PREFIX_PROBE.md",
    "docs/depth3_prefix_probe.json",
    "docs/DEPTH3_COMPRESSION_FOLLOWUP.md",
    "docs/depth3_compression_followup.json",
    "docs/FIFTH_BYTE_RESIDUAL.md",
    "docs/fifth_byte_residual.json",
    "docs/FIFTH_BYTE_STEERING.md",
    "docs/fifth_byte_steering.json",
    "docs/CONTEXTUAL_FIFTH_BYTE_STEERING.md",
    "docs/contextual_fifth_byte_steering.json",
    "docs/GOAL_AUDIT.md",
    "docs/goal_audit.json",
    "docs/GOAL_COMPLETION_AUDIT.md",
    "docs/goal_completion_audit.json",
    "docs/NATURAL_CORPUS_PROOF_MATRIX.md",
    "docs/natural_corpus_proof_matrix.json",
    "docs/NATURAL_CORPUS_REOPEN_MANIFEST.md",
    "docs/natural_corpus_reopen_manifest.json",
    "corpora/external/manifest.json",
    "docs/EXTERNAL_CORPUS_ACCESSION.md",
    "docs/external_corpus_accession.json",
    "docs/PRODUCTION_PROOF_MATRIX.md",
    "docs/production_proof_matrix.json",
    "docs/BLOCKED_REQUIREMENT_DISPATCH.md",
    "docs/blocked_requirement_dispatch.json",
    "docs/RESEARCH_HYPOTHESES.md",
    "docs/research_hypotheses.json",
    "docs/RESEARCH_TEAM_PACKET.md",
    "docs/research_team_packet.json",
    "docs/RESEARCH_AGENT_PROMPTS.md",
    "docs/research_agent_prompts.json",
    "docs/agent_reports/manifest.json",
    "docs/agent_reports/REPORT_TEMPLATES.md",
    "docs/agent_reports/report_templates.json",
    "docs/RESEARCH_AGENT_RESULT_INTAKE.md",
    "docs/research_agent_result_intake.json",
    "docs/CLAIM_BOUNDARY_AUDIT.md",
    "docs/claim_boundary_audit.json",
    "docs/EXPERIMENT_QUEUE.md",
    "docs/experiment_queue.json",
    "docs/RESEARCH_DECISION.md",
    "docs/research_decision.json",
    "docs/RESEARCH_FRONTIER.md",
    "docs/research_frontier.json",
    "docs/RESEARCH_TEAM_PROTOCOL.md",
    "docs/research_team_protocol.json",
    "docs/RESEARCH_SCORECARD.md",
    "docs/research_scorecard.json",
    "docs/adr/0001-transform-preconditioners.md",
    "docs/adr/0002-gpu-acceleration-status.md",
    "docs/VIABILITY.md",
    "docs/viability.json",
    "docs/CANDIDATE_LATTICE.md",
    "docs/TOOLS.md",
    "docs/RESEARCH_PROGRAM.md",
    "docs/GENERATED_LEDGER_PIPELINE.md",
    "docs/RELEASE_CHECKLIST.md",
    "docs/Telomere Whitepaper V2.md",
    "ui/index.html",
]

README_REQUIRED = [
    "--json",
    "--verify",
    "--hasher",
    "--memory-limit",
    "--force",
    "--engine",
    "telomere index build",
    ".tlmr",
    "seed depth 1",
    "seed depth 2",
    "seed depth 3",
]

FORMAT_REQUIRED = [
    "hasher_id",
    "lotus_preset",
    "layer_count",
    "format_version` is `3`",
    "exact generated-prefix lookup",
    "arity 2",
    "small indices encode in fewer",
]

RESEARCH_REQUIRED = [
    "evidence ladder",
    "experiment matrix",
    "falsification criteria",
    "streaming/indexed engines diverge",
    "random controls are expected to bloat",
    "external corpus ingress",
]

ADR_REQUIRED = [
    "Keep transform preconditioners outside `.tlmr` v1 and `.tlmr` v2",
    "not proof that the Telomere generative matcher found structure",
    "Promotion Criteria",
]

GPU_ADR_REQUIRED = [
    "GPU remains research-only",
    "Do not call a feature production-ready because it compiles",
    "a real OpenCL/CUDA/kernel-backed matcher exists",
]

LATTICE_REQUIRED = [
    "not the `.tlmr` v2 wire contract",
    "within an 8-bit delta",
    "decompression never needs a candidate lattice",
    "selected output must collapse to ordinary v1 or v2 records",
]

FORBIDDEN_PHRASES = [
    "arity 2 is reserved",
    "reserved for literal marker",
    "random data should compress",
    "guarantee compression",
    "recursive convergence goal",
    "seed-hash to a block",
]

WHITEPAPER_REQUIRED = [
    "historical status note",
    "canonical current architecture",
    "planted positives",
    "hypothetical cost model",
    "production proof",
]

WHITEPAPER_FORBIDDEN = [
    "replaces all raw data",
    "viable enterprise compression process today",
    "compression-as-a-service",
    "miniscule percentage",
    "no raw data is stored",
    "every byte is replaceable",
    "without bound",
    "double the compression ratio",
    "typically 1",
    "routinely lift",
    "1-3%",
    "1–3%",
    "1–3 %",
    "matches observed data",
    "well within modern computational limits",
    "40-bit window fits into",
]

UI_EVIDENCE_REQUIRED = [
    'id="evidenceGates"',
    "renderResearchArtifacts",
    "ready_count",
    "heldout_exact_hits",
    "match_selected_spans",
    "lead_exact_hits",
    "depth4_exact_hits",
    "gpu_real_kernel_detected",
    "recursive_structured_ordinary_later_win_families",
]

TAURI_EVIDENCE_REQUIRED = [
    "ResearchEvidenceSummary",
    "top_ready_lane",
    "heldout_prefix4_win_corpora",
    "match_selected_spans",
    "lead_exact_hits",
    "depth4_exact_hits",
    "gpu_real_kernel_detected",
    "recursive_structured_ordinary_later_win_families",
    "exact-discovery",
]


def fail(msg: str) -> None:
    print(f"ERROR: {msg}")
    sys.exit(1)


def read(path: str) -> str:
    full = ROOT / path
    if not full.exists():
        fail(f"missing required doc {path}")
    return full.read_text(encoding="utf-8")


def main() -> None:
    texts = {path: read(path) for path in REQUIRED_FILES}
    tauri_host = read("src-tauri/src/main.rs")

    readme_lower = texts["README.md"].lower()
    for phrase in README_REQUIRED:
        if phrase not in readme_lower:
            fail(f"README.md missing {phrase}")

    format_lower = texts["docs/FORMAT.md"].lower()
    for phrase in FORMAT_REQUIRED:
        if phrase not in format_lower:
            fail(f"docs/FORMAT.md missing {phrase}")

    research_lower = texts["docs/RESEARCH_PROGRAM.md"].lower()
    for phrase in RESEARCH_REQUIRED:
        if phrase not in research_lower:
            fail(f"docs/RESEARCH_PROGRAM.md missing {phrase}")

    adr_text = texts["docs/adr/0001-transform-preconditioners.md"]
    for phrase in ADR_REQUIRED:
        if phrase not in adr_text:
            fail(f"docs/adr/0001-transform-preconditioners.md missing {phrase}")

    gpu_adr_text = texts["docs/adr/0002-gpu-acceleration-status.md"]
    for phrase in GPU_ADR_REQUIRED:
        if phrase not in gpu_adr_text:
            fail(f"docs/adr/0002-gpu-acceleration-status.md missing {phrase}")

    lattice_lower = texts["docs/CANDIDATE_LATTICE.md"].lower()
    for phrase in LATTICE_REQUIRED:
        if phrase not in lattice_lower:
            fail(f"docs/CANDIDATE_LATTICE.md missing {phrase}")

    for path, text in texts.items():
        lower = text.lower()
        for phrase in FORBIDDEN_PHRASES:
            if phrase in lower:
                fail(f"{path} contains stale phrase: {phrase}")

    whitepaper_lower = texts["docs/Telomere Whitepaper V2.md"].lower()
    for phrase in WHITEPAPER_REQUIRED:
        if phrase not in whitepaper_lower:
            fail(f"docs/Telomere Whitepaper V2.md missing {phrase}")
    for phrase in WHITEPAPER_FORBIDDEN:
        if phrase in whitepaper_lower:
            fail(f"docs/Telomere Whitepaper V2.md contains stale production claim: {phrase}")

    ui_text = texts["ui/index.html"]
    for phrase in UI_EVIDENCE_REQUIRED:
        if phrase not in ui_text:
            fail(f"ui/index.html missing evidence ledger smoke marker: {phrase}")
    for phrase in TAURI_EVIDENCE_REQUIRED:
        if phrase not in tauri_host:
            fail(f"src-tauri/src/main.rs missing evidence ledger smoke marker: {phrase}")

    results = json.loads(texts["docs/results.json"])
    if results.get("generated_by") != "scripts/generate_results.py":
        fail("docs/results.json is not marked as generated by scripts/generate_results.py")
    if not results.get("results"):
        fail("docs/results.json contains no result rows")
    if results.get("case_manifest_sha256") != generate_results.case_manifest_hash():
        fail("docs/results.json case matrix hash is stale; run scripts/generate_results.py")
    expected_cases = [case["name"] for case in generate_results.CASE_MATRIX]
    actual_cases = [row.get("name") for row in results["results"]]
    if actual_cases != expected_cases:
        fail("docs/results.json does not contain the full generated-results case matrix")
    missing_from_results_md = [
        name for name in expected_cases if name not in texts["docs/RESULTS.md"]
    ]
    if missing_from_results_md:
        fail(f"docs/RESULTS.md missing generated cases: {', '.join(missing_from_results_md)}")

    sweeps = json.loads(texts["docs/sweeps.json"])
    if sweeps.get("generated_by") != "scripts/generate_sweeps.py":
        fail("docs/sweeps.json is not marked as generated by scripts/generate_sweeps.py")
    if sweeps.get("sweep_manifest_sha256") != generate_sweeps.sweep_manifest_hash():
        fail("docs/sweeps.json sweep matrix hash is stale; run scripts/generate_sweeps.py")
    expected_sweeps = [case["name"] for case in generate_sweeps.SWEEP_MATRIX]
    actual_sweeps = [row.get("name") for row in sweeps.get("results", [])]
    if actual_sweeps != expected_sweeps:
        fail("docs/sweeps.json does not contain the full generated sweep matrix")
    required_sweep_telemetry = {
        "seeds_scanned",
        "seed_expansions",
        "tier_count",
        "tier_lookup_count_total",
        "tier_target_windows_total",
        "tier_unique_spans_total",
        "tier_estimated_target_table_bytes_total",
        "tier_estimated_target_table_bytes_max",
        "candidate_hits_raw_total",
        "candidate_hits_profitable_total",
    }
    for row in sweeps.get("results", []):
        telemetry = row.get("telemetry", {})
        missing_keys = sorted(required_sweep_telemetry.difference(telemetry))
        if missing_keys:
            fail(
                "docs/sweeps.json missing scale/work telemetry for "
                f"{row.get('name', '<unknown>')}: {', '.join(missing_keys)}"
            )
    missing_from_sweeps_md = [
        name for name in expected_sweeps if name not in texts["docs/SWEEPS.md"]
    ]
    if missing_from_sweeps_md:
        fail(f"docs/SWEEPS.md missing generated sweeps: {', '.join(missing_from_sweeps_md)}")
    for phrase in (
        "Work/Memory Accounting",
        "seed expansions",
        "target windows",
        "estimated target-table bytes",
        "peak/est",
    ):
        if phrase not in texts["docs/SWEEPS.md"]:
            fail(f"docs/SWEEPS.md missing sweep telemetry phrase: {phrase}")

    deep_sweeps = json.loads(texts["docs/deep_sweeps.json"])
    if deep_sweeps.get("generated_by") != "scripts/generate_deep_sweeps.py":
        fail("docs/deep_sweeps.json is not marked as generated by scripts/generate_deep_sweeps.py")
    if deep_sweeps.get("deep_manifest_sha256") != generate_deep_sweeps.deep_manifest_hash():
        fail("docs/deep_sweeps.json deep matrix hash is stale; run scripts/generate_deep_sweeps.py")
    expected_deep = [case["name"] for case in generate_deep_sweeps.DEEP_SWEEP_MATRIX]
    actual_deep = [row.get("name") for row in deep_sweeps.get("results", [])]
    if actual_deep != expected_deep:
        fail("docs/deep_sweeps.json does not contain the full generated deep sweep matrix")
    missing_from_deep_md = [
        name for name in expected_deep if name not in texts["docs/DEEP_SWEEPS.md"]
    ]
    if missing_from_deep_md:
        fail(f"docs/DEEP_SWEEPS.md missing generated deep sweeps: {', '.join(missing_from_deep_md)}")

    transform_sweeps = json.loads(texts["docs/transform_sweeps.json"])
    if transform_sweeps.get("generated_by") != "scripts/generate_transform_sweeps.py":
        fail("docs/transform_sweeps.json is not marked as generated by scripts/generate_transform_sweeps.py")
    if transform_sweeps.get("transform_manifest_sha256") != generate_transform_sweeps.transform_manifest_hash():
        fail("docs/transform_sweeps.json transform matrix hash is stale; run scripts/generate_transform_sweeps.py")
    expected_transforms = [case["name"] for case in generate_transform_sweeps.TRANSFORM_MATRIX]
    actual_transforms = [row.get("name") for row in transform_sweeps.get("results", [])]
    if actual_transforms != expected_transforms:
        fail("docs/transform_sweeps.json does not contain the full generated transform matrix")
    missing_from_transform_md = [
        name for name in expected_transforms if name not in texts["docs/TRANSFORM_SWEEPS.md"]
    ]
    if missing_from_transform_md:
        fail(
            f"docs/TRANSFORM_SWEEPS.md missing generated transform sweeps: {', '.join(missing_from_transform_md)}"
        )

    transform_probe = json.loads(texts["docs/transform_probe.json"])
    if transform_probe.get("generated_by") != "scripts/generate_transform_probe.py":
        fail("docs/transform_probe.json is not marked as generated by scripts/generate_transform_probe.py")
    if transform_probe.get("probe_manifest_sha256") != generate_transform_probe.probe_manifest_hash():
        fail("docs/transform_probe.json probe manifest hash is stale; run scripts/generate_transform_probe.py")
    if transform_probe.get("probe_count") != len(generate_transform_probe.probe_manifest()):
        fail("docs/transform_probe.json probe count is stale")
    transform_probe_text = texts["docs/TRANSFORM_PROBE.md"]
    for phrase in (
        "multiple-comparison research probe",
        "Top Prefix >=4 Probes",
        "No row here found an exact 8-byte seed-span hit",
        "not format support",
    ):
        if phrase not in transform_probe_text:
            fail(f"docs/TRANSFORM_PROBE.md missing {phrase}")

    transform_validation = json.loads(texts["docs/transform_validation.json"])
    if transform_validation.get("generated_by") != "scripts/generate_transform_validation.py":
        fail("docs/transform_validation.json is not marked as generated by scripts/generate_transform_validation.py")
    if (
        transform_validation.get("validation_manifest_sha256")
        != generate_transform_validation.validation_manifest_hash()
    ):
        fail(
            "docs/transform_validation.json validation manifest hash is stale; run scripts/generate_transform_validation.py"
        )
    if transform_validation.get("source_probe_sha256") != generate_research_scorecard.sha256(
        ROOT / "docs/transform_probe.json"
    ):
        fail("docs/transform_validation.json source probe hash is stale")
    expected_validation_rows = len(generate_transform_validation.CORPUS_VALIDATION_MATRIX) * len(
        generate_transform_validation.TRANSFORM_VALIDATION_MATRIX
    )
    if len(transform_validation.get("results", [])) != expected_validation_rows:
        fail("docs/transform_validation.json does not contain the full validation matrix")
    transform_validation_text = texts["docs/TRANSFORM_VALIDATION.md"]
    for phrase in (
        "held-out structured corpora",
        "Corpus Summary",
        "Held-out exact hits",
        "not format support",
    ):
        if phrase not in transform_validation_text:
            fail(f"docs/TRANSFORM_VALIDATION.md missing {phrase}")

    generate_structural_transform_search.check_report()
    generate_byte_permutation_transform_search.check_report()
    generate_bwt_mtf_transform_probe.check_report()
    generate_grammar_channel_match_discovery.check_report()
    generate_numeric_value_channel_match_discovery.check_report()
    generate_heldout_corpus_expansion.check_report()
    generate_record_context_transform_search.check_report()
    generate_token_dictionary_transform_search.check_report()
    generate_affine_transform_search.check_report()
    generate_seed_manifold_residual_steering.check_report()
    generate_sidecar_break_even.check_report()
    generate_residual_payload_compressibility.check_report()
    generate_experimental_sidecar_descriptor.check_report()
    generate_sidecar_record_overhead.check_report()
    generate_packed_sidecar_descriptor.check_report()
    generate_packed_sidecar_controls.check_report()
    generate_generalized_packed_sidecar.check_report()
    generate_packed_sidecar_replication.check_report()
    generate_match_discovery.check_report()
    generate_alignment_arity_discovery.check_report()
    generate_transformed_match_discovery.check_report()
    generate_lead_exact_discovery.check_report()
    generate_lead_depth3_prefix_probe.check_report()
    generate_lead_depth3_compression_followup.check_report()
    generate_depth3_frontier_exact_discovery.check_report()
    generate_depth4_shard_plan.check_report()
    generate_depth4_pilot_shard.check_report()
    generate_search_frontier_gate.check_report()
    generate_mechanism_experiment_ranking.check_report()
    generate_seed_table_preset_probe.check_report()
    generate_seed_table_preset_replay.check_report()
    generate_seed_table_fasta_ablation.check_report()
    generate_exact_short_hit_bundle_economics.check_report()
    generate_whole_stream_residual_vector_probe.check_report()
    generate_expander_salt_ensemble.check_report()
    generate_schema_native_public_dictionaries.check_report()
    generate_schema_native_public_dictionary_replication.check_report()
    generate_public_preset_promotion_gate.check_report()
    generate_public_preset_control_audit.check_report()
    generate_public_preset_control_ablation.check_report()
    generate_public_preset_ablation_projection.check_report()
    generate_public_preset_control_rerun.check_report()
    generate_public_preset_codeword_sweep.check_report()
    generate_superposition_telemetry.check_report()
    generate_lattice_selection_heldout_probe.check_report()
    generate_long_span_bundle_gate.check_report()
    generate_mechanism_closure_audit.check_report()
    generate_next_mechanism_designs.check_report()
    generate_frozen_rank_source_candidates.check_report()
    generate_recursive_structured_fixtures.check_report()
    generate_scale_performance_report.check_report()
    generate_bounded_streaming_memory_gate.check_report()
    generate_streaming_economics_gate.check_report()
    generate_ui_workflow_smoke.check_report()

    periodic_probe = json.loads(texts["docs/periodic_transform_probe.json"])
    if periodic_probe.get("generated_by") != "scripts/generate_periodic_transform_probe.py":
        fail(
            "docs/periodic_transform_probe.json is not marked as generated by scripts/generate_periodic_transform_probe.py"
        )
    if (
        periodic_probe.get("candidate_manifest_sha256")
        != generate_periodic_transform_probe.candidate_manifest_hash()
    ):
        fail(
            "docs/periodic_transform_probe.json candidate manifest hash is stale; run scripts/generate_periodic_transform_probe.py"
        )
    if periodic_probe.get("candidate_count") != len(
        generate_periodic_transform_probe.candidate_manifest()
    ):
        fail("docs/periodic_transform_probe.json candidate count is stale")
    expected_periodic_rows = len(generate_periodic_transform_probe.VALIDATION_CORPORA) * periodic_probe.get(
        "selected_transform_count", 0
    )
    if len(periodic_probe.get("validation_results", [])) != expected_periodic_rows:
        fail("docs/periodic_transform_probe.json does not contain the full validation matrix")
    periodic_probe_text = texts["docs/PERIODIC_TRANSFORM_PROBE.md"]
    for phrase in (
        "bounded reversible-transform research probe",
        "Discovery Leads",
        "Held-out corpora with prefix >=5 uplift",
        "not format support",
    ):
        if phrase not in periodic_probe_text:
            fail(f"docs/PERIODIC_TRANSFORM_PROBE.md missing {phrase}")

    composed_probe = json.loads(texts["docs/composed_transform_probe.json"])
    if composed_probe.get("generated_by") != "scripts/generate_composed_transform_probe.py":
        fail(
            "docs/composed_transform_probe.json is not marked as generated by scripts/generate_composed_transform_probe.py"
        )
    if (
        composed_probe.get("candidate_manifest_sha256")
        != generate_composed_transform_probe.candidate_manifest_hash()
    ):
        fail(
            "docs/composed_transform_probe.json candidate manifest hash is stale; run scripts/generate_composed_transform_probe.py"
        )
    if composed_probe.get("base_manifest_sha256") != generate_composed_transform_probe.base_manifest_hash():
        fail("docs/composed_transform_probe.json base manifest hash is stale")
    if (
        composed_probe.get("selected_periodic_manifest_sha256")
        != generate_composed_transform_probe.selected_periodic_manifest_hash()
    ):
        fail("docs/composed_transform_probe.json selected periodic manifest hash is stale")
    if composed_probe.get("source_hashes") != generate_composed_transform_probe.source_hashes():
        fail("docs/composed_transform_probe.json source hashes are stale")
    if composed_probe.get("candidate_count") != len(
        generate_composed_transform_probe.candidate_manifest()
    ):
        fail("docs/composed_transform_probe.json candidate count is stale")
    expected_composed_rows = len(
        generate_composed_transform_probe.VALIDATION_CORPORA
    ) * composed_probe.get("selected_transform_count", 0)
    if len(composed_probe.get("validation_results", [])) != expected_composed_rows:
        fail("docs/composed_transform_probe.json does not contain the full validation matrix")
    composed_probe_text = texts["docs/COMPOSED_TRANSFORM_PROBE.md"]
    for phrase in (
        "composed context+periodic",
        "Held-out corpora with prefix >=5 uplift",
        "Held-out exact hits",
        "not `.tlmr` format support",
    ):
        if phrase not in composed_probe_text:
            fail(f"docs/COMPOSED_TRANSFORM_PROBE.md missing {phrase}")

    corpus_matrix = json.loads(texts["docs/corpus_matrix.json"])
    if corpus_matrix.get("generated_by") != "scripts/generate_corpus_matrix.py":
        fail("docs/corpus_matrix.json is not marked as generated by scripts/generate_corpus_matrix.py")
    if corpus_matrix.get("corpus_manifest_sha256") != generate_corpus_matrix.corpus_manifest_hash():
        fail("docs/corpus_matrix.json corpus matrix hash is stale; run scripts/generate_corpus_matrix.py")
    expected_corpus = [case["name"] for case in generate_corpus_matrix.CORPUS_MATRIX]
    actual_corpus = [row.get("name") for row in corpus_matrix.get("results", [])]
    if actual_corpus != expected_corpus:
        fail("docs/corpus_matrix.json does not contain the full generated corpus matrix")
    control_kinds = {row.get("control_kind") for row in corpus_matrix.get("results", [])}
    for required in ("shadow-vocab", "binary-tlv", "binary-varint"):
        if required not in control_kinds:
            fail(f"docs/corpus_matrix.json missing {required} control")
    if any(
        row.get("lexeme_overlap_rate", 1.0) != 0.0
        for row in corpus_matrix.get("results", [])
        if row.get("control_kind") == "shadow-vocab"
    ):
        fail("docs/corpus_matrix.json shadow-vocab controls must have zero semantic lexeme overlap")
    missing_from_corpus_md = [
        name for name in expected_corpus if name not in texts["docs/CORPUS_MATRIX.md"]
    ]
    if missing_from_corpus_md:
        fail(f"docs/CORPUS_MATRIX.md missing generated corpus cases: {', '.join(missing_from_corpus_md)}")
    for phrase in ("vocabulary-disjoint", "TLV/varint controls"):
        if phrase not in texts["docs/CORPUS_MATRIX.md"]:
            fail(f"docs/CORPUS_MATRIX.md missing {phrase}")
    generate_corpus_generalization_probe.check_report()

    acceleration = json.loads(texts["docs/acceleration_report.json"])
    if acceleration.get("generated_by") != "scripts/generate_acceleration_report.py":
        fail("docs/acceleration_report.json is not marked as generated by scripts/generate_acceleration_report.py")
    expected_accel_hashes = {
        path: generate_acceleration_report.sha256(path)
        for path in generate_acceleration_report.SOURCE_FILES
    }
    if acceleration.get("source_hashes") != expected_accel_hashes:
        fail("docs/acceleration_report.json source hashes are stale; run scripts/generate_acceleration_report.py")
    if acceleration.get("detected", {}).get("production_ready") is not False:
        fail("docs/acceleration_report.json must not claim production-ready acceleration")
    acceleration_text = texts["docs/ACCELERATION.md"]
    for phrase in ("research-only-cpu-semantics", "Real kernel detected", "Promotion Criteria"):
        if phrase not in acceleration_text:
            fail(f"docs/ACCELERATION.md missing {phrase}")

    theory = json.loads(texts["docs/theory.json"])
    if theory.get("generated_by") != "scripts/generate_theory_report.py":
        fail("docs/theory.json is not marked as generated by scripts/generate_theory_report.py")
    if theory.get("artifact_hashes") != generate_theory_report.build_report()["artifact_hashes"]:
        fail("docs/theory.json artifact hashes are stale; run scripts/generate_theory_report.py")
    theory_text = texts["docs/THEORY.md"]
    for phrase in (
        "expected_hits = candidate_spans",
        "Minimum Profitable Frontier",
        "Structured Expectations",
        "near-zero random exact-prefix hit",
    ):
        if phrase not in theory_text:
            fail(f"docs/THEORY.md missing {phrase}")

    manifold = json.loads(texts["docs/manifold.json"])
    if manifold.get("generated_by") != "scripts/generate_manifold_report.py":
        fail("docs/manifold.json is not marked as generated by scripts/generate_manifold_report.py")
    if manifold.get("case_manifest_sha256") != generate_manifold_report.case_manifest_hash():
        fail("docs/manifold.json case manifest hash is stale; run scripts/generate_manifold_report.py")
    expected_manifold = [case["name"] for case in generate_manifold_report.MANIFOLD_CASES]
    actual_manifold = [row.get("name") for row in manifold.get("results", [])]
    if actual_manifold != expected_manifold:
        fail("docs/manifold.json does not contain the full manifold case matrix")
    manifold_text = texts["docs/MANIFOLD.md"]
    for phrase in (
        "diagnostic, not a compression benchmark",
        "Generated Prefix Set",
        "Proximity Matrix",
        "planted positive control",
    ):
        if phrase not in manifold_text:
            fail(f"docs/MANIFOLD.md missing {phrase}")

    nearmiss = json.loads(texts["docs/nearmiss_forecast.json"])
    if nearmiss.get("generated_by") != "scripts/generate_nearmiss_forecast.py":
        fail("docs/nearmiss_forecast.json is not marked as generated by scripts/generate_nearmiss_forecast.py")
    if nearmiss.get("artifact_hashes") != generate_nearmiss_forecast.build_report()["artifact_hashes"]:
        fail("docs/nearmiss_forecast.json artifact hashes are stale; run scripts/generate_nearmiss_forecast.py")
    nearmiss_text = texts["docs/NEARMISS_FORECAST.md"]
    for phrase in (
        "random-suffix forecast",
        "Best Non-Planted Forecast",
        "excludes planted positive controls",
        "GiB for one expected exact hit",
        "Exact 8-byte seed-span hits remain",
    ):
        if phrase not in nearmiss_text:
            fail(f"docs/NEARMISS_FORECAST.md missing {phrase}")

    prefix_ladder = json.loads(texts["docs/prefix_ladder.json"])
    if prefix_ladder.get("generated_by") != "scripts/generate_prefix_ladder.py":
        fail("docs/prefix_ladder.json is not marked as generated by scripts/generate_prefix_ladder.py")
    if prefix_ladder.get("artifact_hashes") != generate_prefix_ladder.build_report()["artifact_hashes"]:
        fail("docs/prefix_ladder.json artifact hashes are stale; run scripts/generate_prefix_ladder.py")
    prefix_ladder_text = texts["docs/PREFIX_LADDER.md"]
    for phrase in (
        "where near misses stop",
        "Top Held-Out Ladders",
        "prefix >=5",
        "position-specific fifth-byte survival",
    ):
        if phrase not in prefix_ladder_text:
            fail(f"docs/PREFIX_LADDER.md missing {phrase}")

    generate_depth3_prefix_probe.check_report()
    generate_depth3_compression_followup.check_report()

    fifth_byte = json.loads(texts["docs/fifth_byte_residual.json"])
    if fifth_byte.get("generated_by") != "scripts/generate_fifth_byte_residual.py":
        fail(
            "docs/fifth_byte_residual.json is not marked as generated by scripts/generate_fifth_byte_residual.py"
        )
    if fifth_byte.get("artifact_hashes") != generate_fifth_byte_residual.artifact_hashes():
        fail("docs/fifth_byte_residual.json artifact hashes are stale; run scripts/generate_fifth_byte_residual.py")
    fifth_byte_text = texts["docs/FIFTH_BYTE_RESIDUAL.md"]
    for phrase in (
        "prefix-4 near misses",
        "Residual Matrix",
        "simple one-byte mask",
        "does not add `.tlmr` transform metadata",
    ):
        if phrase not in fifth_byte_text:
            fail(f"docs/FIFTH_BYTE_RESIDUAL.md missing {phrase}")

    fifth_steering = json.loads(texts["docs/fifth_byte_steering.json"])
    if fifth_steering.get("generated_by") != "scripts/generate_fifth_byte_steering.py":
        fail(
            "docs/fifth_byte_steering.json is not marked as generated by scripts/generate_fifth_byte_steering.py"
        )
    expected_steering_candidates = generate_fifth_byte_steering.candidate_manifest(fifth_byte)
    if fifth_steering.get("artifact_hashes") != generate_fifth_byte_steering.artifact_hashes():
        fail("docs/fifth_byte_steering.json artifact hashes are stale; run scripts/generate_fifth_byte_steering.py")
    if fifth_steering.get("candidate_manifest_sha256") != generate_fifth_byte_steering.candidate_manifest_hash(
        expected_steering_candidates
    ):
        fail("docs/fifth_byte_steering.json candidate manifest hash is stale; run scripts/generate_fifth_byte_steering.py")
    fifth_steering_text = texts["docs/FIFTH_BYTE_STEERING.md"]
    for phrase in (
        "cross-corpus",
        "prefix >=5",
        "not `.tlmr` format support",
        "self-source movement is treated as overfit",
    ):
        if phrase not in fifth_steering_text:
            fail(f"docs/FIFTH_BYTE_STEERING.md missing {phrase}")

    generate_contextual_fifth_byte_steering.check_report()

    goal_audit = json.loads(texts["docs/goal_audit.json"])
    if goal_audit.get("generated_by") != "scripts/generate_goal_audit.py":
        fail("docs/goal_audit.json is not marked as generated by scripts/generate_goal_audit.py")
    if goal_audit.get("source_hashes") != generate_goal_audit.hashes(
        generate_goal_audit.SOURCE_PATHS
    ):
        fail("docs/goal_audit.json source hashes are stale; run scripts/generate_goal_audit.py")
    if goal_audit.get("artifact_hashes") != generate_goal_audit.hashes(
        generate_goal_audit.ARTIFACT_PATHS
    ):
        fail("docs/goal_audit.json artifact hashes are stale; run scripts/generate_goal_audit.py")
    if goal_audit.get("evidence_hashes") != generate_goal_audit.evidence_hashes(
        goal_audit.get("entries", [])
    ):
        fail("docs/goal_audit.json evidence hashes are stale; run scripts/generate_goal_audit.py")
    if goal_audit.get("missing_expected_results"):
        fail("docs/goal_audit.json is missing expected generated-result rows")
    goal_audit_text = texts["docs/GOAL_AUDIT.md"]
    for phrase in (
        "canonical requirement-to-evidence ledger",
        "architecture-implemented; research-viable; not production-proven",
        "Audit Matrix",
        "Unresolved Gates",
        "Held-out exact hits",
        "Grammar channel exact hits",
    ):
        if phrase not in goal_audit_text:
            fail(f"docs/GOAL_AUDIT.md missing {phrase}")

    experiment_queue = json.loads(texts["docs/experiment_queue.json"])
    if experiment_queue.get("generated_by") != "scripts/generate_experiment_queue.py":
        fail("docs/experiment_queue.json is not marked as generated by scripts/generate_experiment_queue.py")
    if experiment_queue.get("artifact_hashes") != generate_experiment_queue.artifact_hashes():
        fail("docs/experiment_queue.json artifact hashes are stale; run scripts/generate_experiment_queue.py")
    if not experiment_queue.get("items"):
        fail("docs/experiment_queue.json contains no queue items")
    experiment_queue_text = texts["docs/EXPERIMENT_QUEUE.md"]
    for phrase in (
        "Ready experiments",
        "Blocked by evidence",
        "promotion gate",
        "stop rule",
        "do not spend on gated compute",
    ):
        if phrase not in experiment_queue_text:
            fail(f"docs/EXPERIMENT_QUEUE.md missing {phrase}")

    generate_research_decision.check_report()
    generate_research_frontier.check_report()
    generate_natural_corpus_proof_matrix.check_report()
    generate_natural_corpus_reopen_manifest.check_report()
    generate_external_corpus_accession.check_report()
    generate_frozen_rank_coded_span_generator.check_report()
    generate_production_proof_matrix.check_report()
    generate_research_team_protocol.check_report()
    generate_goal_completion_audit.check_report()
    generate_blocked_requirement_dispatch.check_report()
    generate_research_hypotheses.check_report()
    generate_research_team_packet.check_report()
    generate_research_agent_prompts.check_report()
    generate_research_agent_result_intake.check_report()
    generate_claim_boundary_audit.check_report()

    scorecard = json.loads(texts["docs/research_scorecard.json"])
    if scorecard.get("generated_by") != "scripts/generate_research_scorecard.py":
        fail("docs/research_scorecard.json is not marked as generated by scripts/generate_research_scorecard.py")
    if scorecard.get("artifact_hashes") != generate_research_scorecard.artifact_hashes():
        fail("docs/research_scorecard.json artifact hashes are stale; run scripts/generate_research_scorecard.py")
    scorecard_text = texts["docs/RESEARCH_SCORECARD.md"]
    for phrase in (
        "Overall research status",
        "Raw structured corpus",
        "Depth-3 prefix frontier",
        "Depth-3 frontier exact discovery",
        "Depth-4 shard plan",
        "Corpus generalization probe",
        "Selected-lead depth-3 follow-up",
        "Manifold proximity",
        "Transform/preconditioner path",
        "Transform probe",
        "Transform validation",
        "Composed transform probe",
        "Contextual fifth-byte steering",
        "Grammar channel match discovery",
        "Near-miss forecast",
    ):
        if phrase not in scorecard_text:
            fail(f"docs/RESEARCH_SCORECARD.md missing {phrase}")

    viability = json.loads(texts["docs/viability.json"])
    if viability.get("generated_by") != "scripts/generate_viability.py":
        fail("docs/viability.json is not marked as generated by scripts/generate_viability.py")
    if viability.get("artifact_hashes") != generate_viability.artifact_hashes():
        fail("docs/viability.json artifact hashes are stale; run scripts/generate_viability.py")
    viability_text = texts["docs/VIABILITY.md"]
    for phrase in (
        "research-viable, not production-proven",
        "Structured and binary controls do not yet show natural-corpus wins",
        "Depth-3 search can move a few held-out prefix frontiers",
        "Depth-3 frontier exact discovery found prefix movement only",
        "Depth-4 search is sharded and explicitly gated",
        "Grammar/channel discovery did not yet produce exact seed-span rows",
        "Corpus generalization controls did not produce exact seed-span rows",
        "Selected-lead depth-3 compression follow-up stayed null",
        "bounded depth-3 compression follow-up",
        "Context-conditioned fifth-byte steering",
    ):
        if phrase not in viability_text:
            fail(f"docs/VIABILITY.md missing {phrase}")

    for test_file in (ROOT / "tests").rglob("*.rs"):
        if "#[ignore" in test_file.read_text(encoding="utf-8"):
            fail(f"{test_file.relative_to(ROOT)} contains #[ignore]")

    if (ROOT / "error.log").exists():
        fail("tracked junk artifact error.log still exists")

    print("Doc lint passed")


if __name__ == "__main__":
    main()
