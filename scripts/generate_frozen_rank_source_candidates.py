#!/usr/bin/env python3
"""Generate frozen-rank external source candidate requirements.

This is the source-candidate layer before actual corpus accession. It does not
fetch or store external bytes. It defines the minimum families, independence
groups, paired controls, license review requirements, and stop rules needed
before rank-table payload accession or replay can be proposed.
"""

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
REPORT_JSON = DOCS / "frozen_rank_source_candidates.json"
REPORT_MD = DOCS / "FROZEN_RANK_SOURCE_CANDIDATES.md"
GENERATED_BY = "scripts/generate_frozen_rank_source_candidates.py"

SOURCE_PATHS = {
    "next_mechanism_designs_sha256": DOCS / "next_mechanism_designs.json",
    "natural_corpus_reopen_manifest_sha256": DOCS / "natural_corpus_reopen_manifest.json",
    "public_preset_control_rerun_sha256": DOCS / "public_preset_control_rerun.json",
    "search_frontier_gate_sha256": DOCS / "search_frontier_gate.json",
    "frozen_rank_source_candidates_generator_sha256": ROOT
    / "scripts"
    / "generate_frozen_rank_source_candidates.py",
}

REQUIRED_CONTROL_KINDS = [
    "paired-shadow-control",
    "random-control",
    "wrong-family-control",
]

OPTIONAL_CONTROL_KINDS = [
    "binary-control",
    "high-entropy-control",
    "generic-token-dictionary-control",
]

SOURCE_FAMILIES = [
    {
        "candidate_id": "standards-protocol-text",
        "family_id": "standards-protocol-text",
        "independence_group": "public-standards-protocol",
        "ordinary_source_requirement": (
            "Externally published protocol or interchange specification text with "
            "explicit redistribution terms and stable retrieval metadata."
        ),
        "rank_signal_target": "headers, field names, delimiters, and common MIME-style values",
        "paired_shadow_rule": (
            "Construct vocabulary-disjoint protocol-shaped text with the same line, "
            "field, and delimiter histogram but no shared semantic labels."
        ),
        "wrong_family_rule": "Replay against schema/config rank entries only.",
    },
    {
        "candidate_id": "schema-and-config",
        "family_id": "schema-and-config",
        "independence_group": "public-schema-config",
        "ordinary_source_requirement": (
            "Externally published schema/configuration examples or specifications "
            "with explicit license and no Telomere/project tokens."
        ),
        "rank_signal_target": "keys, separators, structural punctuation, and common type labels",
        "paired_shadow_rule": (
            "Construct schema-shaped text with shadow keys and value labels while "
            "preserving punctuation and nesting depth."
        ),
        "wrong_family_rule": "Replay against protocol-header rank entries only.",
    },
    {
        "candidate_id": "records-and-ledgers",
        "family_id": "records-and-ledgers",
        "independence_group": "public-record-ledger",
        "ordinary_source_requirement": (
            "Externally published tabular/ledger-like examples with explicit "
            "provenance, stable hashes, and no project-local identifiers."
        ),
        "rank_signal_target": "column labels, delimiters, timestamp/status motifs, and record separators",
        "paired_shadow_rule": (
            "Construct ledger-shaped text with shadow column labels and same row/field "
            "histograms."
        ),
        "wrong_family_rule": "Replay against protocol and schema rank entries only.",
    },
    {
        "candidate_id": "source-code",
        "family_id": "source-code",
        "independence_group": "public-source-code",
        "ordinary_source_requirement": (
            "Externally licensed source-code snippets or fixtures with explicit "
            "license compatibility review and no target-project identifiers."
        ),
        "rank_signal_target": "language keywords, braces, imports/includes, comments, and separators",
        "paired_shadow_rule": (
            "Construct source-shaped text with shadow identifiers and equivalent "
            "token-class histograms."
        ),
        "wrong_family_rule": "Replay against non-source rank entries only.",
    },
]

STOP_RULES = [
    "Do not add payload bytes until license and redistribution review is explicit.",
    "Do not replay until every ordinary candidate has paired shadow and random controls.",
    "Do not treat source candidates as external corpus accession or natural-corpus proof.",
    "Do not count same-family or project-token leakage as ordinary signal.",
    "Do not build a rank table from target or held-out files.",
]


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


def candidate_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for rank, family in enumerate(SOURCE_FAMILIES, start=1):
        rows.append(
            {
                **family,
                "rank": rank,
                "candidate_status": "candidate_only_license_review_required",
                "required_controls": REQUIRED_CONTROL_KINDS,
                "optional_controls": OPTIONAL_CONTROL_KINDS,
                "source_uri_status": "not_selected",
                "payload_status": "not_acquired",
                "ready_for_external_manifest": False,
                "ready_for_replay": False,
            }
        )
    return rows


