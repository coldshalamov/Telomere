#!/usr/bin/env python3
"""Generate the Telomere mechanism-experiment ranking from current evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
REPORT_JSON = DOCS / "mechanism_experiment_ranking.json"
REPORT_MD = DOCS / "MECHANISM_EXPERIMENT_RANKING.md"

SOURCE_PATHS = {
    "search_frontier_gate_sha256": DOCS / "search_frontier_gate.json",
    "structural_transform_search_sha256": DOCS / "structural_transform_search.json",
    "byte_permutation_transform_search_sha256": DOCS
    / "byte_permutation_transform_search.json",
    "bwt_mtf_transform_probe_sha256": DOCS / "bwt_mtf_transform_probe.json",
    "grammar_channel_match_discovery_sha256": DOCS
    / "grammar_channel_match_discovery.json",
    "numeric_value_channel_match_discovery_sha256": DOCS
    / "numeric_value_channel_match_discovery.json",
    "record_context_transform_search_sha256": DOCS
    / "record_context_transform_search.json",
    "token_dictionary_transform_search_sha256": DOCS
    / "token_dictionary_transform_search.json",
    "affine_transform_search_sha256": DOCS / "affine_transform_search.json",
    "seed_manifold_residual_steering_sha256": DOCS
    / "seed_manifold_residual_steering.json",
    "sidecar_break_even_sha256": DOCS / "sidecar_break_even.json",
    "residual_payload_compressibility_sha256": DOCS
    / "residual_payload_compressibility.json",
    "experimental_sidecar_descriptor_sha256": DOCS
    / "experimental_sidecar_descriptor.json",
    "sidecar_record_overhead_sha256": DOCS / "sidecar_record_overhead.json",
    "packed_sidecar_descriptor_sha256": DOCS / "packed_sidecar_descriptor.json",
    "packed_sidecar_controls_sha256": DOCS / "packed_sidecar_controls.json",
    "generalized_packed_sidecar_sha256": DOCS / "generalized_packed_sidecar.json",
    "packed_sidecar_replication_sha256": DOCS / "packed_sidecar_replication.json",
    "match_discovery_sha256": DOCS / "match_discovery.json",
    "alignment_arity_discovery_sha256": DOCS / "alignment_arity_discovery.json",
    "transformed_match_discovery_sha256": DOCS / "transformed_match_discovery.json",
    "lead_exact_discovery_sha256": DOCS / "lead_exact_discovery.json",
    "corpus_generalization_probe_sha256": DOCS / "corpus_generalization_probe.json",
    "heldout_corpus_expansion_sha256": DOCS / "heldout_corpus_expansion.json",
    "transform_validation_sha256": DOCS / "transform_validation.json",
    "periodic_transform_probe_sha256": DOCS / "periodic_transform_probe.json",
    "composed_transform_probe_sha256": DOCS / "composed_transform_probe.json",
    "fifth_byte_residual_sha256": DOCS / "fifth_byte_residual.json",
    "fifth_byte_steering_sha256": DOCS / "fifth_byte_steering.json",
    "contextual_fifth_byte_steering_sha256": DOCS
    / "contextual_fifth_byte_steering.json",
}

VALID_STATUSES = {"ready", "gated", "blocked-by-evidence"}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_hashes() -> dict[str, str]:
    return {name: sha256(path) for name, path in SOURCE_PATHS.items()}


def summary(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("summary", {})
    return value if isinstance(value, dict) else {}


def scoring_manifest() -> dict[str, Any]:
    return {
        "purpose": "rank next mechanism experiments from generated evidence",
        "not_a_compression_claim": True,
        "not_format_support": True,
        "broad_raw_depth_requires_search_frontier_gate": True,
        "format_promotion_requires_search_frontier_gate": True,
        "ranking_policy": [
            "prefer mechanisms that change byte-to-seed mapping over raw-depth escalation",
            "prefer exact decode paths over transform-only byte shortening",
            "penalize wins that also appear in paired shadows, binary controls, or random controls",
            "block format work until selected exact spans exist after metadata",
            "block hardware work until CPU evidence finds a promoted workload",
        ],
        "required_row_fields": [
            "promotion_gate",
            "stop_rule",
            "source_artifacts",
            "evidence_signal",
            "control_penalty",
            "next_artifact",
        ],
    }


def scoring_manifest_hash() -> str:
    payload = json.dumps(
        scoring_manifest(), sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def ranked_rows(inputs: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    search_gate = summary(inputs["search_frontier_gate"])
    residual_payload = summary(inputs["residual_payload_compressibility"])
    packed_replication = summary(inputs["packed_sidecar_replication"])
    alignment = summary(inputs["alignment_arity_discovery"])
    sidecar_break_even = summary(inputs["sidecar_break_even"])
    grammar = summary(inputs["grammar_channel_match_discovery"])
    record_context = summary(inputs["record_context_transform_search"])
    token_dictionary = summary(inputs["token_dictionary_transform_search"])
    match = summary(inputs["match_discovery"])
    lead_exact = summary(inputs["lead_exact_discovery"])
    transformed = summary(inputs["transformed_match_discovery"])

    selected_total = sum(
        int(value)
        for value in (
            search_gate.get("selected_span_total", 0),
            match.get("total_selected_spans", 0),
            alignment.get("total_selected_spans", 0),
            transformed.get("total_selected_spans", 0),
            lead_exact.get("total_selected_spans", 0),
            grammar.get("total_selected_spans", 0),
            record_context.get("total_selected_spans", 0),
            token_dictionary.get("total_selected_spans", 0),
        )
    )
    broad_depth_open = bool(search_gate.get("broad_depth_search_allowed", False))
    format_open = bool(search_gate.get("format_promotion_allowed", False))

    return [
        {
            "rank": 1,
            "lane_id": "seed-table-preset-probe",
            "title": "Canonical seed-table / Lotus preset probe",
            "status": "ready",
            "requires_broad_raw_depth": False,
            "requires_format_promotion": False,
            "next_artifact": "docs/SEED_TABLE_PRESET_PROBE.md",
            "evidence_signal": (
                "Uniform cryptographic expanders currently have zero selected spans, "
                "so the strongest next question is whether a frozen public "
                "corpus-shaped codebook changes the byte-to-seed distribution."
            ),
            "material_difference": (
                "Changes the deterministic expander/codebook instead of transforming "
                "target bytes or searching deeper through the same random-looking "
                "SHA/BLAKE output space."
            ),
            "promotion_gate": (
                "Freeze discovery and held-out splits before table construction; "
                "require ordinary_heldout_negative_groups >= 3, "
                "control_negative_groups == 0, exact decode from preset/version "
                "metadata only, and improvement beyond equivalent random-trial "
                "scaling."
            ),
            "stop_rule": (
                "Stop if held-out wins disappear, controls win similarly, selected "
                "spans remain zero, or gains require training on the same file being "
                "compressed."
            ),
            "control_penalty": (
                "High unless random, binary, compressed, and vocabulary-shadow "
                "controls stay null."
            ),
            "source_artifacts": [
                "search_frontier_gate",
                "match_discovery",
                "transformed_match_discovery",
                "lead_exact_discovery",
            ],
        },
        {
            "rank": 2,
            "lane_id": "exact-short-hit-bundle-economics",
            "title": "Exact short-hit bundle economics",
            "status": "ready",
            "requires_broad_raw_depth": False,
            "requires_format_promotion": False,
            "next_artifact": "docs/EXACT_SHORT_HIT_BUNDLE_ECONOMICS.md",
            "evidence_signal": (
                f"Alignment/arity discovery has {alignment.get('total_exact_hits', 0)} "
                "verified exact short hits, but "
                f"{alignment.get('total_positive_exact_hits', 0)} positive exact hits "
                "and zero selected spans under current byte-heavy records."
            ),
            "material_difference": (
                "Uses already verified exact hits and attacks shared offset/seed/config "
                "overhead instead of spending more seed search."
            ),
            "promotion_gate": (
                "Only use pre-existing verified hits; require full-stream negative "
                "delta after all shared table/checksum/config bytes and at least two "
                "unrelated ordinary held-out groups."
            ),
            "stop_rule": (
                "Stop if the zero-overhead lower bound is not negative or controls "
                "show comparable short-hit density."
            ),
            "control_penalty": "High because current exact hits are short, unprofitable, and control-like.",
            "source_artifacts": [
                "alignment_arity_discovery",
                "sidecar_record_overhead",
                "packed_sidecar_controls",
            ],
        },
        {
            "rank": 3,
            "lane_id": "whole-stream-residual-vector-probe",
            "title": "Whole-stream residual vector probe",
            "status": "ready",
            "requires_broad_raw_depth": False,
            "requires_format_promotion": False,
            "next_artifact": "docs/WHOLE_STREAM_RESIDUAL_VECTOR_PROBE.md",
            "evidence_signal": (
                "Residual payload coders produced "
                f"{residual_payload.get('measured_heldout_negative_rows', 0)} "
                "measured held-out negative row, but frozen packed replication has "
                f"{packed_replication.get('ordinary_heldout_negative_groups', 0)} "
                "ordinary held-out negative groups."
            ),
            "material_difference": (
                "Tests global residual entropy and bitplane/vector channels instead "
                "of narrow prefix-suffix residual sidecars."
            ),
            "promotion_gate": (
                "Require exact decode, corrupt rejection, all residual/offset/seed "
                "metadata charged, ordinary_heldout_negative_groups >= 3, controls "
                "null, and measured residual coding near the entropy bound."
            ),
            "stop_rule": (
                "Stop if residual entropy remains random-like, replication stays at "
                "zero negative ordinary groups, or per-file tuning exceeds savings."
            ),
            "control_penalty": "Medium-high because the latest packed replication matrix is null.",
            "source_artifacts": [
                "seed_manifold_residual_steering",
                "sidecar_break_even",
                "residual_payload_compressibility",
                "packed_sidecar_replication",
            ],
        },
        {
            "rank": 4,
            "lane_id": "expander-salt-ensemble",
            "title": "Expander salt / preset ensemble",
            "status": "ready",
            "requires_broad_raw_depth": False,
            "requires_format_promotion": False,
            "next_artifact": "docs/EXPANDER_SALT_ENSEMBLE.md",
            "evidence_signal": (
                "Current BLAKE3/SHA-256 style uniform outputs have no selected spans; "
                "a predeclared salt/preset ensemble tests whether low-cost manifold "
                "rotation beats the expected random-trial multiplier."
            ),
            "material_difference": (
                "Adds a file/layer-level expander selector instead of longer seeds; "
                "selector cost is charged once."
            ),
            "promotion_gate": (
                "Predeclare presets, charge preset IDs, compare against equivalent "
                "extra random trials, and require selected exact spans after metadata."
            ),
            "stop_rule": (
                "Stop if gains match only the random-trial multiplier or full-stream "
                "negative rows remain absent."
            ),
            "control_penalty": "Medium because multiple uniform functions can mimic extra depth.",
            "source_artifacts": [
                "search_frontier_gate",
                "affine_transform_search",
                "fifth_byte_residual",
            ],
        },
        {
            "rank": 5,
            "lane_id": "schema-native-public-dictionaries",
            "title": "Schema-native public dictionaries",
            "status": "ready",
            "requires_broad_raw_depth": False,
            "requires_format_promotion": False,
            "next_artifact": "docs/SCHEMA_NATIVE_PUBLIC_DICTIONARIES.md",
            "evidence_signal": (
                "Simple grammar/token/record channels have zero exact selected spans, "
                "but public versioned schema dictionaries may test a stronger "
                "corpus-shaped preset without per-file training."
            ),
            "material_difference": (
                "Uses frozen public schema dictionaries as generator presets rather "
                "than storing per-file grammar sidecars."
            ),
            "promotion_gate": (
                "Freeze schema preset, forbid held-out leakage, require unrelated "
                "held-out files in the schema family to shrink, and paired shadow "
                "vocab controls to stay null."
            ),
            "stop_rule": (
                "Stop if renamed/shadow controls perform the same or schema metadata "
                "eats all savings."
            ),
            "control_penalty": "Medium-high because prior simple grammar/token lanes are null.",
            "source_artifacts": [
                "grammar_channel_match_discovery",
                "token_dictionary_transform_search",
                "record_context_transform_search",
                "transform_validation",
            ],
        },
        {
            "rank": 6,
            "lane_id": "candidate-lattice-telemetry",
            "title": "Candidate lattice telemetry",
            "status": "ready",
            "requires_broad_raw_depth": False,
            "requires_format_promotion": False,
            "next_artifact": "docs/SUPERPOSITION_TELEMETRY.md",
            "evidence_signal": (
                "The current engine uses weighted non-overlap selection, but the "
                "whitepaper superposition claim needs retained/rejected candidate "
                "telemetry before wider research can be trusted."
            ),
            "material_difference": (
                "Improves auditability and selection correctness rather than hit rate."
            ),
            "promotion_gate": (
                "A deterministic overlap fixture shows retained alternatives beating "
                "greedy selection, with every discarded candidate explained."
            ),
            "stop_rule": (
                "Keep as correctness work only if it does not change selected spans "
                "or reveal missed profitable alternatives."
            ),
            "control_penalty": "Low for correctness; not natural-corpus proof.",
            "source_artifacts": [
                "alignment_arity_discovery",
                "match_discovery",
                "search_frontier_gate",
            ],
        },
        {
            "rank": 7,
            "lane_id": "recursive-structured-fixtures",
            "title": "Recursive v2 structured fixtures",
            "status": "ready",
            "requires_broad_raw_depth": False,
            "requires_format_promotion": False,
            "next_artifact": "docs/RECURSIVE_STRUCTURED_FIXTURES.md",
            "evidence_signal": (
                "Recursive v2 decode exists, but natural recursive gain is still an "
                "open claim outside planted or deliberately constructed cases."
            ),
            "material_difference": (
                "Tests the pass-to-pass transformation thesis directly on generated "
                "structured fixtures."
            ),
            "promotion_gate": (
                "At least two non-offset fixture families produce smaller verified "
                "later layers after all v2 layer metadata is charged."
            ),
            "stop_rule": (
                "Do not generalize recursion if later layers help only planted offset "
                "fixtures or disappear at container level."
            ),
            "control_penalty": "Medium because structured fixtures are mechanism proof, not prevalence proof.",
            "source_artifacts": [
                "search_frontier_gate",
                "heldout_corpus_expansion",
                "corpus_generalization_probe",
            ],
        },
        {
            "rank": 8,
            "lane_id": "long-span-bundle-gate",
            "title": "Long-span bundle gate",
            "status": "gated",
            "requires_broad_raw_depth": True,
            "requires_format_promotion": False,
            "next_artifact": "docs/LONG_SPAN_BUNDLE_GATE.md",
            "evidence_signal": (
                "Raw-suffix strict gain starts around prefix "
                f"{sidecar_break_even.get('minimum_raw_suffix_negative_prefix_len')}, "
                "but current held-out forced prefixes stop before that."
            ),
            "material_difference": (
                "Can amortize metadata only after a stronger frontier supplies "
                "candidate spans."
            ),
            "promotion_gate": (
                "Require prefix>=6, exact hits, selected spans, or sub-1-GiB forecast "
                "before long-span sweeps run."
            ),
            "stop_rule": (
                "Stay gated while SEARCH_FRONTIER_GATE reports broad raw depth closed "
                "and selected spans remain zero."
            ),
            "control_penalty": "High until the frontier gate opens.",
            "source_artifacts": [
                "sidecar_break_even",
                "search_frontier_gate",
            ],
        },
        {
            "rank": 9,
            "lane_id": "format-extension-prototype",
            "title": "Format extension prototype",
            "status": "blocked-by-evidence",
            "requires_broad_raw_depth": False,
            "requires_format_promotion": True,
            "next_artifact": "docs/FORMAT.md",
            "evidence_signal": (
                "Current selected-span total is "
                f"{selected_total}; format metadata should follow evidence, not "
                "manufacture it."
            ),
            "material_difference": (
                "Turns a proved mechanism into a compatibility contract; it is not "
                "a discovery mechanism."
            ),
            "promotion_gate": (
                "A mechanism has exact decode, corrupt-input rejection, controls, "
                "golden vectors, and at least two unrelated ordinary wins."
            ),
            "stop_rule": "Reject format work while exact selected spans remain absent.",
            "control_penalty": "Very high because format promotion is currently closed.",
            "source_artifacts": [
                "search_frontier_gate",
                "packed_sidecar_replication",
                "lead_exact_discovery",
            ],
        },
        {
            "rank": 10,
            "lane_id": "hardware-streaming-pipeline",
            "title": "Hardware streaming pipeline",
            "status": "blocked-by-evidence",
            "requires_broad_raw_depth": False,
            "requires_format_promotion": False,
            "next_artifact": "docs/ACCELERATION.md",
            "evidence_signal": (
                "Hardware can reduce runtime only after CPU evidence identifies a "
                "profitable selected-span workload."
            ),
            "material_difference": (
                "Improves throughput, not hit probability."
            ),
            "promotion_gate": (
                "CPU streaming finds repeatable selected spans but misses the "
                "archival runtime envelope."
            ),
            "stop_rule": "Stop if GPU output diverges from CPU parity or lacks a promoted workload.",
            "control_penalty": "High cost and low value before hit-rate evidence.",
            "source_artifacts": [
                "search_frontier_gate",
                "match_discovery",
            ],
        },
    ]


def enforce_gate_invariants(
    rows: list[dict[str, Any]], search_gate: dict[str, Any]
) -> None:
    broad_depth_open = bool(
        search_gate.get("summary", {}).get("broad_depth_search_allowed", False)
    )
    format_open = bool(
        search_gate.get("summary", {}).get("format_promotion_allowed", False)
    )
    for row in rows:
        if row["requires_broad_raw_depth"] and not broad_depth_open and row["status"] == "ready":
            raise AssertionError(
                f"{row['lane_id']} cannot be ready while broad raw depth is closed"
            )
        if row["requires_format_promotion"] and not format_open and row["status"] == "ready":
            raise AssertionError(
                f"{row['lane_id']} cannot be ready while format promotion is closed"
            )


def build_report() -> dict[str, Any]:
    inputs = {
        key.removesuffix("_sha256"): load_json(path)
        for key, path in SOURCE_PATHS.items()
    }
    rows = ranked_rows(inputs)
    enforce_gate_invariants(rows, inputs["search_frontier_gate"])
    search_gate = summary(inputs["search_frontier_gate"])
    selected_total = int(search_gate.get("selected_span_total", 0))
    exact_hit_rows = sum(
        int(summary(inputs[name]).get("rows_with_exact_hits", 0))
        for name in (
            "match_discovery",
            "transformed_match_discovery",
            "lead_exact_discovery",
            "grammar_channel_match_discovery",
            "numeric_value_channel_match_discovery",
            "record_context_transform_search",
            "token_dictionary_transform_search",
        )
    )
    status_counts = {
        status: sum(1 for row in rows if row["status"] == status)
        for status in sorted(VALID_STATUSES)
    }
    recommended = rows[0]

    return {
        "generated_by": "scripts/generate_mechanism_experiment_ranking.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "artifact_hashes": artifact_hashes(),
        "scoring_manifest_sha256": scoring_manifest_hash(),
        "scoring_manifest": scoring_manifest(),
        "summary": {
            "ranking_count": len(rows),
            "ready_count": status_counts["ready"],
            "gated_count": status_counts["gated"],
            "blocked_by_evidence_count": status_counts["blocked-by-evidence"],
            "top_lane_id": recommended["lane_id"],
            "top_next_artifact": recommended["next_artifact"],
            "top_status": recommended["status"],
            "search_frontier_status": search_gate.get("recommended_status"),
            "broad_depth_search_allowed": search_gate.get(
                "broad_depth_search_allowed", False
            ),
            "format_promotion_allowed": search_gate.get(
                "format_promotion_allowed", False
            ),
            "selected_span_total": selected_total,
            "exact_hit_rows_across_recent_discovery": exact_hit_rows,
            "natural_corpus_compression_proven": False,
            "conclusion": (
                "Run seed-table preset probing before raw-depth escalation, "
                "format promotion, descriptor packing, or hardware acceleration."
            ),
        },
        "rankings": rows,
    }


def write_report(payload: dict[str, Any]) -> None:
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary_payload = payload["summary"]
    lines = [
        "# Telomere Mechanism Experiment Ranking",
        "",
        "Generated by scripts/generate_mechanism_experiment_ranking.py.",
        "This is evidence triage, not a compression claim and not .tlmr format support.",
        "",
        "## Summary",
        "",
        f"- Ranked rows: `{summary_payload['ranking_count']}`",
        f"- Ready: `{summary_payload['ready_count']}`",
        f"- Gated: `{summary_payload['gated_count']}`",
        f"- Blocked by evidence: `{summary_payload['blocked_by_evidence_count']}`",
        f"- Top lane: `{summary_payload['top_lane_id']}`",
        f"- Top next artifact: `{summary_payload['top_next_artifact']}`",
        f"- Search frontier: `{summary_payload['search_frontier_status']}`",
        f"- Selected spans: `{summary_payload['selected_span_total']}`",
        f"- Natural-corpus compression proven: `{summary_payload['natural_corpus_compression_proven']}`",
        f"- Scoring policy SHA-256: `{payload['scoring_manifest_sha256']}`",
        "",
        "No broad raw depth search while SEARCH_FRONTIER_GATE is closed.",
        "",
        summary_payload["conclusion"],
        "",
        "## Ranked Mechanism Experiments",
        "",
        "| rank | lane | status | next artifact | evidence signal |",
        "| ---: | --- | --- | --- | --- |",
    ]
    for row in payload["rankings"]:
        lines.append(
            f"| {row['rank']} | `{row['lane_id']}` | {row['status']} | `{row['next_artifact']}` | {row['evidence_signal']} |"
        )

    lines.extend(["", "## Details", ""])
    for row in payload["rankings"]:
        lines.extend(
            [
                f"### {row['rank']}. `{row['lane_id']}`",
                "",
                f"Title: {row['title']}",
                "",
                f"Material difference: {row['material_difference']}",
                "",
                f"Promotion gate: {row['promotion_gate']}",
                "",
                f"Stop rule: {row['stop_rule']}",
                "",
                f"Control penalty: {row['control_penalty']}",
                "",
                "Source artifacts: "
                + ", ".join(f"`{artifact}`" for artifact in row["source_artifacts"]),
                "",
            ]
        )

    lines.extend(["## Source Artifacts", ""])
    for key, value in payload["artifact_hashes"].items():
        lines.append(f"- `{key}`: `{value}`")

    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not REPORT_JSON.exists() or not REPORT_MD.exists():
        raise SystemExit("generated mechanism experiment ranking files are missing")
    payload = load_json(REPORT_JSON)
    if payload.get("generated_by") != "scripts/generate_mechanism_experiment_ranking.py":
        raise SystemExit("mechanism_experiment_ranking.json has wrong generated_by marker")
    if payload.get("artifact_hashes") != artifact_hashes():
        raise SystemExit("mechanism_experiment_ranking.json artifact hashes are stale")
    if payload.get("scoring_manifest_sha256") != scoring_manifest_hash():
        raise SystemExit("mechanism_experiment_ranking.json scoring manifest is stale")
    rows = payload.get("rankings", [])
    if not rows:
        raise SystemExit("mechanism_experiment_ranking.json has no rankings")
    ranks = [row.get("rank") for row in rows]
    if ranks != list(range(1, len(rows) + 1)):
        raise SystemExit("mechanism_experiment_ranking.json ranks are not contiguous")
    lane_ids = [row.get("lane_id") for row in rows]
    if len(lane_ids) != len(set(lane_ids)):
        raise SystemExit("mechanism_experiment_ranking.json lane IDs are not unique")
    required = {
        "promotion_gate",
        "stop_rule",
        "source_artifacts",
        "evidence_signal",
        "control_penalty",
        "next_artifact",
    }
    for row in rows:
        if row.get("status") not in VALID_STATUSES:
            raise SystemExit(f"invalid mechanism status: {row.get('status')}")
        missing = sorted(required - set(row))
        if missing:
            raise SystemExit(f"{row.get('lane_id')} missing fields: {missing}")
    search_gate = load_json(SOURCE_PATHS["search_frontier_gate_sha256"])
    enforce_gate_invariants(rows, search_gate)
    if (
        payload.get("summary", {}).get("selected_span_total", 0) == 0
        and payload.get("summary", {}).get("natural_corpus_compression_proven")
    ):
        raise SystemExit("ranking must not claim natural-corpus compression proof")
    text = REPORT_MD.read_text(encoding="utf-8")
    for phrase in (
        "Telomere Mechanism Experiment Ranking",
        "Generated by scripts/generate_mechanism_experiment_ranking.py",
        "evidence triage, not a compression claim",
        "not .tlmr format support",
        "No broad raw depth search while SEARCH_FRONTIER_GATE is closed",
        "Ranked Mechanism Experiments",
        "Promotion gate",
        "Stop rule",
        "Control penalty",
        "Source Artifacts",
        "Scoring policy SHA-256",
    ):
        if phrase not in text:
            raise SystemExit(f"MECHANISM_EXPERIMENT_RANKING.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="validate generated mechanism ranking"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.check:
        check_report()
        return
    write_report(build_report())


if __name__ == "__main__":
    main()
