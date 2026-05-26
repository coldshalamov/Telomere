#!/usr/bin/env python3
"""Generate the streaming/indexed economics decision gate."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
REPORT_JSON = DOCS / "streaming_economics_gate.json"
REPORT_MD = DOCS / "STREAMING_ECONOMICS_GATE.md"
GENERATED_BY = "scripts/generate_streaming_economics_gate.py"

SOURCE_PATHS = {
    "results_sha256": DOCS / "results.json",
    "results_doc_sha256": DOCS / "RESULTS.md",
    "scale_performance_report_sha256": DOCS / "scale_performance_report.json",
    "scale_performance_doc_sha256": DOCS / "SCALE_PERFORMANCE.md",
    "bounded_streaming_memory_gate_sha256": DOCS / "bounded_streaming_memory_gate.json",
    "bounded_streaming_memory_gate_doc_sha256": DOCS / "BOUNDED_STREAMING_MEMORY_GATE.md",
    "search_frontier_gate_sha256": DOCS / "search_frontier_gate.json",
    "search_frontier_gate_doc_sha256": DOCS / "SEARCH_FRONTIER_GATE.md",
    "streaming_engine_sha256": ROOT / "src" / "streaming.rs",
    "indexed_engine_sha256": ROOT / "src" / "indexed.rs",
    "streaming_tests_sha256": ROOT / "tests" / "streaming.rs",
    "indexed_v2_tests_sha256": ROOT / "tests" / "indexed_v2.rs",
    "results_generator_sha256": ROOT / "scripts" / "generate_results.py",
    "scale_generator_sha256": ROOT / "scripts" / "generate_scale_performance_report.py",
    "gate_generator_sha256": ROOT / GENERATED_BY,
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes() -> dict[str, str]:
    return {name: sha256(path) for name, path in SOURCE_PATHS.items()}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def stable_projection(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if key != "generated_at"}


def result_rows(results: dict[str, Any]) -> list[dict[str, Any]]:
    return list(results.get("results", []))


def streaming_rows(results: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        row
        for row in result_rows(results)
        if row.get("engine") == "streaming" and row.get("format") == "v2"
    ]


def planted_kind(kind: str) -> bool:
    return "planted" in kind


def control_kind(kind: str) -> bool:
    return kind.startswith("null-") or kind.endswith("-control")


def row_by_name(results: dict[str, Any], name: str) -> dict[str, Any] | None:
    return next((row for row in result_rows(results) if row.get("name") == name), None)


def indexed_streaming_parity(results: dict[str, Any]) -> dict[str, Any]:
    indexed = row_by_name(results, "indexed-planted-span8")
    streaming = row_by_name(results, "streaming-planted-span8")
    if indexed is None or streaming is None:
        return {
            "available": False,
            "matches": False,
            "observed": "indexed-planted-span8 or streaming-planted-span8 missing",
        }
    compared_fields = [
        "input_bytes",
        "output_bytes",
        "delta_bytes",
        "delta_pct",
        "hasher",
        "block_size",
        "max_span_len",
        "seed_depth",
        "passes",
    ]
    mismatches = [
        field
        for field in compared_fields
        if indexed.get(field) != streaming.get(field)
    ]
    return {
        "available": True,
        "matches": not mismatches,
        "compared_fields": compared_fields,
        "mismatches": mismatches,
        "indexed_output_bytes": indexed.get("output_bytes"),
        "streaming_output_bytes": streaming.get("output_bytes"),
        "indexed_delta_bytes": indexed.get("delta_bytes"),
        "streaming_delta_bytes": streaming.get("delta_bytes"),
        "observed": (
            "indexed and streaming planted span-8 rows match"
            if not mismatches
            else f"mismatched fields: {', '.join(mismatches)}"
        ),
    }


def test_markers() -> dict[str, bool]:
    streaming_text = (ROOT / "tests" / "streaming.rs").read_text(encoding="utf-8")
    indexed_text = (ROOT / "tests" / "indexed_v2.rs").read_text(encoding="utf-8")
    return {
        "stratified_raw_target_tables": (
            "streaming_matcher_uses_stratified_raw_target_tables" in streaming_text
            and "must not hash target bytes before lookup" in streaming_text
        ),
        "streaming_brute_roundtrip_parity": (
            "streaming_and_brute_agree_on_small_seed_planted_roundtrip" in streaming_text
        ),
        "streaming_recursive_v2_decode": (
            "streaming_v2_second_pass_can_compress_literal_payload" in streaming_text
        ),
        "indexed_exact_generated_prefixes": (
            "seed_expansion_index_uses_exact_generated_prefixes" in indexed_text
            and "must not treat hash(target) as target bytes" in indexed_text
        ),
        "indexed_weighted_selection": (
            "weighted_selection_beats_greedy_overlap" in indexed_text
        ),
    }


def streaming_case_summary(results: dict[str, Any]) -> dict[str, Any]:
    rows = streaming_rows(results)
    negative = [row for row in rows if row.get("delta_bytes", 0) < 0]
    planted_negative = [
        row for row in negative if planted_kind(str(row.get("kind", "")))
    ]
    non_planted_negative = [
        row for row in negative if not planted_kind(str(row.get("kind", "")))
    ]
    ordinary_non_planted_negative = [
        row
        for row in non_planted_negative
        if not control_kind(str(row.get("kind", "")))
    ]
    control_negative = [
        row for row in negative if control_kind(str(row.get("kind", "")))
    ]
    return {
        "streaming_v2_case_count": len(rows),
        "streaming_negative_case_count": len(negative),
        "streaming_planted_negative_case_count": len(planted_negative),
        "streaming_non_planted_negative_case_count": len(non_planted_negative),
        "streaming_ordinary_non_planted_negative_case_count": len(
            ordinary_non_planted_negative
        ),
        "streaming_control_negative_case_count": len(control_negative),
        "streaming_case_names": [str(row.get("name")) for row in rows],
        "streaming_negative_case_names": [str(row.get("name")) for row in negative],
        "streaming_non_planted_negative_case_names": [
            str(row.get("name")) for row in non_planted_negative
        ],
        "streaming_ordinary_non_planted_negative_case_names": [
            str(row.get("name")) for row in ordinary_non_planted_negative
        ],
        "streaming_control_negative_case_names": [
            str(row.get("name")) for row in control_negative
        ],
        "rows": [
            {
                "name": row.get("name"),
                "kind": row.get("kind"),
                "input_bytes": row.get("input_bytes"),
                "output_bytes": row.get("output_bytes"),
                "delta_bytes": row.get("delta_bytes"),
                "delta_pct": row.get("delta_pct"),
                "max_span_len": row.get("max_span_len"),
                "passes": row.get("passes"),
                "expected": row.get("expected"),
            }
            for row in rows
        ],
    }


def gate_checks(
    summary: dict[str, Any],
    markers: dict[str, bool],
    parity: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        {
            "gate": "streaming-correctness-fixtures",
            "requirement": "streaming tests cover raw target tables, brute parity, and recursive v2 decode",
            "observed": (
                f"{sum(1 for value in markers.values() if value)} of "
                f"{len(markers)} test markers present"
            ),
            "met": all(markers.values()),
            "consequence": "Keep CPU streaming as a correctness-covered experimental engine.",
        },
        {
            "gate": "indexed-streaming-planted-parity",
            "requirement": "indexed and streaming v2 agree on the planted span-8 result row",
            "observed": parity["observed"],
            "met": bool(parity.get("matches", False)),
            "consequence": "Use indexed/brute paths as references for small streaming fixtures.",
        },
        {
            "gate": "planted-scale-economics",
            "requirement": "planted scale telemetry remains interpretable before any larger run",
            "observed": (
                f"scale promotion={summary['scale_promotion_met']}, "
                f"largest peak={summary['largest_peak_memory_mib']} MiB, "
                f"peak/table={summary['largest_peak_to_estimated_table_ratio']}"
            ),
            "met": bool(summary["scale_promotion_met"]),
            "consequence": "Treat planted scale as memory evidence only, not natural-corpus proof.",
        },
        {
            "gate": "control-boundary-clean",
            "requirement": "streaming null/control result rows do not go negative",
            "observed": (
                f"{summary['streaming_control_negative_case_count']} control negative rows"
            ),
            "met": summary["streaming_control_negative_case_count"] == 0,
            "consequence": "Investigate immediately if random, binary, or structured controls shrink.",
        },
        {
            "gate": "non-planted-selected-span-evidence",
            "requirement": "non-planted rows show selected spans or negative delta before wider search",
            "observed": (
                f"selected spans={summary['selected_span_total']}, "
                f"ordinary non-planted streaming negatives="
                f"{summary['streaming_ordinary_non_planted_negative_case_count']}"
            ),
            "met": bool(summary["non_planted_streaming_evidence"]),
            "consequence": "Do not widen search or promote format work without non-planted evidence.",
        },
        {
            "gate": "search-frontier-open",
            "requirement": "SEARCH_FRONTIER_GATE allows broad depth search",
            "observed": (
                f"broad_depth_search_allowed="
                f"{summary['broad_depth_search_allowed']}"
            ),
            "met": bool(summary["broad_depth_search_allowed"]),
            "consequence": "Streaming implementation alone must not override the frontier gate.",
        },
    ]


def build_report() -> dict[str, Any]:
    results = load_json(DOCS / "results.json")
    scale = load_json(DOCS / "scale_performance_report.json")
    bounded = load_json(DOCS / "bounded_streaming_memory_gate.json")
    search = load_json(DOCS / "search_frontier_gate.json")
    case_summary = streaming_case_summary(results)
    parity = indexed_streaming_parity(results)
    markers = test_markers()
    scale_summary = scale["summary"]
    bounded_summary = bounded["summary"]
    search_summary = search["summary"]
    non_planted_streaming_evidence = (
        case_summary["streaming_ordinary_non_planted_negative_case_count"] > 0
        or search_summary.get("selected_span_total", 0) > 0
    )
    compute_reopen_allowed = bool(
        search_summary.get("broad_depth_search_allowed", False)
        and non_planted_streaming_evidence
    )
    format_promotion_allowed = bool(
        search_summary.get("format_promotion_allowed", False)
        and non_planted_streaming_evidence
    )
    summary = {
        **{
            key: value
            for key, value in case_summary.items()
            if key != "rows"
        },
        "gate_status": "search_closed_streaming_maintenance",
        "streaming_engine_status": "implemented_correctness_covered_experimental_path",
        "indexed_streaming_span8_parity": bool(parity.get("matches", False)),
        "streaming_test_marker_count": sum(1 for value in markers.values() if value),
        "streaming_test_marker_total": len(markers),
        "streaming_all_test_markers_present": all(markers.values()),
        "scale_promotion_met": bool(scale_summary.get("promotion_met", False)),
        "scale_recommendation": scale_summary.get("recommendation"),
        "bounded_memory_gate_status": bounded_summary.get("gate_status"),
        "target_table_preflight_present": bool(
            bounded_summary.get("target_table_preflight_present", False)
        ),
        "full_rss_containment": bool(
            bounded_summary.get("full_rss_containment", False)
        ),
        "chunked_target_tables_implemented": bool(
            bounded_summary.get("chunked_target_tables_implemented", False)
        ),
        "largest_scale_mib": scale_summary.get("largest_scale_mib"),
        "largest_peak_memory_mib": scale_summary.get("largest_peak_memory_mib"),
        "largest_peak_to_estimated_table_ratio": scale_summary.get(
            "largest_peak_to_estimated_table_ratio"
        ),
        "next_double_peak_memory_mib_at_current_ratio": scale_summary.get(
            "next_double_peak_memory_mib_at_current_ratio"
        ),
        "search_frontier_status": search_summary.get("recommended_status"),
        "broad_depth_search_allowed": bool(
            search_summary.get("broad_depth_search_allowed", False)
        ),
        "format_promotion_allowed": format_promotion_allowed,
        "selected_span_total": int(search_summary.get("selected_span_total", 0)),
        "best_non_planted_gib_for_one_expected_hit": search_summary.get(
            "best_non_planted_gib_for_one_expected_hit"
        ),
        "non_planted_streaming_evidence": non_planted_streaming_evidence,
        "compute_reopen_allowed": compute_reopen_allowed,
        "production_promotion_allowed": False,
        "recommendation": "keep_streaming_cpu_maintenance_do_not_widen_search",
        "claim_boundary": (
            "Streaming is the scalable CPU matcher path and planted-scale evidence, "
            "not natural-corpus proof, not production proof, and not a search-frontier override."
        ),
        "stop_rule": (
            "Do not widen seed depth, GPU work, or format promotion from streaming "
            "economics alone; require non-planted selected spans or negative rows with "
            "controls intact and SEARCH_FRONTIER_GATE reopened."
        ),
    }
    checks = gate_checks(summary, markers, parity)
    summary["gate_met_count"] = sum(1 for check in checks if check["met"])
    summary["gate_count"] = len(checks)
    summary["blocking_gates"] = [
        check["gate"] for check in checks if not check["met"]
    ]
    return {
        "generated_by": GENERATED_BY,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "scope": {
            "kind": "streaming economics gate",
            "performs_seed_search": False,
            "performs_replay": False,
            "launches_agents": False,
            "makes_compression_claim": False,
            "is_natural_corpus_proof": False,
            "is_production_proof": False,
            "overrides_search_frontier_gate": False,
        },
        "source_hashes": source_hashes(),
        "summary": summary,
        "test_markers": markers,
        "indexed_streaming_parity": parity,
        "gate_checks": checks,
        "streaming_cases": case_summary["rows"],
        "promotion_criteria": [
            "Keep raw-target-table and reference parity tests passing.",
            "Show non-planted selected spans or negative rows while random, binary, and structured controls stay non-negative.",
            "Keep planted-scale memory growth explainable or implement a chunked target-table strategy.",
            "Reopen SEARCH_FRONTIER_GATE before widening raw seed depth or broad long-span search.",
            "Treat GPU as research-only until a promoted CPU streaming workload exists.",
        ],
    }


def write_report(payload: dict[str, Any]) -> None:
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary = payload["summary"]
    lines = [
        "# Telomere Streaming Economics Gate",
        "",
        f"Generated by `{GENERATED_BY}` from results, scale telemetry, search-frontier gates, and streaming/indexed tests.",
        "This is a No Seed Search decision gate: it performs no seed search, performs no replay, makes no compression claim, is not natural-corpus proof, and is not production proof.",
        "",
        "## Summary",
        "",
        f"- Gate status: `{summary['gate_status']}`",
        f"- Streaming engine status: `{summary['streaming_engine_status']}`",
        f"- Streaming v2 cases: `{summary['streaming_v2_case_count']}`",
        f"- Streaming planted negative cases: `{summary['streaming_planted_negative_case_count']}`",
        f"- Streaming non-planted negative cases: `{summary['streaming_non_planted_negative_case_count']}`",
        f"- Streaming ordinary non-planted negative cases: `{summary['streaming_ordinary_non_planted_negative_case_count']}`",
        f"- Streaming control negative cases: `{summary['streaming_control_negative_case_count']}`",
        f"- Indexed/streaming planted span-8 parity: `{summary['indexed_streaming_span8_parity']}`",
        f"- Streaming test markers: `{summary['streaming_test_marker_count']}` / `{summary['streaming_test_marker_total']}`",
        f"- Scale recommendation: `{summary['scale_recommendation']}`",
        f"- Bounded memory gate status: `{summary['bounded_memory_gate_status']}`",
        f"- Target-table preflight present: `{summary['target_table_preflight_present']}`",
        f"- Full RSS containment: `{summary['full_rss_containment']}`",
        f"- Chunked target tables implemented: `{summary['chunked_target_tables_implemented']}`",
        f"- Largest planted scale: `{summary['largest_scale_mib']}` MiB",
        f"- Largest peak memory: `{summary['largest_peak_memory_mib']}` MiB",
        f"- Largest peak/estimated-table ratio: `{summary['largest_peak_to_estimated_table_ratio']}`",
        f"- Next doubled peak estimate: `{summary['next_double_peak_memory_mib_at_current_ratio']}` MiB",
        f"- Search frontier status: `{summary['search_frontier_status']}`",
        f"- Selected span total: `{summary['selected_span_total']}`",
        f"- Best non-planted forecast: `{summary['best_non_planted_gib_for_one_expected_hit']}` GiB per expected exact hit",
        f"- Compute reopen allowed: `{summary['compute_reopen_allowed']}`",
        f"- Format promotion allowed: `{summary['format_promotion_allowed']}`",
        f"- Production promotion allowed: `{summary['production_promotion_allowed']}`",
        f"- Recommendation: `{summary['recommendation']}`",
        "",
        summary["claim_boundary"],
        "",
        "## Gate Checks",
        "",
        "| gate | met | observed | consequence |",
        "| --- | --- | --- | --- |",
    ]
    for check in payload["gate_checks"]:
        lines.append(
            f"| `{check['gate']}` | `{check['met']}` | {check['observed']} | {check['consequence']} |"
        )

    lines.extend(
        [
            "",
            "## Streaming Result Rows",
            "",
            "| case | kind | input bytes | output bytes | delta bytes | delta % | span limit | passes | expected |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for row in payload["streaming_cases"]:
        lines.append(
            f"| `{row['name']}` | `{row['kind']}` | {row['input_bytes']} | "
            f"{row['output_bytes']} | {row['delta_bytes']} | {row['delta_pct']} | "
            f"{row['max_span_len']} | {row['passes']} | `{row['expected']}` |"
        )

    lines.extend(["", "## Promotion Criteria", ""])
    lines.extend(f"- {item}" for item in payload["promotion_criteria"])
    lines.extend(["", "## Stop Rule", "", f"- {summary['stop_rule']}"])
    lines.extend(["", "## Source Artifacts", ""])
    for name, digest in payload["source_hashes"].items():
        lines.append(f"- `{name}`: `{digest}`")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not REPORT_JSON.exists() or not REPORT_MD.exists():
        raise SystemExit("generated streaming economics gate files are missing")
    payload = load_json(REPORT_JSON)
    if payload.get("generated_by") != GENERATED_BY:
        raise SystemExit("streaming_economics_gate.json has wrong generated_by marker")
    expected = build_report()
    if stable_projection(payload) != stable_projection(expected):
        raise SystemExit("streaming economics gate is stale; regenerate it")
    text = REPORT_MD.read_text(encoding="utf-8")
    for phrase in (
        "Telomere Streaming Economics Gate",
        "No Seed Search decision gate",
        "search_closed_streaming_maintenance",
        "not natural-corpus proof",
        "Stop Rule",
    ):
        if phrase not in text:
            raise SystemExit(f"STREAMING_ECONOMICS_GATE.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate generated gate")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.check:
        check_report()
        return
    write_report(build_report())


if __name__ == "__main__":
    main()
