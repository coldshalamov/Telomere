#!/usr/bin/env python3
"""Generate the current Telomere research decision and reopen ledger."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
REPORT_JSON = DOCS / "research_decision.json"
REPORT_MD = DOCS / "RESEARCH_DECISION.md"
GENERATED_BY = "scripts/generate_research_decision.py"

SOURCE_PATHS = {
    "experiment_queue_sha256": DOCS / "experiment_queue.json",
    "goal_audit_sha256": DOCS / "goal_audit.json",
    "research_scorecard_sha256": DOCS / "research_scorecard.json",
    "viability_sha256": DOCS / "viability.json",
    "long_span_bundle_gate_sha256": DOCS / "long_span_bundle_gate.json",
    "search_frontier_gate_sha256": DOCS / "search_frontier_gate.json",
    "acceleration_report_sha256": DOCS / "acceleration_report.json",
    "scale_performance_report_sha256": DOCS / "scale_performance_report.json",
    "recursive_structured_fixtures_sha256": DOCS / "recursive_structured_fixtures.json",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes() -> dict[str, str]:
    return {name: sha256(path) for name, path in SOURCE_PATHS.items()}


def summary(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("summary", {})
    return value if isinstance(value, dict) else {}


def stable_projection(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if key != "generated_at"
    }


def build_report() -> dict[str, Any]:
    queue = load_json(SOURCE_PATHS["experiment_queue_sha256"])
    goal = load_json(SOURCE_PATHS["goal_audit_sha256"])
    scorecard = load_json(SOURCE_PATHS["research_scorecard_sha256"])
    viability = load_json(SOURCE_PATHS["viability_sha256"])
    long_span = load_json(SOURCE_PATHS["long_span_bundle_gate_sha256"])
    search_frontier = load_json(SOURCE_PATHS["search_frontier_gate_sha256"])
    acceleration = load_json(SOURCE_PATHS["acceleration_report_sha256"])
    scale = load_json(SOURCE_PATHS["scale_performance_report_sha256"])
    recursive = load_json(SOURCE_PATHS["recursive_structured_fixtures_sha256"])

    queue_summary = queue["summary"]
    long_span_summary = long_span["summary"]
    search_summary = search_frontier["summary"]
    scale_summary = scale["summary"]
    recursive_summary = recursive["summary"]
    ready_items = [item for item in queue["items"] if item["status"] == "ready"]
    blocked_items = [
        item for item in queue["items"] if item["status"] == "blocked-by-evidence"
    ]
    gated_items = [item for item in queue["items"] if item["status"] == "gated"]
    qualified_items = [item for item in queue["items"] if item["status"] == "qualified"]
    ready_count = int(queue_summary["ready_count"])
    unresolved_count = int(goal.get("unresolved_count", goal.get("open_count", 0)))
    production_proven = (
        "production-proven" in str(scorecard.get("verdict", ""))
        and "not production-proven" not in str(scorecard.get("verdict", ""))
    )
    decision = (
        "run_ready_experiments"
        if ready_count
        else "hold_gated_compute_and_continue_evidence_maintenance"
    )
    completion_boundary = (
        "goal_not_complete_until_natural_corpus_or_supported_production_claims_are_proven"
        if unresolved_count or not production_proven
        else "goal_evidence_complete"
    )

    blocked_actions = [
        {
            "lane": item["lane"],
            "status": item["status"],
            "do_not_do": item["action"],
            "stop_rule": item["stop_rule"],
        }
        for item in blocked_items + gated_items
    ]
    reopen_triggers = [
        {
            "lane": item["lane"],
            "status": item["status"],
            "promotion_gate": item["promotion_gate"],
            "suggested_artifact": item["suggested_artifact"],
        }
        for item in queue["items"]
        if item["status"] in {"blocked-by-evidence", "gated"}
    ]
    unmet_long_span_gates = [
        {
            "gate": check["gate"],
            "observed": check["observed"],
            "consequence": check["consequence"],
        }
        for check in long_span["gate_checks"]
        if not check["met"]
    ]
    allowed_maintenance = [
        "regenerate checked evidence artifacts when an upstream source changes",
        "run verification gates and fix stale hashes or stale wording",
        "tighten documentation around non-claims, stop rules, and compatibility boundaries",
        "pre-register new corpus or preset manifests without claiming compression",
        "use subagents for independent read-only audits or disjoint low-risk patches",
    ]

    summary_payload = {
        "decision": decision,
        "completion_boundary": completion_boundary,
        "verdict": viability["verdict"],
        "overall_status": goal["overall_status"],
        "ready_count": ready_count,
        "top_ready_lane": queue_summary["top_ready_lane"],
        "gated_count": int(queue_summary["gated_count"]),
        "blocked_by_evidence_count": int(queue_summary["blocked_by_evidence_count"]),
        "qualified_count": len(qualified_items),
        "unresolved_count": unresolved_count,
        "open_count": int(goal.get("open_count", 0)),
        "long_span_gate_met_count": int(long_span_summary["gate_met_count"]),
        "long_span_gate_count": int(long_span_summary["gate_count"]),
        "long_span_recommendation": long_span_summary["recommendation"],
        "search_frontier_status": search_summary["recommended_status"],
        "broad_depth_search_allowed": bool(search_summary["broad_depth_search_allowed"]),
        "best_non_planted_gib_for_one_expected_hit": search_summary[
            "best_non_planted_gib_for_one_expected_hit"
        ],
        "recursive_claim_level": recursive_summary["claim_level"],
        "scale_largest_peak_memory_mib": scale_summary["largest_peak_memory_mib"],
        "scale_next_double_peak_memory_mib": scale_summary[
            "next_double_peak_memory_mib_at_current_ratio"
        ],
        "acceleration_status": acceleration["detected"]["status"],
        "production_proven": production_proven,
    }

    return {
        "generated_by": GENERATED_BY,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "source_hashes": source_hashes(),
        "summary": summary_payload,
        "ready_items": ready_items,
        "blocked_actions": blocked_actions,
        "reopen_triggers": reopen_triggers,
        "unmet_long_span_gates": unmet_long_span_gates,
        "allowed_maintenance": allowed_maintenance,
    }


def write_report(payload: dict[str, Any]) -> None:
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    data = payload["summary"]
    lines = [
        "# Telomere Research Decision",
        "",
        f"Generated by `{GENERATED_BY}` from checked-in queue, audit, and gate artifacts.",
        "This is a downstream decision ledger. It performs no seed search and makes no compression claim.",
        "",
        "## Current Decision",
        "",
        f"- Decision: `{data['decision']}`",
        f"- Verdict: `{data['verdict']}`",
        f"- Overall status: `{data['overall_status']}`",
        f"- Ready ungated experiments: `{data['ready_count']}`",
        f"- Top ready lane: `{data['top_ready_lane']}`",
        f"- Gated lanes: `{data['gated_count']}`",
        f"- Blocked-by-evidence lanes: `{data['blocked_by_evidence_count']}`",
        f"- Unresolved evidence gates: `{data['unresolved_count']}`",
        f"- Production proven: `{data['production_proven']}`",
        "",
        "No ready ungated experiments remain; do not spend on gated compute or production GPU until evidence improves.",
        "",
        "## Completion Boundary",
        "",
        f"- Completion boundary: `{data['completion_boundary']}`",
        "- The active research goal is not complete while generalized natural-corpus compression, production acceleration, or supported production-format claims remain unproved.",
        "- Planted/generative wins prove the mechanism can work, not that arbitrary natural data is compressible.",
        "",
        "## Blocked Actions",
        "",
        "| lane | status | do not do | stop rule |",
        "| --- | --- | --- | --- |",
    ]
    for item in payload["blocked_actions"]:
        lines.append(
            f"| `{item['lane']}` | `{item['status']}` | {item['do_not_do']} | {item['stop_rule']} |"
        )

    lines.extend(
        [
            "",
            "## Reopen Triggers",
            "",
            "| lane | status | promotion gate | suggested artifact |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in payload["reopen_triggers"]:
        lines.append(
            f"| `{item['lane']}` | `{item['status']}` | {item['promotion_gate']} | {item['suggested_artifact']} |"
        )

    lines.extend(
        [
            "",
            "## Long-Span Gate Details",
            "",
            f"- Long-span checks met: `{data['long_span_gate_met_count']}` / `{data['long_span_gate_count']}`",
            f"- Recommendation: `{data['long_span_recommendation']}`",
            f"- Search frontier status: `{data['search_frontier_status']}`",
            f"- Broad depth search allowed: `{data['broad_depth_search_allowed']}`",
            f"- Best non-planted forecast: `{data['best_non_planted_gib_for_one_expected_hit']}` GiB per expected exact hit",
            "",
            "| gate | observed | consequence |",
            "| --- | --- | --- |",
        ]
    )
    for gate in payload["unmet_long_span_gates"]:
        lines.append(
            f"| `{gate['gate']}` | {gate['observed']} | {gate['consequence']} |"
        )

    lines.extend(["", "## Allowed Maintenance", ""])
    for action in payload["allowed_maintenance"]:
        lines.append(f"- {action}")

    lines.extend(["", "## Source Artifacts", ""])
    for name, digest in payload["source_hashes"].items():
        lines.append(f"- `{name}`: `{digest}`")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not REPORT_JSON.exists() or not REPORT_MD.exists():
        raise SystemExit("generated research decision files are missing")
    payload = load_json(REPORT_JSON)
    if payload.get("generated_by") != GENERATED_BY:
        raise SystemExit("research_decision.json has wrong generated_by marker")
    if payload.get("source_hashes") != source_hashes():
        raise SystemExit("research decision source hashes are stale")
    expected = stable_projection(build_report())
    current = stable_projection(payload)
    if current != expected:
        raise SystemExit("research_decision.json is stale; regenerate it")
    text = REPORT_MD.read_text(encoding="utf-8")
    for phrase in (
        "Telomere Research Decision",
        f"Generated by `{GENERATED_BY}`",
        "No ready ungated experiments remain",
        "do not spend on gated compute",
        "Completion Boundary",
        "Blocked Actions",
        "Reopen Triggers",
        "Allowed Maintenance",
        "not complete",
        "not that arbitrary natural data is compressible",
    ):
        if phrase not in text:
            raise SystemExit(f"RESEARCH_DECISION.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate generated research decision files",
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
