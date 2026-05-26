#!/usr/bin/env python3
"""Generate the Telomere research-team operating packet.

This is a no-compute coordination artifact. It joins the hypothesis registry,
parallel-agent protocol, and blocked-requirement dispatch into one operational
roster for future agent work. It launches no agents and performs no seed search.
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
REPORT_JSON = DOCS / "research_team_packet.json"
REPORT_MD = DOCS / "RESEARCH_TEAM_PACKET.md"
GENERATED_BY = "scripts/generate_research_team_packet.py"

SOURCE_PATHS = {
    "research_hypotheses_sha256": DOCS / "research_hypotheses.json",
    "research_team_protocol_sha256": DOCS / "research_team_protocol.json",
    "blocked_requirement_dispatch_sha256": DOCS / "blocked_requirement_dispatch.json",
    "goal_completion_audit_sha256": DOCS / "goal_completion_audit.json",
    "research_frontier_sha256": DOCS / "research_frontier.json",
    "mechanism_experiment_ranking_sha256": DOCS / "mechanism_experiment_ranking.json",
    "natural_corpus_proof_matrix_sha256": DOCS / "natural_corpus_proof_matrix.json",
    "external_corpus_accession_sha256": DOCS / "external_corpus_accession.json",
    "production_proof_matrix_sha256": DOCS / "production_proof_matrix.json",
}

AGENT_ORDER = [
    "corpus-transform",
    "compute-economics",
    "format-policy",
    "acceleration",
    "operator-ui",
    "meta-research",
]

AGENT_CALLSIGNS = {
    "acceleration": "kernel-sentinel",
    "compute-economics": "frontier-accountant",
    "corpus-transform": "corpus-alchemist",
    "format-policy": "format-guardian",
    "meta-research": "ledger-captain",
    "operator-ui": "observatory-operator",
}

COMMON_HANDOFF_CONTRACT = [
    "findings first, with source artifacts and generated status",
    "state whether current evidence proves, contradicts, or blocks the lane",
    "list proposed files and exact check commands before broad edits",
    "preserve No Seed Search, not natural-corpus proof, and not production proof boundaries",
    "return a small diff plan if code/docs changes are recommended",
]

GLOBAL_FORBIDDEN_ACTIONS = [
    "do not launch broad compute",
    "No Seed Search: do not start new depth-3, depth-4, or long-span sweeps",
    "do not claim natural-corpus compression is proven",
    "do not claim production readiness",
    "do not weaken controls or source-hash checks",
    "do not edit generated markdown or JSON by hand",
]

INTEGRATION_GATES = [
    "python scripts/generate_research_team_packet.py --check",
    "python scripts/generate_research_hypotheses.py --check",
    "python scripts/generate_external_corpus_accession.py --check",
    "python scripts/generate_evidence_regimen.py --start-at external-corpus-accession --check",
    "python scripts/doc_lint.py",
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


def unique(items: list[Any]) -> list[Any]:
    seen = set()
    result = []
    for item in items:
        marker = json.dumps(item, sort_keys=True) if isinstance(item, (dict, list)) else item
        if marker in seen:
            continue
        seen.add(marker)
        result.append(item)
    return result


def hypothesis_by_id(hypotheses: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["hypothesis_id"]: item for item in hypotheses["hypotheses"]}


def team_brief_by_group(team: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["parallel_group"]: item for item in team["agent_briefs"]}


def blockers_by_group(blockers: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    groups = {group: [] for group in AGENT_ORDER}
    for brief in blockers["briefs"]:
        for group in brief["parallel_groups"]:
            groups.setdefault(group, []).append(brief)
    return groups


def priority_for_status(status: str) -> int:
    return {
        "pre-registered-design": 0,
        "ready-if-triggered": 1,
        "maintenance-only": 2,
        "blocked-by-evidence": 3,
    }.get(status, 9)


def agent_mode(hypotheses: list[dict[str, Any]], blocked: list[dict[str, Any]]) -> str:
    if any(item["status"] == "pre-registered-design" for item in hypotheses):
        return "pre_register_without_compute"
    if any(item["status"] == "ready-if-triggered" for item in hypotheses):
        return "design_and_wait_for_trigger"
    if blocked:
        return "blocked_requirement_audit"
    return "maintenance_only"


def primary_hypotheses(group: str, hypotheses: dict[str, Any]) -> list[dict[str, Any]]:
    lookup = hypothesis_by_id(hypotheses)
    ids = hypotheses["dispatch_matrix"].get(group, [])
    rows = [lookup[item] for item in ids]
    return sorted(rows, key=lambda item: (priority_for_status(item["status"]), item["hypothesis_id"]))


def build_agent_prompt(agent: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"Agent {agent['agent_id']} ({agent['callsign']}): use dispatching-parallel-agents as the operating model.",
            f"Mission: {agent['mission']}",
            f"Mode: {agent['mode']}",
            "Scope: No Seed Search, not a compression claim, not natural-corpus proof, and not production proof.",
            f"Primary hypotheses: {', '.join(agent['hypothesis_ids']) or 'none'}.",
            f"Blocked requirements: {', '.join(agent['blocked_requirement_ids']) or 'none'}.",
            f"Source artifacts: {', '.join(agent['source_artifacts'])}.",
            f"Allowed actions: {'; '.join(agent['allowed_actions'])}.",
            f"Forbidden actions: {'; '.join(agent['forbidden_actions'])}.",
            f"Handoff contract: {'; '.join(agent['handoff_contract'])}.",
            f"Integration gates: {'; '.join(agent['integration_gates'])}.",
            "Return findings first and do not launch broad compute.",
        ]
    )


def build_agents(
    hypotheses: dict[str, Any],
    team: dict[str, Any],
    blockers: dict[str, Any],
) -> list[dict[str, Any]]:
    team_by_group = team_brief_by_group(team)
    blockers_grouped = blockers_by_group(blockers)
    agents = []
    for group in AGENT_ORDER:
        team_brief = team_by_group[group]
        group_hypotheses = primary_hypotheses(group, hypotheses)
        group_blockers = blockers_grouped.get(group, [])
        source_artifacts = unique(
            team_brief.get("source_artifacts", [])
            + [
                artifact
                for hypothesis in group_hypotheses
                for artifact in hypothesis["source_artifacts"]
            ]
            + [
                artifact
                for blocker in group_blockers
                for artifact in blocker["source_artifacts"]
            ]
        )
        allowed_actions = unique(
            team_brief.get("allowed_actions", [])
            + [
                "pre-register narrow artifacts without running broad compute"
                if any(h["status"] == "pre-registered-design" for h in group_hypotheses)
                else "read-only evidence audit and generated-artifact maintenance"
            ]
            + [
                action
                for blocker in group_blockers
                for action in blocker["allowed_actions"]
            ]
        )
        forbidden_actions = unique(
            GLOBAL_FORBIDDEN_ACTIONS
            + team_brief.get("forbidden_actions", [])
            + [
                action
                for hypothesis in group_hypotheses
                for action in hypothesis["forbidden_actions"]
            ]
            + [
                action
                for blocker in group_blockers
                for action in blocker["forbidden_actions"]
            ]
        )
        promotion_triggers = unique(
            [hypothesis["promotion_trigger"] for hypothesis in group_hypotheses]
            + [blocker["promotion_trigger"] for blocker in group_blockers]
        )
        stop_rules = unique(
            [team_brief["stop_rule"]]
            + [hypothesis["stop_rule"] for hypothesis in group_hypotheses]
            + [blocker["stop_rule"] for blocker in group_blockers]
        )
        agent = {
            "agent_id": f"agent-{group}",
            "parallel_group": group,
            "callsign": AGENT_CALLSIGNS[group],
            "mode": agent_mode(group_hypotheses, group_blockers),
            "mission": team_brief["mission"],
            "hypothesis_ids": [item["hypothesis_id"] for item in group_hypotheses],
            "hypothesis_statuses": {
                item["hypothesis_id"]: item["status"] for item in group_hypotheses
            },
            "blocked_requirement_ids": [
                item["requirement_id"] for item in group_blockers
            ],
            "source_artifacts": source_artifacts,
            "write_scope": team_brief.get("write_scope", []),
            "allowed_actions": allowed_actions,
            "forbidden_actions": forbidden_actions,
            "promotion_triggers": promotion_triggers,
            "stop_rules": stop_rules,
            "handoff_contract": COMMON_HANDOFF_CONTRACT + team_brief.get("output_contract", []),
            "integration_gates": INTEGRATION_GATES,
        }
        agent["prompt"] = build_agent_prompt(agent)
        agents.append(agent)
    return agents


def build_work_board(
    agents: list[dict[str, Any]],
    hypotheses: dict[str, Any],
    blockers: dict[str, Any],
) -> list[dict[str, Any]]:
    lookup = hypothesis_by_id(hypotheses)
    board = []
    for agent in agents:
        for hypothesis_id in agent["hypothesis_ids"]:
            hypothesis = lookup[hypothesis_id]
            board.append(
                {
                    "agent_id": agent["agent_id"],
                    "parallel_group": agent["parallel_group"],
                    "item_id": hypothesis_id,
                    "kind": "hypothesis",
                    "status": hypothesis["status"],
                    "suggested_artifact": hypothesis["suggested_artifact"],
                    "promotion_trigger": hypothesis["promotion_trigger"],
                    "stop_rule": hypothesis["stop_rule"],
                }
            )
        for blocker in blockers_by_group(blockers).get(agent["parallel_group"], []):
            board.append(
                {
                    "agent_id": agent["agent_id"],
                    "parallel_group": agent["parallel_group"],
                    "item_id": blocker["requirement_id"],
                    "kind": "blocked-requirement",
                    "status": blocker["requirement_status"],
                    "suggested_artifact": "docs/BLOCKED_REQUIREMENT_DISPATCH.md",
                    "promotion_trigger": blocker["promotion_trigger"],
                    "stop_rule": blocker["stop_rule"],
                }
            )
    return sorted(
        board,
        key=lambda item: (
            AGENT_ORDER.index(item["parallel_group"]),
            item["kind"],
            priority_for_status(item["status"]),
            item["item_id"],
        ),
    )


def build_report() -> dict[str, Any]:
    hypotheses = load_json(SOURCE_PATHS["research_hypotheses_sha256"])
    team = load_json(SOURCE_PATHS["research_team_protocol_sha256"])
    blockers = load_json(SOURCE_PATHS["blocked_requirement_dispatch_sha256"])
    completion = load_json(SOURCE_PATHS["goal_completion_audit_sha256"])
    frontier = load_json(SOURCE_PATHS["research_frontier_sha256"])
    mechanism = load_json(SOURCE_PATHS["mechanism_experiment_ranking_sha256"])
    natural = load_json(SOURCE_PATHS["natural_corpus_proof_matrix_sha256"])
    production = load_json(SOURCE_PATHS["production_proof_matrix_sha256"])

    agents = build_agents(hypotheses, team, blockers)
    work_board = build_work_board(agents, hypotheses, blockers)
    completion_summary = summary(completion)
    frontier_summary = summary(frontier)
    natural_summary = summary(natural)
    production_summary = summary(production)
    hypothesis_summary = summary(hypotheses)

    return {
        "generated_by": GENERATED_BY,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "scope": {
            "kind": "research team operating packet",
            "dispatching_parallel_agents": True,
            "launches_agents": False,
            "performs_seed_search": False,
            "makes_compression_claim": False,
            "is_natural_corpus_proof": False,
            "is_production_proof": False,
            "overrides_search_frontier_gate": False,
        },
        "source_hashes": source_hashes(),
        "summary": {
            "agent_count": len(agents),
            "work_item_count": len(work_board),
            "hypothesis_count": hypothesis_summary["hypothesis_count"],
            "blocked_requirement_count": len(blockers["briefs"]),
            "parallel_groups": AGENT_ORDER,
            "launch_ready_agent_count": 0,
            "ungated_compute_allowed": bool(frontier_summary["ungated_compute_allowed"]),
            "broad_depth_search_allowed": bool(
                frontier_summary["broad_depth_search_allowed"]
            ),
            "natural_corpus_proven": bool(natural_summary["natural_corpus_proven"]),
            "production_proven": bool(production_summary["production_proven"]),
            "objective_status": completion_summary["objective_status"],
            "completion_recommendation": completion_summary[
                "completion_recommendation"
            ],
            "top_mechanism_lane": summary(mechanism)["top_lane_id"],
            "team_mode": "parallel_research_design_and_evidence_maintenance",
            "claim_boundary": (
                "No Seed Search; not natural-corpus proof; not production proof; "
                "not a compression claim."
            ),
            "conclusion": (
                "Run these as independent design/audit briefs only; integration "
                "happens through generated artifacts and checks, not by weakening gates."
            ),
        },
        "integration_protocol": {
            "integration_gates": INTEGRATION_GATES,
            "global_forbidden_actions": GLOBAL_FORBIDDEN_ACTIONS,
            "merge_policy": [
                "integrate one parallel group at a time",
                "prefer generator changes over hand-written generated-doc edits",
                "rerun the final evidence-regimen segment after packet or hypothesis changes",
                "reject any lane that removes blockers without source evidence moving",
            ],
            "conflict_policy": [
                "agents may read shared artifacts concurrently",
                "agents should not edit the same generator in parallel",
                "format-policy must review any proposed .tlmr metadata change",
                "meta-research owns source-hash and completion-boundary changes",
            ],
        },
        "agents": agents,
        "work_board": work_board,
    }


def write_report(payload: dict[str, Any]) -> None:
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary_payload = payload["summary"]
    lines = [
        "# Telomere Research Team Packet",
        "",
        f"Generated by `{GENERATED_BY}` from the hypothesis registry, dispatch protocol, and blocked-requirement briefs.",
        "This is a No Seed Search dispatching-parallel-agents operating packet: it launches no agents, performs no seed search, is not natural-corpus proof, is not production proof, and is not a compression claim.",
        "",
        "## Summary",
        "",
        f"- Agents: `{summary_payload['agent_count']}`",
        f"- Work items: `{summary_payload['work_item_count']}`",
        f"- Hypotheses: `{summary_payload['hypothesis_count']}`",
        f"- Blocked requirements: `{summary_payload['blocked_requirement_count']}`",
        f"- Launch-ready agents: `{summary_payload['launch_ready_agent_count']}`",
        f"- Ungated compute allowed: `{summary_payload['ungated_compute_allowed']}`",
        f"- Broad depth search allowed: `{summary_payload['broad_depth_search_allowed']}`",
        f"- Natural-corpus proven: `{summary_payload['natural_corpus_proven']}`",
        f"- Production proven: `{summary_payload['production_proven']}`",
        f"- Objective status: `{summary_payload['objective_status']}`",
        f"- Top mechanism lane: `{summary_payload['top_mechanism_lane']}`",
        "",
        summary_payload["conclusion"],
        "",
        "## Agent Roster",
        "",
        "| agent | group | mode | hypotheses | blockers |",
        "| --- | --- | --- | ---: | ---: |",
    ]
    for agent in payload["agents"]:
        lines.append(
            f"| `{agent['callsign']}` | `{agent['parallel_group']}` | `{agent['mode']}` | "
            f"{len(agent['hypothesis_ids'])} | {len(agent['blocked_requirement_ids'])} |"
        )

    lines.extend(["", "## Work Board", ""])
    lines.extend(
        [
            "| group | item | kind | status | suggested artifact |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for item in payload["work_board"]:
        lines.append(
            f"| `{cell(item['parallel_group'])}` | `{cell(item['item_id'])}` | "
            f"`{cell(item['kind'])}` | `{cell(item['status'])}` | "
            f"`{cell(item['suggested_artifact'])}` |"
        )

    lines.extend(["", "## Agent Briefs", ""])
    for agent in payload["agents"]:
        lines.extend(
            [
                f"### {agent['callsign']}",
                "",
                f"- Agent ID: `{agent['agent_id']}`",
                f"- Parallel group: `{agent['parallel_group']}`",
                f"- Mode: `{agent['mode']}`",
                f"- Mission: {agent['mission']}",
                f"- Hypotheses: {', '.join(f'`{item}`' for item in agent['hypothesis_ids']) or '`none`'}",
                f"- Blocked requirements: {', '.join(f'`{item}`' for item in agent['blocked_requirement_ids']) or '`none`'}",
                f"- Source artifacts: {', '.join(f'`{item}`' for item in agent['source_artifacts'])}",
                f"- Write scope: {', '.join(f'`{item}`' for item in agent['write_scope'])}",
                "",
                "Promotion triggers:",
            ]
        )
        for trigger in agent["promotion_triggers"]:
            lines.append(f"- {trigger}")
        lines.extend(["", "Stop rules:"])
        for stop_rule in agent["stop_rules"]:
            lines.append(f"- {stop_rule}")
        lines.extend(
            [
                "",
                "Prompt:",
                "",
                "```text",
                agent["prompt"],
                "```",
                "",
            ]
        )

    lines.extend(["## Integration Protocol", ""])
    lines.append("Integration gates:")
    for command in payload["integration_protocol"]["integration_gates"]:
        lines.append(f"- `{command}`")
    lines.extend(["", "Merge policy:"])
    for item in payload["integration_protocol"]["merge_policy"]:
        lines.append(f"- {item}")
    lines.extend(["", "Conflict policy:"])
    for item in payload["integration_protocol"]["conflict_policy"]:
        lines.append(f"- {item}")
    lines.extend(["", "Global forbidden actions:"])
    for item in payload["integration_protocol"]["global_forbidden_actions"]:
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## Source Artifacts",
            "",
            "The JSON `source_hashes` map pins this packet to the exact upstream evidence files below.",
        ]
    )
    for name, digest in payload["source_hashes"].items():
        lines.append(f"- `{name}`: `{digest}`")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not REPORT_JSON.exists() or not REPORT_MD.exists():
        raise SystemExit("generated research team packet files are missing")
    payload = load_json(REPORT_JSON)
    if payload.get("generated_by") != GENERATED_BY:
        raise SystemExit("research_team_packet.json has wrong generated_by marker")
    if payload.get("source_hashes") != source_hashes():
        raise SystemExit("research_team_packet.json source hashes are stale")
    expected = stable_projection(build_report())
    current = stable_projection(payload)
    if current != expected:
        raise SystemExit("research_team_packet.json is stale; regenerate it")
    scope = payload.get("scope", {})
    for field in (
        "launches_agents",
        "performs_seed_search",
        "makes_compression_claim",
        "is_natural_corpus_proof",
        "is_production_proof",
        "overrides_search_frontier_gate",
    ):
        if scope.get(field) is not False:
            raise SystemExit(f"research_team_packet.json scope field must be false: {field}")
    summary_payload = payload["summary"]
    if summary_payload["agent_count"] != len(AGENT_ORDER):
        raise SystemExit("research team packet lost one or more required agents")
    if summary_payload["launch_ready_agent_count"] != 0:
        raise SystemExit("research team packet must not launch agents automatically")
    for agent in payload["agents"]:
        for field in (
            "agent_id",
            "parallel_group",
            "callsign",
            "mode",
            "mission",
            "hypothesis_ids",
            "source_artifacts",
            "forbidden_actions",
            "handoff_contract",
            "integration_gates",
            "prompt",
        ):
            if not agent.get(field):
                raise SystemExit(
                    f"research team packet agent {agent.get('agent_id')} missing {field}"
                )
        prompt = agent["prompt"]
        for phrase in (
            "dispatching-parallel-agents",
            "No Seed Search",
            "not a compression claim",
            "not natural-corpus proof",
            "not production proof",
            "Integration gates",
            "Handoff contract",
        ):
            if phrase not in prompt:
                raise SystemExit(
                    f"research team packet agent {agent['agent_id']} prompt missing phrase: {phrase}"
                )
    text = REPORT_MD.read_text(encoding="utf-8")
    for phrase in (
        "Telomere Research Team Packet",
        "Agent Roster",
        "Work Board",
        "Agent Briefs",
        "Integration Protocol",
        "dispatching-parallel-agents",
        "No Seed Search",
        "not natural-corpus proof",
        "not production proof",
        "source_hashes",
    ):
        if phrase not in text:
            raise SystemExit(f"RESEARCH_TEAM_PACKET.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="validate generated research team packet"
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