def build_report() -> dict[str, Any]:
    next_designs = summary(load_json(DOCS / "next_mechanism_designs.json"))
    reopen = summary(load_json(DOCS / "natural_corpus_reopen_manifest.json"))
    public_rerun = summary(load_json(DOCS / "public_preset_control_rerun.json"))
    search = summary(load_json(DOCS / "search_frontier_gate.json"))
    if next_designs.get("top_design_id") != "frozen-rank-coded-span-generator":
        raise RuntimeError("source candidates expect frozen-rank to remain the top next mechanism")
    rows = candidate_rows()
    status_counts = Counter(row["candidate_status"] for row in rows)
    ready_for_manifest = sum(1 for row in rows if row["ready_for_external_manifest"])
    ready_for_replay = sum(1 for row in rows if row["ready_for_replay"])
    required_manifest_rows = len(rows) * (1 + len(REQUIRED_CONTROL_KINDS))
    return {
        "generated_by": GENERATED_BY,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "scope": {
            "kind": "frozen rank source candidate requirements",
            "performs_seed_search": False,
            "performs_replay": False,
            "fetches_external_sources": False,
            "stores_external_payloads": False,
            "launches_agents": False,
            "makes_compression_claim": False,
            "is_format_support": False,
            "is_natural_corpus_proof": False,
            "allows_broad_compute": False,
            "overrides_search_frontier_gate": False,
        },
        "source_hashes": source_hashes(),
        "summary": {
            "candidate_status": "candidate_matrix_only",
            "candidate_family_count": len(rows),
            "status_counts": dict(sorted(status_counts.items())),
            "ready_for_external_manifest_count": ready_for_manifest,
            "ready_for_replay_count": ready_for_replay,
            "required_control_kind_count": len(REQUIRED_CONTROL_KINDS),
            "required_external_manifest_row_count": required_manifest_rows,
            "top_design_id": next_designs.get("top_design_id"),
            "natural_corpus_first_allowed_stage": reopen.get("first_allowed_stage"),
            "public_preset_rerun_status": public_rerun.get("rerun_status"),
            "broad_depth_search_allowed": bool(
                search.get("broad_depth_search_allowed", False)
            ),
            "compute_allowed": False,
            "replay_allowed": False,
            "promotion_ready": False,
            "natural_corpus_proven": False,
            "claim_boundary": (
                "No Seed Search; source-candidate requirements only; not corpus "
                "accession; not natural-corpus proof; not `.tlmr` format support."
            ),
            "next_allowed_action": (
                "select externally licensed source URIs and create payload manifest "
                "rows with paired controls, then rerun external accession validation"
            ),
            "conclusion": (
                "The frozen-rank lane now has an acquisition matrix, but no source "
                "candidate is ready for the external manifest or replay."
            ),
        },
        "source_candidate_requirements": {
            "ordinary_row_per_family": 1,
            "required_controls_per_ordinary": REQUIRED_CONTROL_KINDS,
            "optional_controls_per_ordinary": OPTIONAL_CONTROL_KINDS,
            "minimum_independence_groups_for_promotion": 3,
            "required_manifest_rows_before_replay": required_manifest_rows,
            "license_review_required": True,
            "payload_hash_required": True,
            "leave_family_out_required": True,
            "project_token_removal_required": True,
            "external_manifest_integration_rule": (
                "External accession may consume this matrix; this matrix must not "
                "consume external accession outputs."
            ),
        },
        "candidate_rows": rows,
        "stop_rules": STOP_RULES,
    }


def cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def write_report(payload: dict[str, Any]) -> None:
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    data = payload["summary"]
    reqs = payload["source_candidate_requirements"]
    lines = [
        "# Frozen Rank Source Candidates",
        "",
        f"Generated by `{GENERATED_BY}` from the next-mechanism registry and natural-corpus reopen gate.",
        "This is a No Seed Search source-candidate requirements artifact. It fetches no external sources, stores no payload bytes, performs no replay, is not corpus accession, is not natural-corpus proof, and is not `.tlmr` format support.",
        "",
        "## Summary",
        "",
        f"- Candidate status: `{data['candidate_status']}`",
        f"- Candidate families: `{data['candidate_family_count']}`",
        f"- Ready for external manifest: `{data['ready_for_external_manifest_count']}`",
        f"- Ready for replay: `{data['ready_for_replay_count']}`",
        f"- Required external manifest rows before replay: `{data['required_external_manifest_row_count']}`",
        f"- Top design: `{data['top_design_id']}`",
        f"- Natural-corpus first allowed stage: `{data['natural_corpus_first_allowed_stage']}`",
        f"- Compute allowed: `{data['compute_allowed']}`",
        f"- Replay allowed: `{data['replay_allowed']}`",
        f"- Promotion ready: `{data['promotion_ready']}`",
        "",
        data["conclusion"],
        "",
        "## Accession Requirements",
        "",
        f"- Ordinary rows per family: `{reqs['ordinary_row_per_family']}`",
        f"- Required controls per ordinary: {', '.join(f'`{item}`' for item in reqs['required_controls_per_ordinary'])}",
        f"- Optional controls per ordinary: {', '.join(f'`{item}`' for item in reqs['optional_controls_per_ordinary'])}",
        f"- Minimum independence groups for promotion: `{reqs['minimum_independence_groups_for_promotion']}`",
        f"- Required manifest rows before replay: `{reqs['required_manifest_rows_before_replay']}`",
        f"- License review required: `{reqs['license_review_required']}`",
        f"- Payload hash required: `{reqs['payload_hash_required']}`",
        f"- Leave-family-out required: `{reqs['leave_family_out_required']}`",
        f"- Project-token removal required: `{reqs['project_token_removal_required']}`",
        f"- External manifest integration rule: {reqs['external_manifest_integration_rule']}",
        "",
        "## Candidate Matrix",
        "",
        "| rank | family | group | status | ready for manifest | ready for replay | rank signal target |",
        "| ---: | --- | --- | --- | --- | --- | --- |",
    ]
    for row in payload["candidate_rows"]:
        lines.append(
            f"| {row['rank']} | `{cell(row['family_id'])}` | "
            f"`{cell(row['independence_group'])}` | `{cell(row['candidate_status'])}` | "
            f"`{row['ready_for_external_manifest']}` | `{row['ready_for_replay']}` | "
            f"{cell(row['rank_signal_target'])} |"
        )
    lines.extend(["", "## Candidate Details", ""])
    for row in payload["candidate_rows"]:
        lines.extend(
            [
                f"### {row['candidate_id']}",
                "",
                f"- Ordinary source requirement: {row['ordinary_source_requirement']}",
                f"- Paired shadow rule: {row['paired_shadow_rule']}",
                f"- Wrong-family rule: {row['wrong_family_rule']}",
                f"- Required controls: {', '.join(f'`{item}`' for item in row['required_controls'])}",
                f"- Optional controls: {', '.join(f'`{item}`' for item in row['optional_controls'])}",
                f"- Source URI status: `{row['source_uri_status']}`",
                f"- Payload status: `{row['payload_status']}`",
                "",
            ]
        )
    lines.extend(["## Stop Rules", ""])
    for rule in payload["stop_rules"]:
        lines.append(f"- {rule}")
    lines.extend(
        [
            "",
            "## Source Artifacts",
            "",
            "The JSON `source_hashes` map pins this candidate matrix to exact upstream evidence and generator files below.",
        ]
    )
    for name, digest in payload["source_hashes"].items():
        lines.append(f"- `{name}`: `{digest}`")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not REPORT_JSON.exists() or not REPORT_MD.exists():
        raise SystemExit("generated frozen rank source candidate files are missing")
    payload = load_json(REPORT_JSON)
    if payload.get("generated_by") != GENERATED_BY:
        raise SystemExit("frozen_rank_source_candidates.json has wrong generated_by marker")
    if payload.get("source_hashes") != source_hashes():
        raise SystemExit("frozen rank source candidate hashes are stale")
    expected = stable_projection(build_report())
    current = stable_projection(payload)
    if current != expected:
        raise SystemExit("frozen_rank_source_candidates.json is stale; regenerate it")
    scope = payload.get("scope", {})
    for field in (
        "performs_seed_search",
        "performs_replay",
        "fetches_external_sources",
        "stores_external_payloads",
        "launches_agents",
        "makes_compression_claim",
        "is_format_support",
        "is_natural_corpus_proof",
        "allows_broad_compute",
        "overrides_search_frontier_gate",
    ):
        if scope.get(field) is not False:
            raise SystemExit(f"frozen rank source candidate scope field must be false: {field}")
    data = payload["summary"]
    if data["ready_for_external_manifest_count"] != 0:
        raise SystemExit("source candidates cannot be manifest-ready before URI/license review")
    if data["ready_for_replay_count"] != 0 or data["replay_allowed"]:
        raise SystemExit("source candidates cannot authorize replay")
    if data["compute_allowed"] or data["promotion_ready"]:
        raise SystemExit("source candidates cannot authorize compute or promotion")
    if data["natural_corpus_proven"]:
        raise SystemExit("source candidates cannot claim natural-corpus proof")
    required_rows = payload["source_candidate_requirements"][
        "required_manifest_rows_before_replay"
    ]
    if required_rows != len(payload["candidate_rows"]) * (1 + len(REQUIRED_CONTROL_KINDS)):
        raise SystemExit("source candidate required manifest row count is stale")
    text = REPORT_MD.read_text(encoding="utf-8")
    for phrase in (
        "Frozen Rank Source Candidates",
        "No Seed Search",
        "fetches no external sources",
        "stores no payload bytes",
        "performs no replay",
        "not corpus accession",
        "not natural-corpus proof",
        "Accession Requirements",
        "Candidate Matrix",
        "Stop Rules",
        "source_hashes",
    ):
        if phrase not in text:
            raise SystemExit(f"FROZEN_RANK_SOURCE_CANDIDATES.md missing phrase: {phrase}")


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
