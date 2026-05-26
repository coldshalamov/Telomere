#!/usr/bin/env python3
"""Generate the Telomere natural-corpus viability proof matrix.

This is a no-compute evidence ledger. It does not run seed search or claim
compression; it records the exact generated evidence needed before Telomere can
claim generalized non-planted or natural-corpus viability.
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
REPORT_JSON = DOCS / "natural_corpus_proof_matrix.json"
REPORT_MD = DOCS / "NATURAL_CORPUS_PROOF_MATRIX.md"
GENERATED_BY = "scripts/generate_natural_corpus_proof_matrix.py"

SOURCE_PATHS = {
    "viability_sha256": DOCS / "viability.json",
    "research_scorecard_sha256": DOCS / "research_scorecard.json",
    "research_decision_sha256": DOCS / "research_decision.json",
    "research_frontier_sha256": DOCS / "research_frontier.json",
    "search_frontier_gate_sha256": DOCS / "search_frontier_gate.json",
    "long_span_bundle_gate_sha256": DOCS / "long_span_bundle_gate.json",
    "heldout_corpus_expansion_sha256": DOCS / "heldout_corpus_expansion.json",
    "match_discovery_sha256": DOCS / "match_discovery.json",
    "transform_validation_sha256": DOCS / "transform_validation.json",
    "corpus_generalization_probe_sha256": DOCS / "corpus_generalization_probe.json",
    "nearmiss_forecast_sha256": DOCS / "nearmiss_forecast.json",
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


def status_count(scorecard: dict[str, Any], status: str) -> int:
    counts = scorecard.get("scorecard_status_counts", {})
    return int(counts.get(status, 0)) if isinstance(counts, dict) else 0


def gate(
    gate_id: str,
    status: str,
    evidence: list[str],
    finding: str,
    promotion_requirement: str,
    owner_group: str,
) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "status": status,
        "owner_group": owner_group,
        "authoritative_evidence": evidence,
        "finding": finding,
        "promotion_requirement": promotion_requirement,
    }


def transform_totals(transform_validation: dict[str, Any]) -> dict[str, int]:
    rows = summary(transform_validation).get("corpus_summaries", [])
    heldout = [
        row
        for row in rows
        if row.get("role") == "held-out"
        and row.get("control_kind") == "ordinary-structured"
    ]
    return {
        "heldout_corpus_count": len(heldout),
        "heldout_prefix4_win_corpora": int(
            summary(transform_validation).get("heldout_prefix4_win_corpora", 0)
        ),
        "heldout_prefix5_win_corpora": sum(
            1 for row in heldout if int(row.get("best_prefix_ge_5", 0)) > 0
        ),
        "heldout_exact_hits": int(
            summary(transform_validation).get("heldout_exact_hits", 0)
        ),
    }


def build_gates(
    viability: dict[str, Any],
    scorecard: dict[str, Any],
    decision: dict[str, Any],
    frontier: dict[str, Any],
    search_gate: dict[str, Any],
    long_span_gate: dict[str, Any],
    heldout: dict[str, Any],
    match: dict[str, Any],
    transform_validation: dict[str, Any],
    generalization: dict[str, Any],
    nearmiss: dict[str, Any],
) -> list[dict[str, Any]]:
    decision_summary = summary(decision)
    frontier_summary = summary(frontier)
    heldout_summary = summary(heldout)
    match_summary = summary(match)
    search_summary = summary(search_gate)
    long_span_summary = summary(long_span_gate)
    transform = transform_totals(transform_validation)
    generalization_summary = summary(generalization)
    nearmiss_summary = summary(nearmiss)

    return [
        gate(
            "mechanism-positive-controls",
            "qualified",
            ["docs/VIABILITY.md", "docs/RESULTS.md"],
            f"Overall verdict is {viability['verdict']}; planted and schema-shaped controls prove the mechanism can work under controlled conditions.",
            "Do not count planted or schema-shaped controls as generalized natural-corpus proof.",
            "meta-research",
        ),
        gate(
            "heldout-corpus-coverage",
            "qualified",
            ["docs/HELDOUT_CORPUS_EXPANSION.md", "docs/heldout_corpus_expansion.json"],
            f"{heldout_summary['corpus_count']} frozen replication corpora exist across {heldout_summary['independence_group_count']} independence groups, with {heldout_summary['ordinary_corpus_count']} ordinary and {heldout_summary['control_corpus_count']} control corpora.",
            "Integrate replication corpora into expensive matrices only with an explicit regeneration budget or after prefix>=5/exact/selected-span evidence appears.",
            "corpus-transform",
        ),
        gate(
            "raw-heldout-seed-span-evidence",
            "blocked-by-evidence",
            ["docs/HELDOUT_CORPUS_EXPANSION.md", "docs/SEARCH_FRONTIER_GATE.md"],
            f"Raw held-out expansion has {heldout_summary['rows_with_prefix_ge_5']} prefix>=5 rows, {heldout_summary['rows_with_exact_hits']} exact-hit rows, and {heldout_summary['rows_with_selected_spans']} selected-span rows.",
            "Promote only after unrelated ordinary held-out corpora produce repeatable prefix>=5, exact hits, or selected spans while controls stay null.",
            "corpus-transform",
        ),
        gate(
            "transformed-heldout-seed-span-evidence",
            "blocked-by-evidence",
            ["docs/TRANSFORM_VALIDATION.md", "docs/transform_validation.json"],
            f"Transform validation has {transform['heldout_prefix4_win_corpora']} held-out prefix>=4 win corpora but {transform['heldout_prefix5_win_corpora']} held-out prefix>=5 win corpora and {transform['heldout_exact_hits']} exact hits.",
            "Treat prefix-4 movement as steering telemetry until a transform produces held-out prefix>=5 or exact seed-span wins after metadata accounting.",
            "corpus-transform",
        ),
        gate(
            "match-discovery-selected-spans",
            "blocked-by-evidence",
            ["docs/MATCH_DISCOVERY.md", "docs/match_discovery.json"],
            f"Match discovery scanned {match_summary['target_span_count']} target spans across {match_summary['corpus_count']} corpora and found {match_summary['rows_with_exact_hits']} exact-hit rows and {match_summary['rows_with_selected_spans']} selected-span rows.",
            "Change match-discovery strategy before returning to sidecar packing or natural-corpus claims.",
            "corpus-transform",
        ),
        gate(
            "near-miss-forecast-scale",
            "blocked-by-evidence",
            ["docs/NEARMISS_FORECAST.md", "docs/nearmiss_forecast.json"],
            f"Best non-planted case is {nearmiss_summary['best_non_planted_case']} at {nearmiss_summary['best_non_planted_gib_for_one_expected_hit']} GiB for one expected exact hit with {nearmiss_summary['best_non_planted_exact_hits']} observed exact hits.",
            "Require a materially better forecast, preferably below 1 GiB per expected exact hit, before broad raw depth search.",
            "compute-economics",
        ),
        gate(
            "control-null-and-overfit-checks",
            "qualified",
            ["docs/CORPUS_GENERALIZATION_PROBE.md", "docs/corpus_generalization_probe.json"],
            f"Generalization controls scanned {generalization_summary['target_span_count']} spans and found {generalization_summary['rows_with_prefix_ge_5']} prefix>=5 rows, {generalization_summary['total_exact_hits']} exact hits, and {generalization_summary['total_selected_spans']} selected spans.",
            "Keep controls null while adding ordinary wins; null controls alone do not prove compression.",
            "corpus-transform",
        ),
        gate(
            "long-span-bundle-prerequisites",
            "blocked-by-evidence",
            ["docs/LONG_SPAN_BUNDLE_GATE.md", "docs/long_span_bundle_gate.json"],
            f"Long-span bundle gate has {long_span_summary['gate_met_count']} of {long_span_summary['gate_count']} gates met and recommendation {long_span_summary['recommendation']}.",
            "Do not run broad long-span sweeps until search frontier, selected-span, raw-suffix, and control gates pass.",
            "compute-economics",
        ),
        gate(
            "broad-depth-search-prerequisites",
            "blocked-by-evidence",
            ["docs/SEARCH_FRONTIER_GATE.md", "docs/search_frontier_gate.json"],
            f"Search frontier gate has {search_summary['gate_met_count']} of {search_summary['gate_count']} gates met; broad_depth_search_allowed={search_summary['broad_depth_search_allowed']}; best forecast {search_summary['best_non_planted_gib_for_one_expected_hit']} GiB.",
            "Do not run broad depth-3, full depth-4, or raw depth escalation until the generated search-frontier gate opens.",
            "compute-economics",
        ),
        gate(
            "decision-boundary",
            "blocked-by-evidence",
            ["docs/RESEARCH_DECISION.md", "docs/RESEARCH_FRONTIER.md"],
            f"Decision is {decision_summary['decision']}; frontier status is {frontier_summary['frontier_status']} with {frontier_summary['ready_count']} ready ungated experiments.",
            "A new generated artifact must reopen a lane before compute-heavy natural-corpus work resumes.",
            "meta-research",
        ),
        gate(
            "scorecard-open-natural-lanes",
            "blocked-by-evidence",
            ["docs/RESEARCH_SCORECARD.md", "docs/research_scorecard.json"],
            f"Scorecard has {status_count(scorecard, 'open')} open areas and {status_count(scorecard, 'blocked-by-evidence')} blocked-by-evidence areas.",
            "Resolve natural-corpus and transform blockers with generated evidence, not prose promotion.",
            "meta-research",
        ),
    ]


def build_report() -> dict[str, Any]:
    viability = load_json(DOCS / "viability.json")
    scorecard = load_json(DOCS / "research_scorecard.json")
    decision = load_json(DOCS / "research_decision.json")
    frontier = load_json(DOCS / "research_frontier.json")
    search_gate = load_json(DOCS / "search_frontier_gate.json")
    long_span_gate = load_json(DOCS / "long_span_bundle_gate.json")
    heldout = load_json(DOCS / "heldout_corpus_expansion.json")
    match = load_json(DOCS / "match_discovery.json")
    transform_validation = load_json(DOCS / "transform_validation.json")
    generalization = load_json(DOCS / "corpus_generalization_probe.json")
    nearmiss = load_json(DOCS / "nearmiss_forecast.json")

    gates = build_gates(
        viability,
        scorecard,
        decision,
        frontier,
        search_gate,
        long_span_gate,
        heldout,
        match,
        transform_validation,
        generalization,
        nearmiss,
    )
    counts = Counter(item["status"] for item in gates)
    blocked = [item for item in gates if item["status"] == "blocked-by-evidence"]
    heldout_summary = summary(heldout)
    match_summary = summary(match)
    search_summary = summary(search_gate)
    long_span_summary = summary(long_span_gate)
    transform = transform_totals(transform_validation)
    nearmiss_summary = summary(nearmiss)
    natural_proven = (
        not blocked
        and heldout_summary["rows_with_selected_spans"] > 0
        and match_summary["rows_with_selected_spans"] > 0
    )

    return {
        "generated_by": GENERATED_BY,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "scope": {
            "kind": "natural corpus proof matrix",
            "performs_seed_search": False,
            "makes_compression_claim": False,
            "marks_natural_corpus_proven": natural_proven,
        },
        "source_hashes": source_hashes(),
        "summary": {
            "natural_corpus_status": (
                "natural_corpus_proven" if natural_proven else "not_natural_corpus_proven"
            ),
            "natural_corpus_proven": natural_proven,
            "natural_corpus_recommendation": (
                "promote_natural_corpus_viability"
                if natural_proven
                else "do_not_claim_natural_corpus_viability"
            ),
            "gate_count": len(gates),
            "qualified_count": int(counts["qualified"]),
            "blocked_by_evidence_count": int(counts["blocked-by-evidence"]),
            "blocked_gate_ids": [item["gate_id"] for item in blocked],
            "heldout_corpus_count": int(heldout_summary["corpus_count"]),
            "heldout_ordinary_corpus_count": int(heldout_summary["ordinary_corpus_count"]),
            "heldout_control_corpus_count": int(heldout_summary["control_corpus_count"]),
            "heldout_prefix5_rows": int(heldout_summary["rows_with_prefix_ge_5"]),
            "heldout_exact_hit_rows": int(heldout_summary["rows_with_exact_hits"]),
            "heldout_selected_span_rows": int(heldout_summary["rows_with_selected_spans"]),
            "match_discovery_target_spans": int(match_summary["target_span_count"]),
            "match_discovery_exact_hit_rows": int(match_summary["rows_with_exact_hits"]),
            "match_discovery_selected_span_rows": int(match_summary["rows_with_selected_spans"]),
            "transform_heldout_prefix4_win_corpora": transform[
                "heldout_prefix4_win_corpora"
            ],
            "transform_heldout_prefix5_win_corpora": transform[
                "heldout_prefix5_win_corpora"
            ],
            "transform_heldout_exact_hits": transform["heldout_exact_hits"],
            "best_non_planted_case": nearmiss_summary["best_non_planted_case"],
            "best_non_planted_gib_for_one_expected_hit": nearmiss_summary[
                "best_non_planted_gib_for_one_expected_hit"
            ],
            "search_frontier_gate_met_count": int(search_summary["gate_met_count"]),
            "search_frontier_gate_count": int(search_summary["gate_count"]),
            "long_span_gate_met_count": int(long_span_summary["gate_met_count"]),
            "long_span_gate_count": int(long_span_summary["gate_count"]),
        },
        "gates": gates,
        "promotion_rule": (
            "Do not claim natural-corpus viability until unrelated ordinary "
            "held-out corpora produce repeatable selected spans or negative delta, "
            "controls stay null, and the generated search-frontier/long-span gates open."
        ),
    }


def write_report(payload: dict[str, Any]) -> None:
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    data = payload["summary"]
    lines = [
        "# Telomere Natural Corpus Proof Matrix",
        "",
        f"Generated by `{GENERATED_BY}` from checked-in natural-corpus evidence.",
        "This is a No Seed Search natural-corpus viability audit: it performs no seed search, makes no compression claim, and does not mark natural-corpus viability proven.",
        "",
        "## Verdict",
        "",
        f"- Natural corpus status: `{data['natural_corpus_status']}`",
        f"- Natural corpus proven: `{data['natural_corpus_proven']}`",
        f"- Recommendation: `{data['natural_corpus_recommendation']}`",
        f"- Gates: `{data['gate_count']}` total, `{data['qualified_count']}` qualified, `{data['blocked_by_evidence_count']}` blocked-by-evidence",
        f"- Held-out corpora: `{data['heldout_corpus_count']}` total, `{data['heldout_ordinary_corpus_count']}` ordinary, `{data['heldout_control_corpus_count']}` controls",
        f"- Held-out prefix>=5 rows: `{data['heldout_prefix5_rows']}`",
        f"- Held-out exact-hit rows: `{data['heldout_exact_hit_rows']}`",
        f"- Held-out selected-span rows: `{data['heldout_selected_span_rows']}`",
        f"- Match-discovery target spans: `{data['match_discovery_target_spans']}`",
        f"- Match-discovery exact-hit rows: `{data['match_discovery_exact_hit_rows']}`",
        f"- Match-discovery selected-span rows: `{data['match_discovery_selected_span_rows']}`",
        f"- Transform held-out prefix>=4 win corpora: `{data['transform_heldout_prefix4_win_corpora']}`",
        f"- Transform held-out prefix>=5 win corpora: `{data['transform_heldout_prefix5_win_corpora']}`",
        f"- Transform held-out exact hits: `{data['transform_heldout_exact_hits']}`",
        f"- Best non-planted case: `{data['best_non_planted_case']}`",
        f"- Best non-planted forecast: `{data['best_non_planted_gib_for_one_expected_hit']}` GiB for one expected exact hit",
        f"- Search frontier gates met: `{data['search_frontier_gate_met_count']}` / `{data['search_frontier_gate_count']}`",
        f"- Long-span gates met: `{data['long_span_gate_met_count']}` / `{data['long_span_gate_count']}`",
        "",
        "Telomere does not yet have natural-corpus viability proof. The strongest current non-planted signal is prefix-4 movement, which is useful steering telemetry but not a selected exact span, negative delta, or format claim.",
        "",
        "## Promotion Rule",
        "",
        payload["promotion_rule"],
        "",
        "## Gates",
        "",
        "| gate | status | group | finding | promotion requirement | evidence |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in payload["gates"]:
        evidence = ", ".join(f"`{path}`" for path in item["authoritative_evidence"])
        lines.append(
            f"| `{cell(item['gate_id'])}` | `{cell(item['status'])}` | `{cell(item['owner_group'])}` | {cell(item['finding'])} | {cell(item['promotion_requirement'])} | {evidence} |"
        )
    lines.extend(["", "## Source Artifacts", ""])
    for name, digest in payload["source_hashes"].items():
        lines.append(f"- `{name}`: `{digest}`")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not REPORT_JSON.exists() or not REPORT_MD.exists():
        raise SystemExit("generated natural corpus proof matrix files are missing")
    payload = load_json(REPORT_JSON)
    if payload.get("generated_by") != GENERATED_BY:
        raise SystemExit("natural_corpus_proof_matrix.json has wrong generated_by marker")
    if payload.get("source_hashes") != source_hashes():
        raise SystemExit("natural corpus proof matrix source hashes are stale")
    expected = stable_projection(build_report())
    current = stable_projection(payload)
    if current != expected:
        raise SystemExit("natural_corpus_proof_matrix.json is stale; regenerate it")

    data = payload["summary"]
    if data["natural_corpus_proven"] and data["blocked_by_evidence_count"]:
        raise SystemExit("natural corpus matrix marked proven with blocked gates")
    if data["natural_corpus_proven"] and data["heldout_selected_span_rows"] == 0:
        raise SystemExit("natural corpus matrix marked proven without selected spans")
    if data["natural_corpus_recommendation"] != "do_not_claim_natural_corpus_viability":
        raise SystemExit("natural corpus matrix should not promote current evidence")
    if data["heldout_prefix5_rows"] or data["heldout_exact_hit_rows"] or data["heldout_selected_span_rows"]:
        raise SystemExit("natural corpus matrix expected current held-out frontier to be null")

    text_body = REPORT_MD.read_text(encoding="utf-8")
    for phrase in (
        "Telomere Natural Corpus Proof Matrix",
        "No Seed Search",
        "not yet have natural-corpus viability proof",
        "prefix-4 movement",
        "prefix>=5",
        "selected-span",
        "negative delta",
        "controls stay null",
        "blocked-by-evidence",
        "Source Artifacts",
    ):
        if phrase not in text_body:
            raise SystemExit(f"NATURAL_CORPUS_PROOF_MATRIX.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate generated natural corpus proof matrix files",
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
