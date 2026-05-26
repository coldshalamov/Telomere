#!/usr/bin/env python3
"""Generate the natural-corpus reopen manifest.

The current ledgers block natural-corpus viability. This manifest pre-registers
the only evidence that can reopen that blocker without launching broad seed
search: external corpus provenance, paired controls, exact promotion triggers,
and parallel-agent briefs.
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
REPORT_JSON = DOCS / "natural_corpus_reopen_manifest.json"
REPORT_MD = DOCS / "NATURAL_CORPUS_REOPEN_MANIFEST.md"
GENERATED_BY = "scripts/generate_natural_corpus_reopen_manifest.py"

SOURCE_PATHS = {
    "natural_corpus_proof_matrix_sha256": DOCS / "natural_corpus_proof_matrix.json",
    "blocked_requirement_dispatch_sha256": DOCS / "blocked_requirement_dispatch.json",
    "research_frontier_sha256": DOCS / "research_frontier.json",
    "search_frontier_gate_sha256": DOCS / "search_frontier_gate.json",
    "long_span_bundle_gate_sha256": DOCS / "long_span_bundle_gate.json",
    "heldout_corpus_expansion_sha256": DOCS / "heldout_corpus_expansion.json",
    "match_discovery_sha256": DOCS / "match_discovery.json",
    "transform_validation_sha256": DOCS / "transform_validation.json",
}

TARGET_FAMILIES = [
    {
        "family_id": "standards-protocol-text",
        "ordinary_sources": "RFC excerpts, HTTP traces, MIME/email/calendar samples",
        "control_sources": "vocabulary-disjoint protocol-shaped shadows plus random-byte payloads",
        "why": "public-preset and transform probes currently show structured text sensitivity but controls remain the risk",
    },
    {
        "family_id": "schema-and-config",
        "ordinary_sources": "OpenAPI, protobuf, Terraform, Kubernetes, JSON/YAML/TOML configs",
        "control_sources": "wrong-family schemas, shadow identifiers, same-size random tables",
        "why": "schema-native dictionaries found wins that failed paired-shadow controls; external provenance is required",
    },
    {
        "family_id": "records-and-ledgers",
        "ordinary_sources": "CSV, fixed-width, Beancount-like ledgers, BibTeX-like citations",
        "control_sources": "field-order shuffles, shadow vocabularies, binary fixed-record controls",
        "why": "record structure is one of the few channels with repeated near-miss movement",
    },
    {
        "family_id": "source-code",
        "ordinary_sources": "small permissively licensed source files across languages",
        "control_sources": "near-family code, token-renamed shadows, syntax-preserving shuffled controls",
        "why": "source-like rows appear in several probes but have not produced promoted exact spans",
    },
]

REOPEN_STAGES = [
    {
        "stage_id": "manifest-only",
        "status": "allowed_now",
        "compute_budget": "0 seed expansions; file provenance and hashes only",
        "entry_condition": "none",
        "exit_condition": "every proposed corpus has license/provenance, independence group, paired controls, size, and SHA-256 recorded",
    },
    {
        "stage_id": "prefix-audit",
        "status": "requires_human_approval",
        "compute_budget": "bounded depth-1/2 prefix telemetry only; no broad depth-3 or depth-4",
        "entry_condition": "manifest-only passes and controls are paired before ordinary rows are scored",
        "exit_condition": "at least three unrelated ordinary groups show prefix>=5 movement while all controls stay null",
    },
    {
        "stage_id": "exact-span-replay",
        "status": "requires_new_prefix_evidence",
        "compute_budget": "bounded exact replay on rows selected by prefix-audit; no corpus-wide broad search",
        "entry_condition": "prefix-audit produces predeclared ordinary prefix>=5 groups with null controls",
        "exit_condition": "repeatable exact hits or selected spans appear in ordinary rows and not controls",
    },
    {
        "stage_id": "negative-delta-proof",
        "status": "requires_exact_spans",
        "compute_budget": "charged v1/v2 encoding only for exact-span rows",
        "entry_condition": "exact-span-replay produces selected spans",
        "exit_condition": "at least three unrelated ordinary groups produce negative delta with metadata charged and controls null",
    },
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


def cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def natural_brief(blocked: dict[str, Any]) -> dict[str, Any]:
    for brief in blocked.get("briefs", []):
        if brief.get("requirement_id") == "natural-corpus-viability":
            return brief
    return {}


def build_agent_briefs() -> list[dict[str, Any]]:
    return [
        {
            "parallel_group": "corpus-transform",
            "mission": "Assemble the external corpus manifest and paired controls without running seed search.",
            "write_scope": [
                "docs/NATURAL_CORPUS_REOPEN_MANIFEST.md",
                "docs/natural_corpus_reopen_manifest.json",
            ],
            "forbidden_actions": [
                "do not add corpora without provenance and paired controls",
                "do not merge new corpora into canonical matrices during manifest-only work",
                "do not claim natural-corpus viability from prefix-only movement",
            ],
        },
        {
            "parallel_group": "compute-economics",
            "mission": "Keep the staged compute budget closed until generated prefix evidence beats current forecasts.",
            "write_scope": [
                "docs/SEARCH_FRONTIER_GATE.md",
                "docs/NATURAL_CORPUS_REOPEN_MANIFEST.md",
            ],
            "forbidden_actions": [
                "do not run broad depth-3, depth-4, or long-span sweeps",
                "do not approve prefix-audit while SEARCH_FRONTIER_GATE remains closed without new evidence",
                "do not spend on GPU acceleration without a promoted CPU workload",
            ],
        },
        {
            "parallel_group": "meta-research",
            "mission": "Audit that any proposed natural-corpus reopen work changes a generated gate rather than prose.",
            "write_scope": [
                "docs/RESEARCH_HYPOTHESES.md",
                "docs/RESEARCH_TEAM_PACKET.md",
                "docs/GOAL_COMPLETION_AUDIT.md",
            ],
            "forbidden_actions": [
                "do not downgrade blockers without source evidence",
                "do not mark the active goal complete while natural-corpus proof is false",
                "do not edit generated markdown or JSON by hand",
            ],
        },
    ]


def build_report() -> dict[str, Any]:
    natural = load_json(DOCS / "natural_corpus_proof_matrix.json")
    blocked = load_json(DOCS / "blocked_requirement_dispatch.json")
    frontier = load_json(DOCS / "research_frontier.json")
    search = load_json(DOCS / "search_frontier_gate.json")
    long_span = load_json(DOCS / "long_span_bundle_gate.json")
    heldout = load_json(DOCS / "heldout_corpus_expansion.json")
    match = load_json(DOCS / "match_discovery.json")
    transform = load_json(DOCS / "transform_validation.json")

    natural_summary = summary(natural)
    blocked_summary = summary(blocked)
    frontier_summary = summary(frontier)
    search_summary = summary(search)
    long_span_summary = summary(long_span)
    heldout_summary = summary(heldout)
    match_summary = summary(match)
    transform_summary = summary(transform)
    natural_dispatch = natural_brief(blocked)

    manifest_ready = (
        not natural_summary["natural_corpus_proven"]
        and search_summary["broad_depth_search_allowed"] is False
        and frontier_summary["ready_count"] == 0
    )

    return {
        "generated_by": GENERATED_BY,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "scope": {
            "kind": "natural corpus reopen manifest",
            "performs_seed_search": False,
            "launches_agents": False,
            "makes_compression_claim": False,
            "is_natural_corpus_proof": False,
            "overrides_search_frontier_gate": False,
            "allows_broad_compute": False,
        },
        "source_hashes": source_hashes(),
        "summary": {
            "manifest_status": "pre_registered_reopen_manifest_only",
            "natural_corpus_proven": natural_summary["natural_corpus_proven"],
            "natural_corpus_status": natural_summary["natural_corpus_status"],
            "blocked_natural_gates": len(natural_summary["blocked_gate_ids"]),
            "ready_ungated_experiments": frontier_summary["ready_count"],
            "broad_depth_search_allowed": search_summary["broad_depth_search_allowed"],
            "long_span_gate_met_count": long_span_summary["gate_met_count"],
            "long_span_gate_count": long_span_summary["gate_count"],
            "heldout_prefix5_rows": heldout_summary["rows_with_prefix_ge_5"],
            "heldout_exact_hit_rows": heldout_summary["rows_with_exact_hits"],
            "heldout_selected_span_rows": heldout_summary["rows_with_selected_spans"],
            "match_selected_span_rows": match_summary["rows_with_selected_spans"],
            "transform_heldout_exact_hits": transform_summary["heldout_exact_hits"],
            "ready_dispatch_count": blocked_summary["ready_dispatch_count"],
            "manifest_ready": manifest_ready,
            "first_allowed_stage": "manifest-only",
            "next_compute_stage_status": "requires_human_approval_and_new_manifest_evidence",
            "claim_boundary": (
                "No Seed Search; manifest/pre-registration only; not a compression "
                "claim; not natural-corpus proof; does not override SEARCH_FRONTIER_GATE."
            ),
            "conclusion": (
                "Natural-corpus viability remains blocked. The only currently aligned "
                "work is manifest-only corpus/control pre-registration; every compute "
                "stage remains closed until new generated evidence changes the gates."
            ),
        },
        "natural_dispatch_brief": natural_dispatch,
        "target_families": TARGET_FAMILIES,
        "reopen_stages": REOPEN_STAGES,
        "promotion_rules": [
            "At least three unrelated ordinary external corpus groups must produce selected spans or negative delta.",
            "All paired shadow, wrong-family, binary, and random controls must remain null.",
            "Every counted row must decode exactly and charge literal, selector, preset, sidecar, and layer metadata.",
            "Prefix-only or transform-only shortening is telemetry, not proof.",
            "No format or production promotion can occur until NATURAL_CORPUS_PROOF_MATRIX and PRODUCTION_PROOF_MATRIX move.",
        ],
        "falsification_rules": [
            "Controls produce comparable wins.",
            "Ordinary rows only improve under project-derived or same-family leakage.",
            "Prefix movement fails to become exact selected spans.",
            "Expected exact-hit scale remains above 1 GiB per hit after the manifest is frozen.",
            "Metadata erases every full-stream win.",
        ],
        "dispatching_parallel_agents": build_agent_briefs(),
    }


def write_report(payload: dict[str, Any]) -> None:
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary_payload = payload["summary"]
    lines = [
        "# Natural Corpus Reopen Manifest",
        "",
        f"Generated by `{GENERATED_BY}` from current proof, frontier, blocked-requirement, and team ledgers.",
        "This is a No Seed Search pre-registration artifact. It launches no agents, is not a compression claim, is not natural-corpus proof, and does not override `SEARCH_FRONTIER_GATE`.",
        "",
        "## Summary",
        "",
        f"- Manifest status: `{summary_payload['manifest_status']}`",
        f"- Natural corpus proven: `{summary_payload['natural_corpus_proven']}`",
        f"- Blocked natural gates: `{summary_payload['blocked_natural_gates']}`",
        f"- Ready ungated experiments: `{summary_payload['ready_ungated_experiments']}`",
        f"- Broad depth search allowed: `{summary_payload['broad_depth_search_allowed']}`",
        f"- Long-span gates met: `{summary_payload['long_span_gate_met_count']}` / `{summary_payload['long_span_gate_count']}`",
        f"- Held-out prefix>=5/exact/selected rows: `{summary_payload['heldout_prefix5_rows']}` / `{summary_payload['heldout_exact_hit_rows']}` / `{summary_payload['heldout_selected_span_rows']}`",
        f"- Match selected-span rows: `{summary_payload['match_selected_span_rows']}`",
        f"- Transform held-out exact hits: `{summary_payload['transform_heldout_exact_hits']}`",
        f"- Ready dispatch count: `{summary_payload['ready_dispatch_count']}`",
        f"- First allowed stage: `{summary_payload['first_allowed_stage']}`",
        f"- Next compute stage: `{summary_payload['next_compute_stage_status']}`",
        "",
        summary_payload["conclusion"],
        "",
        "## Reopen Stages",
        "",
        "| stage | status | compute budget | entry condition | exit condition |",
        "| --- | --- | --- | --- | --- |",
    ]
    for stage in payload["reopen_stages"]:
        lines.append(
            f"| `{cell(stage['stage_id'])}` | `{cell(stage['status'])}` | "
            f"{cell(stage['compute_budget'])} | {cell(stage['entry_condition'])} | "
            f"{cell(stage['exit_condition'])} |"
        )

    lines.extend(["", "## Target Families", ""])
    lines.extend(
        [
            "| family | ordinary sources | controls | why |",
            "| --- | --- | --- | --- |",
        ]
    )
    for family in payload["target_families"]:
        lines.append(
            f"| `{cell(family['family_id'])}` | {cell(family['ordinary_sources'])} | "
            f"{cell(family['control_sources'])} | {cell(family['why'])} |"
        )

    lines.extend(["", "## Promotion Rules", ""])
    for rule in payload["promotion_rules"]:
        lines.append(f"- {rule}")

    lines.extend(["", "## Falsification Rules", ""])
    for rule in payload["falsification_rules"]:
        lines.append(f"- {rule}")

    lines.extend(["", "## dispatching-parallel-agents Briefs", ""])
    for brief in payload["dispatching_parallel_agents"]:
        lines.extend(
            [
                f"### {brief['parallel_group']}",
                "",
                f"- Mission: {brief['mission']}",
                f"- Write scope: {', '.join(f'`{item}`' for item in brief['write_scope'])}",
                f"- Forbidden actions: {'; '.join(brief['forbidden_actions'])}",
                "",
            ]
        )

    lines.extend(
        [
            "## Source Artifacts",
            "",
            "The JSON `source_hashes` map pins this manifest to exact upstream evidence files below.",
        ]
    )
    for name, digest in payload["source_hashes"].items():
        lines.append(f"- `{name}`: `{digest}`")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not REPORT_JSON.exists() or not REPORT_MD.exists():
        raise SystemExit("generated natural corpus reopen manifest files are missing")
    payload = load_json(REPORT_JSON)
    if payload.get("generated_by") != GENERATED_BY:
        raise SystemExit("natural_corpus_reopen_manifest.json has wrong generated_by marker")
    if payload.get("source_hashes") != source_hashes():
        raise SystemExit("natural corpus reopen manifest source hashes are stale")
    expected = stable_projection(build_report())
    current = stable_projection(payload)
    if current != expected:
        raise SystemExit("natural_corpus_reopen_manifest.json is stale; regenerate it")
    scope = payload.get("scope", {})
    for field in (
        "performs_seed_search",
        "launches_agents",
        "makes_compression_claim",
        "is_natural_corpus_proof",
        "overrides_search_frontier_gate",
        "allows_broad_compute",
    ):
        if scope.get(field) is not False:
            raise SystemExit(f"natural corpus reopen manifest scope field must be false: {field}")
    summary_payload = payload["summary"]
    if summary_payload["natural_corpus_proven"]:
        raise SystemExit("natural corpus reopen manifest cannot claim proof")
    if summary_payload["broad_depth_search_allowed"]:
        raise SystemExit("natural corpus reopen manifest cannot allow broad depth search")
    if summary_payload["ready_ungated_experiments"] != 0:
        raise SystemExit("natural corpus reopen manifest expects zero ready ungated experiments")
    if payload["reopen_stages"][0]["stage_id"] != "manifest-only":
        raise SystemExit("natural corpus reopen manifest must start at manifest-only")
    text = REPORT_MD.read_text(encoding="utf-8")
    for phrase in (
        "Natural Corpus Reopen Manifest",
        "No Seed Search",
        "not natural-corpus proof",
        "SEARCH_FRONTIER_GATE",
        "Reopen Stages",
        "Target Families",
        "Promotion Rules",
        "Falsification Rules",
        "dispatching-parallel-agents Briefs",
        "source_hashes",
    ):
        if phrase not in text:
            raise SystemExit(f"NATURAL_CORPUS_REOPEN_MANIFEST.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="validate generated natural-corpus reopen manifest"
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
