#!/usr/bin/env python3
"""Generate a static smoke report for the Tauri/UI research-ledger workflow."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
UI_INDEX = ROOT / "ui" / "index.html"
TAURI_MAIN = ROOT / "src-tauri" / "src" / "main.rs"
REPORT_JSON = DOCS / "ui_workflow_smoke.json"
REPORT_MD = DOCS / "UI_WORKFLOW_SMOKE.md"
GENERATED_BY = "scripts/generate_ui_workflow_smoke.py"

REQUIRED_ARTIFACTS = [
    "goal_audit.json",
    "goal_completion_audit.json",
    "blocked_requirement_dispatch.json",
    "natural_corpus_proof_matrix.json",
    "production_proof_matrix.json",
    "experiment_queue.json",
    "research_frontier.json",
    "research_team_protocol.json",
    "research_scorecard.json",
    "nearmiss_forecast.json",
    "transform_validation.json",
    "heldout_corpus_expansion.json",
    "match_discovery.json",
    "lead_exact_discovery.json",
    "exact_short_hit_bundle_economics.json",
    "whole_stream_residual_vector_probe.json",
    "expander_salt_ensemble.json",
    "schema_native_public_dictionaries.json",
    "schema_native_public_dictionary_replication.json",
    "superposition_telemetry.json",
    "recursive_structured_fixtures.json",
    "scale_performance_report.json",
    "depth4_pilot_shard.json",
    "acceleration_report.json",
]

REQUIRED_CARD_IDS = [
    "goal-audit",
    "goal-completion-audit",
    "blocked-requirement-dispatch",
    "natural-corpus-proof",
    "production-proof",
    "scorecard",
    "queue",
    "research-frontier",
    "research-team-protocol",
    "near-miss",
    "transform-validation",
    "heldout-expansion",
    "exact-discovery",
    "exact-short-economics",
    "whole-stream-residual",
    "expander-salt",
    "schema-native-dictionaries",
    "schema-replication",
    "superposition-telemetry",
    "recursive-structured-fixtures",
    "scale-performance",
    "acceleration",
]

REQUIRED_TAURI_SNIPPETS = [
    "pub struct ResearchEvidenceSummary",
    "pub struct ResearchArtifactsResult",
    "fn load_research_artifacts_from_docs",
    "fn research_artifacts",
    "recursive_structured_fixtures.json",
    "scale_performance_report.json",
    "research_frontier.json",
    "research_team_protocol.json",
    "goal_completion_audit.json",
    "blocked_requirement_dispatch.json",
    "natural_corpus_proof_matrix.json",
    "production_proof_matrix.json",
]

REQUIRED_UI_SNIPPETS = [
    'id="evidenceGates"',
    'id="ledgerCards"',
    "function loadResearchArtifacts",
    "function renderResearchArtifacts",
    "recursive_structured_ordinary_later_win_families",
    "scale_performance_peak_table_ratio",
    "frontier_ungated_compute_allowed",
    "research_team_protocol_status",
    "goal_completion_recommendation",
    "blocked_dispatch_status",
    "natural_corpus_status",
    "production_status",
]


SOURCE_PATHS = {
    "ui_index_sha256": UI_INDEX,
    "tauri_main_sha256": TAURI_MAIN,
    "generator_sha256": ROOT / GENERATED_BY,
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes() -> dict[str, str]:
    return {name: sha256(path) for name, path in SOURCE_PATHS.items()}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def extract_ui_evidence_keys(text: str) -> list[str]:
    return sorted(set(re.findall(r"evidence\.([A-Za-z_][A-Za-z0-9_]*)", text)))


def extract_tauri_evidence_fields(text: str) -> list[str]:
    match = re.search(
        r"pub struct ResearchEvidenceSummary\s*\{(?P<body>.*?)\n\}",
        text,
        re.S,
    )
    if not match:
        return []
    return sorted(
        set(re.findall(r"pub\s+([A-Za-z_][A-Za-z0-9_]*)\s*:", match.group("body")))
    )


def extract_mock_evidence_keys(text: str) -> list[str]:
    match = re.search(
        r"evidence:\s*\{(?P<body>.*?)\n\s*\},\n\s*cards:",
        text,
        re.S,
    )
    if not match:
        return []
    return sorted(
        set(
            re.findall(
                r"^\s*([A-Za-z_][A-Za-z0-9_]*):",
                match.group("body"),
                re.M,
            )
        )
    )


def extract_tauri_card_ids(text: str) -> list[str]:
    return sorted(set(re.findall(r'id:\s*"([^"]+)"', text)))


def extract_tauri_artifact_loads(text: str) -> list[str]:
    return sorted(set(re.findall(r'docs_dir\.join\("([^"]+\.json)"\)', text)))


def missing_snippets(text: str, snippets: list[str]) -> list[str]:
    return [snippet for snippet in snippets if snippet not in text]


def artifact_parse_failures() -> list[str]:
    failures = []
    for artifact in REQUIRED_ARTIFACTS:
        path = DOCS / artifact
        if not path.exists():
            failures.append(f"{artifact}: missing")
            continue
        try:
            load_json(path)
        except json.JSONDecodeError as exc:
            failures.append(f"{artifact}: {exc}")
    return failures


def build_report() -> dict[str, Any]:
    ui_text = UI_INDEX.read_text(encoding="utf-8")
    tauri_text = TAURI_MAIN.read_text(encoding="utf-8")
    ui_evidence_keys = extract_ui_evidence_keys(ui_text)
    tauri_fields = extract_tauri_evidence_fields(tauri_text)
    mock_keys = extract_mock_evidence_keys(ui_text)
    card_ids = extract_tauri_card_ids(tauri_text)
    artifact_loads = extract_tauri_artifact_loads(tauri_text)
    missing_tauri_fields = sorted(set(ui_evidence_keys) - set(tauri_fields))
    missing_mock_fields = sorted(set(ui_evidence_keys) - set(mock_keys))
    missing_required_cards = sorted(set(REQUIRED_CARD_IDS) - set(card_ids))
    missing_required_artifact_loads = sorted(
        set(REQUIRED_ARTIFACTS) - set(artifact_loads)
    )
    missing_required_artifact_files = sorted(
        artifact for artifact in REQUIRED_ARTIFACTS if not (DOCS / artifact).exists()
    )
    parse_failures = artifact_parse_failures()
    missing_tauri_snippets = missing_snippets(tauri_text, REQUIRED_TAURI_SNIPPETS)
    missing_ui_snippets = missing_snippets(ui_text, REQUIRED_UI_SNIPPETS)
    promotion_met = not any(
        [
            missing_tauri_fields,
            missing_mock_fields,
            missing_required_cards,
            missing_required_artifact_loads,
            missing_required_artifact_files,
            parse_failures,
            missing_tauri_snippets,
            missing_ui_snippets,
        ]
    )
    summary = {
        "ui_evidence_key_count": len(ui_evidence_keys),
        "tauri_evidence_field_count": len(tauri_fields),
        "mock_evidence_key_count": len(mock_keys),
        "tauri_card_count": len(card_ids),
        "required_card_count": len(REQUIRED_CARD_IDS),
        "required_artifact_count": len(REQUIRED_ARTIFACTS),
        "tauri_artifact_load_count": len(artifact_loads),
        "missing_tauri_fields": missing_tauri_fields,
        "missing_mock_fields": missing_mock_fields,
        "missing_required_cards": missing_required_cards,
        "missing_required_artifact_loads": missing_required_artifact_loads,
        "missing_required_artifact_files": missing_required_artifact_files,
        "artifact_parse_failures": parse_failures,
        "missing_tauri_snippets": missing_tauri_snippets,
        "missing_ui_snippets": missing_ui_snippets,
        "promotion_met": promotion_met,
        "claim_level": (
            "ui_workflow_static_smoke_passed"
            if promotion_met
            else "ui_workflow_static_smoke_failed"
        ),
        "stop_rule": (
            "Do not call the desktop workflow covered unless this static schema "
            "smoke and the Tauri command tests stay green."
        ),
        "conclusion": (
            "The evidence ledger panel and Tauri research-artifact DTO are statically aligned."
            if promotion_met
            else "The UI/Tauri research-ledger contract has drifted."
        ),
    }
    return {
        "generated_by": GENERATED_BY,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "source_hashes": source_hashes(),
        "summary": summary,
        "ui_evidence_keys": ui_evidence_keys,
        "tauri_evidence_fields": tauri_fields,
        "mock_evidence_keys": mock_keys,
        "tauri_card_ids": card_ids,
        "tauri_artifact_loads": artifact_loads,
    }


def write_report(payload: dict[str, Any]) -> None:
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary = payload["summary"]
    lines = [
        "# Telomere UI Workflow Smoke",
        "",
        f"Generated by `{GENERATED_BY}` from the static UI and Tauri host sources.",
        "This is a static UI/Tauri schema smoke, not a substitute for a desktop browser run.",
        "",
        "## Summary",
        "",
        f"- UI evidence keys: `{summary['ui_evidence_key_count']}`",
        f"- Tauri evidence fields: `{summary['tauri_evidence_field_count']}`",
        f"- Mock preview evidence keys: `{summary['mock_evidence_key_count']}`",
        f"- Required cards: `{summary['required_card_count']}`",
        f"- Required artifacts: `{summary['required_artifact_count']}`",
        f"- Promotion met: `{summary['promotion_met']}`",
        f"- Claim level: `{summary['claim_level']}`",
        "",
        summary["conclusion"],
        "",
        "## Coverage Checks",
        "",
        f"- `missing_tauri_fields`: `{summary['missing_tauri_fields']}`",
        f"- `missing_mock_fields`: `{summary['missing_mock_fields']}`",
        f"- Missing required cards: `{summary['missing_required_cards']}`",
        f"- Missing required artifact loads: `{summary['missing_required_artifact_loads']}`",
        f"- Missing required artifact files: `{summary['missing_required_artifact_files']}`",
        f"- Artifact parse failures: `{summary['artifact_parse_failures']}`",
        f"- Missing Tauri snippets: `{summary['missing_tauri_snippets']}`",
        f"- Missing UI snippets: `{summary['missing_ui_snippets']}`",
        "",
        "## Evidence Ledger Panel",
        "",
        "The smoke check verifies that every `evidence.*` key rendered by the panel "
        "exists in `ResearchEvidenceSummary` and in the static mock preview object.",
        "",
        "## Required Cards",
        "",
    ]
    for card_id in REQUIRED_CARD_IDS:
        lines.append(f"- `{card_id}`")
    lines.extend(["", "## Stop Rule", ""])
    lines.append(f"- {summary['stop_rule']}")
    lines.extend(["", "## Source Artifacts", ""])
    for name, digest in payload["source_hashes"].items():
        lines.append(f"- `{name}`: `{digest}`")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not REPORT_JSON.exists() or not REPORT_MD.exists():
        raise SystemExit("generated UI workflow smoke files are missing")
    payload = load_json(REPORT_JSON)
    if payload.get("generated_by") != GENERATED_BY:
        raise SystemExit("ui_workflow_smoke.json has wrong generated_by marker")
    if payload.get("source_hashes") != source_hashes():
        raise SystemExit("UI workflow smoke source hashes are stale")
    expected = build_report()["summary"]
    current = payload.get("summary", {})
    comparable_keys = [key for key in expected if key not in {"conclusion"}]
    for key in comparable_keys:
        if current.get(key) != expected[key]:
            raise SystemExit(f"UI workflow smoke summary field is stale: {key}")
    if not current.get("promotion_met"):
        raise SystemExit("UI workflow smoke did not pass")
    text = REPORT_MD.read_text(encoding="utf-8")
    for phrase in (
        "Telomere UI Workflow Smoke",
        f"Generated by `{GENERATED_BY}`",
        "static UI/Tauri schema smoke",
        "evidence ledger panel",
        "missing_tauri_fields",
        "missing_mock_fields",
        "Required Cards",
        "Stop Rule",
    ):
        if phrase not in text:
            raise SystemExit(f"UI_WORKFLOW_SMOKE.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate generated UI workflow smoke report",
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
