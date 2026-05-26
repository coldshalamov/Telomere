#!/usr/bin/env python3
"""Generate an implementation and research-goal audit for Telomere."""

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

GOAL_AUDIT_JSON = DOCS / "goal_audit.json"
GOAL_AUDIT_MD = DOCS / "GOAL_AUDIT.md"

ARTIFACT_PATHS = {
    "results_sha256": DOCS / "results.json",
    "sweeps_sha256": DOCS / "sweeps.json",
    "viability_sha256": DOCS / "viability.json",
    "research_scorecard_sha256": DOCS / "research_scorecard.json",
    "corpus_matrix_sha256": DOCS / "corpus_matrix.json",
    "corpus_generalization_probe_sha256": DOCS / "corpus_generalization_probe.json",
    "heldout_corpus_expansion_sha256": DOCS / "heldout_corpus_expansion.json",
    "transform_validation_sha256": DOCS / "transform_validation.json",
    "periodic_transform_probe_sha256": DOCS / "periodic_transform_probe.json",
    "composed_transform_probe_sha256": DOCS / "composed_transform_probe.json",
    "nearmiss_forecast_sha256": DOCS / "nearmiss_forecast.json",
    "prefix_ladder_sha256": DOCS / "prefix_ladder.json",
    "depth3_prefix_probe_sha256": DOCS / "depth3_prefix_probe.json",
    "depth3_compression_followup_sha256": DOCS / "depth3_compression_followup.json",
    "lead_depth3_prefix_probe_sha256": DOCS / "lead_depth3_prefix_probe.json",
    "lead_depth3_compression_followup_sha256": DOCS / "lead_depth3_compression_followup.json",
    "depth3_frontier_exact_discovery_sha256": DOCS / "depth3_frontier_exact_discovery.json",
    "depth4_shard_plan_sha256": DOCS / "depth4_shard_plan.json",
    "depth4_pilot_shard_sha256": DOCS / "depth4_pilot_shard.json",
    "search_frontier_gate_sha256": DOCS / "search_frontier_gate.json",
    "mechanism_experiment_ranking_sha256": DOCS / "mechanism_experiment_ranking.json",
    "seed_table_preset_probe_sha256": DOCS / "seed_table_preset_probe.json",
    "exact_short_hit_bundle_economics_sha256": DOCS
    / "exact_short_hit_bundle_economics.json",
    "whole_stream_residual_vector_probe_sha256": DOCS
    / "whole_stream_residual_vector_probe.json",
    "expander_salt_ensemble_sha256": DOCS / "expander_salt_ensemble.json",
    "schema_native_public_dictionaries_sha256": DOCS
    / "schema_native_public_dictionaries.json",
    "schema_native_public_dictionary_replication_sha256": DOCS
    / "schema_native_public_dictionary_replication.json",
    "superposition_telemetry_sha256": DOCS / "superposition_telemetry.json",
    "long_span_bundle_gate_sha256": DOCS / "long_span_bundle_gate.json",
    "recursive_structured_fixtures_sha256": DOCS / "recursive_structured_fixtures.json",
    "scale_performance_report_sha256": DOCS / "scale_performance_report.json",
    "ui_workflow_smoke_sha256": DOCS / "ui_workflow_smoke.json",
    "fifth_byte_steering_sha256": DOCS / "fifth_byte_steering.json",
    "contextual_fifth_byte_steering_sha256": DOCS / "contextual_fifth_byte_steering.json",
    "structural_transform_search_sha256": DOCS / "structural_transform_search.json",
    "byte_permutation_transform_search_sha256": DOCS / "byte_permutation_transform_search.json",
    "bwt_mtf_transform_probe_sha256": DOCS / "bwt_mtf_transform_probe.json",
    "grammar_channel_match_discovery_sha256": DOCS / "grammar_channel_match_discovery.json",
    "numeric_value_channel_match_discovery_sha256": DOCS
    / "numeric_value_channel_match_discovery.json",
    "record_context_transform_search_sha256": DOCS / "record_context_transform_search.json",
    "token_dictionary_transform_search_sha256": DOCS / "token_dictionary_transform_search.json",
    "affine_transform_search_sha256": DOCS / "affine_transform_search.json",
    "seed_manifold_residual_steering_sha256": DOCS / "seed_manifold_residual_steering.json",
    "sidecar_break_even_sha256": DOCS / "sidecar_break_even.json",
    "residual_payload_compressibility_sha256": DOCS / "residual_payload_compressibility.json",
    "experimental_sidecar_descriptor_sha256": DOCS / "experimental_sidecar_descriptor.json",
    "sidecar_record_overhead_sha256": DOCS / "sidecar_record_overhead.json",
    "packed_sidecar_descriptor_sha256": DOCS / "packed_sidecar_descriptor.json",
    "packed_sidecar_controls_sha256": DOCS / "packed_sidecar_controls.json",
    "generalized_packed_sidecar_sha256": DOCS / "generalized_packed_sidecar.json",
    "packed_sidecar_replication_sha256": DOCS / "packed_sidecar_replication.json",
    "match_discovery_sha256": DOCS / "match_discovery.json",
    "alignment_arity_discovery_sha256": DOCS / "alignment_arity_discovery.json",
    "transformed_match_discovery_sha256": DOCS / "transformed_match_discovery.json",
    "lead_exact_discovery_sha256": DOCS / "lead_exact_discovery.json",
    "acceleration_report_sha256": DOCS / "acceleration_report.json",
}

