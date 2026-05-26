#!/usr/bin/env python3
"""Generate dispatch-ready Telomere research-team briefs.

This is a no-compute coordination artifact. It turns the generated frontier
ledger into constrained subagent briefs so parallel work can proceed without
accidentally launching gated seed search, format promotion, or unsupported
compression claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
REPORT_JSON = DOCS / "research_team_protocol.json"
REPORT_MD = DOCS / "RESEARCH_TEAM_PROTOCOL.md"
GENERATED_BY = "scripts/generate_research_team_protocol.py"

SOURCE_PATHS = {
    "research_frontier_sha256": DOCS / "research_frontier.json",
    "research_decision_sha256": DOCS / "research_decision.json",
    "experiment_queue_sha256": DOCS / "experiment_queue.json",
    "goal_audit_sha256": DOCS / "goal_audit.json",
}

GROUP_MISSIONS = {
    "acceleration": (
        "Audit acceleration readiness and keep GPU/CPU parity requirements "
        "explicit until a CPU workload justifies real GPU work."
    ),
    "compute-economics": (
        "Maintain the search-depth and scale-performance economics without "
        "starting gated depth sweeps."
    ),
    "corpus-transform": (
        "Audit corpus, long-span, and transform-frontier evidence while "
        "preserving controls and null-result visibility."
    ),
    "format-policy": (
        "Keep format-extension proposals blocked until exact seed-span wins "
        "justify versioned metadata."
    ),
    "meta-research": (
        "Keep the generated research ledgers coherent, reproducible, and "
        "honest about unresolved evidence gates."
    ),
    "operator-ui": (
        "Keep the Tauri/operator evidence surfaces aligned with generated "
        "artifacts without making unsupported compression claims."
    ),
}

GROUP_WRITE_SCOPES = {
    "acceleration": [
        "docs/ACCELERATION.md",
        "docs/adr/0002-gpu-acceleration-status.md",
        "tests/gpu_*.rs",
        "src/gpu*.rs",
    ],
    "compute-economics": [
        "docs/SEARCH_FRONTIER_GATE.md",
        "docs/SCALE_PERFORMANCE.md",
        "scripts/generate_search_frontier_gate.py",
        "scripts/generate_scale_performance_report.py",
    ],
    "corpus-transform": [
        "docs/LONG_SPAN_BUNDLE_GATE.md",
        "docs/HELDOUT_CORPUS_EXPANSION.md",
        "docs/*TRANSFORM*.md",
        "scripts/generate_*transform*.py",
    ],
    "format-policy": [
        "docs/FORMAT.md",
        "docs/adr/0001-transform-preconditioners.md",
        "src/tlmr_v2.rs",
        "tests/indexed_v2.rs",
    ],
    "meta-research": [
        "docs/RESEARCH_*.md",
        "docs/GOAL_AUDIT.md",
        "docs/EXPERIMENT_QUEUE.md",
        "docs/GENERATED_LEDGER_PIPELINE.md",
        "scripts/generate_evidence_regimen.py",
        "scripts/generate_research_*.py",
        "scripts/generate_goal_audit.py",
        "scripts/generate_experiment_queue.py",
    ],
    "operator-ui": [
        "src-tauri/src/main.rs",
        "ui/index.html",
        "docs/UI_WORKFLOW_SMOKE.md",
        "scripts/generate_ui_workflow_smoke.py",
    ],
}

COMMON_FORBIDDEN_ACTIONS = [
    "do not launch broad compute",
    "No Seed Search: do not start new depth-3, depth-4, or long-span sweeps",
    "do not promote .tlmr format semantics",
    "do not claim natural-corpus compression is proven",
    "not a compression claim: do not reword null results as wins",
    "does not override SEARCH_FRONTIER_GATE",
    "do not edit generated markdown or JSON by hand",
]

COMMON_ALLOWED_ACTIONS = [
    "read-only audits of generated evidence artifacts",
    "generated-artifact maintenance through checked scripts",
    "small deterministic tests for existing supported behavior",
    "documentation clarifications that preserve current claim boundaries",
    "subagent brainstorming that returns bounded hypotheses instead of running compute",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes() -> dict[str, str]:
    return {name: sha256(path) for name, path in SOURCE_PATHS.items()}


def stable_projection(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if key != "generated_at"}


def cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def grouped_lanes(frontier: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in frontier["frontier_lanes"]:
        groups[item["parallel_group"]].append(item)
    return dict(sorted(groups.items()))


def frontier_by_id(frontier: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["frontier_id"]: item for item in frontier["frontiers"]}


def group_source_artifacts(
    lanes: list[dict[str, Any]],
    frontier_lookup: dict[str, dict[str, Any]],
) -> list[str]:
    artifacts = {
        "docs/RESEARCH_FRONTIER.md",
        "docs/EXPERIMENT_QUEUE.md",
        "docs/RESEARCH_DECISION.md",
    }
    for lane in lanes:
        lane_frontier = frontier_lookup.get(lane["lane"])
        if lane_frontier:
            artifacts.add(lane_frontier["canonical_artifact"])
        suggested = lane.get("suggested_artifact", "")
        if "`" in suggested:
            parts = suggested.split("`")
            if len(parts) >= 2:
                artifacts.add(parts[1])
    return sorted(artifacts)


def group_allowed_actions(
    group: str,
    lanes: list[dict[str, Any]],
    maintenance_only: bool,
) -> list[str]:
    actions = list(COMMON_ALLOWED_ACTIONS)
    if group == "acceleration":
        actions.append("parity-test design and CPU fallback audits only")
    elif group == "compute-economics":
        actions.append("cost-model and gate-threshold audits without new sweeps")
    elif group == "corpus-transform":
        actions.append("control-matrix audits and transform-policy notes")
    elif group == "format-policy":
        actions.append("wire-format review and ADR drafting without promotion")
    elif group == "meta-research":
        actions.append("ledger consistency checks and dispatch-brief maintenance")
        actions.append(
            "full evidence-regimen maintenance through scripts/generate_evidence_regimen.py"
        )
    elif group == "operator-ui":
        actions.append("static schema and evidence-card wiring checks")

    if not maintenance_only and any(item["status"] == "ready" for item in lanes):
        actions.append(
            "run only the pre-registered ready experiment after recording budget"
        )
    return actions


def group_forbidden_actions(group: str) -> list[str]:
    actions = list(COMMON_FORBIDDEN_ACTIONS)
    if group == "acceleration":
        actions.extend(
            [
                "do not trust GPU output without CPU parity",
                "do not market GPU as production acceleration",
            ]
        )
    elif group == "compute-economics":
        actions.extend(
            [
                "do not run full depth-4 execution",
                "do not expand broad raw depth search without a generated reopen trigger",
            ]
        )
    elif group == "corpus-transform":
        actions.extend(
            [
                "do not count transform-only shortening as Lotus compression",
                "do not merge held-out corpora into canonical matrices without a regeneration budget",
            ]
        )
    elif group == "format-policy":
        actions.extend(
            [
                "do not alter stable v1 compatibility",
                "do not add transform metadata to .tlmr before exact seed-span wins",
            ]
        )
    elif group == "operator-ui":
        actions.append("do not hide null results behind optimistic UI language")
    return actions


def output_contract(group: str) -> list[str]:
    return [
        "Findings first, with source artifact paths and current hash status.",
        "State whether every relevant stop rule remains active.",
        "List changed files, if any, and explain why the write scope was safe.",
        "If proposing compute, name the generated reopen trigger and budget gate.",
        "Report verification commands run, or say exactly why they were not run.",
        "Prefer the full evidence regimen when low-level generated artifacts move.",
        f"Keep the {group} claim boundary explicit and avoid unsupported conclusions.",
    ]


def build_prompt(
    brief_id: str,
    mission: str,
    artifacts: list[str],
    allowed_actions: list[str],
    forbidden_actions: list[str],
    contract: list[str],
    stop_rules: list[str],
) -> str:
    return "\n".join(
        [
            f"Brief {brief_id}: use dispatching-parallel-agents as an operating model.",
            f"Mission: {mission}",
            "Scope: No Seed Search, not a compression claim, and does not override SEARCH_FRONTIER_GATE.",
            f"Source artifacts: {', '.join(artifacts)}.",
            f"allowed_actions: {'; '.join(allowed_actions)}.",
            f"forbidden_actions: {'; '.join(forbidden_actions)}.",
            f"stop_rules: {'; '.join(stop_rules)}.",
            f"output_contract: {'; '.join(contract)}.",
            "Do not launch broad compute unless a generated artifact explicitly reopens the lane.",
        ]
    )


def build_briefs(frontier: dict[str, Any]) -> list[dict[str, Any]]:
    summary = frontier["summary"]
    maintenance_only = bool(summary["allowed_maintenance_only"])
    lookup = frontier_by_id(frontier)
    briefs = []
    for group, lanes in grouped_lanes(frontier).items():
        statuses = Counter(item["status"] for item in lanes)
        lane_ids = [item["lane"] for item in lanes]
        stop_rules = [item["stop_rule"] for item in lanes]
        artifacts = group_source_artifacts(lanes, lookup)
        allowed_actions = group_allowed_actions(group, lanes, maintenance_only)
        forbidden_actions = group_forbidden_actions(group)
        contract = output_contract(group)
        mission = GROUP_MISSIONS.get(
            group,
            "Audit the assigned generated evidence lane without changing claim boundaries.",
        )
        status = (
            "maintenance_only"
            if maintenance_only or statuses.get("ready", 0) == 0
            else "ready_requires_budget"
        )
        brief_id = f"brief-{group}"
        briefs.append(
            {
                "brief_id": brief_id,
                "parallel_group": group,
                "frontier_ids": lane_ids,
                "status": status,
                "mission": mission,
                "source_artifacts": artifacts,
                "allowed_actions": allowed_actions,
                "forbidden_actions": forbidden_actions,
                "write_scope": GROUP_WRITE_SCOPES.get(group, ["docs/", "scripts/"]),
                "output_contract": contract,
                "stop_rule": " | ".join(stop_rules),
                "claim_boundary": (
                    "This brief may improve evidence hygiene, but it may not claim "
                    "production viability or natural-corpus compression proof."
                ),
                "prompt": build_prompt(
                    brief_id,
                    mission,
                    artifacts,
                    allowed_actions,
                    forbidden_actions,
                    contract,
                    stop_rules,
                ),
            }
        )
    return briefs


def build_report() -> dict[str, Any]:
    frontier = load_json(SOURCE_PATHS["research_frontier_sha256"])
    decision = load_json(SOURCE_PATHS["research_decision_sha256"])
    queue = load_json(SOURCE_PATHS["experiment_queue_sha256"])
    goal = load_json(SOURCE_PATHS["goal_audit_sha256"])

    summary = frontier["summary"]
    briefs = build_briefs(frontier)
    forbidden_action_count = len(
        {action for brief in briefs for action in brief["forbidden_actions"]}
    )
    ready_dispatch_count = sum(
        1 for brief in briefs if brief["status"] == "ready_requires_budget"
    )
    protocol_status = (
        "maintenance_only_no_seed_search"
        if summary["ready_count"] == 0
        else "ready_lanes_require_budgeted_dispatch"
    )

    return {
        "generated_by": GENERATED_BY,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "scope": {
            "kind": "dispatch protocol",
            "dispatching_parallel_agents": True,
            "performs_seed_search": False,
            "launches_agents": False,
            "makes_compression_claim": False,
            "adds_format_support": False,
            "overrides_search_frontier_gate": False,
        },
        "source_hashes": source_hashes(),
        "summary": {
            "protocol_status": protocol_status,
            "ready_dispatch_count": ready_dispatch_count,
            "brief_count": len(briefs),
            "work_package_count": len(frontier["subagent_work_packages"]),
            "frontier_count": len(frontier["frontiers"]),
            "forbidden_action_count": forbidden_action_count,
            "ungated_compute_allowed": bool(summary["ungated_compute_allowed"]),
            "maintenance_only": bool(summary["allowed_maintenance_only"]),
            "production_proven": bool(summary["production_proven"]),
            "unresolved_count": int(summary["unresolved_count"]),
            "decision": decision["summary"]["decision"],
            "queue_ready_count": int(queue["summary"]["ready_count"]),
            "goal_unresolved_count": int(goal["unresolved_count"]),
        },
        "dispatch_policy": {
            "posture": (
                "Use subagents for read-only audits, generated-artifact "
                "maintenance, tests, and bounded design briefs only."
            ),
            "override_policy": frontier["override_policy"],
            "global_forbidden_actions": COMMON_FORBIDDEN_ACTIONS,
            "review_contract": [
                "Integrate one parallel group at a time.",
                "Check generated artifacts before trusting summaries.",
                "Reject briefs that weaken stop rules or source hashes.",
                "Run doc lint and relevant Rust/Tauri gates after edits.",
            ],
        },
        "agent_briefs": briefs,
    }


def write_report(payload: dict[str, Any]) -> None:
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary = payload["summary"]
    lines = [
        "# Telomere Research Team Protocol",
        "",
        f"Generated by `{GENERATED_BY}` from the generated frontier, decision, queue, and goal-audit artifacts.",
        "This is a No Seed Search dispatching-parallel-agents protocol: it launches no agents, performs no seed search, is not a compression claim, adds no `.tlmr` format support, and does not override SEARCH_FRONTIER_GATE.",
        "",
        "## Dispatch Posture",
        "",
        f"- Protocol status: `{summary['protocol_status']}`",
        f"- Ready dispatch count: `{summary['ready_dispatch_count']}`",
        f"- Brief count: `{summary['brief_count']}`",
        f"- Work package count: `{summary['work_package_count']}`",
        f"- Frontier count: `{summary['frontier_count']}`",
        f"- Forbidden action count: `{summary['forbidden_action_count']}`",
        f"- Ungated compute allowed: `{summary['ungated_compute_allowed']}`",
        f"- Maintenance only: `{summary['maintenance_only']}`",
        f"- Production proven: `{summary['production_proven']}`",
        f"- Unresolved evidence gates: `{summary['unresolved_count']}`",
        f"- Decision: `{summary['decision']}`",
        "",
        "Current posture: read-only audits and generated-artifact maintenance are allowed; do not launch broad compute.",
        "",
        "## Dispatch Policy",
        "",
        payload["dispatch_policy"]["posture"],
        "",
        payload["dispatch_policy"]["override_policy"],
        "",
        "## Agent Briefs",
        "",
        "| brief | group | status | lanes | mission |",
        "| --- | --- | --- | --- | --- |",
    ]
    for brief in payload["agent_briefs"]:
        lines.append(
            f"| `{cell(brief['brief_id'])}` | `{cell(brief['parallel_group'])}` | `{cell(brief['status'])}` | {cell(', '.join(brief['frontier_ids']))} | {cell(brief['mission'])} |"
        )

    for brief in payload["agent_briefs"]:
        lines.extend(
            [
                "",
                f"## {brief['brief_id']}",
                "",
                f"- Group: `{brief['parallel_group']}`",
                f"- Status: `{brief['status']}`",
                f"- Mission: {brief['mission']}",
                f"- Stop rule: {brief['stop_rule']}",
                f"- Claim boundary: {brief['claim_boundary']}",
                f"- Source artifacts: {', '.join(f'`{item}`' for item in brief['source_artifacts'])}",
                f"- Write scope: {', '.join(f'`{item}`' for item in brief['write_scope'])}",
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

    lines.extend(
        [
            "",
            "## Global Forbidden Actions",
            "",
        ]
    )
    for action in payload["dispatch_policy"]["global_forbidden_actions"]:
        lines.append(f"- {action}")

    lines.extend(
        [
            "",
            "## Review And Integration",
            "",
        ]
    )
    for item in payload["dispatch_policy"]["review_contract"]:
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## Source Artifacts",
            "",
            "The JSON `source_hashes` map pins this protocol to the exact upstream evidence files below.",
        ]
    )
    for name, digest in payload["source_hashes"].items():
        lines.append(f"- `{name}`: `{digest}`")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not REPORT_JSON.exists() or not REPORT_MD.exists():
        raise SystemExit("generated research team protocol files are missing")
    payload = load_json(REPORT_JSON)
    if payload.get("generated_by") != GENERATED_BY:
        raise SystemExit("research_team_protocol.json has wrong generated_by marker")
    if payload.get("source_hashes") != source_hashes():
        raise SystemExit("research team protocol source hashes are stale")
    expected = stable_projection(build_report())
    current = stable_projection(payload)
    if current != expected:
        raise SystemExit("research_team_protocol.json is stale; regenerate it")

    summary = payload["summary"]
    if summary["queue_ready_count"] == 0:
        if not summary["maintenance_only"]:
            raise SystemExit("research team protocol lost maintenance-only posture")
        if summary["ready_dispatch_count"] != 0:
            raise SystemExit("research team protocol exposes ready dispatch with no ready lanes")
    for brief in payload["agent_briefs"]:
        for field in (
            "brief_id",
            "parallel_group",
            "source_artifacts",
            "allowed_actions",
            "forbidden_actions",
            "write_scope",
            "output_contract",
            "stop_rule",
            "prompt",
        ):
            if not brief.get(field):
                raise SystemExit(
                    f"research team protocol brief {brief.get('brief_id')} missing {field}"
                )
        prompt = brief["prompt"]
        for phrase in (
            "dispatching-parallel-agents",
            "No Seed Search",
            "do not launch broad compute",
            "not a compression claim",
            "does not override SEARCH_FRONTIER_GATE",
            "forbidden_actions",
            "output_contract",
        ):
            if phrase not in prompt:
                raise SystemExit(
                    f"research team protocol brief {brief['brief_id']} missing prompt phrase: {phrase}"
                )

    text = REPORT_MD.read_text(encoding="utf-8")
    for phrase in (
        "Telomere Research Team Protocol",
        "dispatching-parallel-agents",
        "No Seed Search",
        "read-only audits",
        "generated-artifact maintenance",
        "forbidden_actions",
        "output_contract",
        "do not launch broad compute",
        "not a compression claim",
        "does not override SEARCH_FRONTIER_GATE",
        "Agent Briefs",
        "Global Forbidden Actions",
        "Review And Integration",
        "source_hashes",
    ):
        if phrase not in text:
            raise SystemExit(f"RESEARCH_TEAM_PROTOCOL.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate generated research team protocol files",
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
