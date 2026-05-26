#!/usr/bin/env python3
"""Generate a post-experiment mechanism closure audit.

The original mechanism ranking is intentionally upstream of the bounded
mechanism artifacts it recommends. This downstream audit consumes those
completed artifacts and states what is still runnable now.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
REPORT_JSON = DOCS / "mechanism_closure_audit.json"
REPORT_MD = DOCS / "MECHANISM_CLOSURE_AUDIT.md"
GENERATED_BY = "scripts/generate_mechanism_closure_audit.py"

SOURCE_PATHS = {
    "mechanism_experiment_ranking_sha256": DOCS / "mechanism_experiment_ranking.json",
    "search_frontier_gate_sha256": DOCS / "search_frontier_gate.json",
    "seed_table_preset_probe_sha256": DOCS / "seed_table_preset_probe.json",
    "seed_table_preset_replay_sha256": DOCS / "seed_table_preset_replay.json",
    "seed_table_fasta_ablation_sha256": DOCS / "seed_table_fasta_ablation.json",
    "exact_short_hit_bundle_economics_sha256": DOCS
    / "exact_short_hit_bundle_economics.json",
    "whole_stream_residual_vector_probe_sha256": DOCS
    / "whole_stream_residual_vector_probe.json",
    "expander_salt_ensemble_sha256": DOCS / "expander_salt_ensemble.json",
    "schema_native_public_dictionary_replication_sha256": DOCS
    / "schema_native_public_dictionary_replication.json",
    "public_preset_promotion_gate_sha256": DOCS / "public_preset_promotion_gate.json",
    "public_preset_control_rerun_sha256": DOCS / "public_preset_control_rerun.json",
    "superposition_telemetry_sha256": DOCS / "superposition_telemetry.json",
    "lattice_selection_heldout_probe_sha256": DOCS
    / "lattice_selection_heldout_probe.json",
    "recursive_structured_fixtures_sha256": DOCS
    / "recursive_structured_fixtures.json",
    "long_span_bundle_gate_sha256": DOCS / "long_span_bundle_gate.json",
    "mechanism_closure_generator_sha256": ROOT
    / "scripts"
    / "generate_mechanism_closure_audit.py",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes() -> dict[str, str]:
    return {name: sha256(path) for name, path in SOURCE_PATHS.items()}


def stable_projection(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if key != "generated_at"}


def summary(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("summary", {})
    return value if isinstance(value, dict) else {}


def source_key(name: str) -> str:
    return name.removesuffix("_sha256")


def source_inputs() -> dict[str, dict[str, Any]]:
    return {
        source_key(name): load_json(path)
        for name, path in SOURCE_PATHS.items()
        if path.suffix == ".json"
    }


def lane(
    lane_id: str,
    title: str,
    status: str,
    outcome: str,
    evidence: str,
    next_action: str,
    source_artifacts: list[str],
) -> dict[str, Any]:
    return {
        "lane_id": lane_id,
        "title": title,
        "status": status,
        "outcome": outcome,
        "evidence": evidence,
        "next_action": next_action,
        "source_artifacts": source_artifacts,
    }


def build_lanes(inputs: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    seed = summary(inputs["seed_table_preset_probe"])
    replay = summary(inputs["seed_table_preset_replay"])
    fasta = summary(inputs["seed_table_fasta_ablation"])
    exact_short = summary(inputs["exact_short_hit_bundle_economics"])
    whole_stream = summary(inputs["whole_stream_residual_vector_probe"])
    expander = summary(inputs["expander_salt_ensemble"])
    schema = summary(inputs["schema_native_public_dictionary_replication"])
    public_gate = summary(inputs["public_preset_promotion_gate"])
    public_rerun = summary(inputs["public_preset_control_rerun"])
    superposition = summary(inputs["superposition_telemetry"])
    lattice = summary(inputs["lattice_selection_heldout_probe"])
    recursive = summary(inputs["recursive_structured_fixtures"])
    long_span = summary(inputs["long_span_bundle_gate"])

    return [
        lane(
            "seed-table-preset-probe",
            "Canonical seed-table / Lotus preset probe",
            "blocked-by-evidence",
            "completed_without_promotion",
            (
                f"probe promotion={seed.get('promotion_met')}; replay promotion="
                f"{replay.get('promotion_candidate')}; FASTA header artifact="
                f"{fasta.get('header_artifact_likely')} with "
                f"{fasta.get('total_header_selected_spans')} header spans and "
                f"{fasta.get('total_sequence_selected_spans')} sequence spans"
            ),
            "Do not rerun this lane until a materially new decoder-public preset is designed.",
            [
                "docs/SEED_TABLE_PRESET_PROBE.md",
                "docs/SEED_TABLE_PRESET_REPLAY.md",
                "docs/SEED_TABLE_FASTA_ABLATION.md",
            ],
        ),
        lane(
            "exact-short-hit-bundle-economics",
            "Exact short-hit bundle economics",
            "blocked-by-evidence",
            "controls_comparable",
            (
                f"promotion={exact_short.get('promotion_met')}; ordinary groups="
                f"{exact_short.get('full_stream_ordinary_negative_groups')}; "
                f"control groups={exact_short.get('full_stream_control_negative_groups')}; "
                f"control density comparable={exact_short.get('control_density', {}).get('control_density_comparable')}"
            ),
            "Do not promote short-hit bundling while controls remain comparable.",
            ["docs/EXACT_SHORT_HIT_BUNDLE_ECONOMICS.md"],
        ),
        lane(
            "whole-stream-residual-vector-probe",
            "Whole-stream residual vector probe",
            "blocked-by-evidence",
            "no_honest_negative_rows",
            (
                f"promotion={whole_stream.get('promotion_met')}; honest negative rows="
                f"{whole_stream.get('honest_full_stream_negative_rows')}; ordinary groups="
                f"{whole_stream.get('ordinary_heldout_negative_groups')}"
            ),
            "Keep as null evidence until a new residual mechanism changes held-out groups.",
            ["docs/WHOLE_STREAM_RESIDUAL_VECTOR_PROBE.md"],
        ),
        lane(
            "expander-salt-ensemble",
            "Expander salt / preset ensemble",
            "blocked-by-evidence",
            "random_trial_multiplier_not_beaten",
            (
                f"promotion={expander.get('promotion_met')}; salted exact hits="
                f"{expander.get('salted_exact_hits')}; random multiplier exceeded="
                f"{expander.get('random_trial_multiplier_exceeded')}"
            ),
            "Do not broaden salt ensembles unless a non-random byte-to-seed mechanism is introduced.",
            ["docs/EXPANDER_SALT_ENSEMBLE.md"],
        ),
        lane(
            "schema-native-public-dictionaries",
            "Schema-native public dictionaries",
            "blocked-by-evidence",
            "blocked_by_controls",
            (
                f"schema claim={schema.get('claim_level')}; public gate promotion="
                f"{public_gate.get('promotion_met')}; rerun status="
                f"{public_rerun.get('rerun_status')}; leave-family-out clean groups="
                f"{public_rerun.get('leave_family_out_no_project_ordinary_negative_groups')}"
            ),
            "Design a new decoder-public preset only if it can survive paired shadow controls.",
            [
                "docs/SCHEMA_NATIVE_PUBLIC_DICTIONARY_REPLICATION.md",
                "docs/PUBLIC_PRESET_PROMOTION_GATE.md",
                "docs/PUBLIC_PRESET_CONTROL_RERUN.md",
            ],
        ),
        lane(
            "candidate-lattice-telemetry",
            "Candidate lattice telemetry",
            "maintenance-only",
            "selector_correctness_only",
            (
                f"fixture promotion={superposition.get('promotion_met')}; held-out "
                f"lattice promotion={lattice.get('promotion_met')}; weighted extra "
                f"held-out groups={lattice.get('ordinary_weighted_extra_groups')}"
            ),
            "Use for auditability, not as a compute lane or compression claim.",
            ["docs/SUPERPOSITION_TELEMETRY.md", "docs/LATTICE_SELECTION_HELDOUT_PROBE.md"],
        ),
        lane(
            "recursive-structured-fixtures",
            "Recursive v2 structured fixtures",
            "blocked-by-evidence",
            "planted_offset_only",
            (
                f"promotion={recursive.get('promotion_met')}; ordinary later-win families="
                f"{recursive.get('ordinary_later_win_families')}; planted offset families="
                f"{recursive.get('planted_offset_later_win_families')}"
            ),
            "Do not claim recursive natural-corpus gain without ordinary later-layer wins.",
            ["docs/RECURSIVE_STRUCTURED_FIXTURES.md"],
        ),
        lane(
            "long-span-bundle-gate",
            "Long-span bundle gate",
            "blocked-by-evidence",
            "top_blocked_gate",
            (
                f"promotion={long_span.get('promotion_met')}; gates met="
                f"{long_span.get('gate_met_count')}/{long_span.get('gate_count')}; "
                f"recommendation={long_span.get('recommendation')}"
            ),
            "Treat this as the top blocked gate; do not run broad long-span sweeps.",
            ["docs/LONG_SPAN_BUNDLE_GATE.md"],
        ),
    ]


def build_report() -> dict[str, Any]:
    inputs = source_inputs()
    search = summary(inputs["search_frontier_gate"])
    ranking = summary(inputs["mechanism_experiment_ranking"])
    lanes = build_lanes(inputs)
    ready_compute_lanes = [
        row for row in lanes if row["status"] == "ready"
    ]
    blocked_lanes = [row for row in lanes if row["status"] == "blocked-by-evidence"]
    maintenance_lanes = [row for row in lanes if row["status"] == "maintenance-only"]
    top_blocked = next(
        row for row in lanes if row["lane_id"] == "long-span-bundle-gate"
    )
    summary_payload = {
        "closure_status": "no_ready_mechanism_compute",
        "ready_compute_lane_count": len(ready_compute_lanes),
        "blocked_by_evidence_lane_count": len(blocked_lanes),
        "maintenance_only_lane_count": len(maintenance_lanes),
        "initial_ranking_top_lane": ranking.get("top_lane_id"),
        "initial_ranking_ready_count": ranking.get("ready_count"),
        "top_blocked_lane": top_blocked["lane_id"],
        "top_blocked_status": top_blocked["status"],
        "top_blocked_next_action": top_blocked["next_action"],
        "broad_depth_search_allowed": search.get("broad_depth_search_allowed", False),
        "format_promotion_allowed": search.get("format_promotion_allowed", False),
        "natural_corpus_proven": False,
        "production_proven": False,
        "allowed_work": "maintenance, audit, falsifiable-design only",
        "forbidden_work": (
            "No broad raw depth search, long-span sweeps, format promotion, public "
            "preset promotion, sidecar packing, or production GPU work until "
            "generated gates move."
        ),
        "conclusion": (
            "All current bounded mechanism lanes are closed, blocked, or "
            "maintenance-only; the next scientific move must be a materially new "
            "byte-to-seed mechanism or a stronger reversible frontier generator."
        ),
    }
    return {
        "generated_by": GENERATED_BY,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "scope": {
            "kind": "post-experiment mechanism closure audit",
            "performs_seed_search": False,
            "launches_agents": False,
            "makes_compression_claim": False,
            "is_format_support": False,
            "is_natural_corpus_proof": False,
            "allows_broad_compute": False,
        },
        "source_hashes": source_hashes(),
        "summary": summary_payload,
        "lanes": lanes,
    }


def cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def write_report(payload: dict[str, Any]) -> None:
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary_payload = payload["summary"]
    lines = [
        "# Mechanism Closure Audit",
        "",
        f"Generated by `{GENERATED_BY}` from completed bounded mechanism artifacts.",
        "This is a No Seed Search closure artifact. It launches no agents, performs no broad seed search, is not natural-corpus proof, is not production proof, and is not `.tlmr` format support.",
        "",
        "## Summary",
        "",
        f"- Closure status: `{summary_payload['closure_status']}`",
        f"- Ready compute lanes: `{summary_payload['ready_compute_lane_count']}`",
        f"- Blocked-by-evidence lanes: `{summary_payload['blocked_by_evidence_lane_count']}`",
        f"- Maintenance-only lanes: `{summary_payload['maintenance_only_lane_count']}`",
        f"- Initial ranking top lane: `{summary_payload['initial_ranking_top_lane']}`",
        f"- Initial ranking ready count: `{summary_payload['initial_ranking_ready_count']}`",
        f"- Top blocked lane: `{summary_payload['top_blocked_lane']}`",
        f"- Broad depth search allowed: `{summary_payload['broad_depth_search_allowed']}`",
        f"- Format promotion allowed: `{summary_payload['format_promotion_allowed']}`",
        f"- Allowed work: `{summary_payload['allowed_work']}`",
        f"- Forbidden work: `{summary_payload['forbidden_work']}`",
        "",
        summary_payload["conclusion"],
        "",
        "## Lane Closure",
        "",
        "| lane | status | outcome | next action |",
        "| --- | --- | --- | --- |",
    ]
    for row in payload["lanes"]:
        lines.append(
            f"| `{cell(row['lane_id'])}` | `{cell(row['status'])}` | "
            f"`{cell(row['outcome'])}` | {cell(row['next_action'])} |"
        )
    lines.extend(
        [
            "",
            "## Source Artifacts",
            "",
            "The JSON `source_hashes` map pins this closure audit to exact upstream evidence and generator files below.",
        ]
    )
    for name, digest in payload["source_hashes"].items():
        lines.append(f"- `{name}`: `{digest}`")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not REPORT_JSON.exists() or not REPORT_MD.exists():
        raise SystemExit("generated mechanism closure audit files are missing")
    payload = load_json(REPORT_JSON)
    if payload.get("generated_by") != GENERATED_BY:
        raise SystemExit("mechanism_closure_audit.json has wrong generated_by marker")
    if payload.get("source_hashes") != source_hashes():
        raise SystemExit("mechanism closure audit source hashes are stale")
    expected = stable_projection(build_report())
    current = stable_projection(payload)
    if current != expected:
        raise SystemExit("mechanism_closure_audit.json is stale; regenerate it")
    scope = payload.get("scope", {})
    for field in (
        "performs_seed_search",
        "launches_agents",
        "makes_compression_claim",
        "is_format_support",
        "is_natural_corpus_proof",
        "allows_broad_compute",
    ):
        if scope.get(field) is not False:
            raise SystemExit(f"mechanism closure audit scope field must be false: {field}")
    summary_payload = payload["summary"]
    if summary_payload["ready_compute_lane_count"] != 0:
        raise SystemExit("mechanism closure audit must not report ready compute lanes")
    text = REPORT_MD.read_text(encoding="utf-8")
    for phrase in (
        "Mechanism Closure Audit",
        "No Seed Search",
        "Ready compute lanes",
        "Top blocked lane",
        "source_hashes",
        "not natural-corpus proof",
        "not `.tlmr` format support",
    ):
        if phrase not in text:
            raise SystemExit(f"MECHANISM_CLOSURE_AUDIT.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate generated files")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.check:
        check_report()
        return
    write_report(build_report())


if __name__ == "__main__":
    main()
