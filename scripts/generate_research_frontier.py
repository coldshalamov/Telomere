#!/usr/bin/env python3
"""Generate the current Telomere research frontier map.

This artifact is a no-compute operating map. It consolidates unresolved gates,
queue lanes, and subagent work packages so the next expensive experiment only
starts after a generated reopen trigger exists.
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
REPORT_JSON = DOCS / "research_frontier.json"
REPORT_MD = DOCS / "RESEARCH_FRONTIER.md"
GENERATED_BY = "scripts/generate_research_frontier.py"

SOURCE_PATHS = {
    "research_decision_sha256": DOCS / "research_decision.json",
    "experiment_queue_sha256": DOCS / "experiment_queue.json",
    "goal_audit_sha256": DOCS / "goal_audit.json",
    "research_scorecard_sha256": DOCS / "research_scorecard.json",
    "long_span_bundle_gate_sha256": DOCS / "long_span_bundle_gate.json",
    "search_frontier_gate_sha256": DOCS / "search_frontier_gate.json",
    "heldout_corpus_expansion_sha256": DOCS / "heldout_corpus_expansion.json",
    "acceleration_report_sha256": DOCS / "acceleration_report.json",
    "recursive_structured_fixtures_sha256": DOCS / "recursive_structured_fixtures.json",
    "scale_performance_report_sha256": DOCS / "scale_performance_report.json",
    "viability_sha256": DOCS / "viability.json",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes() -> dict[str, str]:
    return {name: sha256(path) for name, path in SOURCE_PATHS.items()}


def stable_projection(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if key != "generated_at"
    }


def cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def queue_items_by_group(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        grouped[item["parallel_group"]].append(item)

    packages = []
    for group, group_items in sorted(grouped.items()):
        statuses = Counter(item["status"] for item in group_items)
        lanes = ", ".join(item["lane"] for item in group_items)
        allowed_now = (
            "run ready experiments"
            if statuses.get("ready", 0)
            else "read-only audits and generated-artifact maintenance only"
        )
        guardrail = (
            "Do not launch broad compute, production GPU, or format promotion "
            "from this work package unless its generated promotion gate changes."
        )
        packages.append(
            {
                "parallel_group": group,
                "lanes": lanes,
                "status_counts": dict(statuses),
                "allowed_now": allowed_now,
                "guardrail": guardrail,
            }
        )
    return packages


def unresolved_clusters(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_section: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in entries:
        if entry["status"] in {"open", "blocked-by-evidence"}:
            by_section[entry["section"]].append(entry)

    clusters = []
    for section, section_entries in sorted(by_section.items()):
        statuses = Counter(entry["status"] for entry in section_entries)
        clusters.append(
            {
                "section": section,
                "count": len(section_entries),
                "status_counts": dict(statuses),
                "first_remaining_gate": section_entries[0]["remaining_gate"],
            }
        )
    return sorted(clusters, key=lambda row: (-row["count"], row["section"]))


def canonical_artifact(item: dict[str, Any]) -> str:
    suggested = item["suggested_artifact"]
    if "`" in suggested:
        parts = suggested.split("`")
        if len(parts) >= 2:
            return parts[1]
    return suggested


def frontiers(
    queue: dict[str, Any],
    goal: dict[str, Any],
    long_span: dict[str, Any],
    search_frontier: dict[str, Any],
    heldout: dict[str, Any],
    acceleration: dict[str, Any],
    recursive: dict[str, Any],
) -> list[dict[str, Any]]:
    long_span_summary = long_span["summary"]
    search_summary = search_frontier["summary"]
    heldout_summary = heldout["summary"]
    recursive_summary = recursive["summary"]
    transform_blockers = [
        entry["section"]
        for entry in goal["entries"]
        if entry["status"] == "blocked-by-evidence"
        and (
            "transform" in entry["section"]
            or "channel" in entry["section"]
            or "dictionary" in entry["section"]
        )
    ]
    blocked_gate_names = [
        check["gate"] for check in search_frontier["gate_checks"] if not check["met"]
    ]
    unmet_long_span = [
        check["gate"] for check in long_span["gate_checks"] if not check["met"]
    ]

    details = {
        "long-span-bundle-gate": {
            "canonical_artifact": "docs/LONG_SPAN_BUNDLE_GATE.md",
            "current_observation": (
                f"{long_span_summary['gate_met_count']} of "
                f"{long_span_summary['gate_count']} gates met; "
                f"recommendation {long_span_summary['recommendation']}."
            ),
            "blocking_gates": unmet_long_span,
            "unlocks_if_met": "a narrow long-span bundle sweep artifact, not broad production claims",
            "still_forbidden": [
                "broad long-span sweeps",
                "format promotion",
                "production compression claims",
            ],
            "control_requirements": [
                "search frontier open",
                "raw-suffix break-even met",
                "selected spans present",
                "controls remain null",
            ],
            "claim_boundary": "long-span bundle evidence only",
        },
        "heldout-corpora": {
            "canonical_artifact": "docs/HELDOUT_CORPUS_EXPANSION.md",
            "current_observation": (
                f"{heldout_summary['corpus_count']} frozen corpora; "
                f"prefix>=5 rows {heldout_summary['rows_with_prefix_ge_5']}; "
                f"exact hits {heldout_summary['total_exact_hits']}; "
                f"selected spans {heldout_summary['total_selected_spans']}."
            ),
            "blocking_gates": [
                "prefix>=5 rows remain zero",
                "exact-hit rows remain zero",
                "selected-span rows remain zero",
            ],
            "unlocks_if_met": "canonical corpus-matrix integration with explicit regeneration budget",
            "still_forbidden": [
                "expensive matrix regeneration by default",
                "natural-corpus compression claims",
            ],
            "control_requirements": [
                "ordinary held-out movement",
                "controls stay null",
                "matrix-regeneration budget accepted",
            ],
            "claim_boundary": "corpus coverage evidence only",
        },
        "search-depth": {
            "canonical_artifact": "docs/SEARCH_FRONTIER_GATE.md",
            "current_observation": (
                f"status {search_summary['recommended_status']}; "
                f"selected spans {search_summary['selected_span_total']}; "
                f"forecast {search_summary['best_non_planted_gib_for_one_expected_hit']} GiB."
            ),
            "blocking_gates": blocked_gate_names,
            "unlocks_if_met": "broader depth-3 or opt-in depth-4 proposal",
            "still_forbidden": [
                "broad raw depth search",
                "full depth-4 execution",
                "compute escalation without exact-hit evidence",
            ],
            "control_requirements": [
                "prefix>=6 movement or exact hits",
                "selected spans greater than zero",
                "forecast below configured threshold",
            ],
            "claim_boundary": "search-frontier evidence only",
        },
        "format-transforms": {
            "canonical_artifact": "docs/adr/0001-transform-preconditioners.md",
            "current_observation": (
                f"{len(transform_blockers)} transform/channel/dictionary blockers "
                "remain blocked-by-evidence."
            ),
            "blocking_gates": transform_blockers,
            "unlocks_if_met": "draft transform metadata proposal outside stable v1",
            "still_forbidden": [
                ".tlmr transform metadata",
                "format support claims",
                "counting transform-only shortening as Lotus compression",
            ],
            "control_requirements": [
                "repeatable exact seed-span wins",
                "metadata charged",
                "held-out/control validation",
            ],
            "claim_boundary": "format-research evidence only",
        },
        "gpu-acceleration": {
            "canonical_artifact": "docs/ACCELERATION.md",
            "current_observation": (
                f"acceleration status {acceleration['detected']['status']}; "
                f"real kernel detected {acceleration['detected']['real_kernel_detected']}."
            ),
            "blocking_gates": [
                "no CPU workload with repeatable exact hits",
                "no real GPU kernel promotion",
                "no production benchmark win",
            ],
            "unlocks_if_met": "real GPU parity and benchmark work",
            "still_forbidden": [
                "production GPU acceleration",
                "trusting GPU output without CPU parity",
            ],
            "control_requirements": [
                "CPU parity tests",
                "benchmark superiority",
                "same selected output as CPU",
            ],
            "claim_boundary": "acceleration evidence only",
        },
    }

    frontier_rows = []
    for item in queue["items"]:
        if item["status"] not in {"blocked-by-evidence", "gated"}:
            continue
        lane = item["lane"]
        lane_details = details.get(
            lane,
            {
                "current_observation": item["why_now"],
                "blocking_gates": [item["stop_rule"]],
                "unlocks_if_met": item["promotion_gate"],
                "still_forbidden": [item["action"]],
                "control_requirements": [item["promotion_gate"]],
                "claim_boundary": "frontier evidence only",
            },
        )
        frontier_rows.append(
            {
                "frontier_id": lane,
                "status": item["status"],
                "canonical_artifact": lane_details.get(
                    "canonical_artifact", canonical_artifact(item)
                ),
                "current_observation": lane_details["current_observation"],
                "blocking_gates": lane_details["blocking_gates"],
                "promotion_trigger": item["promotion_gate"],
                "unlocks_if_met": lane_details["unlocks_if_met"],
                "still_forbidden": lane_details["still_forbidden"],
                "stop_rule": item["stop_rule"],
                "control_requirements": lane_details["control_requirements"],
                "claim_boundary": lane_details["claim_boundary"],
            }
        )
    return frontier_rows


def next_evidence_triggers() -> list[dict[str, str]]:
    return [
        {
            "trigger": "prefix>=6",
            "meaning": "held-out generated-prefix movement strong enough to revisit raw-suffix economics",
        },
        {
            "trigger": "exact_hits>0",
            "meaning": "a non-planted target span exactly equals a generated seed prefix",
        },
        {
            "trigger": "selected_spans>0",
            "meaning": "the compressor selected profitable seed-span records after metadata",
        },
        {
            "trigger": "forecast_gib<1",
            "meaning": "expected exact-hit cost is low enough to revisit broad depth search",
        },
        {
            "trigger": "ordinary_negative_groups_with_null_controls",
            "meaning": "negative delta appears in unrelated ordinary groups while controls stay null",
        },
    ]


def build_report() -> dict[str, Any]:
    decision = load_json(SOURCE_PATHS["research_decision_sha256"])
    queue = load_json(SOURCE_PATHS["experiment_queue_sha256"])
    goal = load_json(SOURCE_PATHS["goal_audit_sha256"])
    scorecard = load_json(SOURCE_PATHS["research_scorecard_sha256"])
    long_span = load_json(SOURCE_PATHS["long_span_bundle_gate_sha256"])
    search_frontier = load_json(SOURCE_PATHS["search_frontier_gate_sha256"])
    heldout = load_json(SOURCE_PATHS["heldout_corpus_expansion_sha256"])
    acceleration = load_json(SOURCE_PATHS["acceleration_report_sha256"])
    recursive = load_json(SOURCE_PATHS["recursive_structured_fixtures_sha256"])
    viability = load_json(SOURCE_PATHS["viability_sha256"])

    queue_summary = queue["summary"]
    decision_summary = decision["summary"]
    production_proven = (
        "production-proven" in str(scorecard.get("verdict", ""))
        and "not production-proven" not in str(scorecard.get("verdict", ""))
    )
    unresolved_requirements = [
        {
            "section": entry["section"],
            "requirement": entry["requirement"],
            "status": entry["status"],
            "remaining_gate": entry["remaining_gate"],
        }
        for entry in goal["entries"]
        if entry["status"] in {"open", "blocked-by-evidence"}
    ]
    ready_count = int(queue_summary["ready_count"])
    unresolved_count = int(goal.get("unresolved_count", len(unresolved_requirements)))
    no_compute_posture = ready_count == 0
    ungated_compute_allowed = ready_count > 0

    summary = {
        "frontier_status": (
            "no_ungated_compute_ready"
            if no_compute_posture
            else "ready_experiments_available"
        ),
        "decision": decision_summary["decision"],
        "completion_boundary": decision_summary["completion_boundary"],
        "verdict": viability["verdict"],
        "ready_count": ready_count,
        "gated_count": int(queue_summary["gated_count"]),
        "blocked_by_evidence_count": int(queue_summary["blocked_by_evidence_count"]),
        "qualified_count": int(queue_summary["qualified_count"]),
        "unresolved_count": unresolved_count,
        "long_span_gate_met_count": int(long_span["summary"]["gate_met_count"]),
        "long_span_gate_count": int(long_span["summary"]["gate_count"]),
        "search_frontier_status": search_frontier["summary"]["recommended_status"],
        "broad_depth_search_allowed": bool(
            search_frontier["summary"]["broad_depth_search_allowed"]
        ),
        "best_non_planted_gib_for_one_expected_hit": search_frontier["summary"][
            "best_non_planted_gib_for_one_expected_hit"
        ],
        "no_compute_posture": no_compute_posture,
        "ungated_compute_allowed": ungated_compute_allowed,
        "production_proven": production_proven,
        "allowed_maintenance_only": no_compute_posture and not production_proven,
    }

    return {
        "generated_by": GENERATED_BY,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "scope": {
            "kind": "downstream trigger ledger",
            "performs_seed_search": False,
            "makes_compression_claim": False,
            "adds_format_support": False,
            "overrides_search_frontier_gate": False,
        },
        "source_hashes": source_hashes(),
        "override_policy": (
            "A gated-compute override requires a new generated evidence artifact, "
            "an explicit compute budget, and preserved stop rules; this artifact "
            "does not override SEARCH_FRONTIER_GATE."
        ),
        "summary": summary,
        "frontier_lanes": queue["items"],
        "frontiers": frontiers(
            queue,
            goal,
            long_span,
            search_frontier,
            heldout,
            acceleration,
            recursive,
        ),
        "reopen_triggers": decision["reopen_triggers"],
        "blocked_actions": decision["blocked_actions"],
        "next_evidence_triggers": next_evidence_triggers(),
        "unresolved_clusters": unresolved_clusters(goal["entries"]),
        "unresolved_requirements": unresolved_requirements,
        "subagent_work_packages": queue_items_by_group(queue["items"]),
    }


def write_report(payload: dict[str, Any]) -> None:
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    data = payload["summary"]
    lines = [
        "# Telomere Research Frontier",
        "",
        f"Generated by `{GENERATED_BY}` from checked-in decision, queue, audit, and gate artifacts.",
        "This is a No Seed Search artifact: it performs no seed search, launches no compute, is not a compression claim, adds no `.tlmr` format support, and does not override SEARCH_FRONTIER_GATE.",
        "",
        "## Compute Posture",
        "",
        f"- Frontier status: `{data['frontier_status']}`",
        f"- Decision: `{data['decision']}`",
        f"- Completion boundary: `{data['completion_boundary']}`",
        f"- Verdict: `{data['verdict']}`",
        f"- Ready ungated experiments: `{data['ready_count']}`",
        f"- Gated lanes: `{data['gated_count']}`",
        f"- Blocked-by-evidence lanes: `{data['blocked_by_evidence_count']}`",
        f"- Qualified lanes: `{data['qualified_count']}`",
        f"- Unresolved evidence gates: `{data['unresolved_count']}`",
        f"- Long-span checks met: `{data['long_span_gate_met_count']}` / `{data['long_span_gate_count']}`",
        f"- Search frontier status: `{data['search_frontier_status']}`",
        f"- Broad depth search allowed: `{data['broad_depth_search_allowed']}`",
        f"- Best non-planted forecast: `{data['best_non_planted_gib_for_one_expected_hit']}` GiB per expected exact hit",
        f"- Ungated compute allowed: `{data['ungated_compute_allowed']}`",
        f"- Production proven: `{data['production_proven']}`",
        f"- Allowed maintenance only: `{data['allowed_maintenance_only']}`",
        "",
        "There is no ready ungated compute: No ready ungated experiments remain; do not spend on gated compute, production GPU, or format promotion until a generated reopen trigger changes.",
        "",
        "## Override Policy",
        "",
        payload["override_policy"],
        "",
        "## Reopen Trigger Matrix",
        "",
        "| lane | status | promotion gate | suggested artifact |",
        "| --- | --- | --- | --- |",
    ]
    for item in payload["reopen_triggers"]:
        lines.append(
            f"| `{cell(item['lane'])}` | `{cell(item['status'])}` | {cell(item['promotion_gate'])} | {cell(item['suggested_artifact'])} |"
        )

    lines.extend(
        [
            "",
            "## Frontier Trigger Board",
            "",
            "| frontier | status | canonical artifact | current observation | promotion trigger | unlocks if met | still forbidden |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for item in payload["frontiers"]:
        lines.append(
            f"| `{cell(item['frontier_id'])}` | `{cell(item['status'])}` | `{cell(item['canonical_artifact'])}` | {cell(item['current_observation'])} | {cell(item['promotion_trigger'])} | {cell(item['unlocks_if_met'])} | {cell('; '.join(item['still_forbidden']))} |"
        )

    lines.extend(
        [
            "",
            "## Next Evidence Triggers",
            "",
            "| trigger | meaning |",
            "| --- | --- |",
        ]
    )
    for item in payload["next_evidence_triggers"]:
        lines.append(f"| `{cell(item['trigger'])}` | {cell(item['meaning'])} |")

    lines.extend(
        [
            "",
            "## Frontier Lanes",
            "",
            "| rank | lane | status | group | stop rule |",
            "| ---: | --- | --- | --- | --- |",
        ]
    )
    for item in payload["frontier_lanes"]:
        lines.append(
            f"| {item['rank']} | `{cell(item['lane'])}` | `{cell(item['status'])}` | `{cell(item['parallel_group'])}` | {cell(item['stop_rule'])} |"
        )

    lines.extend(
        [
            "",
            "## Unresolved Requirement Clusters",
            "",
            "| section | unresolved count | status counts | first remaining gate |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for cluster in payload["unresolved_clusters"]:
        status_text = ", ".join(
            f"{status}={count}"
            for status, count in sorted(cluster["status_counts"].items())
        )
        lines.append(
            f"| `{cell(cluster['section'])}` | {cluster['count']} | {cell(status_text)} | {cell(cluster['first_remaining_gate'])} |"
        )

    lines.extend(
        [
            "",
            "## Unresolved Requirements",
            "",
            "| section | status | requirement | remaining gate |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in payload["unresolved_requirements"]:
        lines.append(
            f"| `{cell(item['section'])}` | `{cell(item['status'])}` | {cell(item['requirement'])} | {cell(item['remaining_gate'])} |"
        )

    lines.extend(
        [
            "",
            "## Subagent Work Packages",
            "",
            "| group | lanes | status counts | allowed now | guardrail |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for package in payload["subagent_work_packages"]:
        status_text = ", ".join(
            f"{status}={count}"
            for status, count in sorted(package["status_counts"].items())
        )
        lines.append(
            f"| `{cell(package['parallel_group'])}` | {cell(package['lanes'])} | {cell(status_text)} | {cell(package['allowed_now'])} | {cell(package['guardrail'])} |"
        )

    lines.extend(
        [
            "",
            "## Source Artifacts",
            "",
            "The JSON `source_hashes` map pins this trigger board to the exact upstream evidence files below.",
        ]
    )
    for name, digest in payload["source_hashes"].items():
        lines.append(f"- `{name}`: `{digest}`")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not REPORT_JSON.exists() or not REPORT_MD.exists():
        raise SystemExit("generated research frontier files are missing")
    payload = load_json(REPORT_JSON)
    if payload.get("generated_by") != GENERATED_BY:
        raise SystemExit("research_frontier.json has wrong generated_by marker")
    if payload.get("source_hashes") != source_hashes():
        raise SystemExit("research frontier source hashes are stale")
    expected = stable_projection(build_report())
    current = stable_projection(payload)
    if current != expected:
        raise SystemExit("research_frontier.json is stale; regenerate it")
    goal = load_json(SOURCE_PATHS["goal_audit_sha256"])
    if len(payload["unresolved_requirements"]) != goal["unresolved_count"]:
        raise SystemExit("research frontier unresolved count is stale")
    posture = payload["summary"]
    if posture["ready_count"] == 0 and posture["ungated_compute_allowed"]:
        raise SystemExit("research frontier allows ungated compute with zero ready lanes")
    if (
        not posture["broad_depth_search_allowed"]
        and any(
            "full depth-4 execution" not in frontier["still_forbidden"]
            for frontier in payload["frontiers"]
            if frontier["frontier_id"] == "search-depth"
        )
    ):
        raise SystemExit("research frontier lost the full depth-4 forbidden action")
    for frontier in payload["frontiers"]:
        for field in (
            "canonical_artifact",
            "promotion_trigger",
            "stop_rule",
            "still_forbidden",
        ):
            if not frontier.get(field):
                raise SystemExit(
                    f"research frontier {frontier.get('frontier_id')} missing {field}"
                )
    text = REPORT_MD.read_text(encoding="utf-8")
    for phrase in (
        "Telomere Research Frontier",
        "No Seed Search",
        "performs no seed search",
        "not a compression claim",
        "does not override SEARCH_FRONTIER_GATE",
        "no ready ungated compute",
        "No ready ungated experiments remain",
        "do not spend on gated compute",
        "Reopen Trigger Matrix",
        "Frontier Trigger Board",
        "Next Evidence Triggers",
        "Override Policy",
        "Unresolved Requirement Clusters",
        "Subagent Work Packages",
        "blocked-by-evidence",
        "source_hashes",
    ):
        if phrase not in text:
            raise SystemExit(f"RESEARCH_FRONTIER.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate generated research frontier files",
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
