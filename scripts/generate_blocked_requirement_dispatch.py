#!/usr/bin/env python3
"""Generate dispatch briefs for active-goal blocking requirements.

This is a no-compute coordination artifact. It translates the current
GOAL_COMPLETION_AUDIT blockers into independent research-team briefs, while
preserving every generated stop rule.
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
REPORT_JSON = DOCS / "blocked_requirement_dispatch.json"
REPORT_MD = DOCS / "BLOCKED_REQUIREMENT_DISPATCH.md"
GENERATED_BY = "scripts/generate_blocked_requirement_dispatch.py"

SOURCE_PATHS = {
    "goal_completion_audit_sha256": DOCS / "goal_completion_audit.json",
    "research_frontier_sha256": DOCS / "research_frontier.json",
    "research_team_protocol_sha256": DOCS / "research_team_protocol.json",
    "research_decision_sha256": DOCS / "research_decision.json",
    "viability_sha256": DOCS / "viability.json",
    "research_scorecard_sha256": DOCS / "research_scorecard.json",
}

BLOCKER_CONFIG = {
    "natural-corpus-viability": {
        "brief_id": "blocked-natural-corpus-viability",
        "parallel_groups": ["corpus-transform", "compute-economics"],
        "mission": (
            "Find evidence paths that could turn non-planted corpora into "
            "repeatable selected seed-span wins without weakening controls."
        ),
        "source_artifacts": [
            "docs/NATURAL_CORPUS_PROOF_MATRIX.md",
            "docs/VIABILITY.md",
            "docs/RESEARCH_SCORECARD.md",
            "docs/RESEARCH_FRONTIER.md",
            "docs/SEARCH_FRONTIER_GATE.md",
            "docs/LONG_SPAN_BUNDLE_GATE.md",
            "docs/HELDOUT_CORPUS_EXPANSION.md",
        ],
        "allowed_actions": [
            "read-only audits of null and near-miss ledgers",
            "pre-register natural-corpus or transform manifests without running search",
            "propose narrow reopen-trigger artifacts with explicit controls",
            "tighten claims so planted evidence is not conflated with natural evidence",
        ],
        "forbidden_actions": [
            "do not launch broad compute",
            "No Seed Search: do not start new depth-3, depth-4, or long-span sweeps",
            "do not claim natural-corpus compression is proven",
            "do not count transform-only shortening as Lotus compression",
            "do not merge held-out corpora into canonical matrices without a regeneration budget",
        ],
        "promotion_trigger": (
            "A generated artifact reports repeatable non-planted selected spans "
            "or negative delta while controls remain null."
        ),
        "stop_rule": (
            "Stop at audit/pre-registration while prefix>=5, exact-hit, selected-span, "
            "or control gates remain null."
        ),
    },
    "production-proof": {
        "brief_id": "blocked-production-proof",
        "parallel_groups": ["acceleration", "format-policy", "operator-ui"],
        "mission": (
            "Define the exact evidence needed before Telomere can make production "
            "format, compatibility, performance, or acceleration claims."
        ),
        "source_artifacts": [
            "docs/PRODUCTION_PROOF_MATRIX.md",
            "docs/RELEASE_CHECKLIST.md",
            "docs/FORMAT.md",
            "docs/ACCELERATION.md",
            "docs/SCALE_PERFORMANCE.md",
            "docs/UI_WORKFLOW_SMOKE.md",
        ],
        "allowed_actions": [
            "read-only release-readiness audits",
            "write compatibility-checklist proposals that do not change v1 semantics",
            "design CPU/GPU parity tests without trusting GPU output",
            "document production blockers and benchmark budgets",
        ],
        "forbidden_actions": [
            "do not promote experimental v2 to stable",
            "do not market GPU as production acceleration",
            "do not alter stable v1 compatibility",
            "do not hide null or blocked results behind optimistic UI language",
            "do not claim production readiness from planted-density benchmarks",
        ],
        "promotion_trigger": (
            "A release-candidate artifact shows supported format guarantees, real "
            "workload wins, CPU/GPU parity where relevant, and clean release gates."
        ),
        "stop_rule": (
            "Stop production promotion while acceleration is research-only, memory "
            "estimates remain bounded/planted, or compatibility guarantees are experimental."
        ),
    },
    "completion-boundary": {
        "brief_id": "blocked-completion-boundary",
        "parallel_groups": ["meta-research"],
        "mission": (
            "Keep the active-goal completion boundary honest as new evidence changes."
        ),
        "source_artifacts": [
            "docs/GOAL_COMPLETION_AUDIT.md",
            "docs/RESEARCH_DECISION.md",
            "docs/GOAL_AUDIT.md",
            "docs/RESEARCH_TEAM_PROTOCOL.md",
            "docs/GENERATED_LEDGER_PIPELINE.md",
        ],
        "allowed_actions": [
            "regenerate the full evidence regimen after low-level artifact changes",
            "regenerate top-level research ledgers after rollup-only evidence changes",
            "audit that blocked requirements still map to authoritative evidence",
            "tighten stop rules when new artifacts introduce ambiguity",
            "prepare integration summaries for human review",
        ],
        "forbidden_actions": [
            "do not mark the active goal complete",
            "do not downgrade blocked evidence to qualified without generated proof",
            "do not remove completion blockers to make dashboards green",
            "do not edit generated markdown or JSON by hand",
        ],
        "promotion_trigger": (
            "GOAL_COMPLETION_AUDIT reports zero blocked requirements, zero unresolved "
            "evidence gates, and production_proven true."
        ),
        "stop_rule": (
            "Keep the goal active while any blocked requirement remains or production_proven is false."
        ),
    },
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


def cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def completion_requirement_map(completion: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["requirement_id"]: item for item in completion["requirements"]}


def build_prompt(brief: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"Brief {brief['brief_id']}: use dispatching-parallel-agents as an operating model.",
            f"Mission: {brief['mission']}",
            "Scope: No Seed Search, not a compression claim, and does not override SEARCH_FRONTIER_GATE.",
            f"Blocking requirement: {brief['requirement_id']} ({brief['requirement_status']}).",
            f"Source artifacts: {', '.join(brief['source_artifacts'])}.",
            f"allowed_actions: {'; '.join(brief['allowed_actions'])}.",
            f"forbidden_actions: {'; '.join(brief['forbidden_actions'])}.",
            f"promotion_trigger: {brief['promotion_trigger']}.",
            f"stop_rule: {brief['stop_rule']}.",
            f"output_contract: {'; '.join(brief['output_contract'])}.",
            "Return a findings-first audit and do not launch broad compute.",
        ]
    )


def build_briefs(completion: dict[str, Any]) -> list[dict[str, Any]]:
    requirements = completion_requirement_map(completion)
    briefs = []
    for requirement_id in summary(completion)["blocking_requirement_ids"]:
        config = BLOCKER_CONFIG[requirement_id]
        requirement = requirements[requirement_id]
        output_contract = [
            "Findings first with file paths and current generated status.",
            "State whether the stop rule still applies.",
            "List any proposed new artifact, its check command, and its compute budget.",
            "Call out any claim that would require human approval before promotion.",
            "Report verification commands run or explain why none were needed.",
            "Use scripts/generate_evidence_regimen.py for full generated-artifact graph changes.",
        ]
        brief = {
            "brief_id": config["brief_id"],
            "requirement_id": requirement_id,
            "requirement_status": requirement["status"],
            "requirement": requirement["requirement"],
            "parallel_groups": config["parallel_groups"],
            "mission": config["mission"],
            "source_artifacts": config["source_artifacts"],
            "allowed_actions": config["allowed_actions"],
            "forbidden_actions": config["forbidden_actions"],
            "promotion_trigger": config["promotion_trigger"],
            "stop_rule": config["stop_rule"],
            "remaining_proof_gap": requirement["remaining_proof_gap"],
            "output_contract": output_contract,
        }
        brief["prompt"] = build_prompt(brief)
        briefs.append(brief)
    return briefs


def build_report() -> dict[str, Any]:
    completion = load_json(SOURCE_PATHS["goal_completion_audit_sha256"])
    frontier = load_json(SOURCE_PATHS["research_frontier_sha256"])
    team = load_json(SOURCE_PATHS["research_team_protocol_sha256"])
    decision = load_json(SOURCE_PATHS["research_decision_sha256"])
    viability = load_json(SOURCE_PATHS["viability_sha256"])
    scorecard = load_json(SOURCE_PATHS["research_scorecard_sha256"])

    completion_summary = summary(completion)
    frontier_summary = summary(frontier)
    team_summary = summary(team)
    decision_summary = summary(decision)
    briefs = build_briefs(completion)
    unique_groups = sorted({group for brief in briefs for group in brief["parallel_groups"]})
    forbidden_action_count = len(
        {action for brief in briefs for action in brief["forbidden_actions"]}
    )

    return {
        "generated_by": GENERATED_BY,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "scope": {
            "kind": "blocked requirement dispatch",
            "dispatching_parallel_agents": True,
            "performs_seed_search": False,
            "launches_agents": False,
            "makes_compression_claim": False,
            "overrides_search_frontier_gate": False,
            "marks_goal_complete": False,
        },
        "source_hashes": source_hashes(),
        "summary": {
            "dispatch_status": "blocked_requirements_maintenance_only",
            "objective_status": completion_summary["objective_status"],
            "completion_recommendation": completion_summary["completion_recommendation"],
            "verdict": viability["verdict"],
            "scorecard_open_count": int(scorecard["scorecard_status_counts"]["open"]),
            "production_proven": bool(completion_summary["production_proven"]),
            "unresolved_evidence_gates": int(
                completion_summary["unresolved_evidence_gates"]
            ),
            "blocked_requirement_count": len(
                completion_summary["blocking_requirement_ids"]
            ),
            "brief_count": len(briefs),
            "parallel_group_count": len(unique_groups),
            "parallel_groups": unique_groups,
            "forbidden_action_count": forbidden_action_count,
            "ready_dispatch_count": 0,
            "ungated_compute_allowed": bool(frontier_summary["ungated_compute_allowed"]),
            "team_protocol_status": team_summary["protocol_status"],
            "research_decision": decision_summary["decision"],
        },
        "briefs": briefs,
        "review_contract": [
            "Dispatch these briefs independently only for read-only audits or generated-artifact maintenance.",
            "Integrate one returned brief at a time and rerun doc lint before any broader gate.",
            "Reject any output that weakens no-seed-search, no-production-claim, or SEARCH_FRONTIER_GATE boundaries.",
        ],
    }


def write_report(payload: dict[str, Any]) -> None:
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    data = payload["summary"]
    lines = [
        "# Telomere Blocked Requirement Dispatch",
        "",
        f"Generated by `{GENERATED_BY}` from the active completion audit, frontier, team protocol, and decision ledgers.",
        "This is a No Seed Search dispatching-parallel-agents artifact: it launches no agents, performs no seed search, makes no compression claim, does not override SEARCH_FRONTIER_GATE, and does not mark the active goal complete.",
        "",
        "## Dispatch Status",
        "",
        f"- Dispatch status: `{data['dispatch_status']}`",
        f"- Objective status: `{data['objective_status']}`",
        f"- Completion recommendation: `{data['completion_recommendation']}`",
        f"- Verdict: `{data['verdict']}`",
        f"- Production proven: `{data['production_proven']}`",
        f"- Unresolved evidence gates: `{data['unresolved_evidence_gates']}`",
        f"- Blocked requirements: `{data['blocked_requirement_count']}`",
        f"- Briefs: `{data['brief_count']}`",
        f"- Parallel groups: `{', '.join(data['parallel_groups'])}`",
        f"- Ready dispatch count: `{data['ready_dispatch_count']}`",
        f"- Ungated compute allowed: `{data['ungated_compute_allowed']}`",
        f"- Team protocol status: `{data['team_protocol_status']}`",
        f"- Research decision: `{data['research_decision']}`",
        "",
        "These briefs are maintenance-only until generated evidence reopens a lane.",
        "",
        "## Brief Matrix",
        "",
        "| brief | requirement | groups | stop rule | promotion trigger |",
        "| --- | --- | --- | --- | --- |",
    ]
    for brief in payload["briefs"]:
        lines.append(
            f"| `{cell(brief['brief_id'])}` | `{cell(brief['requirement_id'])}` | {cell(', '.join(brief['parallel_groups']))} | {cell(brief['stop_rule'])} | {cell(brief['promotion_trigger'])} |"
        )

    for brief in payload["briefs"]:
        lines.extend(
            [
                "",
                f"## {brief['brief_id']}",
                "",
                f"- Requirement: `{brief['requirement_id']}`",
                f"- Status: `{brief['requirement_status']}`",
                f"- Mission: {brief['mission']}",
                f"- Remaining proof gap: {brief['remaining_proof_gap']}",
                f"- Source artifacts: {', '.join(f'`{item}`' for item in brief['source_artifacts'])}",
                f"- allowed_actions: {'; '.join(brief['allowed_actions'])}",
                f"- forbidden_actions: {'; '.join(brief['forbidden_actions'])}",
                f"- output_contract: {'; '.join(brief['output_contract'])}",
                "",
                "Prompt:",
                "",
                "```text",
                brief["prompt"],
                "```",
            ]
        )

    lines.extend(["", "## Review Contract", ""])
    for item in payload["review_contract"]:
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## Source Artifacts",
            "",
            "The JSON `source_hashes` map pins this dispatch plan to the exact upstream evidence files below.",
        ]
    )
    for name, digest in payload["source_hashes"].items():
        lines.append(f"- `{name}`: `{digest}`")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not REPORT_JSON.exists() or not REPORT_MD.exists():
        raise SystemExit("generated blocked requirement dispatch files are missing")
    payload = load_json(REPORT_JSON)
    if payload.get("generated_by") != GENERATED_BY:
        raise SystemExit("blocked_requirement_dispatch.json has wrong generated_by marker")
    if payload.get("source_hashes") != source_hashes():
        raise SystemExit("blocked requirement dispatch source hashes are stale")
    expected = stable_projection(build_report())
    current = stable_projection(payload)
    if current != expected:
        raise SystemExit("blocked_requirement_dispatch.json is stale; regenerate it")

    data = payload["summary"]
    if data["ready_dispatch_count"] != 0:
        raise SystemExit("blocked requirement dispatch unexpectedly allows ready dispatch")
    if data["ungated_compute_allowed"]:
        raise SystemExit("blocked requirement dispatch unexpectedly allows ungated compute")
    if data["completion_recommendation"] != "keep_goal_active":
        raise SystemExit("blocked requirement dispatch lost keep-goal-active boundary")
    expected_blockers = set(load_json(SOURCE_PATHS["goal_completion_audit_sha256"])["summary"]["blocking_requirement_ids"])
    actual_blockers = {brief["requirement_id"] for brief in payload["briefs"]}
    if actual_blockers != expected_blockers:
        raise SystemExit("blocked requirement dispatch does not match completion blockers")
    for brief in payload["briefs"]:
        for field in (
            "brief_id",
            "requirement_id",
            "parallel_groups",
            "source_artifacts",
            "allowed_actions",
            "forbidden_actions",
            "promotion_trigger",
            "stop_rule",
            "output_contract",
            "prompt",
        ):
            if not brief.get(field):
                raise SystemExit(
                    f"blocked requirement brief {brief.get('brief_id')} missing {field}"
                )
        for phrase in (
            "dispatching-parallel-agents",
            "No Seed Search",
            "not a compression claim",
            "does not override SEARCH_FRONTIER_GATE",
            "forbidden_actions",
            "output_contract",
            "do not launch broad compute",
        ):
            if phrase not in brief["prompt"]:
                raise SystemExit(
                    f"blocked requirement brief {brief['brief_id']} missing prompt phrase: {phrase}"
                )

    text = REPORT_MD.read_text(encoding="utf-8")
    for phrase in (
        "Telomere Blocked Requirement Dispatch",
        "No Seed Search",
        "dispatching-parallel-agents",
        "maintenance-only",
        "natural-corpus-viability",
        "production-proof",
        "completion-boundary",
        "keep_goal_active",
        "forbidden_actions",
        "output_contract",
        "does not override SEARCH_FRONTIER_GATE",
        "does not mark the active goal complete",
        "source_hashes",
    ):
        if phrase not in text:
            raise SystemExit(f"BLOCKED_REQUIREMENT_DISPATCH.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate generated blocked requirement dispatch files",
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
