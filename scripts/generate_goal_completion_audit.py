#!/usr/bin/env python3
"""Generate the active-goal completion audit for Telomere.

This is a no-compute proof ledger. It maps the user's active research objective
to checked-in evidence and keeps the completion boundary explicit: the project
can be research-viable while the active goal remains unfinished.
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
REPORT_JSON = DOCS / "goal_completion_audit.json"
REPORT_MD = DOCS / "GOAL_COMPLETION_AUDIT.md"
GENERATED_BY = "scripts/generate_goal_completion_audit.py"

SOURCE_PATHS = {
    "whitepaper_sha256": DOCS / "Telomere Whitepaper V2.md",
    "architecture_sha256": DOCS / "ARCHITECTURE.md",
    "format_sha256": DOCS / "FORMAT.md",
    "research_program_sha256": DOCS / "RESEARCH_PROGRAM.md",
    "results_sha256": DOCS / "results.json",
    "viability_sha256": DOCS / "viability.json",
    "research_scorecard_sha256": DOCS / "research_scorecard.json",
    "goal_audit_sha256": DOCS / "goal_audit.json",
    "research_decision_sha256": DOCS / "research_decision.json",
    "research_frontier_sha256": DOCS / "research_frontier.json",
    "natural_corpus_proof_matrix_sha256": DOCS / "natural_corpus_proof_matrix.json",
    "production_proof_matrix_sha256": DOCS / "production_proof_matrix.json",
    "research_team_protocol_sha256": DOCS / "research_team_protocol.json",
    "ui_workflow_smoke_sha256": DOCS / "ui_workflow_smoke.json",
}

OBJECTIVE = (
    "come up with all the ways that you would take this project, as a .01% top "
    "researcher in this new field of compression science; build a whole regimen "
    "of testing and documenting and explore this idea until you've proven its "
    "viability and made the program work; read Telomere Whitepaper V2.md; "
    "identify things that could be tweaked and use subagents in brainstorming "
    "sessions; organize a dispatching-parallel-agents research team that will "
    "test, explore, research, and prove the viability of this idea and program "
    "as it runs"
)


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


def scorecard_status_count(scorecard: dict[str, Any], status: str) -> int:
    counts = scorecard.get("scorecard_status_counts", {})
    return int(counts.get(status, 0)) if isinstance(counts, dict) else 0


def build_requirements(
    goal: dict[str, Any],
    decision: dict[str, Any],
    frontier: dict[str, Any],
    team: dict[str, Any],
    viability: dict[str, Any],
    scorecard: dict[str, Any],
    results: dict[str, Any],
    ui_smoke: dict[str, Any],
    natural_proof: dict[str, Any],
    production_proof: dict[str, Any],
) -> list[dict[str, Any]]:
    decision_summary = summary(decision)
    frontier_summary = summary(frontier)
    team_summary = summary(team)
    ui_summary = summary(ui_smoke)
    natural_summary = summary(natural_proof)
    production_summary = summary(production_proof)

    return [
        {
            "requirement_id": "whitepaper-alignment",
            "requirement": "Read and anchor the project against Telomere Whitepaper V2.",
            "status": "complete",
            "authoritative_evidence": [
                "docs/Telomere Whitepaper V2.md",
                "docs/ARCHITECTURE.md",
                "docs/FORMAT.md",
                "docs/RESEARCH_PROGRAM.md",
            ],
            "finding": (
                "The canonical docs separate implemented architecture, experimental "
                "v2/indexed work, and theoretical whitepaper claims."
            ),
            "remaining_proof_gap": (
                "Keep future whitepaper-derived claims tied to generated evidence and "
                "compatibility boundaries."
            ),
        },
        {
            "requirement_id": "program-works-as-codec",
            "requirement": "Make the program work as a deterministic lossless codec and CLI.",
            "status": "complete",
            "authoritative_evidence": [
                "docs/GOAL_AUDIT.md",
                "src/main.rs",
                "src/lib.rs",
                "tests/cli_tests.rs",
                "tests/indexed_v2.rs",
                "tests/streaming.rs",
            ],
            "finding": (
                f"Goal audit status is {goal['overall_status']}; current implementation "
                "covers v1, experimental v2, indexed/streaming engines, and decoder checks."
            ),
            "remaining_proof_gap": (
                "Passing gates prove current behavior, not generalized compression viability."
            ),
        },
        {
            "requirement_id": "testing-documentation-regimen",
            "requirement": "Build a whole regimen of testing, documentation, and generated results.",
            "status": "complete",
            "authoritative_evidence": [
                "docs/RELEASE_CHECKLIST.md",
                "docs/RESULTS.md",
                "docs/results.json",
                "scripts/doc_lint.py",
            ],
            "finding": (
                f"Generated results format {results['format_version']} and doc lint "
                "tie claims to checked artifacts and release gates."
            ),
            "remaining_proof_gap": (
                "Continue regenerating ledgers whenever new experimental evidence is added."
            ),
        },
        {
            "requirement_id": "mechanism-evidence",
            "requirement": "Prove the mechanism can produce negative delta under controlled conditions.",
            "status": "proved",
            "authoritative_evidence": [
                "docs/RESULTS.md",
                "docs/VIABILITY.md",
                "tests/planted_corpus.rs",
                "tests/fixtures/planted_sha256_arity2.hex",
            ],
            "finding": (
                "Viability ledger records planted short-seed and planted-span negative "
                "delta evidence."
            ),
            "remaining_proof_gap": (
                "Planted data proves mechanism, not prevalence in natural corpora."
            ),
        },
        {
            "requirement_id": "frontier-exploration",
            "requirement": "Explore tweaks and frontiers like transforms, depth, sidecars, GPU, and recursion.",
            "status": "qualified",
            "authoritative_evidence": [
                "docs/RESEARCH_FRONTIER.md",
                "docs/EXPERIMENT_QUEUE.md",
                "docs/SEARCH_FRONTIER_GATE.md",
                "docs/LONG_SPAN_BUNDLE_GATE.md",
            ],
            "finding": (
                f"Frontier status is {frontier_summary['frontier_status']}; "
                f"{frontier_summary['ready_count']} ready lanes, "
                f"{frontier_summary['gated_count']} gated lanes, and "
                f"{frontier_summary['blocked_by_evidence_count']} blocked-by-evidence lanes."
            ),
            "remaining_proof_gap": (
                "No ready ungated compute remains; reopen requires generated evidence triggers."
            ),
        },
        {
            "requirement_id": "parallel-research-team",
            "requirement": "Organize a dispatching-parallel-agents research team.",
            "status": "complete",
            "authoritative_evidence": [
                "docs/RESEARCH_TEAM_PROTOCOL.md",
                "docs/research_team_protocol.json",
                "docs/UI_WORKFLOW_SMOKE.md",
            ],
            "finding": (
                f"Team protocol defines {team_summary['brief_count']} briefs across "
                f"{team_summary['work_package_count']} work packages with "
                f"{team_summary['forbidden_action_count']} forbidden actions."
            ),
            "remaining_proof_gap": (
                "Current posture is maintenance-only; future agents need generated reopen "
                "triggers before running compute-heavy lanes."
            ),
        },
        {
            "requirement_id": "operator-visibility",
            "requirement": "Make research state visible enough for future operators and UI work.",
            "status": "complete",
            "authoritative_evidence": [
                "docs/UI_WORKFLOW_SMOKE.md",
                "docs/ui_workflow_smoke.json",
                "src-tauri/src/main.rs",
                "ui/index.html",
            ],
            "finding": (
                f"UI smoke promotion is {ui_summary['promotion_met']} with "
                f"{ui_summary['required_artifact_count']} required artifacts and "
                f"{ui_summary['required_card_count']} required cards."
            ),
            "remaining_proof_gap": (
                "Static smoke is not a desktop browser run; keep Tauri tests green after UI changes."
            ),
        },
        {
            "requirement_id": "natural-corpus-viability",
            "requirement": "Prove generalized viability on non-planted or natural corpora.",
            "status": "blocked-by-evidence",
            "authoritative_evidence": [
                "docs/VIABILITY.md",
                "docs/NATURAL_CORPUS_PROOF_MATRIX.md",
                "docs/RESEARCH_SCORECARD.md",
                "docs/RESEARCH_DECISION.md",
                "docs/SEARCH_FRONTIER_GATE.md",
            ],
            "finding": (
                f"Natural-corpus matrix status is {natural_summary['natural_corpus_status']}; "
                f"{natural_summary['blocked_by_evidence_count']} natural-corpus gates are blocked-by-evidence, "
                f"held-out selected-span rows are {natural_summary['heldout_selected_span_rows']}, "
                f"and the best non-planted forecast is {natural_summary['best_non_planted_gib_for_one_expected_hit']} GiB per expected exact hit."
            ),
            "remaining_proof_gap": (
                "Need repeatable non-planted selected spans or negative delta with controls intact."
            ),
        },
        {
            "requirement_id": "production-proof",
            "requirement": "Prove production readiness, compatibility guarantees, and acceleration value.",
            "status": "blocked-by-evidence",
            "authoritative_evidence": [
                "docs/RELEASE_CHECKLIST.md",
                "docs/PRODUCTION_PROOF_MATRIX.md",
                "docs/ACCELERATION.md",
                "docs/SCALE_PERFORMANCE.md",
                "docs/RESEARCH_DECISION.md",
            ],
            "finding": (
                f"Production matrix status is {production_summary['production_status']}; "
                f"{production_summary['blocked_by_evidence_count']} production gates are blocked-by-evidence and "
                f"{production_summary['runtime_required_count']} gates require fresh release-candidate runtime proof."
            ),
            "remaining_proof_gap": (
                "Need supported production-format claims, real acceleration evidence, and release-ready compatibility policy."
            ),
        },
        {
            "requirement_id": "completion-boundary",
            "requirement": "Only mark the active goal complete when every explicit requirement is proven.",
            "status": "blocked-by-evidence",
            "authoritative_evidence": [
                "docs/GOAL_COMPLETION_AUDIT.md",
                "docs/RESEARCH_DECISION.md",
                "docs/GOAL_AUDIT.md",
            ],
            "finding": (
                f"Completion boundary is {decision_summary['completion_boundary']} with "
                f"{decision_summary['unresolved_count']} unresolved evidence gates."
            ),
            "remaining_proof_gap": (
                "Keep the active goal open until natural-corpus or supported production claims are proven."
            ),
        },
    ]


def build_report() -> dict[str, Any]:
    results = load_json(SOURCE_PATHS["results_sha256"])
    viability = load_json(SOURCE_PATHS["viability_sha256"])
    scorecard = load_json(SOURCE_PATHS["research_scorecard_sha256"])
    goal = load_json(SOURCE_PATHS["goal_audit_sha256"])
    decision = load_json(SOURCE_PATHS["research_decision_sha256"])
    frontier = load_json(SOURCE_PATHS["research_frontier_sha256"])
    natural_proof = load_json(SOURCE_PATHS["natural_corpus_proof_matrix_sha256"])
    production_proof = load_json(SOURCE_PATHS["production_proof_matrix_sha256"])
    team = load_json(SOURCE_PATHS["research_team_protocol_sha256"])
    ui_smoke = load_json(SOURCE_PATHS["ui_workflow_smoke_sha256"])

    requirements = build_requirements(
        goal,
        decision,
        frontier,
        team,
        viability,
        scorecard,
        results,
        ui_smoke,
        natural_proof,
        production_proof,
    )
    counts = Counter(item["status"] for item in requirements)
    decision_summary = summary(decision)
    team_summary = summary(team)
    blocking_ids = [
        item["requirement_id"]
        for item in requirements
        if item["status"] == "blocked-by-evidence"
    ]
    production_proven = bool(decision_summary["production_proven"])
    objective_complete = not blocking_ids and production_proven

    return {
        "generated_by": GENERATED_BY,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "scope": {
            "kind": "active goal completion audit",
            "performs_seed_search": False,
            "makes_compression_claim": False,
            "marks_goal_complete": objective_complete,
            "overrides_research_decision": False,
        },
        "objective": OBJECTIVE,
        "source_hashes": source_hashes(),
        "summary": {
            "objective_status": (
                "goal_complete" if objective_complete else "active_goal_not_complete"
            ),
            "completion_recommendation": (
                "mark_goal_complete" if objective_complete else "keep_goal_active"
            ),
            "verdict": viability["verdict"],
            "overall_status": goal["overall_status"],
            "production_proven": production_proven,
            "unresolved_evidence_gates": int(decision_summary["unresolved_count"]),
            "ready_ungated_experiments": int(decision_summary["ready_count"]),
            "requirements_total": len(requirements),
            "requirements_complete": int(counts["complete"]),
            "requirements_proved": int(counts["proved"]),
            "requirements_qualified": int(counts["qualified"]),
            "requirements_blocked_by_evidence": int(counts["blocked-by-evidence"]),
            "blocking_requirement_ids": blocking_ids,
            "team_brief_count": int(team_summary["brief_count"]),
            "team_ready_dispatch_count": int(team_summary["ready_dispatch_count"]),
            "ui_smoke_promotion_met": bool(summary(ui_smoke)["promotion_met"]),
            "natural_corpus_proof_status": summary(natural_proof)["natural_corpus_status"],
            "natural_corpus_proof_blocked_gates": int(
                summary(natural_proof)["blocked_by_evidence_count"]
            ),
            "natural_corpus_heldout_selected_span_rows": int(
                summary(natural_proof)["heldout_selected_span_rows"]
            ),
            "production_proof_status": summary(production_proof)["production_status"],
            "production_proof_blocked_gates": int(
                summary(production_proof)["blocked_by_evidence_count"]
            ),
            "production_proof_runtime_required_gates": int(
                summary(production_proof)["runtime_required_count"]
            ),
            "completion_boundary": decision_summary["completion_boundary"],
        },
        "requirements": requirements,
        "completion_rule": (
            "Do not mark the active goal complete until every requirement is complete "
            "or proved, production_proven is true, and unresolved_evidence_gates is zero."
        ),
    }


def write_report(payload: dict[str, Any]) -> None:
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    data = payload["summary"]
    lines = [
        "# Telomere Active Goal Completion Audit",
        "",
        f"Generated by `{GENERATED_BY}` from checked-in objective evidence ledgers.",
        "This is a No Seed Search completion audit: it performs no seed search, makes no compression claim, does not override the research decision, and does not mark the active goal complete unless the evidence proves completion.",
        "",
        "## Verdict",
        "",
        f"- Objective status: `{data['objective_status']}`",
        f"- Completion recommendation: `{data['completion_recommendation']}`",
        f"- Verdict: `{data['verdict']}`",
        f"- Overall status: `{data['overall_status']}`",
        f"- Production proven: `{data['production_proven']}`",
        f"- Unresolved evidence gates: `{data['unresolved_evidence_gates']}`",
        f"- Ready ungated experiments: `{data['ready_ungated_experiments']}`",
        f"- Requirements: `{data['requirements_complete']}` complete, `{data['requirements_proved']}` proved, `{data['requirements_qualified']}` qualified, `{data['requirements_blocked_by_evidence']}` blocked-by-evidence",
        f"- Team briefs: `{data['team_brief_count']}`",
        f"- Team ready dispatches: `{data['team_ready_dispatch_count']}`",
        f"- UI smoke promotion met: `{data['ui_smoke_promotion_met']}`",
        f"- Natural corpus proof status: `{data['natural_corpus_proof_status']}`",
        f"- Natural corpus proof blocked gates: `{data['natural_corpus_proof_blocked_gates']}`",
        f"- Natural corpus held-out selected-span rows: `{data['natural_corpus_heldout_selected_span_rows']}`",
        f"- Production proof status: `{data['production_proof_status']}`",
        f"- Production proof blocked gates: `{data['production_proof_blocked_gates']}`",
        f"- Production proof runtime-required gates: `{data['production_proof_runtime_required_gates']}`",
        f"- Completion boundary: `{data['completion_boundary']}`",
        "",
        "The active goal is not complete: Telomere is research-viable, not production-proven, and natural-corpus or supported production claims remain blocked by evidence.",
        "",
        "## Completion Rule",
        "",
        payload["completion_rule"],
        "",
        "## Objective Requirements",
        "",
        "| id | status | requirement | authoritative evidence | remaining proof gap |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in payload["requirements"]:
        evidence = ", ".join(f"`{path}`" for path in item["authoritative_evidence"])
        lines.append(
            f"| `{cell(item['requirement_id'])}` | `{cell(item['status'])}` | {cell(item['requirement'])} | {evidence} | {cell(item['remaining_proof_gap'])} |"
        )

    lines.extend(
        [
            "",
            "## Blocking Requirements",
            "",
        ]
    )
    for item in payload["requirements"]:
        if item["status"] != "blocked-by-evidence":
            continue
        lines.append(
            f"- `{item['requirement_id']}`: {item['finding']} Remaining proof gap: {item['remaining_proof_gap']}"
        )

    lines.extend(
        [
            "",
            "## Source Artifacts",
            "",
            "The JSON `source_hashes` map pins this completion audit to the exact upstream evidence files below.",
        ]
    )
    for name, digest in payload["source_hashes"].items():
        lines.append(f"- `{name}`: `{digest}`")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not REPORT_JSON.exists() or not REPORT_MD.exists():
        raise SystemExit("generated goal completion audit files are missing")
    payload = load_json(REPORT_JSON)
    if payload.get("generated_by") != GENERATED_BY:
        raise SystemExit("goal_completion_audit.json has wrong generated_by marker")
    if payload.get("source_hashes") != source_hashes():
        raise SystemExit("goal completion audit source hashes are stale")
    expected = stable_projection(build_report())
    current = stable_projection(payload)
    if current != expected:
        raise SystemExit("goal_completion_audit.json is stale; regenerate it")

    data = payload["summary"]
    if not data["production_proven"]:
        if data["objective_status"] == "goal_complete":
            raise SystemExit("completion audit marked complete without production proof")
        if data["completion_recommendation"] != "keep_goal_active":
            raise SystemExit("completion audit should keep the active goal open")
    if data["requirements_blocked_by_evidence"] == 0 and not data["production_proven"]:
        raise SystemExit("completion audit lost blocked-by-evidence requirements")
    for item in payload["requirements"]:
        for field in (
            "requirement_id",
            "requirement",
            "status",
            "authoritative_evidence",
            "finding",
            "remaining_proof_gap",
        ):
            if not item.get(field):
                raise SystemExit(
                    f"goal completion requirement {item.get('requirement_id')} missing {field}"
                )

    text = REPORT_MD.read_text(encoding="utf-8")
    for phrase in (
        "Telomere Active Goal Completion Audit",
        "No Seed Search",
        "completion audit",
        "active goal is not complete",
        "keep_goal_active",
        "research-viable, not production-proven",
        "natural-corpus",
        "Natural corpus proof status",
        "production_proven",
        "Production proof status",
        "dispatching-parallel-agents",
        "authoritative evidence",
        "remaining proof gap",
        "Blocking Requirements",
        "source_hashes",
    ):
        if phrase not in text:
            raise SystemExit(f"GOAL_COMPLETION_AUDIT.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate generated goal completion audit files",
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