SOURCE_PATHS = {
    "cargo_toml_sha256": ROOT / "Cargo.toml",
    "main_cli_sha256": ROOT / "src/main.rs",
    "lib_sha256": ROOT / "src/lib.rs",
    "compress_sha256": ROOT / "src/compress.rs",
    "config_sha256": ROOT / "src/config.rs",
    "v1_header_sha256": ROOT / "src/tlmr.rs",
    "v2_format_sha256": ROOT / "src/tlmr_v2.rs",
    "indexed_engine_sha256": ROOT / "src/indexed.rs",
    "streaming_engine_sha256": ROOT / "src/streaming.rs",
    "seed_index_sha256": ROOT / "src/seed_expansion_index.rs",
    "gpu_sha256": ROOT / "src/gpu.rs",
    "whitepaper_sha256": DOCS / "Telomere Whitepaper V2.md",
    "tauri_host_sha256": ROOT / "src-tauri/src/main.rs",
    "ui_index_sha256": ROOT / "ui/index.html",
    "ui_readme_sha256": ROOT / "ui/README.md",
    "cli_tests_sha256": ROOT / "tests/cli_tests.rs",
    "indexed_v2_tests_sha256": ROOT / "tests/indexed_v2.rs",
    "streaming_tests_sha256": ROOT / "tests/streaming.rs",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hashes(paths: dict[str, Path]) -> dict[str, str]:
    return {name: sha256(path) for name, path in paths.items()}


def evidence_hashes(entries: list[dict[str, Any]]) -> dict[str, str]:
    evidence_paths = sorted(
        {path for item in entries for path in item.get("evidence", [])}
    )
    output: dict[str, str] = {}
    for evidence_path in evidence_paths:
        full_path = ROOT / evidence_path
        if not full_path.exists():
            raise RuntimeError(f"goal audit evidence path does not exist: {evidence_path}")
        output[f"{evidence_path}_sha256"] = sha256(full_path)
    return output


def has_result(results: dict[str, Any], name: str) -> bool:
    return any(row.get("name") == name for row in results.get("results", []))


def card_by_area(scorecard: dict[str, Any], area: str) -> dict[str, Any]:
    for card in scorecard.get("cards", []):
        if card.get("area") == area:
            return card
    raise KeyError(area)


def entry(
    section: str,
    requirement: str,
    status: str,
    evidence: list[str],
    finding: str,
    remaining_gate: str,
) -> dict[str, Any]:
    return {
        "section": section,
        "requirement": requirement,
        "status": status,
        "evidence": evidence,
        "finding": finding,
        "remaining_gate": remaining_gate,
    }


def build_audit() -> dict[str, Any]:
    results = load_json(DOCS / "results.json")
    sweeps = load_json(DOCS / "sweeps.json")
    viability = load_json(DOCS / "viability.json")
    scorecard = load_json(DOCS / "research_scorecard.json")
    corpus = load_json(DOCS / "corpus_matrix.json")
    corpus_generalization = load_json(DOCS / "corpus_generalization_probe.json")
    heldout_corpus_expansion = load_json(DOCS / "heldout_corpus_expansion.json")
    transform_validation = load_json(DOCS / "transform_validation.json")
    periodic = load_json(DOCS / "periodic_transform_probe.json")
    composed = load_json(DOCS / "composed_transform_probe.json")
    nearmiss = load_json(DOCS / "nearmiss_forecast.json")
    prefix_ladder = load_json(DOCS / "prefix_ladder.json")
    depth3_prefix = load_json(DOCS / "depth3_prefix_probe.json")
    depth3_followup = load_json(DOCS / "depth3_compression_followup.json")
    lead_depth3_prefix = load_json(DOCS / "lead_depth3_prefix_probe.json")
    lead_depth3_followup = load_json(DOCS / "lead_depth3_compression_followup.json")
    depth3_frontier = load_json(DOCS / "depth3_frontier_exact_discovery.json")
    depth4_shard_plan = load_json(DOCS / "depth4_shard_plan.json")
    depth4_pilot = load_json(DOCS / "depth4_pilot_shard.json")
    search_frontier_gate = load_json(DOCS / "search_frontier_gate.json")
    mechanism_experiment_ranking = load_json(
        DOCS / "mechanism_experiment_ranking.json"
    )
    seed_table_preset_probe = load_json(DOCS / "seed_table_preset_probe.json")
    exact_short_hit_bundle_economics = load_json(
        DOCS / "exact_short_hit_bundle_economics.json"
    )
    whole_stream_residual_vector_probe = load_json(
        DOCS / "whole_stream_residual_vector_probe.json"
    )
    expander_salt_ensemble = load_json(DOCS / "expander_salt_ensemble.json")
    schema_native_public_dictionaries = load_json(
        DOCS / "schema_native_public_dictionaries.json"
    )
    schema_native_public_dictionary_replication = load_json(
        DOCS / "schema_native_public_dictionary_replication.json"
    )
    superposition_telemetry = load_json(DOCS / "superposition_telemetry.json")
    long_span_bundle_gate = load_json(DOCS / "long_span_bundle_gate.json")
    recursive_structured_fixtures = load_json(
        DOCS / "recursive_structured_fixtures.json"
    )
    scale_performance = load_json(DOCS / "scale_performance_report.json")
    ui_workflow_smoke = load_json(DOCS / "ui_workflow_smoke.json")
    fifth_steering = load_json(DOCS / "fifth_byte_steering.json")
    contextual_steering = load_json(DOCS / "contextual_fifth_byte_steering.json")
    structural_search = load_json(DOCS / "structural_transform_search.json")
    byte_permutation_search = load_json(DOCS / "byte_permutation_transform_search.json")
    bwt_mtf_probe = load_json(DOCS / "bwt_mtf_transform_probe.json")
    grammar_channel_discovery = load_json(DOCS / "grammar_channel_match_discovery.json")
    numeric_value_channel_discovery = load_json(
        DOCS / "numeric_value_channel_match_discovery.json"
    )
    record_context_search = load_json(DOCS / "record_context_transform_search.json")
    token_dictionary_search = load_json(DOCS / "token_dictionary_transform_search.json")
    affine_search = load_json(DOCS / "affine_transform_search.json")
    residual_steering = load_json(DOCS / "seed_manifold_residual_steering.json")
    sidecar_break_even = load_json(DOCS / "sidecar_break_even.json")
    residual_payload_compressibility = load_json(
        DOCS / "residual_payload_compressibility.json"
    )
    experimental_sidecar_descriptor = load_json(
        DOCS / "experimental_sidecar_descriptor.json"
    )
    sidecar_record_overhead = load_json(DOCS / "sidecar_record_overhead.json")
    packed_sidecar_descriptor = load_json(DOCS / "packed_sidecar_descriptor.json")
    packed_sidecar_controls = load_json(DOCS / "packed_sidecar_controls.json")
    generalized_packed_sidecar = load_json(DOCS / "generalized_packed_sidecar.json")
    packed_sidecar_replication = load_json(DOCS / "packed_sidecar_replication.json")
    match_discovery = load_json(DOCS / "match_discovery.json")
    alignment_arity_discovery = load_json(DOCS / "alignment_arity_discovery.json")
    transformed_match_discovery = load_json(DOCS / "transformed_match_discovery.json")
    lead_exact_discovery = load_json(DOCS / "lead_exact_discovery.json")
    acceleration = load_json(DOCS / "acceleration_report.json")

    result_names = {row.get("name") for row in results.get("results", [])}
    scale_rows = [
        row for row in sweeps.get("results", []) if row.get("group") == "memory-scaling"
    ]
    largest_scale = max(scale_rows, key=lambda row: row["input_bytes"], default=None)
    largest_scale_mib = (
        f"{largest_scale['input_bytes'] / (1024 * 1024):.0f} MiB"
        if largest_scale
        else "no"
    )
    viability_entries = viability.get("entries", [])
    viability_status_counts = Counter(entry["status"] for entry in viability_entries)
    scorecard_status_counts = Counter(card["status"] for card in scorecard.get("cards", []))
    corpus_generalization_summary = corpus_generalization["summary"]
    heldout_expansion_summary = heldout_corpus_expansion["summary"]
    validation_summary = transform_validation["summary"]
    periodic_summary = periodic["summary"]
    composed_summary = composed["summary"]
    nearmiss_summary = nearmiss["summary"]
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
    steering_summary = fifth_steering["summary"]
    contextual_summary = contextual_steering["summary"]
    structural_summary = structural_search["summary"]
    byte_permutation_summary = byte_permutation_search["summary"]
    bwt_mtf_summary = bwt_mtf_probe["summary"]
    grammar_channel_summary = grammar_channel_discovery["summary"]
    numeric_value_channel_summary = numeric_value_channel_discovery["summary"]
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

    entries = [
        entry(
            "canonical-architecture",
            "Define what Telomere is now, what Lotus means here, and what is explicitly gone.",
            "complete",
            [
                "docs/ARCHITECTURE.md",
                "docs/FORMAT.md",
                "docs/TOOLS.md",
                "docs/Telomere Whitepaper V2.md",
            ],
            "The active architecture separates stable v1, experimental v2, and removed gloss/bloom/fuzz/hash-table stubs.",
            "Keep doc lint rejecting stale claims and removed components.",
        ),
        entry(
            "canonical-architecture",
            "Replace README with a current user guide and make FORMAT.md the source of truth.",
            "complete",
            ["README.md", "docs/FORMAT.md", "scripts/doc_lint.py"],
            "The README documents real CLI flags, limits, and honest performance tiers; FORMAT.md owns v1/v2 wire contracts.",
            "Update both when the CLI or wire format changes.",
        ),
        entry(
            "format-v1",
            "Decide and implement the header strategy for hasher kind, Lotus preset/version, layer count, lengths, and hash.",
            "complete",
            ["src/tlmr.rs", "tests/tlmr_header.rs", "docs/FORMAT.md"],
            "v1 uses a variable-length Lotus bit-stream header (J3D2 for general fields, J1D1 for arity) written after a 5-byte raw TLMR magic + version prefix, and the selected hasher is authoritative during decompression.",
            "Do not emit recursive v1 output; use v2 for recursive layers.",
        ),
        entry(
            "format-v1",
            "Reject or formally support non-byte-aligned seed payloads.",
            "complete",
            ["src/tlmr.rs", "src/lib.rs", "tests/decompress.rs", "docs/FORMAT.md"],
            "v1 records carry a Lotus J1D1 arity discriminator and (for compressed records) a Lotus J3D2 bit-aligned seed index; literal records pad to a byte boundary before their raw block bytes. Invalid or truncated payloads are rejected.",
            "Any change to the bit-stream layout needs a new format version and golden vectors.",
        ),
        entry(
            "format-v2",
            "Keep v1 stable and make v2 explicit experimental indexed/multi-layer format.",
            "complete",
            ["src/tlmr_v2.rs", "tests/indexed_v2.rs", "tests/streaming.rs", "docs/FORMAT.md"],
            "v2 has recursive layer descriptors, seed-span records, literal records, hasher metadata, and index-free decode.",
            "Treat v2 compatibility as experimental until a release checklist promotes it.",
        ),
        entry(
            "multi-pass",
            "Fix multi-pass semantics so decompression is unambiguous.",
            "complete",
            ["src/compress.rs", "src/tlmr_v2.rs", "tests/indexed_v2.rs", "tests/streaming.rs"],
            "v1 emits one-layer-decodable output; v2 records layer descriptors for recursive decode without an index.",
            "Do not add recursive superposition; selected layers only.",
        ),
        entry(
            "byte-accounting",
            "Ensure reported final_bytes always matches bytes actually written.",
            "complete",
            ["src/compress.rs", "src/main.rs", "tests/cli_tests.rs"],
            "Run summaries and CLI JSON report the encoded buffer length after the engine returns bytes.",
            "Keep CLI JSON tests tied to output file sizes.",
        ),
        entry(
            "lotus-codec",
            "Restore arity 2 and add compressor-level regression coverage.",
            "complete",
            ["src/header.rs", "tests/tlmr_header.rs", "docs/results.json"],
            "Lotus arity 2 is valid and the generated planted arity-2 result remains negative delta.",
            "Keep arity 2 out of reserved-marker space forever.",
        ),
        entry(
            "config",
            "Validate block_size, max_seed_len, max_arity, hash_bits, and memory limits.",
            "complete",
            ["src/config.rs", "src/tlmr_v2.rs", "tests/cli_tests.rs", "tests/indexed_v2.rs"],
            "Runtime and v2 search configs reject invalid sizes, hash bits, span lengths, and span-step settings.",
            "Add regression tests with every new tuning knob.",
        ),
        entry(
            "cleanup",
            "Remove slow default tests, broken fuzz targets, gloss/bloom stubs, disabled binaries, and junk artifacts.",
            "complete",
            ["Cargo.toml", "docs/TOOLS.md", ".gitignore", "scripts/doc_lint.py"],
            "The supported bin list is explicit, fuzz/hash-dump stubs are gone, gloss/bloom are removed or archived as absent, and logs/caches are ignored.",
            "Run doc lint and git status review before release.",
        ),
        entry(
            "gpu",
            "Decide GPU fate and keep the selected path buildable with parity tests.",
            "qualified",
            ["docs/ACCELERATION.md", "docs/adr/0002-gpu-acceleration-status.md", "tests/gpu_determinism.rs"],
            f"GPU status is {acceleration['detected']['status']}; the feature must compile, but no production kernel is claimed.",
            "Promote only after a real kernel beats CPU streaming under parity and benchmark gates.",
        ),
        entry(
            "cli-api",
            "Add index build/info/verify and engine/format dispatch while preserving v1 defaults.",
            "complete",
            ["src/main.rs", "tests/cli_tests.rs", "docs/FORMAT.md"],
            "CLI supports index build/info/verify, brute v1 default, indexed/streaming v2 opt-in, --json, --verify, --hasher, --memory-limit, --force, and v2 auto-decode.",
            "Keep v1 compatibility defaults unless the user explicitly selects v2 engines.",
        ),
        entry(
            "indexed-engine",
            "Build exact generated-prefix seed indexing with reusable/mmap tier backends.",
            "complete",
            ["src/seed_expansion_index.rs", "src/indexed.rs", "tests/indexed_v2.rs"],
            "The index records generated prefixes by tier, verifies hits by regenerating exact bytes, and rejects stale/cross-hasher manifests.",
            "Scale index build memory and IO only after the streaming CPU path identifies valuable workloads.",
        ),
        entry(
            "streaming-engine",
            "Build stratified target span tables and seed-streaming lookup.",
            "complete",
            ["src/streaming.rs", "tests/streaming.rs", "docs/RESEARCH_PROGRAM.md"],
            "The streaming matcher groups raw target spans by tier, enumerates seeds once, checks generated prefixes across tiers, and verifies exact bytes before candidate emission.",
            "Extend only with evidence-driven transforms or better tier policies.",
        ),
        entry(
            "selection-model",
            "Replace lightweight pruning with deterministic candidate lattice and weighted non-overlap selection.",
            "complete",
            ["src/indexed.rs", "docs/CANDIDATE_LATTICE.md", "tests/indexed_v2.rs"],
            "Selected records collapse to ordinary v2 seed-span/literal records; decompression never needs candidate state.",
            "Keep superposition as telemetry and selection, not recursive format state.",
        ),
        entry(
            "tauri",
            "Wire the Tauri app to real indexed/v2/index-building workflows.",
            "qualified",
            [
                "src-tauri/src/main.rs",
                "ui/index.html",
                "ui/README.md",
                "docs/UI_WORKFLOW_SMOKE.md",
                "docs/ui_workflow_smoke.json",
                "scripts/generate_ui_workflow_smoke.py",
            ],
            (
                "The Tauri host exposes real index, compress, decompress, "
                "telemetry, and research-artifact summary commands; UI workflow "
                f"smoke covers {ui_workflow_summary['ui_evidence_key_count']} "
                "evidence keys with "
                f"{len(ui_workflow_summary['missing_tauri_fields'])} missing "
                "Tauri fields and "
                f"{len(ui_workflow_summary['missing_mock_fields'])} missing mock fields."
            ),
            "Add live desktop/browser smoke coverage before calling the UI production-ready.",
        ),
        entry(
            "generated-results",
            "Create generated benchmark/result scripts and honest results docs.",
            "complete",
            ["scripts/generate_results.py", "docs/RESULTS.md", "docs/results.json"],
            "Results are generated from CLI/engine runs and include planted, random, structured, binary, Kolyma, indexed, streaming, and recursive controls.",
            "Never hand-edit benchmark claims; regenerate artifacts.",
        ),
        entry(
            "planted-proof",
            "Add deterministic planted corpus proving the mechanism can produce negative delta.",
            "proved",
            ["docs/results.json", "docs/VIABILITY.md"],
            "Planted v1 arity2, indexed span8, and streaming span8 cases prove the mechanism when data contains generated spans.",
            "Do not generalize planted wins to natural corpora.",
        ),
        entry(
            "random-controls",
            "Remove stale claims that random controls are expected to shrink.",
            "proved",
            ["docs/RESULTS.md", "docs/RESEARCH_SCORECARD.md", "scripts/doc_lint.py"],
            "Random controls are expected to bloat; doc lint rejects the stale random-compression claim.",
            "Investigate any future random negative delta as suspicious until reproduced.",
        ),
        entry(
            "natural-corpus",
            "Find repeatable natural or transformed structured-corpus seed-span wins.",
            "blocked-by-evidence",
            [
                "docs/CORPUS_MATRIX.md",
                "docs/CORPUS_GENERALIZATION_PROBE.md",
                "docs/TRANSFORM_VALIDATION.md",
                "docs/COMPOSED_TRANSFORM_PROBE.md",
                "docs/RESEARCH_SCORECARD.md",
            ],
            (
                f"Current held-out validation has prefix>=4 uplift in "
                f"{validation_summary['heldout_prefix4_win_corpora']} corpora but "
                f"{validation_summary['heldout_exact_hits']} held-out exact hits; "
                f"corpus generalization controls found "
                f"{corpus_generalization_summary['rows_with_prefix_ge_5']} prefix>=5 rows and "
                f"{corpus_generalization_summary['total_exact_hits']} exact hits; "
                f"composed context+periodic probes have "
                f"{composed_summary['heldout_prefix5_win_corpora']} held-out prefix>=5 uplift corpora "
                f"and {composed_summary['heldout_exact_hits']} exact hits."
            ),
            "Promote only after repeatable prefix>=5 uplift or exact seed-span hits on held-out data.",
        ),
        entry(
            "heldout-corpus-expansion",
            "Audit deterministic replication corpora before mutating the expensive corpus matrix.",
            "qualified",
            [
                "docs/HELDOUT_CORPUS_EXPANSION.md",
                "docs/heldout_corpus_expansion.json",
                "scripts/generate_heldout_corpus_expansion.py",
            ],
            (
                f"{heldout_expansion_summary['corpus_count']} frozen replication corpora "
                f"({heldout_expansion_summary['ordinary_corpus_count']} ordinary, "
                f"{heldout_expansion_summary['control_corpus_count']} controls) are missing from both "
                f"the corpus matrix and transform validation. The raw expansion scanned "
                f"{heldout_expansion_summary['target_span_count']} spans and found "
                f"{heldout_expansion_summary['rows_with_prefix_ge_5']} prefix>=5 rows, "
                f"{heldout_expansion_summary['rows_with_exact_hits']} exact-hit rows, and "
                f"{heldout_expansion_summary['rows_with_selected_spans']} selected-span rows."
            ),
            "Promote these corpora into the canonical matrices only after a follow-up changes prefix>=5, exact-hit, or selected-span evidence.",
        ),
        entry(
            "composed-transform",
            "Test whether context/residual transforms and periodic masks work better when composed.",
            "blocked-by-evidence",
            ["docs/COMPOSED_TRANSFORM_PROBE.md", "docs/composed_transform_probe.json"],
            (
                f"{composed['candidate_count']} compositions selected "
                f"{composed['selected_transform_count']} discovery leads; held-out prefix>=5 uplift "
                f"{composed_summary['heldout_prefix5_win_corpora']} corpora and exact hits "
                f"{composed_summary['heldout_exact_hits']}."
            ),
            "Reject composition as a promotion path unless it produces held-out prefix>=5 or exact seed-span events.",
        ),
        entry(
            "near-miss-theory",
            "Model whether deeper search is compute-justified.",
            "qualified",
            [
                "docs/THEORY.md",
                "docs/NEARMISS_FORECAST.md",
                "docs/PREFIX_LADDER.md",
                "docs/DEPTH3_PREFIX_PROBE.md",
                "docs/DEPTH3_COMPRESSION_FOLLOWUP.md",
                "docs/LEAD_DEPTH3_PREFIX_PROBE.md",
                "docs/LEAD_DEPTH3_COMPRESSION_FOLLOWUP.md",
                "docs/DEPTH3_FRONTIER_EXACT_DISCOVERY.md",
            ],
            (
                f"Best non-planted case {nearmiss_summary['best_non_planted_case']} "
                f"needs about {nearmiss_summary['best_non_planted_gib_for_one_expected_hit']:.3e} GiB "
                "for one expected exact hit; held-out prefix>=5 rows remain "
                f"{ladder_summary['heldout_rows_with_prefix5']} at depth 2. "
                f"The depth-3 prefix probe found {depth3_summary['heldout_rows_with_prefix5_uplift']} "
                f"held-out prefix>=5 uplift rows and {depth3_summary['heldout_exact_hits']} exact hits; "
                f"the bounded compression follow-up found "
                f"{depth3_followup_summary['total_depth3_selected_spans']} selected spans. "
                f"The selected-lead follow-up found "
                f"{lead_depth3_followup_summary['total_depth3_selected_spans']} selected spans, and "
                f"frontier exact discovery found {depth3_frontier_summary['total_exact_hits']} exact hits."
            ),
            "Do not spend on depth-3+ broad sweeps until a narrow follow-up turns prefix movement into exact hits or compression.",
        ),
        entry(
            "depth3-prefix-frontier",
            "Test whether searching farther moves held-out near misses beyond the fifth-byte gate.",
            "qualified",
            [
                "docs/DEPTH3_PREFIX_PROBE.md",
                "docs/depth3_prefix_probe.json",
                "docs/DEPTH3_COMPRESSION_FOLLOWUP.md",
                "docs/depth3_compression_followup.json",
            ],
            (
                f"{depth3_summary['enumerated_seed_count']} depth-3 seeds were enumerated; "
                f"{depth3_summary['heldout_rows_with_prefix5_uplift']} held-out rows gained "
                f"prefix>=5 movement, but exact 8-byte hits remain "
                f"{depth3_summary['heldout_exact_hits']}. The compression follow-up deduped this to "
                f"{depth3_followup_summary['promoted_prefix_rows']} physical input and found "
                f"{depth3_followup_summary['total_depth3_selected_spans']} selected spans."
            ),
            "Keep broad depth-3 sweeps gated until a new lead produces exact hits or selected spans.",
        ),
        entry(
            "depth3-frontier-exact-discovery",
            "Enumerate the full depth-3 frontier on frozen depth-2 null/frontier rows before considering depth 4.",
            "blocked-by-evidence",
            [
                "docs/LEAD_DEPTH3_PREFIX_PROBE.md",
                "docs/LEAD_DEPTH3_COMPRESSION_FOLLOWUP.md",
                "docs/DEPTH3_FRONTIER_EXACT_DISCOVERY.md",
                "docs/depth3_frontier_exact_discovery.json",
            ],
            (
                f"Lead depth-3 prefix probe found "
                f"{lead_depth3_prefix_summary['rows_with_depth3_prefix5_uplift']} prefix>=5 uplift rows; "
                f"the lead compression follow-up selected "
                f"{lead_depth3_followup_summary['total_depth3_selected_spans']} spans. "
                f"Frontier exact discovery enumerated "
                f"{depth3_frontier_summary['enumerated_seed_count']} seeds over "
                f"{depth3_frontier_summary['frontier_rows']} rows and found "
                f"{depth3_frontier_summary['total_exact_hits']} exact hits, "
                f"{depth3_frontier_summary['total_selected_spans']} selected spans, and "
                f"{depth3_frontier_summary['metadata_profitable_rows']} metadata-profitable rows."
            ),
            "Keep depth 4 opt-in and sharded until this gate finds prefix>=6 movement, exact hits, or selected spans.",
        ),
        entry(
            "depth4-shard-plan",
            "Plan depth-4 as explicit deterministic shards with expected-hit math and stop rules.",
            "qualified",
            ["docs/DEPTH4_SHARD_PLAN.md", "docs/depth4_shard_plan.json"],
            (
                f"Depth-4 shard status is {depth4_gate['recommended_status']}; "
                f"estimated full incremental depth-4 time is "
                f"{depth4_estimates['estimated_incremental_depth4_hours']} hours; "
                f"exact-8 probability on the current frontier is "
                f"{depth4_estimates['exact8_probability_at_least_one']:.6g}."
            ),
            "Run only pilot shards until the promotion gate is met by stronger depth-3, transform, or corpus evidence.",
        ),
        entry(
            "depth4-pilot-shard",
            "Run bounded depth-4 pilot shards as generated evidence before considering full depth-4 execution.",
            "blocked-by-evidence",
            ["docs/DEPTH4_PILOT_SHARD.md", "docs/depth4_pilot_shard.json"],
            (
                f"{depth4_pilot_summary['pilot_shard_count']} pilot shard enumerated "
                f"{depth4_pilot_summary['enumerated_seed_count']} four-byte seeds; "
                f"prefix>=5 rows {depth4_pilot_summary['rows_with_depth4_prefix5']}; "
                f"prefix>=6 rows {depth4_pilot_summary['rows_with_depth4_prefix6']}; "
                f"exact hits {depth4_pilot_summary['total_exact_hits']}; "
                f"selected spans {depth4_pilot_summary['total_selected_spans']}."
            ),
            "Keep remaining depth-4 shards gated unless a pilot or upstream lead produces prefix>=6, exact hits, or selected spans.",
        ),
        entry(
            "search-frontier-gate",
            "Create a generated go/no-go gate before broad raw depth search or full depth-4 execution.",
            "qualified",
            [
                "docs/SEARCH_FRONTIER_GATE.md",
                "docs/search_frontier_gate.json",
                "scripts/generate_search_frontier_gate.py",
            ],
            (
                f"Search gate status is {search_gate_summary['recommended_status']}; "
                f"best non-planted forecast is "
                f"{search_gate_summary['best_non_planted_gib_for_one_expected_hit']} GiB "
                f"per expected exact hit; depth-4 exact-8 probability is "
                f"{search_gate_summary['depth4_exact8_probability']:.6g}; "
                f"selected span total is {search_gate_summary['selected_span_total']}; "
                f"{len(search_gate_summary['blocking_gates'])} of "
                f"{search_gate_summary['gate_count']} gates remain blocking."
            ),
            "Change this gate only when a generated artifact produces prefix>=6, exact hits, selected spans, or a materially better forecast.",
        ),
        entry(
            "mechanism-experiment-ranking",
            "Rank the next non-depth mechanism experiments from generated evidence.",
            "qualified",
            [
                "docs/MECHANISM_EXPERIMENT_RANKING.md",
                "docs/mechanism_experiment_ranking.json",
                "scripts/generate_mechanism_experiment_ranking.py",
            ],
            (
                f"Mechanism experiment ranking top lane is "
                f"{mechanism_ranking_summary['top_lane_id']}; "
                f"next artifact {mechanism_ranking_summary['top_next_artifact']}; "
                f"ready lanes {mechanism_ranking_summary['ready_count']}; "
                f"selected spans {mechanism_ranking_summary['selected_span_total']}; "
                f"natural-corpus compression proven "
                f"{mechanism_ranking_summary['natural_corpus_compression_proven']}."
            ),
            "Generate the seed-table preset probe before raw-depth escalation, format promotion, descriptor packing, or hardware acceleration.",
        ),
        entry(
            "seed-table-preset-probe",
            "Execute the top-ranked seed-table/Lotus preset evidence probe.",
            "blocked-by-evidence",
            [
                "docs/SEED_TABLE_PRESET_PROBE.md",
                "docs/seed_table_preset_probe.json",
                "scripts/generate_seed_table_preset_probe.py",
            ],
            (
                f"Seed-table preset probe selected "
                f"{seed_table_summary['canonical_selected_spans']} canonical spans; "
                f"ordinary held-out negative groups "
                f"{seed_table_summary['canonical_ordinary_heldout_negative_groups']}; "
                f"control negative groups "
                f"{seed_table_summary['canonical_control_negative_groups']}; "
                f"promotion met {seed_table_summary['promotion_met']}."
            ),
            "Do not promote a public Lotus preset unless ordinary held-out negative groups reach the gate and controls remain null.",
        ),
        entry(
            "exact-short-hit-bundle-economics",
            "Execute the exact short-hit bundle economics evidence probe.",
            "blocked-by-evidence",
            [
                "docs/EXACT_SHORT_HIT_BUNDLE_ECONOMICS.md",
                "docs/exact_short_hit_bundle_economics.json",
                "scripts/generate_exact_short_hit_bundle_economics.py",
            ],
            (
                f"Exact short-hit bundle economics reconstructed "
                f"{exact_short_summary['reconstructed_exact_hits']} verified hits; "
                f"zero-overhead best delta "
                f"{exact_short_summary['zero_overhead_best_delta_bytes']} bytes; "
                f"full-stream negative rows "
                f"{exact_short_summary['full_stream_negative_rows']}; "
                f"ordinary negative groups "
                f"{exact_short_summary['full_stream_ordinary_negative_groups']}; "
                f"control negative groups "
                f"{exact_short_summary['full_stream_control_negative_groups']}; "
                f"promotion met {exact_short_summary['promotion_met']}."
            ),
            "Do not promote span-3 hit bundling unless full-stream wins survive unrelated ordinary groups with null controls and non-comparable control density.",
        ),
        entry(
            "whole-stream-residual-vector-probe",
            "Execute the whole-stream residual-vector falsification probe.",
            "blocked-by-evidence",
            [
                "docs/WHOLE_STREAM_RESIDUAL_VECTOR_PROBE.md",
                "docs/whole_stream_residual_vector_probe.json",
                "scripts/generate_whole_stream_residual_vector_probe.py",
            ],
            (
                f"Whole-stream residual vector probe encoded "
                f"{whole_stream_summary['honest_encoded_rows']} honest rows; "
                f"exact decode rows {whole_stream_summary['decode_verified_rows']}; "
                f"honest full-stream negative rows "
                f"{whole_stream_summary['honest_full_stream_negative_rows']}; "
                f"ordinary held-out negative groups "
                f"{whole_stream_summary['ordinary_heldout_negative_groups']}; "
                f"control negative groups {whole_stream_summary['control_negative_groups']}; "
                f"promotion met {whole_stream_summary['promotion_met']}."
            ),
            "Do not continue residual-sidecar promotion unless whole-stream vector rows produce unrelated ordinary held-out wins with controls null.",
        ),
        entry(
            "expander-salt-ensemble",
            "Execute the expander salt/preset ensemble falsification probe.",
            "blocked-by-evidence",
            [
                "docs/EXPANDER_SALT_ENSEMBLE.md",
                "docs/expander_salt_ensemble.json",
                "scripts/generate_expander_salt_ensemble.py",
            ],
            (
                f"Expander salt ensemble tested "
                f"{expander_salt_summary['predeclared_salt_count']} predeclared salts; "
                f"salted exact hits {expander_salt_summary['salted_exact_hits']}; "
                f"salted expected exact hits "
                f"{expander_salt_summary['salted_expected_exact_hits']:.6g}; "
                f"random-trial multiplier exceeded "
                f"{expander_salt_summary['random_trial_multiplier_exceeded']}; "
                f"selected-span rows "
                f"{expander_salt_summary['salted_selected_span_rows']}; "
                f"full-stream negative rows "
                f"{expander_salt_summary['full_stream_negative_rows']}; "
                f"promotion met {expander_salt_summary['promotion_met']}."
            ),
            "Do not promote salted expanders unless they beat equivalent random trials and create full-stream ordinary held-out wins with null controls.",
        ),
        entry(
            "schema-native-public-dictionaries",
            "Execute the schema-native public dictionary preset probe.",
            "qualified",
            [
                "docs/SCHEMA_NATIVE_PUBLIC_DICTIONARIES.md",
                "docs/schema_native_public_dictionaries.json",
                "scripts/generate_schema_native_public_dictionaries.py",
            ],
            (
                f"Schema-native public dictionaries used "
                f"{schema_native_summary['public_entry_count']} frozen entries; "
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
                f"promotion met {schema_native_summary['promotion_met']}."
            ),
            "Treat this as public dictionary-preset evidence only until a format registry, compatibility rule, and non-synthetic replication path exist.",
        ),
        entry(
            "schema-native-public-dictionary-replication",
            "Replicate and harden the schema-native public dictionary result on frozen expansion corpora.",
            "qualified"
            if schema_replication_summary["promotion_met"]
            else "blocked-by-evidence",
            [
                "docs/SCHEMA_NATIVE_PUBLIC_DICTIONARY_REPLICATION.md",
                "docs/schema_native_public_dictionary_replication.json",
                "scripts/generate_schema_native_public_dictionary_replication.py",
            ],
            (
                f"Replication used {schema_replication_summary['corpus_count']} "
                f"frozen corpora; standards selected spans "
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
            "Do not promote a public dictionary registry or format-level support until paired shadow controls and external corpora separate cleanly.",
        ),
        entry(
            "superposition-telemetry",
            "Generate deterministic candidate-lattice telemetry with explained discarded candidates.",
            "qualified" if superposition_summary["promotion_met"] else "open",
            [
                "docs/SUPERPOSITION_TELEMETRY.md",
                "docs/superposition_telemetry.json",
                "scripts/generate_superposition_telemetry.py",
            ],
            (
                f"Superposition telemetry used "
                f"{superposition_summary['fixture_count']} fixtures and "
                f"{superposition_summary['candidate_count']} candidates; "
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
            "Keep the lattice decoder-invisible; this is selector telemetry, not recursive format state.",
        ),
        entry(
            "long-span-bundle-gate",
            "Gate broad long-span bundle sweeps before spending compute.",
            "qualified" if long_span_gate_summary["promotion_met"] else "blocked-by-evidence",
            [
                "docs/LONG_SPAN_BUNDLE_GATE.md",
                "docs/long_span_bundle_gate.json",
                "scripts/generate_long_span_bundle_gate.py",
            ],
            (
                f"Long-span bundle gate met "
                f"{long_span_gate_summary['gate_met_count']} of "
                f"{long_span_gate_summary['gate_count']} checks; "
                f"recommendation {long_span_gate_summary['recommendation']}; "
                f"selected spans {long_span_gate_summary['selected_span_total']}; "
                f"raw-suffix prefix "
                f"{long_span_gate_summary['max_observed_heldout_forced_prefix_len']}/"
                f"{long_span_gate_summary['minimum_raw_suffix_negative_prefix_len']}; "
                f"claim level {long_span_gate_summary['claim_level']}."
            ),
            "Do not run broad long-span bundle sweeps until the generated gate passes.",
        ),
        entry(
            "recursive-structured-fixtures",
            "Gate recursive v2 claims against ordinary structured fixtures, not planted offsets.",
            "qualified"
            if recursive_structured_summary["promotion_met"]
            else "blocked-by-evidence",
            [
                "docs/RECURSIVE_STRUCTURED_FIXTURES.md",
                "docs/recursive_structured_fixtures.json",
                "scripts/generate_recursive_structured_fixtures.py",
            ],
            (
                f"Recursive structured fixtures used "
                f"{recursive_structured_summary['fixture_count']} CLI-verified fixtures; "
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
            "Do not generalize recursive v2 gains unless ordinary non-offset fixtures produce verified later-layer container wins.",
        ),
        entry(
            "fifth-byte-steering",
            "Test whether residual fifth-byte masks make prefix ladders survive held-out data.",
            "blocked-by-evidence",
            [
                "docs/FIFTH_BYTE_RESIDUAL.md",
                "docs/FIFTH_BYTE_STEERING.md",
                "docs/CONTEXTUAL_FIFTH_BYTE_STEERING.md",
            ],
            (
                f"{steering_summary['candidate_count']} residual masks produced "
                f"{steering_summary['cross_prefix5_win_rows']} cross-corpus prefix>=5 win rows "
                f"and {steering_summary['cross_exact_hit_rows']} exact-hit rows; "
                f"contextual steering checked {contextual_summary['candidate_count']} masks and produced "
                f"{contextual_summary['cross_prefix5_win_rows']} cross-corpus prefix>=5 win rows."
            ),
            "Reject residual masks unless they generalize into prefix>=5 or exact hits.",
        ),
        entry(
            "contextual-fifth-byte-steering",
            "Test whether context-conditioned fifth-byte masks beat same-shape null controls.",
            "blocked-by-evidence",
            [
                "docs/CONTEXTUAL_FIFTH_BYTE_STEERING.md",
                "docs/contextual_fifth_byte_steering.json",
            ],
            (
                f"{contextual_summary['candidate_count']} contextual masks were checked over "
                f"{contextual_summary['heldout_cross_rows']} held-out cross rows; "
                f"prefix>=5 win rows {contextual_summary['cross_prefix5_win_rows']}, "
                f"exact-hit rows {contextual_summary['cross_exact_hit_rows']}, "
                f"null prefix>=5 win rows {contextual_summary['null_cross_prefix5_win_rows']}."
            ),
            "Reject contextual steering as a promotion path unless it beats null controls on held-out prefix>=5 or exact hits.",
        ),
        entry(
            "structural-transform-search",
            "Test bounded structural reversible transforms across held-out, shadow, and binary controls.",
            "blocked-by-evidence",
            [
                "docs/STRUCTURAL_TRANSFORM_SEARCH.md",
                "docs/structural_transform_search.json",
            ],
            (
                f"{structural_summary['candidate_count']} structural candidates over "
                f"{structural_summary['validation_rows']} validation rows produced "
                f"{structural_summary['heldout_prefix5_win_corpora']} held-out prefix>=5 win corpora, "
                f"{structural_summary['heldout_exact_hits']} held-out exact hits, "
                f"{structural_summary['shadow_prefix5_win_corpora']} shadow prefix>=5 win corpora, "
                f"and {structural_summary['binary_exact_hits']} binary exact hits."
            ),
            "Keep format-transform and broad depth work gated until structural or successor transforms produce repeatable promotion signals.",
        ),
        entry(
            "byte-permutation-transform-search",
            "Test finite seed-output byte-distribution alignment with reversible global and phase-local byte permutations.",
            "blocked-by-evidence",
            [
                "docs/BYTE_PERMUTATION_TRANSFORM_SEARCH.md",
                "docs/byte_permutation_transform_search.json",
            ],
            (
                f"{byte_permutation_summary['transform_count']} byte-permutation candidates over "
                f"{byte_permutation_summary['row_count']} rows produced "
                f"{byte_permutation_summary['rows_with_prefix_ge_5']} prefix>=5 rows, "
                f"{byte_permutation_summary['total_exact_hits']} exact hits, "
                f"{byte_permutation_summary['total_selected_spans']} selected spans, "
                f"and {byte_permutation_summary['rows_negative_after_metadata']} rows negative after metadata."
            ),
            "Treat byte-distribution alignment as null until it produces prefix>=5, exact hits, or metadata-profitable selected spans.",
        ),
        entry(
            "bwt-mtf-transform-probe",
            "Test bounded BWT/MTF/RLE classic preconditioners without counting transform-only shortening as Lotus evidence.",
            "blocked-by-evidence",
            [
                "docs/BWT_MTF_TRANSFORM_PROBE.md",
                "docs/bwt_mtf_transform_probe.json",
            ],
            (
                f"{bwt_mtf_summary['transform_count']} BWT/MTF/RLE candidates over "
                f"{bwt_mtf_summary['row_count']} rows produced "
                f"{bwt_mtf_summary['rows_with_prefix_ge_5']} prefix>=5 rows, "
                f"{bwt_mtf_summary['total_exact_hits']} exact hits, "
                f"{bwt_mtf_summary['total_selected_spans']} selected spans, "
                f"{bwt_mtf_summary['rows_negative_after_metadata']} rows negative after metadata, "
                f"and {bwt_mtf_summary['rows_with_shorter_transformed_payload']} shorter transformed-payload rows."
            ),
            "Treat BWT/MTF/RLE as null seed-span evidence unless it produces prefix>=5, exact hits, or metadata-profitable selected spans.",
        ),
        entry(
            "grammar-channel-match-discovery",
            "Test reversible grammar/channel streams with literal sidecars charged before promotion.",
            "blocked-by-evidence",
            [
                "docs/GRAMMAR_CHANNEL_MATCH_DISCOVERY.md",
                "docs/grammar_channel_match_discovery.json",
            ],
            (
                f"{grammar_channel_summary['channel_count']} grammar channels over "
                f"{grammar_channel_summary['row_count']} rows produced "
                f"{grammar_channel_summary['rows_with_prefix_ge_5']} prefix>=5 rows, "
                f"{grammar_channel_summary['total_exact_hits']} exact hits, "
                f"{grammar_channel_summary['total_selected_spans']} selected spans, "
                f"and {grammar_channel_summary['rows_negative_after_metadata']} rows negative after metadata."
            ),
            "Treat grammar-channel sidecar models as null until a parser-backed channel survives held-out/control promotion.",
        ),
        entry(
            "numeric-value-channel-match-discovery",
            "Test parsed numeric value streams with exact reconstruction metadata charged before promotion.",
            "blocked-by-evidence",
            [
                "docs/NUMERIC_VALUE_CHANNEL_MATCH_DISCOVERY.md",
                "docs/numeric_value_channel_match_discovery.json",
            ],
            (
                f"{numeric_value_channel_summary['channel_count']} numeric value channels over "
                f"{numeric_value_channel_summary['row_count']} rows parsed "
                f"{numeric_value_channel_summary['parsed_value_count']} values and produced "
                f"{numeric_value_channel_summary['rows_with_prefix_ge_5']} prefix>=5 rows, "
                f"{numeric_value_channel_summary['total_exact_hits']} exact hits, "
                f"{numeric_value_channel_summary['total_selected_spans']} selected spans, "
                f"and {numeric_value_channel_summary['rows_negative_after_metadata']} rows negative after metadata."
            ),
            "Treat parsed numeric value channels as null until exact seed spans survive full reconstruction metadata.",
        ),
        entry(
            "record-context-transform-search",
            "Test record/context-aware reversible transforms with metadata charged before promotion.",
            "blocked-by-evidence",
            [
                "docs/RECORD_CONTEXT_TRANSFORM_SEARCH.md",
                "docs/record_context_transform_search.json",
            ],
            (
                f"{record_context_summary['transform_count']} record/context candidates over "
                f"{record_context_summary['row_count']} rows produced "
                f"{record_context_summary['rows_with_prefix_ge_5']} prefix>=5 rows, "
                f"{record_context_summary['total_exact_hits']} exact hits, "
                f"{record_context_summary['total_selected_spans']} selected spans, "
                f"and {record_context_summary['rows_negative_after_metadata']} rows negative after metadata."
            ),
            "Treat the current record-context lane as null until exact seed spans appear after metadata.",
        ),
        entry(
            "token-dictionary-transform-search",
            "Test token/dictionary reversible transforms with dictionary metadata charged before promotion.",
            "blocked-by-evidence",
            [
                "docs/TOKEN_DICTIONARY_TRANSFORM_SEARCH.md",
                "docs/token_dictionary_transform_search.json",
            ],
            (
                f"{token_dictionary_summary['transform_count']} token/dictionary candidates over "
                f"{token_dictionary_summary['row_count']} rows produced "
                f"{token_dictionary_summary['rows_with_prefix_ge_5']} prefix>=5 rows, "
                f"{token_dictionary_summary['total_exact_hits']} exact hits, "
                f"{token_dictionary_summary['total_selected_spans']} selected spans, "
                f"and {token_dictionary_summary['rows_negative_after_metadata']} rows negative after metadata."
            ),
            "Treat the current token-dictionary lane as null until exact seed spans appear after metadata.",
        ),
        entry(
            "affine-transform-search",
            "Test reversible affine byte remaps as a stronger alphabet-alignment preconditioner.",
            "blocked-by-evidence",
            [
                "docs/AFFINE_TRANSFORM_SEARCH.md",
                "docs/affine_transform_search.json",
            ],
            (
                f"{affine_summary['searched_candidate_count']} affine candidates produced "
                f"{affine_summary['heldout_prefix4_win_corpora']} held-out prefix>=4 win corpora, "
                f"but {affine_summary['heldout_prefix5_win_corpora']} held-out prefix>=5 win corpora "
                f"and {affine_summary['heldout_exact_hits']} held-out exact hits."
            ),
            "Treat prefix-4 movement as a steering clue only; require residual-sidecar savings, prefix>=5, or exact hits before depth escalation.",
        ),
        entry(
            "seed-manifold-residual-steering",
            "Test whether forced exact seed spans plus residual sidecar bytes beat literal storage.",
            "blocked-by-evidence",
            [
                "docs/SEED_MANIFOLD_RESIDUAL_STEERING.md",
                "docs/seed_manifold_residual_steering.json",
            ],
            (
                f"{residual_summary['heldout_forced_rows']} held-out rows had forced exact spans, "
                f"{residual_summary['heldout_seed_contribution_positive_rows']} had positive seed contribution, "
                f"but {residual_summary['heldout_positive_rows']} held-out rows had negative net delta; "
                f"best held-out net delta was {residual_summary['best_heldout_net_delta_bytes']} bytes."
            ),
            "Do not promote residual steering until sidecar bytes plus metadata beat literal storage on held-out corpora.",
        ),
        entry(
            "sidecar-break-even",
            "Derive longer-span sidecar break-even rules before spending on more residual steering variants.",
            "qualified",
            [
                "docs/SIDECAR_BREAK_EVEN.md",
                "docs/sidecar_break_even.json",
            ],
            (
                f"{sidecar_break_even_summary['row_count']} break-even rows show raw-suffix "
                f"strict gain starts at prefix "
                f"{sidecar_break_even_summary['minimum_raw_suffix_negative_prefix_len']} while "
                f"current held-out forced prefixes stop at "
                f"{sidecar_break_even_summary['max_observed_heldout_forced_prefix_len']}; "
                f"raw-suffix viable rows at observed prefix "
                f"{sidecar_break_even_summary['raw_suffix_viable_at_observed_prefix_rows']} and "
                f"sublinear-model viable rows "
                f"{sidecar_break_even_summary['sublinear_model_viable_at_observed_prefix_rows']}."
            ),
            "Measure actual residual payload compressibility before promoting any sidecar format or engine variant.",
        ),
        entry(
            "residual-payload-compressibility",
            "Measure whether selected residual suffix bytes can be compressed enough to beat sidecar overhead.",
            "qualified",
            [
                "docs/RESIDUAL_PAYLOAD_COMPRESSIBILITY.md",
                "docs/residual_payload_compressibility.json",
            ],
            (
                f"{residual_payload_summary['heldout_payload_rows']} held-out payload rows "
                f"include {residual_payload_summary['measured_heldout_negative_rows']} measured "
                f"negative sidecar row; best case "
                f"{residual_payload_summary['best_measured_heldout_negative_case']}."
            ),
            "Prototype exact experimental descriptor decode for the zlib/LZMA signal before any format support claim.",
        ),
        entry(
            "experimental-sidecar-descriptor",
            "Prototype exact decode and corrupt rejection for the promoted residual payload sidecar signal.",
            "qualified",
            [
                "docs/EXPERIMENTAL_SIDECAR_DESCRIPTOR.md",
                "docs/experimental_sidecar_descriptor.json",
            ],
            (
                f"{experimental_sidecar_summary['prototype_rows']} descriptor rows decode and "
                f"reject corruption; full-stream negative rows "
                f"{experimental_sidecar_summary['full_stream_negative_rows']} and best full-stream "
                f"delta {experimental_sidecar_summary['best_full_stream_delta_bytes']} bytes."
            ),
            "Reduce record/literal overhead or find larger span bundles before revisiting sidecar format support.",
        ),
        entry(
            "sidecar-record-overhead",
            "Budget lower-overhead sidecar record layouts for the promoted residual payload signal.",
            "qualified",
            [
                "docs/SIDECAR_RECORD_OVERHEAD.md",
                "docs/sidecar_record_overhead.json",
            ],
            (
                f"{sidecar_record_summary['negative_layout_rows']} budget rows go negative; "
                f"best safe layout {sidecar_record_summary['best_safe_layout']} reaches "
                f"{sidecar_record_summary['best_safe_delta_bytes']} bytes."
            ),
            "Build an exact packed-table decoder prototype before treating the budget as compression evidence.",
        ),
        entry(
            "packed-sidecar-descriptor",
            "Prototype a packed offset/seed-index residual sidecar descriptor with exact decode proof.",
            "qualified",
            [
                "docs/PACKED_SIDECAR_DESCRIPTOR.md",
                "docs/packed_sidecar_descriptor.json",
            ],
            (
                f"{packed_sidecar_summary['full_stream_negative_rows']} packed rows are "
                f"full-stream negative; best coder {packed_sidecar_summary['best_coder']} "
                f"reaches {packed_sidecar_summary['best_delta_bytes']} bytes."
            ),
            "Replicate on controls and additional held-out corpora before changing `.tlmr`.",
        ),
        entry(
            "packed-sidecar-controls",
            "Run packed sidecar descriptor controls across selected discovery, held-out, shadow, and binary rows.",
            "qualified",
            [
                "docs/PACKED_SIDECAR_CONTROLS.md",
                "docs/packed_sidecar_controls.json",
            ],
            (
                f"{packed_controls_summary['unique_negative_cases']} unique cases go negative, "
                f"including {packed_controls_summary['ordinary_heldout_negative_cases']} ordinary "
                "held-out case; most selected rows are skipped by strict packed-table assumptions."
            ),
            "Generalize packed encodability before treating this as broad compression evidence.",
        ),
        entry(
            "generalized-packed-sidecar",
            "Generalize packed sidecar descriptors across wider offset and seed modes.",
            "qualified",
            [
                "docs/GENERALIZED_PACKED_SIDECAR.md",
                "docs/generalized_packed_sidecar.json",
            ],
            (
                f"{generalized_packed_summary['unique_encoded_source_rows']} unique source rows encode, "
                f"but ordinary held-out negative cases remain "
                f"{generalized_packed_summary['ordinary_heldout_negative_cases']}; "
                f"best-supported table bytes are "
                f"{generalized_packed_summary['best_of_supported_modes_total_table_bytes']} "
                f"versus baseline "
                f"{generalized_packed_summary['baseline_delta_u16_global_u16_total_table_bytes']}."
            ),
            "Run frozen replication before proposing format changes.",
        ),
        entry(
            "packed-sidecar-replication",
            "Replicate packed sidecar descriptor evidence on predeclared unrelated held-out corpora.",
            "blocked-by-evidence",
            [
                "docs/PACKED_SIDECAR_REPLICATION.md",
                "docs/packed_sidecar_replication.json",
            ],
            (
                f"{packed_replication_summary['source_case_count']} source cases and "
                f"{packed_replication_summary['descriptor_row_count']} descriptor rows produced "
                f"{packed_replication_summary['full_stream_negative_rows']} full-stream negative rows."
            ),
            "Find new independent match-discovery leads before more descriptor packing work.",
        ),
        entry(
            "match-discovery",
            "Run pre-sidecar exact match discovery across validation and replication corpora.",
            "blocked-by-evidence",
            ["docs/MATCH_DISCOVERY.md", "docs/match_discovery.json"],
            (
                f"{match_discovery_summary['target_span_count']} target spans across "
                f"{match_discovery_summary['row_count']} rows produced "
                f"{match_discovery_summary['rows_with_exact_hits']} exact-hit rows and "
                f"{match_discovery_summary['total_selected_spans']} selected spans."
            ),
            "Change match-discovery strategy before returning to sidecar packing or format work.",
        ),
        entry(
            "alignment-arity-discovery",
            "Test whether the match-discovery null result is caused by block alignment, phase, or arity policy.",
            "blocked-by-evidence",
            [
                "docs/ALIGNMENT_ARITY_DISCOVERY.md",
                "docs/alignment_arity_discovery.json",
            ],
            (
                f"{alignment_summary['target_span_count']} target spans across "
                f"{alignment_summary['row_count']} rows produced "
                f"{alignment_summary['total_exact_hits']} exact hits, "
                f"{alignment_summary['total_positive_exact_hits']} positive exact hits, and "
                f"{alignment_summary['total_selected_spans']} selected spans."
            ),
            "Find profitable exact hits or prefix>=5 movement before spending more on alignment-only tuning.",
        ),
        entry(
            "transformed-match-discovery",
            "Run exact seed-span discovery after the frozen reversible transform-validation matrix.",
            "blocked-by-evidence",
            [
                "docs/TRANSFORMED_MATCH_DISCOVERY.md",
                "docs/transformed_match_discovery.json",
            ],
            (
                f"{transformed_match_summary['target_span_count']} transformed target spans "
                f"across {transformed_match_summary['row_count']} rows produced "
                f"{transformed_match_summary['total_exact_hits']} exact hits, "
                f"{transformed_match_summary['total_selected_spans']} selected spans, and "
                f"{transformed_match_summary['metadata_profitable_rows']} metadata-profitable rows."
            ),
            "Find a new transform family or deeper seed lane before promoting transform metadata.",
        ),
        entry(
            "lead-exact-discovery",
            "Run exact seed-span discovery over selected affine, periodic, and composed transform leads.",
            "blocked-by-evidence",
            ["docs/LEAD_EXACT_DISCOVERY.md", "docs/lead_exact_discovery.json"],
            (
                f"{lead_exact_summary['target_span_count']} selected-lead target spans "
                f"across {lead_exact_summary['row_count']} rows produced "
                f"{lead_exact_summary['total_exact_hits']} exact hits, "
                f"{lead_exact_summary['total_selected_spans']} selected spans, and "
                f"{lead_exact_summary['metadata_profitable_rows']} metadata-profitable rows."
            ),
            "Stop broadening selected prefix-4 leads until a new family or deeper seed lane crosses prefix>=5 or exact-hit thresholds.",
        ),
        entry(
            "recursive-claim",
            "Avoid unsupported recursive convergence claims while testing recursive v2 mechanics.",
            "qualified",
            ["docs/RESULTS.md", "docs/VIABILITY.md", "docs/RESEARCH_PROGRAM.md"],
            "Recursive v2 mechanics are implemented and planted recursive controls work, but compounding natural-corpus gains are not proved.",
            "Promote recursive research only after selected spans appear outside planted controls.",
        ),
        entry(
            "scale-economics",
            "Scale planted-density sweeps for runtime and memory evidence.",
            "qualified",
            [
                "docs/SWEEPS.md",
                "docs/SCALE_PERFORMANCE.md",
                "docs/scale_performance_report.json",
                "docs/RESEARCH_SCORECARD.md",
            ],
            (
                f"Current scale evidence reaches the generated {largest_scale_mib} "
                f"planted-density sweep; the scale report finds peak memory "
                f"{scale_performance_summary['largest_peak_memory_mib']} MiB, "
                f"peak/table ratio "
                f"{scale_performance_summary['largest_peak_to_estimated_table_ratio']}, "
                f"and next-double peak estimate "
                f"{scale_performance_summary['next_double_peak_memory_mib_at_current_ratio']} MiB."
            ),
            "Extend bounded scale rows only after memory telemetry or chunked target tables explain and reduce the working set.",
        ),
        entry(
            "release-process",
            "Add CI and production release checklist.",
            "complete",
            ["docs/RELEASE_CHECKLIST.md", ".github/workflows/ci.yml"],
            "Release docs define supported format versions, compatibility guarantees, gates, known limitations, and migration rules.",
            "Run the full release gate set before tagging.",
        ),
    ]

    status_counts = Counter(item["status"] for item in entries)
    open_entries = [item for item in entries if item["status"] == "open"]
    unresolved_entries = [
        item for item in entries if item["status"] in {"open", "blocked-by-evidence"}
    ]

    implemented_sections = sorted(
        {
            item["section"]
            for item in entries
            if item["status"] in {"complete", "proved", "qualified"}
        }
    )

    missing_expected_results = sorted(
        {
            "planted-sha256-arity2",
            "indexed-planted-span8",
            "streaming-planted-span8",
            "streaming-random-null-1k",
            "streaming-structured-json-control",
            "kolyma-pdf-streaming-control",
        }
        - result_names
    )

    return {
        "generated_by": "scripts/generate_goal_audit.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "overall_status": "architecture-implemented; research-viable; not production-proven",
        "verdict": viability["verdict"],
        "status_counts": dict(status_counts),
        "scorecard_status_counts": dict(scorecard_status_counts),
        "viability_status_counts": dict(viability_status_counts),
        "source_hashes": hashes(SOURCE_PATHS),
        "artifact_hashes": hashes(ARTIFACT_PATHS),
        "evidence_hashes": evidence_hashes(entries),
        "implemented_sections": implemented_sections,
        "open_count": len(open_entries),
        "open_requirements": [item["requirement"] for item in open_entries],
        "unresolved_count": len(unresolved_entries),
        "unresolved_requirements": [
            item["requirement"] for item in unresolved_entries
        ],
        "missing_expected_results": missing_expected_results,
        "scorecard_snapshot": {
            "codec": card_by_area(scorecard, "Codec and format safety")["status"],
            "planted": card_by_area(scorecard, "Planted generative mechanism")["status"],
            "raw_structured": card_by_area(scorecard, "Raw structured corpus")["status"],
            "production_acceleration": card_by_area(scorecard, "Production acceleration")["status"],
        },
        "external_summaries": {
            "corpus_rows": len(corpus.get("results", [])),
            "corpus_generalization_controls": corpus_generalization_summary[
                "control_count"
            ],
            "corpus_generalization_prefix5_rows": corpus_generalization_summary[
                "rows_with_prefix_ge_5"
            ],
            "corpus_generalization_exact_hits": corpus_generalization_summary[
                "total_exact_hits"
            ],
            "heldout_expansion_corpora": heldout_expansion_summary["corpus_count"],
            "heldout_expansion_missing_matrix": heldout_expansion_summary[
                "missing_corpus_matrix_count"
            ],
            "heldout_expansion_prefix5_rows": heldout_expansion_summary[
                "rows_with_prefix_ge_5"
            ],
            "heldout_expansion_exact_hit_rows": heldout_expansion_summary[
                "rows_with_exact_hits"
            ],
            "heldout_expansion_selected_span_rows": heldout_expansion_summary[
                "rows_with_selected_spans"
            ],
            "periodic_selected_transforms": periodic.get("selected_transform_count", 0),
            "periodic_heldout_prefix5_win_corpora": periodic_summary[
                "heldout_prefix5_win_corpora"
            ],
            "composed_selected_transforms": composed.get("selected_transform_count", 0),
            "composed_heldout_prefix5_win_corpora": composed_summary[
                "heldout_prefix5_win_corpora"
            ],
            "heldout_exact_hits": validation_summary["heldout_exact_hits"],
            "fifth_steering_cross_exact_hit_rows": steering_summary["cross_exact_hit_rows"],
            "contextual_steering_cross_prefix5_win_rows": contextual_summary[
                "cross_prefix5_win_rows"
            ],
            "contextual_steering_cross_exact_hit_rows": contextual_summary[
                "cross_exact_hit_rows"
            ],
            "depth3_prefix5_uplift_rows": depth3_summary[
                "heldout_rows_with_prefix5_uplift"
            ],
            "depth3_exact_hits": depth3_summary["heldout_exact_hits"],
            "depth3_followup_selected_spans": depth3_followup_summary[
                "total_depth3_selected_spans"
            ],
            "lead_depth3_prefix5_uplift_rows": lead_depth3_prefix_summary[
                "rows_with_depth3_prefix5_uplift"
            ],
            "lead_depth3_followup_selected_spans": lead_depth3_followup_summary[
                "total_depth3_selected_spans"
            ],
            "depth3_frontier_rows": depth3_frontier_summary["frontier_rows"],
            "depth3_frontier_exact_hits": depth3_frontier_summary["total_exact_hits"],
            "depth3_frontier_selected_spans": depth3_frontier_summary[
                "total_selected_spans"
            ],
            "depth4_shard_status": depth4_gate["recommended_status"],
            "depth4_estimated_hours": depth4_estimates[
                "estimated_incremental_depth4_hours"
            ],
            "depth4_exact8_probability": depth4_estimates[
                "exact8_probability_at_least_one"
            ],
            "depth4_pilot_shards": depth4_pilot_summary["pilot_shard_count"],
            "depth4_pilot_seeds": depth4_pilot_summary["enumerated_seed_count"],
            "depth4_pilot_prefix5_rows": depth4_pilot_summary[
                "rows_with_depth4_prefix5"
            ],
            "depth4_pilot_prefix6_rows": depth4_pilot_summary[
                "rows_with_depth4_prefix6"
            ],
            "depth4_pilot_exact_hits": depth4_pilot_summary["total_exact_hits"],
            "depth4_pilot_selected_spans": depth4_pilot_summary[
                "total_selected_spans"
            ],
            "search_frontier_status": search_gate_summary["recommended_status"],
            "search_frontier_forecast_gib": search_gate_summary[
                "best_non_planted_gib_for_one_expected_hit"
            ],
            "search_frontier_depth4_probability": search_gate_summary[
                "depth4_exact8_probability"
            ],
            "search_frontier_selected_spans": search_gate_summary[
                "selected_span_total"
            ],
            "search_frontier_blocking_gates": len(
                search_gate_summary["blocking_gates"]
            ),
            "mechanism_ranking_top_lane": mechanism_ranking_summary["top_lane_id"],
            "mechanism_ranking_top_artifact": mechanism_ranking_summary[
                "top_next_artifact"
            ],
            "mechanism_ranking_ready_count": mechanism_ranking_summary[
                "ready_count"
            ],
            "mechanism_ranking_selected_spans": mechanism_ranking_summary[
                "selected_span_total"
            ],
            "seed_table_promotion_met": seed_table_summary["promotion_met"],
            "seed_table_canonical_selected_spans": seed_table_summary[
                "canonical_selected_spans"
            ],
            "seed_table_ordinary_negative_groups": seed_table_summary[
                "canonical_ordinary_heldout_negative_groups"
            ],
            "seed_table_control_negative_groups": seed_table_summary[
                "canonical_control_negative_groups"
            ],
            "seed_table_sha256_selected_spans": seed_table_summary[
                "sha256_selected_spans"
            ],
            "exact_short_total_verified_hits": exact_short_summary[
                "reconstructed_exact_hits"
            ],
            "exact_short_zero_overhead_delta_bytes": exact_short_summary[
                "zero_overhead_best_delta_bytes"
            ],
            "exact_short_full_stream_negative_groups": exact_short_summary[
                "full_stream_ordinary_negative_groups"
            ],
            "exact_short_control_negative_groups": exact_short_summary[
                "full_stream_control_negative_groups"
            ],
            "exact_short_control_density_comparable": exact_short_summary[
                "control_density"
            ]["control_density_comparable"],
            "exact_short_promotion_met": exact_short_summary["promotion_met"],
            "whole_stream_honest_encoded_rows": whole_stream_summary[
                "honest_encoded_rows"
            ],
            "whole_stream_decode_verified_rows": whole_stream_summary[
                "decode_verified_rows"
            ],
            "whole_stream_honest_negative_rows": whole_stream_summary[
                "honest_full_stream_negative_rows"
            ],
            "whole_stream_ordinary_negative_groups": whole_stream_summary[
                "ordinary_heldout_negative_groups"
            ],
            "whole_stream_control_negative_groups": whole_stream_summary[
                "control_negative_groups"
            ],
            "whole_stream_best_honest_delta": whole_stream_summary[
                "best_honest_delta_bytes"
            ],
            "whole_stream_promotion_met": whole_stream_summary["promotion_met"],
            "expander_salt_predeclared_salts": expander_salt_summary[
                "predeclared_salt_count"
            ],
            "expander_salt_exact_hits": expander_salt_summary["salted_exact_hits"],
            "expander_salt_expected_exact_hits": expander_salt_summary[
                "salted_expected_exact_hits"
            ],
            "expander_salt_random_multiplier_exceeded": expander_salt_summary[
                "random_trial_multiplier_exceeded"
            ],
            "expander_salt_selected_span_rows": expander_salt_summary[
                "salted_selected_span_rows"
            ],
            "expander_salt_full_stream_negative_rows": expander_salt_summary[
                "full_stream_negative_rows"
            ],
            "expander_salt_ordinary_negative_groups": expander_salt_summary[
                "ordinary_heldout_negative_groups"
            ],
            "expander_salt_control_negative_groups": expander_salt_summary[
                "control_negative_groups"
            ],
            "expander_salt_promotion_met": expander_salt_summary["promotion_met"],
            "schema_native_public_entries": schema_native_summary[
                "public_entry_count"
            ],
            "schema_native_family_selected_spans": schema_native_summary[
                "family_selected_spans"
            ],
            "schema_native_ordinary_negative_groups": schema_native_summary[
                "family_ordinary_heldout_negative_groups"
            ],
            "schema_native_control_negative_groups": schema_native_summary[
                "family_control_negative_groups"
            ],
            "schema_native_wrong_schema_negative_groups": schema_native_summary[
                "wrong_schema_ordinary_negative_groups"
            ],
            "schema_native_random_negative_groups": schema_native_summary[
                "random_table_ordinary_negative_groups"
            ],
            "schema_native_shadow_negative_groups": schema_native_summary[
                "shadow_ordinary_negative_groups"
            ],
            "schema_native_beats_generic": schema_native_summary[
                "beats_generic_dictionary_baseline"
            ],
            "schema_native_promotion_met": schema_native_summary["promotion_met"],
            "schema_replication_corpora": schema_replication_summary["corpus_count"],
            "schema_replication_standards_selected_spans": schema_replication_summary[
                "standards_selected_spans"
            ],
            "schema_replication_ordinary_negative_groups": schema_replication_summary[
                "standards_ordinary_negative_groups"
            ],
            "schema_replication_control_negative_groups": schema_replication_summary[
                "standards_control_negative_groups"
            ],
            "schema_replication_generic_negative_groups": schema_replication_summary[
                "generic_ordinary_negative_groups"
            ],
            "schema_replication_claim_level": schema_replication_summary[
                "claim_level"
            ],
            "schema_replication_promotion_met": schema_replication_summary[
                "promotion_met"
            ],
            "superposition_fixture_count": superposition_summary["fixture_count"],
            "superposition_candidate_count": superposition_summary["candidate_count"],
            "superposition_retained_alternatives": superposition_summary[
                "retained_alternative_count"
            ],
            "superposition_weighted_extra_savings": superposition_summary[
                "weighted_extra_savings"
            ],
            "superposition_weighted_beats_greedy": superposition_summary[
                "weighted_beats_greedy_fixture_count"
            ],
            "superposition_unexplained_discards": superposition_summary[
                "unexplained_discard_count"
            ],
            "superposition_promotion_met": superposition_summary["promotion_met"],
            "long_span_gate_met_count": long_span_gate_summary["gate_met_count"],
            "long_span_gate_count": long_span_gate_summary["gate_count"],
            "long_span_recommendation": long_span_gate_summary["recommendation"],
            "long_span_selected_span_total": long_span_gate_summary[
                "selected_span_total"
            ],
            "long_span_required_raw_suffix_prefix": long_span_gate_summary[
                "minimum_raw_suffix_negative_prefix_len"
            ],
            "long_span_max_observed_prefix": long_span_gate_summary[
                "max_observed_heldout_forced_prefix_len"
            ],
            "long_span_claim_level": long_span_gate_summary["claim_level"],
            "long_span_promotion_met": long_span_gate_summary["promotion_met"],
            "recursive_structured_fixture_count": recursive_structured_summary[
                "fixture_count"
            ],
            "recursive_structured_ordinary_later_win_families": recursive_structured_summary[
                "ordinary_later_win_families"
            ],
            "recursive_structured_planted_offset_later_win_families": recursive_structured_summary[
                "planted_offset_later_win_families"
            ],
            "recursive_structured_claim_level": recursive_structured_summary[
                "claim_level"
            ],
            "recursive_structured_promotion_met": recursive_structured_summary[
                "promotion_met"
            ],
            "scale_performance_largest_scale_mib": scale_performance_summary[
                "largest_scale_mib"
            ],
            "scale_performance_largest_peak_memory_mib": scale_performance_summary[
                "largest_peak_memory_mib"
            ],
            "scale_performance_peak_table_ratio": scale_performance_summary[
                "largest_peak_to_estimated_table_ratio"
            ],
            "scale_performance_next_double_peak_mib": scale_performance_summary[
                "next_double_peak_memory_mib_at_current_ratio"
            ],
            "scale_performance_promotion_met": scale_performance_summary[
                "promotion_met"
            ],
            "ui_workflow_ui_evidence_keys": ui_workflow_summary[
                "ui_evidence_key_count"
            ],
            "ui_workflow_tauri_evidence_fields": ui_workflow_summary[
                "tauri_evidence_field_count"
            ],
            "ui_workflow_required_cards": ui_workflow_summary["required_card_count"],
            "ui_workflow_missing_tauri_fields": len(
                ui_workflow_summary["missing_tauri_fields"]
            ),
            "ui_workflow_missing_mock_fields": len(
                ui_workflow_summary["missing_mock_fields"]
            ),
            "ui_workflow_claim_level": ui_workflow_summary["claim_level"],
            "ui_workflow_promotion_met": ui_workflow_summary["promotion_met"],
            "shadow_prefix5_win_corpora": validation_summary[
                "shadow_prefix5_win_corpora"
            ],
            "binary_exact_hits": validation_summary["binary_exact_hits"],
            "structural_candidates": structural_summary["candidate_count"],
            "structural_validation_rows": structural_summary["validation_rows"],
            "structural_heldout_prefix5_win_corpora": structural_summary[
                "heldout_prefix5_win_corpora"
            ],
            "structural_heldout_exact_hits": structural_summary["heldout_exact_hits"],
            "byte_permutation_transforms": byte_permutation_summary["transform_count"],
            "byte_permutation_rows": byte_permutation_summary["row_count"],
            "byte_permutation_prefix5_rows": byte_permutation_summary[
                "rows_with_prefix_ge_5"
            ],
            "byte_permutation_exact_hits": byte_permutation_summary[
                "total_exact_hits"
            ],
            "byte_permutation_selected_spans": byte_permutation_summary[
                "total_selected_spans"
            ],
            "byte_permutation_negative_after_metadata_rows": byte_permutation_summary[
                "rows_negative_after_metadata"
            ],
            "bwt_mtf_transforms": bwt_mtf_summary["transform_count"],
            "bwt_mtf_rows": bwt_mtf_summary["row_count"],
            "bwt_mtf_prefix5_rows": bwt_mtf_summary["rows_with_prefix_ge_5"],
            "bwt_mtf_exact_hits": bwt_mtf_summary["total_exact_hits"],
            "bwt_mtf_selected_spans": bwt_mtf_summary["total_selected_spans"],
            "bwt_mtf_negative_after_metadata_rows": bwt_mtf_summary[
                "rows_negative_after_metadata"
            ],
            "bwt_mtf_shorter_payload_rows": bwt_mtf_summary[
                "rows_with_shorter_transformed_payload"
            ],
            "grammar_channel_channels": grammar_channel_summary["channel_count"],
            "grammar_channel_rows": grammar_channel_summary["row_count"],
            "grammar_channel_prefix5_rows": grammar_channel_summary[
                "rows_with_prefix_ge_5"
            ],
            "grammar_channel_exact_hits": grammar_channel_summary["total_exact_hits"],
            "grammar_channel_selected_spans": grammar_channel_summary[
                "total_selected_spans"
            ],
            "grammar_channel_negative_after_metadata_rows": grammar_channel_summary[
                "rows_negative_after_metadata"
            ],
            "numeric_value_channel_channels": numeric_value_channel_summary[
                "channel_count"
            ],
            "numeric_value_channel_rows": numeric_value_channel_summary["row_count"],
            "numeric_value_channel_parsed_values": numeric_value_channel_summary[
                "parsed_value_count"
            ],
            "numeric_value_channel_prefix5_rows": numeric_value_channel_summary[
                "rows_with_prefix_ge_5"
            ],
            "numeric_value_channel_exact_hits": numeric_value_channel_summary[
                "total_exact_hits"
            ],
            "numeric_value_channel_selected_spans": numeric_value_channel_summary[
                "total_selected_spans"
            ],
            "numeric_value_channel_negative_after_metadata_rows": numeric_value_channel_summary[
                "rows_negative_after_metadata"
            ],
            "record_context_transforms": record_context_summary["transform_count"],
            "record_context_rows": record_context_summary["row_count"],
            "record_context_prefix5_rows": record_context_summary[
                "rows_with_prefix_ge_5"
            ],
            "record_context_exact_hits": record_context_summary["total_exact_hits"],
            "record_context_selected_spans": record_context_summary[
                "total_selected_spans"
            ],
            "record_context_negative_after_metadata_rows": record_context_summary[
                "rows_negative_after_metadata"
            ],
            "token_dictionary_transforms": token_dictionary_summary["transform_count"],
            "token_dictionary_rows": token_dictionary_summary["row_count"],
            "token_dictionary_prefix5_rows": token_dictionary_summary[
                "rows_with_prefix_ge_5"
            ],
            "token_dictionary_exact_hits": token_dictionary_summary["total_exact_hits"],
            "token_dictionary_selected_spans": token_dictionary_summary[
                "total_selected_spans"
            ],
            "token_dictionary_negative_after_metadata_rows": token_dictionary_summary[
                "rows_negative_after_metadata"
            ],
            "affine_searched_candidates": affine_summary["searched_candidate_count"],
            "affine_selected_candidates": affine_summary["selected_candidate_count"],
            "affine_heldout_prefix4_win_corpora": affine_summary[
                "heldout_prefix4_win_corpora"
            ],
            "affine_heldout_prefix5_win_corpora": affine_summary[
                "heldout_prefix5_win_corpora"
            ],
            "affine_heldout_exact_hits": affine_summary["heldout_exact_hits"],
            "residual_candidate_count": residual_summary["candidate_count"],
            "residual_validation_rows": residual_summary["validation_rows"],
            "residual_heldout_forced_rows": residual_summary["heldout_forced_rows"],
            "residual_heldout_seed_contribution_positive_rows": residual_summary[
                "heldout_seed_contribution_positive_rows"
            ],
            "residual_heldout_positive_rows": residual_summary["heldout_positive_rows"],
            "residual_best_heldout_net_delta_bytes": residual_summary[
                "best_heldout_net_delta_bytes"
            ],
            "sidecar_break_even_rows": sidecar_break_even_summary["row_count"],
            "sidecar_raw_suffix_min_prefix": sidecar_break_even_summary[
                "minimum_raw_suffix_negative_prefix_len"
            ],
            "sidecar_max_observed_forced_prefix": sidecar_break_even_summary[
                "max_observed_heldout_forced_prefix_len"
            ],
            "sidecar_raw_suffix_viable_rows": sidecar_break_even_summary[
                "raw_suffix_viable_at_observed_prefix_rows"
            ],
            "sidecar_sublinear_viable_rows": sidecar_break_even_summary[
                "sublinear_model_viable_at_observed_prefix_rows"
            ],
            "sidecar_promoted_rows": sidecar_break_even_summary["promoted_rows"],
            "residual_payload_heldout_rows": residual_payload_summary[
                "heldout_payload_rows"
            ],
            "residual_payload_measured_negative_rows": residual_payload_summary[
                "measured_heldout_negative_rows"
            ],
            "residual_payload_best_measured_case": residual_payload_summary[
                "best_measured_heldout_negative_case"
            ],
            "residual_payload_zlib_best_delta": residual_payload_summary[
                "best_heldout_net_delta_by_policy"
            ]["zlib_level9"],
            "experimental_sidecar_rows": experimental_sidecar_summary["prototype_rows"],
            "experimental_sidecar_decode_verified_rows": experimental_sidecar_summary[
                "decode_verified_rows"
            ],
            "experimental_sidecar_full_stream_negative_rows": experimental_sidecar_summary[
                "full_stream_negative_rows"
            ],
            "experimental_sidecar_best_full_delta": experimental_sidecar_summary[
                "best_full_stream_delta_bytes"
            ],
            "sidecar_record_negative_rows": sidecar_record_summary[
                "negative_layout_rows"
            ],
            "sidecar_record_best_safe_layout": sidecar_record_summary[
                "best_safe_layout"
            ],
            "sidecar_record_best_safe_delta": sidecar_record_summary[
                "best_safe_delta_bytes"
            ],
            "packed_sidecar_rows": packed_sidecar_summary["prototype_rows"],
            "packed_sidecar_full_stream_negative_rows": packed_sidecar_summary[
                "full_stream_negative_rows"
            ],
            "packed_sidecar_best_coder": packed_sidecar_summary["best_coder"],
            "packed_sidecar_best_delta": packed_sidecar_summary["best_delta_bytes"],
            "packed_controls_rows": packed_controls_summary["control_rows"],
            "packed_controls_encoded_rows": packed_controls_summary["encoded_rows"],
            "packed_controls_unique_negative_cases": packed_controls_summary[
                "unique_negative_cases"
            ],
            "packed_controls_ordinary_heldout_negative_cases": packed_controls_summary[
                "ordinary_heldout_negative_cases"
            ],
            "generalized_packed_encoded_rows": generalized_packed_summary[
                "encoded_rows"
            ],
            "generalized_packed_unique_encoded_source_rows": generalized_packed_summary[
                "unique_encoded_source_rows"
            ],
            "generalized_packed_unique_negative_cases": generalized_packed_summary[
                "unique_negative_cases"
            ],
            "generalized_packed_ordinary_heldout_negative_cases": generalized_packed_summary[
                "ordinary_heldout_negative_cases"
            ],
            "packed_replication_source_cases": packed_replication_summary[
                "source_case_count"
            ],
            "packed_replication_descriptor_rows": packed_replication_summary[
                "descriptor_row_count"
            ],
            "packed_replication_full_stream_negative_rows": packed_replication_summary[
                "full_stream_negative_rows"
            ],
            "packed_replication_ordinary_heldout_negative_groups": packed_replication_summary[
                "ordinary_heldout_negative_groups"
            ],
            "match_discovery_rows": match_discovery_summary["row_count"],
            "match_discovery_target_spans": match_discovery_summary[
                "target_span_count"
            ],
            "match_discovery_prefix5_rows": match_discovery_summary[
                "rows_with_prefix_ge_5"
            ],
            "match_discovery_exact_hit_rows": match_discovery_summary[
                "rows_with_exact_hits"
            ],
            "match_discovery_selected_span_rows": match_discovery_summary[
                "rows_with_selected_spans"
            ],
            "match_discovery_total_selected_spans": match_discovery_summary[
                "total_selected_spans"
            ],
            "match_discovery_ordinary_heldout_selected_groups": match_discovery_summary[
                "ordinary_heldout_selected_groups"
            ],
            "alignment_arity_rows": alignment_summary["row_count"],
            "alignment_arity_target_spans": alignment_summary["target_span_count"],
            "alignment_arity_prefix5_rows": alignment_summary["rows_with_prefix_ge_5"],
            "alignment_arity_exact_hits": alignment_summary["total_exact_hits"],
            "alignment_arity_positive_exact_hits": alignment_summary[
                "total_positive_exact_hits"
            ],
            "alignment_arity_selected_spans": alignment_summary["total_selected_spans"],
            "transformed_match_rows": transformed_match_summary["row_count"],
            "transformed_match_target_spans": transformed_match_summary[
                "target_span_count"
            ],
            "transformed_match_prefix5_rows": transformed_match_summary[
                "rows_with_prefix_ge_5"
            ],
            "transformed_match_exact_hits": transformed_match_summary[
                "total_exact_hits"
            ],
            "transformed_match_selected_spans": transformed_match_summary[
                "total_selected_spans"
            ],
            "transformed_match_metadata_profitable_rows": transformed_match_summary[
                "metadata_profitable_rows"
            ],
            "lead_exact_rows": lead_exact_summary["row_count"],
            "lead_exact_target_spans": lead_exact_summary["target_span_count"],
            "lead_exact_prefix5_rows": lead_exact_summary["rows_with_prefix_ge_5"],
            "lead_exact_exact_hits": lead_exact_summary["total_exact_hits"],
            "lead_exact_selected_spans": lead_exact_summary["total_selected_spans"],
            "lead_exact_metadata_profitable_rows": lead_exact_summary[
                "metadata_profitable_rows"
            ],
        },
        "entries": entries,
    }


def write_audit(payload: dict[str, Any]) -> None:
    GOAL_AUDIT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Telomere Goal Audit",
        "",
        "Generated by `scripts/generate_goal_audit.py` from source files and checked-in evidence artifacts.",
        "This is the canonical requirement-to-evidence ledger for the optimization architecture plan and research program.",
        "",
        f"Overall status: **{payload['overall_status']}**.",
        f"Viability verdict: **{payload['verdict']}**.",
        "",
        "## Status Counts",
        "",
    ]
    for status, count in sorted(payload["status_counts"].items()):
        lines.append(f"- `{status}`: {count}")

    lines.extend(
        [
            "",
            "## Audit Matrix",
            "",
            "| section | requirement | status | evidence | finding | remaining gate |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for item in payload["entries"]:
        evidence = ", ".join(f"`{path}`" for path in item["evidence"])
        lines.append(
            "| {section} | {requirement} | {status} | {evidence} | {finding} | {remaining_gate} |".format(
                section=item["section"],
                requirement=item["requirement"],
                status=item["status"],
                evidence=evidence,
                finding=item["finding"],
                remaining_gate=item["remaining_gate"],
            )
        )

    lines.extend(
        [
            "",
            "## Unresolved Gates",
            "",
            "This section lists unresolved `open` and `blocked-by-evidence` requirements.",
            "",
        ]
    )
    if payload["unresolved_requirements"]:
        lines.extend(
            f"- {requirement}" for requirement in payload["unresolved_requirements"]
        )
    else:
        lines.append("- None.")

    lines.extend(
        [
            "",
            "## Integrity",
            "",
            f"- Missing expected generated-result rows: `{len(payload['missing_expected_results'])}`",
            f"- Corpus matrix rows: `{payload['external_summaries']['corpus_rows']}`",
            f"- Corpus generalization controls: `{payload['external_summaries']['corpus_generalization_controls']}`",
            f"- Corpus generalization prefix>=5 rows: `{payload['external_summaries']['corpus_generalization_prefix5_rows']}`",
            f"- Corpus generalization exact hits: `{payload['external_summaries']['corpus_generalization_exact_hits']}`",
            f"- Held-out corpus expansion corpora: `{payload['external_summaries']['heldout_expansion_corpora']}`",
            f"- Held-out corpus expansion missing matrix rows: `{payload['external_summaries']['heldout_expansion_missing_matrix']}`",
            f"- Held-out corpus expansion prefix>=5 rows: `{payload['external_summaries']['heldout_expansion_prefix5_rows']}`",
            f"- Held-out corpus expansion exact-hit rows: `{payload['external_summaries']['heldout_expansion_exact_hit_rows']}`",
            f"- Held-out corpus expansion selected-span rows: `{payload['external_summaries']['heldout_expansion_selected_span_rows']}`",
            f"- Held-out exact hits: `{payload['external_summaries']['heldout_exact_hits']}`",
            f"- Fifth-byte steering exact-hit rows: `{payload['external_summaries']['fifth_steering_cross_exact_hit_rows']}`",
            f"- Contextual steering prefix>=5 win rows: `{payload['external_summaries']['contextual_steering_cross_prefix5_win_rows']}`",
            f"- Depth-3 prefix>=5 uplift rows: `{payload['external_summaries']['depth3_prefix5_uplift_rows']}`",
            f"- Depth-3 follow-up selected spans: `{payload['external_summaries']['depth3_followup_selected_spans']}`",
            f"- Lead depth-3 prefix>=5 uplift rows: `{payload['external_summaries']['lead_depth3_prefix5_uplift_rows']}`",
            f"- Lead depth-3 follow-up selected spans: `{payload['external_summaries']['lead_depth3_followup_selected_spans']}`",
            f"- Depth-3 frontier exact-discovery rows: `{payload['external_summaries']['depth3_frontier_rows']}`",
            f"- Depth-3 frontier exact hits: `{payload['external_summaries']['depth3_frontier_exact_hits']}`",
            f"- Depth-3 frontier selected spans: `{payload['external_summaries']['depth3_frontier_selected_spans']}`",
            f"- Depth-4 shard status: `{payload['external_summaries']['depth4_shard_status']}`",
            f"- Depth-4 estimated full hours: `{payload['external_summaries']['depth4_estimated_hours']}`",
            f"- Depth-4 exact-8 probability: `{payload['external_summaries']['depth4_exact8_probability']}`",
            f"- Depth-4 pilot shards: `{payload['external_summaries']['depth4_pilot_shards']}`",
            f"- Depth-4 pilot seeds: `{payload['external_summaries']['depth4_pilot_seeds']}`",
            f"- Depth-4 pilot prefix>=5 rows: `{payload['external_summaries']['depth4_pilot_prefix5_rows']}`",
            f"- Depth-4 pilot prefix>=6 rows: `{payload['external_summaries']['depth4_pilot_prefix6_rows']}`",
            f"- Depth-4 pilot exact hits: `{payload['external_summaries']['depth4_pilot_exact_hits']}`",
            f"- Depth-4 pilot selected spans: `{payload['external_summaries']['depth4_pilot_selected_spans']}`",
            f"- Search frontier status: `{payload['external_summaries']['search_frontier_status']}`",
            f"- Search frontier forecast GiB: `{payload['external_summaries']['search_frontier_forecast_gib']}`",
            f"- Search frontier depth-4 probability: `{payload['external_summaries']['search_frontier_depth4_probability']}`",
            f"- Search frontier selected spans: `{payload['external_summaries']['search_frontier_selected_spans']}`",
            f"- Search frontier blocking gates: `{payload['external_summaries']['search_frontier_blocking_gates']}`",
            f"- Mechanism experiment ranking top lane: `{payload['external_summaries']['mechanism_ranking_top_lane']}`",
            f"- Mechanism experiment ranking top artifact: `{payload['external_summaries']['mechanism_ranking_top_artifact']}`",
            f"- Mechanism experiment ranking ready lanes: `{payload['external_summaries']['mechanism_ranking_ready_count']}`",
            f"- Mechanism experiment ranking selected spans: `{payload['external_summaries']['mechanism_ranking_selected_spans']}`",
            f"- Seed-table preset probe promotion met: `{payload['external_summaries']['seed_table_promotion_met']}`",
            f"- Seed-table preset probe selected spans: `{payload['external_summaries']['seed_table_canonical_selected_spans']}`",
            f"- Seed-table preset probe ordinary negative groups: `{payload['external_summaries']['seed_table_ordinary_negative_groups']}`",
            f"- Seed-table preset probe control negative groups: `{payload['external_summaries']['seed_table_control_negative_groups']}`",
            f"- Seed-table preset probe SHA-256 selected spans: `{payload['external_summaries']['seed_table_sha256_selected_spans']}`",
            f"- Exact short-hit bundle economics verified hits: `{payload['external_summaries']['exact_short_total_verified_hits']}`",
            f"- Exact short-hit bundle economics zero-overhead delta: `{payload['external_summaries']['exact_short_zero_overhead_delta_bytes']}`",
            f"- Exact short-hit bundle economics full-stream ordinary groups: `{payload['external_summaries']['exact_short_full_stream_negative_groups']}`",
            f"- Exact short-hit bundle economics control negative groups: `{payload['external_summaries']['exact_short_control_negative_groups']}`",
            f"- Exact short-hit bundle economics control density comparable: `{payload['external_summaries']['exact_short_control_density_comparable']}`",
            f"- Exact short-hit bundle economics promotion met: `{payload['external_summaries']['exact_short_promotion_met']}`",
            f"- Whole-stream residual vector probe honest encoded rows: `{payload['external_summaries']['whole_stream_honest_encoded_rows']}`",
            f"- Whole-stream residual vector probe exact decode rows: `{payload['external_summaries']['whole_stream_decode_verified_rows']}`",
            f"- Whole-stream residual vector probe full-stream negative rows: `{payload['external_summaries']['whole_stream_honest_negative_rows']}`",
            f"- Whole-stream residual vector probe ordinary held-out negative groups: `{payload['external_summaries']['whole_stream_ordinary_negative_groups']}`",
            f"- Whole-stream residual vector probe control negative groups: `{payload['external_summaries']['whole_stream_control_negative_groups']}`",
            f"- Whole-stream residual vector probe best honest delta: `{payload['external_summaries']['whole_stream_best_honest_delta']}`",
            f"- Whole-stream residual vector probe promotion met: `{payload['external_summaries']['whole_stream_promotion_met']}`",
            f"- Expander salt ensemble predeclared salts: `{payload['external_summaries']['expander_salt_predeclared_salts']}`",
            f"- Expander salt ensemble exact hits: `{payload['external_summaries']['expander_salt_exact_hits']}`",
            f"- Expander salt ensemble expected exact hits: `{payload['external_summaries']['expander_salt_expected_exact_hits']}`",
            f"- Expander salt ensemble random multiplier exceeded: `{payload['external_summaries']['expander_salt_random_multiplier_exceeded']}`",
            f"- Expander salt ensemble selected span rows: `{payload['external_summaries']['expander_salt_selected_span_rows']}`",
            f"- Expander salt ensemble full-stream negative rows: `{payload['external_summaries']['expander_salt_full_stream_negative_rows']}`",
            f"- Expander salt ensemble ordinary negative groups: `{payload['external_summaries']['expander_salt_ordinary_negative_groups']}`",
            f"- Expander salt ensemble control negative groups: `{payload['external_summaries']['expander_salt_control_negative_groups']}`",
            f"- Expander salt ensemble promotion met: `{payload['external_summaries']['expander_salt_promotion_met']}`",
            f"- Schema-native public dictionary entries: `{payload['external_summaries']['schema_native_public_entries']}`",
            f"- Schema-native public dictionary selected spans: `{payload['external_summaries']['schema_native_family_selected_spans']}`",
            f"- Schema-native public dictionary ordinary groups: `{payload['external_summaries']['schema_native_ordinary_negative_groups']}`",
            f"- Schema-native public dictionary control groups: `{payload['external_summaries']['schema_native_control_negative_groups']}`",
            f"- Schema-native public dictionary wrong-schema groups: `{payload['external_summaries']['schema_native_wrong_schema_negative_groups']}`",
            f"- Schema-native public dictionary random-table groups: `{payload['external_summaries']['schema_native_random_negative_groups']}`",
            f"- Schema-native public dictionary shadow groups: `{payload['external_summaries']['schema_native_shadow_negative_groups']}`",
            f"- Schema-native public dictionary beats generic baseline: `{payload['external_summaries']['schema_native_beats_generic']}`",
            f"- Schema-native public dictionary promotion met: `{payload['external_summaries']['schema_native_promotion_met']}`",
            f"- Schema-native public dictionary replication corpora: `{payload['external_summaries']['schema_replication_corpora']}`",
            f"- Schema-native public dictionary replication selected spans: `{payload['external_summaries']['schema_replication_standards_selected_spans']}`",
            f"- Schema-native public dictionary replication ordinary groups: `{payload['external_summaries']['schema_replication_ordinary_negative_groups']}`",
            f"- Schema-native public dictionary replication control groups: `{payload['external_summaries']['schema_replication_control_negative_groups']}`",
            f"- Schema-native public dictionary replication generic groups: `{payload['external_summaries']['schema_replication_generic_negative_groups']}`",
            f"- Schema-native public dictionary replication claim level: `{payload['external_summaries']['schema_replication_claim_level']}`",
            f"- Schema-native public dictionary replication promotion met: `{payload['external_summaries']['schema_replication_promotion_met']}`",
            f"- Superposition telemetry fixtures: `{payload['external_summaries']['superposition_fixture_count']}`",
            f"- Superposition telemetry candidates: `{payload['external_summaries']['superposition_candidate_count']}`",
            f"- Superposition telemetry retained alternatives: `{payload['external_summaries']['superposition_retained_alternatives']}`",
            f"- Superposition telemetry weighted extra savings: `{payload['external_summaries']['superposition_weighted_extra_savings']}`",
            f"- Superposition telemetry weighted-beats-greedy fixtures: `{payload['external_summaries']['superposition_weighted_beats_greedy']}`",
            f"- Superposition telemetry unexplained discards: `{payload['external_summaries']['superposition_unexplained_discards']}`",
            f"- Superposition telemetry promotion met: `{payload['external_summaries']['superposition_promotion_met']}`",
            f"- Long-span bundle gate checks met: `{payload['external_summaries']['long_span_gate_met_count']}`",
            f"- Long-span bundle gate checks total: `{payload['external_summaries']['long_span_gate_count']}`",
            f"- Long-span bundle recommendation: `{payload['external_summaries']['long_span_recommendation']}`",
            f"- Long-span bundle selected span total: `{payload['external_summaries']['long_span_selected_span_total']}`",
            f"- Long-span bundle required raw-suffix prefix: `{payload['external_summaries']['long_span_required_raw_suffix_prefix']}`",
            f"- Long-span bundle max observed prefix: `{payload['external_summaries']['long_span_max_observed_prefix']}`",
            f"- Long-span bundle claim level: `{payload['external_summaries']['long_span_claim_level']}`",
            f"- Long-span bundle promotion met: `{payload['external_summaries']['long_span_promotion_met']}`",
            f"- Recursive structured fixtures: `{payload['external_summaries']['recursive_structured_fixture_count']}`",
            f"- Recursive structured ordinary later-win families: `{payload['external_summaries']['recursive_structured_ordinary_later_win_families']}`",
            f"- Recursive structured planted offset later-win families: `{payload['external_summaries']['recursive_structured_planted_offset_later_win_families']}`",
            f"- Recursive structured claim level: `{payload['external_summaries']['recursive_structured_claim_level']}`",
            f"- Recursive structured promotion met: `{payload['external_summaries']['recursive_structured_promotion_met']}`",
            f"- Scale performance largest scale MiB: `{payload['external_summaries']['scale_performance_largest_scale_mib']}`",
            f"- Scale performance peak memory MiB: `{payload['external_summaries']['scale_performance_largest_peak_memory_mib']}`",
            f"- Scale performance peak/table ratio: `{payload['external_summaries']['scale_performance_peak_table_ratio']}`",
            f"- Scale performance next-double peak MiB: `{payload['external_summaries']['scale_performance_next_double_peak_mib']}`",
            f"- Scale performance promotion met: `{payload['external_summaries']['scale_performance_promotion_met']}`",
            f"- UI workflow evidence keys: `{payload['external_summaries']['ui_workflow_ui_evidence_keys']}`",
            f"- UI workflow Tauri evidence fields: `{payload['external_summaries']['ui_workflow_tauri_evidence_fields']}`",
            f"- UI workflow required cards: `{payload['external_summaries']['ui_workflow_required_cards']}`",
            f"- UI workflow missing Tauri fields: `{payload['external_summaries']['ui_workflow_missing_tauri_fields']}`",
            f"- UI workflow missing mock fields: `{payload['external_summaries']['ui_workflow_missing_mock_fields']}`",
            f"- UI workflow claim level: `{payload['external_summaries']['ui_workflow_claim_level']}`",
            f"- UI workflow promotion met: `{payload['external_summaries']['ui_workflow_promotion_met']}`",
            f"- Vocabulary-disjoint shadow prefix>=5 win corpora: `{payload['external_summaries']['shadow_prefix5_win_corpora']}`",
            f"- Binary exact hits: `{payload['external_summaries']['binary_exact_hits']}`",
            f"- Structural transform candidates: `{payload['external_summaries']['structural_candidates']}`",
            f"- Structural transform validation rows: `{payload['external_summaries']['structural_validation_rows']}`",
            f"- Structural transform held-out prefix>=5 win corpora: `{payload['external_summaries']['structural_heldout_prefix5_win_corpora']}`",
            f"- Structural transform held-out exact hits: `{payload['external_summaries']['structural_heldout_exact_hits']}`",
            f"- Byte permutation transforms: `{payload['external_summaries']['byte_permutation_transforms']}`",
            f"- Byte permutation rows: `{payload['external_summaries']['byte_permutation_rows']}`",
            f"- Byte permutation prefix>=5 rows: `{payload['external_summaries']['byte_permutation_prefix5_rows']}`",
            f"- Byte permutation exact hits: `{payload['external_summaries']['byte_permutation_exact_hits']}`",
            f"- Byte permutation selected spans: `{payload['external_summaries']['byte_permutation_selected_spans']}`",
            f"- Byte permutation negative after metadata rows: `{payload['external_summaries']['byte_permutation_negative_after_metadata_rows']}`",
            f"- BWT/MTF transforms: `{payload['external_summaries']['bwt_mtf_transforms']}`",
            f"- BWT/MTF rows: `{payload['external_summaries']['bwt_mtf_rows']}`",
            f"- BWT/MTF prefix>=5 rows: `{payload['external_summaries']['bwt_mtf_prefix5_rows']}`",
            f"- BWT/MTF exact hits: `{payload['external_summaries']['bwt_mtf_exact_hits']}`",
            f"- BWT/MTF selected spans: `{payload['external_summaries']['bwt_mtf_selected_spans']}`",
            f"- BWT/MTF negative after metadata rows: `{payload['external_summaries']['bwt_mtf_negative_after_metadata_rows']}`",
            f"- BWT/MTF shorter transformed-payload rows: `{payload['external_summaries']['bwt_mtf_shorter_payload_rows']}`",
            f"- Grammar channel channels: `{payload['external_summaries']['grammar_channel_channels']}`",
            f"- Grammar channel rows: `{payload['external_summaries']['grammar_channel_rows']}`",
            f"- Grammar channel prefix>=5 rows: `{payload['external_summaries']['grammar_channel_prefix5_rows']}`",
            f"- Grammar channel exact hits: `{payload['external_summaries']['grammar_channel_exact_hits']}`",
            f"- Grammar channel selected spans: `{payload['external_summaries']['grammar_channel_selected_spans']}`",
            f"- Grammar channel negative after metadata rows: `{payload['external_summaries']['grammar_channel_negative_after_metadata_rows']}`",
            f"- Numeric value-channel channels: `{payload['external_summaries']['numeric_value_channel_channels']}`",
            f"- Numeric value-channel rows: `{payload['external_summaries']['numeric_value_channel_rows']}`",
            f"- Numeric value-channel parsed values: `{payload['external_summaries']['numeric_value_channel_parsed_values']}`",
            f"- Numeric value-channel prefix>=5 rows: `{payload['external_summaries']['numeric_value_channel_prefix5_rows']}`",
            f"- Numeric value-channel exact hits: `{payload['external_summaries']['numeric_value_channel_exact_hits']}`",
            f"- Numeric value-channel selected spans: `{payload['external_summaries']['numeric_value_channel_selected_spans']}`",
            f"- Numeric value-channel negative after metadata rows: `{payload['external_summaries']['numeric_value_channel_negative_after_metadata_rows']}`",
            f"- Record context transforms: `{payload['external_summaries']['record_context_transforms']}`",
            f"- Record context rows: `{payload['external_summaries']['record_context_rows']}`",
            f"- Record context prefix>=5 rows: `{payload['external_summaries']['record_context_prefix5_rows']}`",
            f"- Record context exact hits: `{payload['external_summaries']['record_context_exact_hits']}`",
            f"- Record context selected spans: `{payload['external_summaries']['record_context_selected_spans']}`",
            f"- Record context negative after metadata rows: `{payload['external_summaries']['record_context_negative_after_metadata_rows']}`",
            f"- Token dictionary transforms: `{payload['external_summaries']['token_dictionary_transforms']}`",
            f"- Token dictionary rows: `{payload['external_summaries']['token_dictionary_rows']}`",
            f"- Token dictionary prefix>=5 rows: `{payload['external_summaries']['token_dictionary_prefix5_rows']}`",
            f"- Token dictionary exact hits: `{payload['external_summaries']['token_dictionary_exact_hits']}`",
            f"- Token dictionary selected spans: `{payload['external_summaries']['token_dictionary_selected_spans']}`",
            f"- Token dictionary negative after metadata rows: `{payload['external_summaries']['token_dictionary_negative_after_metadata_rows']}`",
            f"- Affine transform searched candidates: `{payload['external_summaries']['affine_searched_candidates']}`",
            f"- Affine transform selected candidates: `{payload['external_summaries']['affine_selected_candidates']}`",
            f"- Affine transform held-out prefix>=4 win corpora: `{payload['external_summaries']['affine_heldout_prefix4_win_corpora']}`",
            f"- Affine transform held-out prefix>=5 win corpora: `{payload['external_summaries']['affine_heldout_prefix5_win_corpora']}`",
            f"- Affine transform held-out exact hits: `{payload['external_summaries']['affine_heldout_exact_hits']}`",
            f"- Residual sidecar candidate count: `{payload['external_summaries']['residual_candidate_count']}`",
            f"- Residual sidecar validation rows: `{payload['external_summaries']['residual_validation_rows']}`",
            f"- Residual sidecar held-out forced rows: `{payload['external_summaries']['residual_heldout_forced_rows']}`",
            f"- Residual sidecar held-out positive net-delta rows: `{payload['external_summaries']['residual_heldout_positive_rows']}`",
            f"- Residual sidecar best held-out net delta bytes: `{payload['external_summaries']['residual_best_heldout_net_delta_bytes']}`",
            f"- Sidecar break-even rows: `{payload['external_summaries']['sidecar_break_even_rows']}`",
            f"- Sidecar raw-suffix strict prefix: `{payload['external_summaries']['sidecar_raw_suffix_min_prefix']}`",
            f"- Sidecar max observed forced prefix: `{payload['external_summaries']['sidecar_max_observed_forced_prefix']}`",
            f"- Sidecar raw-suffix viable rows: `{payload['external_summaries']['sidecar_raw_suffix_viable_rows']}`",
            f"- Sidecar sublinear-model viable rows: `{payload['external_summaries']['sidecar_sublinear_viable_rows']}`",
            f"- Sidecar promoted rows: `{payload['external_summaries']['sidecar_promoted_rows']}`",
            f"- Residual payload held-out rows: `{payload['external_summaries']['residual_payload_heldout_rows']}`",
            f"- Residual payload measured negative rows: `{payload['external_summaries']['residual_payload_measured_negative_rows']}`",
            f"- Residual payload best measured case: `{payload['external_summaries']['residual_payload_best_measured_case']}`",
            f"- Residual payload zlib best delta: `{payload['external_summaries']['residual_payload_zlib_best_delta']}`",
            f"- Experimental sidecar descriptor rows: `{payload['external_summaries']['experimental_sidecar_rows']}`",
            f"- Experimental sidecar decode verified rows: `{payload['external_summaries']['experimental_sidecar_decode_verified_rows']}`",
            f"- Experimental sidecar full-stream negative rows: `{payload['external_summaries']['experimental_sidecar_full_stream_negative_rows']}`",
            f"- Experimental sidecar best full delta: `{payload['external_summaries']['experimental_sidecar_best_full_delta']}`",
            f"- Sidecar record negative layout rows: `{payload['external_summaries']['sidecar_record_negative_rows']}`",
            f"- Sidecar record best safe layout: `{payload['external_summaries']['sidecar_record_best_safe_layout']}`",
            f"- Sidecar record best safe delta: `{payload['external_summaries']['sidecar_record_best_safe_delta']}`",
            f"- Packed sidecar descriptor rows: `{payload['external_summaries']['packed_sidecar_rows']}`",
            f"- Packed sidecar full-stream negative rows: `{payload['external_summaries']['packed_sidecar_full_stream_negative_rows']}`",
            f"- Packed sidecar best coder: `{payload['external_summaries']['packed_sidecar_best_coder']}`",
            f"- Packed sidecar best delta: `{payload['external_summaries']['packed_sidecar_best_delta']}`",
            f"- Packed sidecar control rows: `{payload['external_summaries']['packed_controls_rows']}`",
            f"- Packed sidecar encoded control rows: `{payload['external_summaries']['packed_controls_encoded_rows']}`",
            f"- Packed sidecar unique negative cases: `{payload['external_summaries']['packed_controls_unique_negative_cases']}`",
            f"- Packed sidecar ordinary held-out negative cases: `{payload['external_summaries']['packed_controls_ordinary_heldout_negative_cases']}`",
            f"- Generalized packed encoded rows: `{payload['external_summaries']['generalized_packed_encoded_rows']}`",
            f"- Generalized packed unique encoded source rows: `{payload['external_summaries']['generalized_packed_unique_encoded_source_rows']}`",
            f"- Generalized packed unique negative cases: `{payload['external_summaries']['generalized_packed_unique_negative_cases']}`",
            f"- Generalized packed ordinary held-out negative cases: `{payload['external_summaries']['generalized_packed_ordinary_heldout_negative_cases']}`",
            f"- Packed sidecar replication source cases: `{payload['external_summaries']['packed_replication_source_cases']}`",
            f"- Packed sidecar replication descriptor rows: `{payload['external_summaries']['packed_replication_descriptor_rows']}`",
            f"- Packed sidecar replication full-stream negative rows: `{payload['external_summaries']['packed_replication_full_stream_negative_rows']}`",
            f"- Packed sidecar replication ordinary held-out negative groups: `{payload['external_summaries']['packed_replication_ordinary_heldout_negative_groups']}`",
            f"- Match discovery rows: `{payload['external_summaries']['match_discovery_rows']}`",
            f"- Match discovery target spans: `{payload['external_summaries']['match_discovery_target_spans']}`",
            f"- Match discovery prefix>=5 rows: `{payload['external_summaries']['match_discovery_prefix5_rows']}`",
            f"- Match discovery exact-hit rows: `{payload['external_summaries']['match_discovery_exact_hit_rows']}`",
            f"- Match discovery selected span rows: `{payload['external_summaries']['match_discovery_selected_span_rows']}`",
            f"- Match discovery total selected spans: `{payload['external_summaries']['match_discovery_total_selected_spans']}`",
            f"- Match discovery ordinary held-out selected groups: `{payload['external_summaries']['match_discovery_ordinary_heldout_selected_groups']}`",
            f"- Alignment and arity discovery rows: `{payload['external_summaries']['alignment_arity_rows']}`",
            f"- Alignment and arity discovery target spans: `{payload['external_summaries']['alignment_arity_target_spans']}`",
            f"- Alignment and arity discovery prefix>=5 rows: `{payload['external_summaries']['alignment_arity_prefix5_rows']}`",
            f"- Alignment and arity discovery exact hits: `{payload['external_summaries']['alignment_arity_exact_hits']}`",
            f"- Alignment and arity discovery positive exact hits: `{payload['external_summaries']['alignment_arity_positive_exact_hits']}`",
            f"- Alignment and arity discovery selected spans: `{payload['external_summaries']['alignment_arity_selected_spans']}`",
            f"- Transformed match discovery rows: `{payload['external_summaries']['transformed_match_rows']}`",
            f"- Transformed match discovery target spans: `{payload['external_summaries']['transformed_match_target_spans']}`",
            f"- Transformed match discovery prefix>=5 rows: `{payload['external_summaries']['transformed_match_prefix5_rows']}`",
            f"- Transformed match discovery exact hits: `{payload['external_summaries']['transformed_match_exact_hits']}`",
            f"- Transformed match discovery selected spans: `{payload['external_summaries']['transformed_match_selected_spans']}`",
            f"- Transformed match discovery metadata-profitable rows: `{payload['external_summaries']['transformed_match_metadata_profitable_rows']}`",
            f"- Lead exact discovery rows: `{payload['external_summaries']['lead_exact_rows']}`",
            f"- Lead exact discovery target spans: `{payload['external_summaries']['lead_exact_target_spans']}`",
            f"- Lead exact discovery prefix>=5 rows: `{payload['external_summaries']['lead_exact_prefix5_rows']}`",
            f"- Lead exact discovery exact hits: `{payload['external_summaries']['lead_exact_exact_hits']}`",
            f"- Lead exact discovery selected spans: `{payload['external_summaries']['lead_exact_selected_spans']}`",
            f"- Lead exact discovery metadata-profitable rows: `{payload['external_summaries']['lead_exact_metadata_profitable_rows']}`",
            "",
            "## Source Hashes",
            "",
        ]
    )
    for name, digest in payload["source_hashes"].items():
        lines.append(f"- `{name}`: `{digest}`")

    lines.extend(["", "## Artifact Hashes", ""])
    for name, digest in payload["artifact_hashes"].items():
        lines.append(f"- `{name}`: `{digest}`")

    lines.extend(["", "## Evidence Hashes", ""])
    for name, digest in payload["evidence_hashes"].items():
        lines.append(f"- `{name}`: `{digest}`")

    GOAL_AUDIT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_audit() -> None:
    if not GOAL_AUDIT_JSON.exists() or not GOAL_AUDIT_MD.exists():
        raise SystemExit("generated goal audit files are missing")
    payload = load_json(GOAL_AUDIT_JSON)
    if payload.get("generated_by") != "scripts/generate_goal_audit.py":
        raise SystemExit("goal_audit.json has wrong generated_by marker")
    if payload.get("source_hashes") != hashes(SOURCE_PATHS):
        raise SystemExit("goal_audit.json source hashes are stale")
    if payload.get("artifact_hashes") != hashes(ARTIFACT_PATHS):
        raise SystemExit("goal_audit.json artifact hashes are stale")
    expected_evidence_hashes = evidence_hashes(payload.get("entries", []))
    if payload.get("evidence_hashes") != expected_evidence_hashes:
        raise SystemExit("goal_audit.json evidence hashes are stale")
    if payload.get("missing_expected_results"):
        raise SystemExit("goal_audit.json is missing expected generated-result rows")
    if payload.get("verdict") != "research-viable, not production-proven":
        raise SystemExit("goal audit must not claim production proof")
    text = GOAL_AUDIT_MD.read_text(encoding="utf-8")
    for phrase in (
        "architecture-implemented; research-viable; not production-proven",
        "canonical requirement-to-evidence ledger",
        "Corpus generalization controls",
        "Held-out corpus expansion",
        "Audit Matrix",
        "Unresolved Gates",
        "Held-out exact hits",
        "Structural transform held-out exact hits",
        "Byte permutation exact hits",
        "BWT/MTF exact hits",
        "Grammar channel exact hits",
        "Numeric value-channel exact hits",
        "Record context exact hits",
        "Token dictionary exact hits",
        "Affine transform held-out exact hits",
        "Residual sidecar held-out positive net-delta rows",
        "Sidecar break-even rows",
        "Residual payload measured negative rows",
        "Experimental sidecar full-stream negative rows",
        "Sidecar record negative layout rows",
        "Packed sidecar full-stream negative rows",
        "Packed sidecar ordinary held-out negative cases",
        "Generalized packed ordinary held-out negative cases",
        "Packed sidecar replication full-stream negative rows",
        "Match discovery rows",
        "Match discovery selected span rows",
        "Alignment and arity discovery target spans",
        "Alignment and arity discovery selected spans",
        "Transformed match discovery target spans",
        "Transformed match discovery metadata-profitable rows",
        "Lead exact discovery target spans",
        "Lead exact discovery metadata-profitable rows",
        "Lead depth-3 follow-up selected spans",
        "Depth-3 frontier exact hits",
        "Depth-4 shard status",
        "Depth-4 pilot exact hits",
        "Search frontier status",
        "Search frontier selected spans",
        "Mechanism experiment ranking top lane",
        "Seed-table preset probe",
        "Exact short-hit bundle economics",
        "Whole-stream residual vector probe",
        "Expander salt ensemble",
        "Schema-native public dictionary",
        "Schema-native public dictionary replication",
        "Superposition telemetry",
        "Long-span bundle",
        "Recursive structured",
        "Scale performance",
        "UI workflow",
    ):
        if phrase not in text:
            raise SystemExit(f"GOAL_AUDIT.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate generated goal audit files")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.check:
        check_audit()
        return
    write_audit(build_audit())


if __name__ == "__main__":
    main()
