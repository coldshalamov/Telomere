#!/usr/bin/env python3
"""Generate dispatch-ready Telomere research-agent prompts.

This is a coordination artifact derived from `docs/research_team_packet.json`.
It does not launch agents, run compute, or make compression claims. Its job is
to expose one self-contained prompt per parallel research lane so future
subagent work starts from the same evidence and stop rules.
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
SOURCE_PACKET = DOCS / "research_team_packet.json"
REPORT_JSON = DOCS / "research_agent_prompts.json"
REPORT_MD = DOCS / "RESEARCH_AGENT_PROMPTS.md"
PROMPT_DIR = DOCS / "agent_prompts"
GENERATED_BY = "scripts/generate_research_agent_prompts.py"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_projection(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if key != "generated_at"}


def cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def prompt_filename(agent: dict[str, Any]) -> str:
    return f"{agent['agent_id']}-{agent['parallel_group']}.prompt.txt"


def prompt_relative_path(agent: dict[str, Any]) -> str:
    return f"docs/agent_prompts/{prompt_filename(agent)}"


def prompt_text(agent: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"# {agent['agent_id']} ({agent['callsign']})",
            "",
            f"parallel_group: {agent['parallel_group']}",
            f"mode: {agent['mode']}",
            "scope: No Seed Search; not natural-corpus proof; not production proof; not a compression claim.",
            "",
            agent["prompt"],
            "",
        ]
    )


def build_prompt_record(agent: dict[str, Any]) -> dict[str, Any]:
    return {
        "agent_id": agent["agent_id"],
        "parallel_group": agent["parallel_group"],
        "callsign": agent["callsign"],
        "mode": agent["mode"],
        "mission": agent["mission"],
        "prompt_filename": prompt_filename(agent),
        "prompt_path": prompt_relative_path(agent),
        "hypothesis_ids": agent["hypothesis_ids"],
        "blocked_requirement_ids": agent["blocked_requirement_ids"],
        "source_artifacts": agent["source_artifacts"],
        "write_scope": agent["write_scope"],
        "integration_gates": agent["integration_gates"],
        "prompt": agent["prompt"],
    }


def build_report() -> dict[str, Any]:
    packet = load_json(SOURCE_PACKET)
    agents = [build_prompt_record(agent) for agent in packet["agents"]]
    summary = packet["summary"]
    return {
        "generated_by": GENERATED_BY,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "scope": {
            "kind": "research-agent prompt pack",
            "dispatching_parallel_agents": True,
            "launches_agents": False,
            "performs_seed_search": False,
            "makes_compression_claim": False,
            "is_natural_corpus_proof": False,
            "is_production_proof": False,
            "allows_compute": False,
        },
        "source_hashes": {
            "research_team_packet_sha256": sha256(SOURCE_PACKET),
        },
        "summary": {
            "agent_prompt_count": len(agents),
            "parallel_groups": summary["parallel_groups"],
            "launch_ready_agent_count": summary["launch_ready_agent_count"],
            "ungated_compute_allowed": summary["ungated_compute_allowed"],
            "broad_depth_search_allowed": summary["broad_depth_search_allowed"],
            "natural_corpus_proven": summary["natural_corpus_proven"],
            "production_proven": summary["production_proven"],
            "team_mode": summary["team_mode"],
            "claim_boundary": summary["claim_boundary"],
            "dispatch_boundary": (
                "Human-dispatchable prompts only; no agents are launched by this artifact."
            ),
        },
        "integration_protocol": packet["integration_protocol"],
        "agent_prompts": agents,
    }


def write_report(payload: dict[str, Any]) -> None:
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    PROMPT_DIR.mkdir(parents=True, exist_ok=True)
    expected_prompt_names = set()
    for agent in payload["agent_prompts"]:
        expected_prompt_names.add(agent["prompt_filename"])
        (PROMPT_DIR / agent["prompt_filename"]).write_text(
            prompt_text(agent), encoding="utf-8"
        )
    for existing in PROMPT_DIR.glob("*.prompt.txt"):
        if existing.name not in expected_prompt_names:
            existing.unlink()

    summary = payload["summary"]
    lines = [
        "# Research Agent Prompts",
        "",
        f"Generated by `{GENERATED_BY}` from `docs/research_team_packet.json`.",
        "This is a dispatching-parallel-agents prompt pack. It launches no agents, performs no seed search, is not natural-corpus proof, is not production proof, and makes no compression claim.",
        "",
        "## Summary",
        "",
        f"- Agent prompts: `{summary['agent_prompt_count']}`",
        f"- Parallel groups: `{', '.join(summary['parallel_groups'])}`",
        f"- Launch-ready agents: `{summary['launch_ready_agent_count']}`",
        f"- Ungated compute allowed: `{summary['ungated_compute_allowed']}`",
        f"- Broad depth search allowed: `{summary['broad_depth_search_allowed']}`",
        f"- Natural-corpus proven: `{summary['natural_corpus_proven']}`",
        f"- Production proven: `{summary['production_proven']}`",
        f"- Team mode: `{summary['team_mode']}`",
        f"- Prompt directory: `docs/agent_prompts/`",
        "",
        "## Prompt Index",
        "",
        "| agent | group | callsign | mode | prompt file |",
        "| --- | --- | --- | --- | --- |",
    ]
    for agent in payload["agent_prompts"]:
        lines.append(
            f"| `{cell(agent['agent_id'])}` | `{cell(agent['parallel_group'])}` | "
            f"`{cell(agent['callsign'])}` | `{cell(agent['mode'])}` | "
            f"`{cell(agent['prompt_path'])}` |"
        )

    lines.extend(
        [
            "",
            "## Integration Gates",
            "",
        ]
    )
    for gate in payload["integration_protocol"]["integration_gates"]:
        lines.append(f"- `{gate}`")

    lines.extend(
        [
            "",
            "## Global Forbidden Actions",
            "",
        ]
    )
    for action in payload["integration_protocol"]["global_forbidden_actions"]:
        lines.append(f"- {action}")

    lines.extend(["", "## Agent Prompts", ""])
    for agent in payload["agent_prompts"]:
        lines.extend(
            [
                f"### {agent['agent_id']} ({agent['callsign']})",
                "",
                f"- Parallel group: `{agent['parallel_group']}`",
                f"- Mode: `{agent['mode']}`",
                f"- Mission: {agent['mission']}",
                f"- Prompt file: `{agent['prompt_path']}`",
                f"- Source artifacts: {', '.join(f'`{item}`' for item in agent['source_artifacts'])}",
                f"- Write scope: {', '.join(f'`{item}`' for item in agent['write_scope']) or '`read-only`'}",
                "",
                "```text",
                agent["prompt"],
                "```",
                "",
            ]
        )

    lines.extend(
        [
            "## Source Artifacts",
            "",
            "The JSON `source_hashes` map pins this prompt pack to the exact upstream team packet.",
        ]
    )
    for name, digest in payload["source_hashes"].items():
        lines.append(f"- `{name}`: `{digest}`")

    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not REPORT_JSON.exists() or not REPORT_MD.exists():
        raise SystemExit("generated research agent prompt files are missing")
    payload = load_json(REPORT_JSON)
    if payload.get("generated_by") != GENERATED_BY:
        raise SystemExit("research_agent_prompts.json has wrong generated_by marker")
    expected = stable_projection(build_report())
    current = stable_projection(payload)
    if current != expected:
        raise SystemExit("research_agent_prompts.json is stale; regenerate it")
    if payload.get("source_hashes", {}).get("research_team_packet_sha256") != sha256(
        SOURCE_PACKET
    ):
        raise SystemExit("research_agent_prompts.json source hash is stale")
    summary = payload["summary"]
    if summary["agent_prompt_count"] != len(payload["agent_prompts"]):
        raise SystemExit("research agent prompt count is stale")
    if summary["agent_prompt_count"] != 6:
        raise SystemExit("research agent prompt pack must contain six agents")
    if summary["launch_ready_agent_count"] != 0:
        raise SystemExit("research agent prompt pack must not mark agents launch-ready")
    for field in (
        "ungated_compute_allowed",
        "broad_depth_search_allowed",
        "natural_corpus_proven",
        "production_proven",
    ):
        if summary[field] is not False:
            raise SystemExit(f"research agent prompt pack cannot set {field}=true")
    scope = payload.get("scope", {})
    for field in (
        "launches_agents",
        "performs_seed_search",
        "makes_compression_claim",
        "is_natural_corpus_proof",
        "is_production_proof",
        "allows_compute",
    ):
        if scope.get(field) is not False:
            raise SystemExit(f"research agent prompt pack scope field must be false: {field}")
    seen = set()
    for agent in payload["agent_prompts"]:
        if agent["agent_id"] in seen:
            raise SystemExit("research agent prompt ids are not unique")
        seen.add(agent["agent_id"])
        prompt_path = ROOT / agent["prompt_path"]
        if not prompt_path.exists():
            raise SystemExit(f"research agent prompt file is missing: {agent['prompt_path']}")
        if prompt_path.read_text(encoding="utf-8") != prompt_text(agent):
            raise SystemExit(f"research agent prompt file is stale: {agent['prompt_path']}")
        prompt = agent["prompt"]
        for phrase in (
            "use dispatching-parallel-agents",
            "No Seed Search",
            "not natural-corpus proof",
            "not production proof",
            "do not launch broad compute",
            "Return findings first",
        ):
            if phrase not in prompt:
                raise SystemExit(
                    f"research agent prompt {agent['agent_id']} missing phrase: {phrase}"
                )
    text = REPORT_MD.read_text(encoding="utf-8")
    for phrase in (
        "Research Agent Prompts",
        "dispatching-parallel-agents prompt pack",
        "Prompt Index",
        "docs/agent_prompts/",
        "Integration Gates",
        "Global Forbidden Actions",
        "Agent Prompts",
        "source_hashes",
    ):
        if phrase not in text:
            raise SystemExit(f"RESEARCH_AGENT_PROMPTS.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="validate generated research-agent prompts"
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
