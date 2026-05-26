#!/usr/bin/env python3
"""Generate the bounded-memory gate for v2 compression/decompression guards."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
REPORT_JSON = DOCS / "bounded_streaming_memory_gate.json"
REPORT_MD = DOCS / "BOUNDED_STREAMING_MEMORY_GATE.md"
GENERATED_BY = "scripts/generate_bounded_streaming_memory_gate.py"

SOURCE_PATHS = {
    "scale_performance_report_sha256": DOCS / "scale_performance_report.json",
    "scale_performance_doc_sha256": DOCS / "SCALE_PERFORMANCE.md",
    "results_sha256": DOCS / "results.json",
    "results_doc_sha256": DOCS / "RESULTS.md",
    "search_frontier_gate_sha256": DOCS / "search_frontier_gate.json",
    "streaming_engine_sha256": ROOT / "src" / "streaming.rs",
    "indexed_engine_sha256": ROOT / "src" / "indexed.rs",
    "decompress_api_sha256": ROOT / "src" / "lib.rs",
    "v2_format_sha256": ROOT / "src" / "tlmr_v2.rs",
    "cli_sha256": ROOT / "src" / "main.rs",
    "streaming_tests_sha256": ROOT / "tests" / "streaming.rs",
    "indexed_v2_tests_sha256": ROOT / "tests" / "indexed_v2.rs",
    "cli_tests_sha256": ROOT / "tests" / "cli_tests.rs",
    "scale_generator_sha256": ROOT / "scripts" / "generate_scale_performance_report.py",
    "generator_sha256": ROOT / GENERATED_BY,
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes() -> dict[str, str]:
    return {name: sha256(path) for name, path in SOURCE_PATHS.items()}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def stable_projection(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if key != "generated_at"}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def marker_status() -> dict[str, bool]:
    main_rs = read(ROOT / "src" / "main.rs")
    lib_rs = read(ROOT / "src" / "lib.rs")
    tlmr_v2_rs = read(ROOT / "src" / "tlmr_v2.rs")
    streaming_rs = read(ROOT / "src" / "streaming.rs")
    indexed_rs = read(ROOT / "src" / "indexed.rs")
    streaming_tests = read(ROOT / "tests" / "streaming.rs")
    indexed_tests = read(ROOT / "tests" / "indexed_v2.rs")
    cli_tests = read(ROOT / "tests" / "cli_tests.rs")
    return {
        "shared_upper_bound_estimator": "estimate_target_table_upper_bound_for_tiers" in indexed_rs,
        "streaming_upper_bound_estimator": "estimate_streaming_target_table_upper_bound" in streaming_rs,
        "cli_memory_preflight": "enforce_target_table_memory_limit" in main_rs,
        "indexed_cli_memory_preflight": '"indexed",' in main_rs
        and "estimate_target_table_upper_bound_for_tiers" in main_rs,
        "streaming_cli_memory_preflight": '"streaming",' in main_rs
        and "estimate_streaming_target_table_upper_bound" in main_rs,
        "streaming_estimate_unit_test": "streaming_target_table_upper_bound_is_conservative" in streaming_tests,
        "streaming_cli_limit_test": "streaming_v2_respects_memory_limit_preflight" in cli_tests,
        "decompress_cli_memory_limit": (
            "struct DecompressArgs" in main_rs
            and "parse_memory_limit(&args.memory_limit)" in main_rs
            and "memory_limit: memory_limit_bytes" in main_rs
            and "decompress_with_limit(&input_data, &config, usize::MAX)" in main_rs
        ),
        "decompress_cli_limit_error": "Decompression exceeded --memory-limit" in main_rs,
        "decompress_cli_limit_test": "decompress_respects_memory_limit_cli" in cli_tests,
        "v2_decompress_cli_limit_test": "v2_decompress_respects_memory_limit_cli" in cli_tests,
        "api_v2_limit_routing": "tlmr_v2::decompress_v2_with_limit(input, limit, memory_limit)" in lib_rs,
        "v1_memory_limit_check": "original_len > config.memory_limit" in lib_rs,
        "v2_original_memory_limit_check": "original_len > limit || original_len > memory_limit" in tlmr_v2_rs,
        "v2_layer_memory_limit_check": "decoded_len > limit || decoded_len > memory_limit" in tlmr_v2_rs,
        "streaming_chunked_api": "find_streaming_candidates_chunked_with_span_step" in streaming_rs
        and "compress_streaming_v2_with_chunked_span_step_and_telemetry" in streaming_rs,
        "streaming_chunk_estimator": "estimate_streaming_target_chunk_upper_bound" in streaming_rs,
        "cli_streaming_target_chunk_bytes": "target_chunk_bytes" in main_rs
        and "compress_streaming_v2_with_chunked_span_step_and_telemetry" in main_rs,
        "streaming_chunked_candidate_test": "streaming_chunked_target_tables_match_unchunked_candidates" in streaming_tests,
        "streaming_chunked_estimate_test": "streaming_chunked_target_table_estimate_bounds_chunk_peak" in streaming_tests,
        "streaming_chunked_roundtrip_test": "streaming_v2_chunked_target_tables_roundtrip_planted_span" in streaming_tests,
        "streaming_chunked_cli_test": "streaming_v2_chunked_target_tables_can_fit_below_whole_preflight" in cli_tests,
        "indexed_chunked_api": "find_indexed_candidates_chunked" in indexed_rs
        and "compress_indexed_v2_with_chunked_span_step_and_telemetry" in indexed_rs,
        "indexed_chunk_estimator": "estimate_target_table_chunk_upper_bound_for_tiers" in indexed_rs,
        "cli_indexed_target_chunk_bytes": "target_chunk_bytes" in main_rs
        and "compress_indexed_v2_with_chunked_span_step_and_telemetry" in main_rs,
        "indexed_chunked_selected_test": "indexed_chunked_target_tables_match_unchunked_selected_spans" in indexed_tests,
        "indexed_chunked_estimate_test": "indexed_chunked_target_table_estimate_bounds_chunk_peak" in indexed_tests,
        "indexed_chunked_cli_test": "indexed_v2_chunked_target_tables_can_fit_below_whole_preflight" in cli_tests,
    }


def gate_checks(summary: dict[str, Any], markers: dict[str, bool]) -> list[dict[str, Any]]:
    return [
        {
            "gate": "target-table-estimate-preflight",
            "requirement": "indexed/streaming v2 compression rejects target-table estimates above --memory-limit before allocation",
            "observed": (
                f"cli preflight={markers['cli_memory_preflight']}, "
                f"indexed={markers['indexed_cli_memory_preflight']}, "
                f"streaming={markers['streaming_cli_memory_preflight']}"
            ),
            "met": bool(
                markers["cli_memory_preflight"]
                and markers["indexed_cli_memory_preflight"]
                and markers["streaming_cli_memory_preflight"]
            ),
            "consequence": "The CLI has an estimate guard for the largest current v2 target-table allocation.",
        },
        {
            "gate": "estimate-test-coverage",
            "requirement": "unit and CLI tests cover the conservative estimator and low-limit rejection",
            "observed": (
                f"unit={markers['streaming_estimate_unit_test']}, "
                f"cli={markers['streaming_cli_limit_test']}"
            ),
            "met": bool(
                markers["streaming_estimate_unit_test"]
                and markers["streaming_cli_limit_test"]
            ),
            "consequence": "The guard is covered without broad search or large fixtures.",
        },
        {
            "gate": "decompression-output-limit-guards",
            "requirement": (
                "CLI decompression routes --memory-limit into v1/v2 decode paths, "
                "and v2 checks final output plus intermediate layer lengths before decode allocation"
            ),
            "observed": (
                f"cli={markers['decompress_cli_memory_limit']}, "
                f"error={markers['decompress_cli_limit_error']}, "
                f"api_v2={markers['api_v2_limit_routing']}, "
                f"v1={markers['v1_memory_limit_check']}, "
                f"v2_output={markers['v2_original_memory_limit_check']}, "
                f"v2_layers={markers['v2_layer_memory_limit_check']}"
            ),
            "met": bool(
                markers["decompress_cli_memory_limit"]
                and markers["decompress_cli_limit_error"]
                and markers["api_v2_limit_routing"]
                and markers["v1_memory_limit_check"]
                and markers["v2_original_memory_limit_check"]
                and markers["v2_layer_memory_limit_check"]
            ),
            "consequence": "Decode output/layer allocation is guarded, but this is not full process RSS containment.",
        },
        {
            "gate": "decompression-limit-test-coverage",
            "requirement": "CLI tests cover low-limit decompression rejection for both v1 and v2 files",
            "observed": (
                f"v1_cli={markers['decompress_cli_limit_test']}, "
                f"v2_cli={markers['v2_decompress_cli_limit_test']}"
            ),
            "met": bool(
                markers["decompress_cli_limit_test"]
                and markers["v2_decompress_cli_limit_test"]
            ),
            "consequence": "Small deterministic fixtures verify the user-facing limit error path for both active formats.",
        },
        {
            "gate": "planted-scale-explainability",
            "requirement": "existing planted-density scale telemetry remains explainable",
            "observed": (
                f"scale promotion={summary['scale_promotion_met']}, "
                f"peak/table={summary['largest_peak_to_estimated_table_ratio']}"
            ),
            "met": bool(summary["scale_promotion_met"]),
            "consequence": "Use the current scale row as planted-memory evidence only.",
        },
        {
            "gate": "full-rss-containment",
            "requirement": "memory limit bounds full process RSS, not only target-table estimates",
            "observed": (
                f"full_rss_containment={summary['full_rss_containment']}, "
                f"largest_peak_memory_mib={summary['largest_peak_memory_mib']}"
            ),
            "met": bool(summary["full_rss_containment"]),
            "consequence": "Do not claim production memory safety yet.",
        },
        {
            "gate": "chunked-target-tables",
            "requirement": "indexed and streaming v2 target tables can be chunked below the configured memory budget on deterministic fixtures",
            "observed": (
                f"streaming_api={markers['streaming_chunked_api']}, "
                f"streaming_estimator={markers['streaming_chunk_estimator']}, "
                f"streaming_cli={markers['cli_streaming_target_chunk_bytes']}, "
                f"streaming_candidate_test={markers['streaming_chunked_candidate_test']}, "
                f"streaming_estimate_test={markers['streaming_chunked_estimate_test']}, "
                f"streaming_roundtrip_test={markers['streaming_chunked_roundtrip_test']}, "
                f"streaming_cli_test={markers['streaming_chunked_cli_test']}, "
                f"indexed_api={markers['indexed_chunked_api']}, "
                f"indexed_estimator={markers['indexed_chunk_estimator']}, "
                f"indexed_cli={markers['cli_indexed_target_chunk_bytes']}, "
                f"indexed_selected_test={markers['indexed_chunked_selected_test']}, "
                f"indexed_estimate_test={markers['indexed_chunked_estimate_test']}, "
                f"indexed_cli_test={markers['indexed_chunked_cli_test']}"
            ),
            "met": bool(summary["chunked_target_tables_implemented"]),
            "consequence": "Indexed and streaming have experimental chunking evidence, but full RSS containment is not proven.",
        },
    ]


def build_report() -> dict[str, Any]:
    scale = load_json(DOCS / "scale_performance_report.json")["summary"]
    search = load_json(DOCS / "search_frontier_gate.json")["summary"]
    results = load_json(DOCS / "results.json")
    markers = marker_status()
    full_rss_containment = False
    chunked_target_tables_implemented = bool(
        markers["streaming_chunked_api"]
        and markers["streaming_chunk_estimator"]
        and markers["cli_streaming_target_chunk_bytes"]
        and markers["streaming_chunked_candidate_test"]
        and markers["streaming_chunked_estimate_test"]
        and markers["streaming_chunked_roundtrip_test"]
        and markers["streaming_chunked_cli_test"]
        and markers["indexed_chunked_api"]
        and markers["indexed_chunk_estimator"]
        and markers["cli_indexed_target_chunk_bytes"]
        and markers["indexed_chunked_selected_test"]
        and markers["indexed_chunked_estimate_test"]
        and markers["indexed_chunked_cli_test"]
    )
    streaming_chunked_fixture_evidence = bool(
        markers["streaming_chunked_api"]
        and markers["streaming_chunk_estimator"]
        and markers["cli_streaming_target_chunk_bytes"]
        and markers["streaming_chunked_candidate_test"]
        and markers["streaming_chunked_estimate_test"]
        and markers["streaming_chunked_roundtrip_test"]
        and markers["streaming_chunked_cli_test"]
    )
    indexed_chunked_fixture_evidence = bool(
        markers["indexed_chunked_api"]
        and markers["indexed_chunk_estimator"]
        and markers["cli_indexed_target_chunk_bytes"]
        and markers["indexed_chunked_selected_test"]
        and markers["indexed_chunked_estimate_test"]
        and markers["indexed_chunked_cli_test"]
    )
    target_table_preflight = bool(
        markers["cli_memory_preflight"]
        and markers["indexed_cli_memory_preflight"]
        and markers["streaming_cli_memory_preflight"]
    )
    tests_cover_preflight = bool(
        markers["streaming_estimate_unit_test"]
        and markers["streaming_cli_limit_test"]
    )
    decompression_limit_guard = bool(
        markers["decompress_cli_memory_limit"]
        and markers["decompress_cli_limit_error"]
        and markers["api_v2_limit_routing"]
        and markers["v1_memory_limit_check"]
        and markers["v2_original_memory_limit_check"]
        and markers["v2_layer_memory_limit_check"]
    )
    tests_cover_decompression_limit = bool(
        markers["decompress_cli_limit_test"]
        and markers["v2_decompress_cli_limit_test"]
    )
    summary = {
        "gate_status": "chunked_target_table_fixture_evidence_no_rss",
        "target_table_preflight_present": target_table_preflight,
        "tests_cover_preflight": tests_cover_preflight,
        "decompression_limit_guard_present": decompression_limit_guard,
        "tests_cover_decompression_limit": tests_cover_decompression_limit,
        "v2_layer_allocation_limit_present": bool(
            markers["v2_layer_memory_limit_check"]
        ),
        "full_rss_containment": full_rss_containment,
        "chunked_target_tables_implemented": chunked_target_tables_implemented,
        "streaming_chunked_fixture_evidence": streaming_chunked_fixture_evidence,
        "indexed_chunked_fixture_evidence": indexed_chunked_fixture_evidence,
        "bounded_memory_production_ready": False,
        "scale_promotion_met": bool(scale.get("promotion_met", False)),
        "scale_recommendation": scale.get("recommendation"),
        "largest_scale_mib": scale.get("largest_scale_mib"),
        "largest_peak_memory_mib": scale.get("largest_peak_memory_mib"),
        "largest_estimated_target_table_mib": scale.get(
            "largest_estimated_target_table_mib"
        ),
        "largest_peak_to_estimated_table_ratio": scale.get(
            "largest_peak_to_estimated_table_ratio"
        ),
        "next_double_peak_memory_mib_at_current_ratio": scale.get(
            "next_double_peak_memory_mib_at_current_ratio"
        ),
        "streaming_v2_case_count": sum(
            1
            for row in results.get("results", [])
            if row.get("engine") == "streaming" and row.get("format") == "v2"
        ),
        "broad_depth_search_allowed": bool(
            search.get("broad_depth_search_allowed", False)
        ),
        "selected_span_total": int(search.get("selected_span_total", 0)),
        "recommendation": "keep_chunked_v2_experimental_do_not_claim_full_rss",
        "claim_boundary": (
            "The CLI now has a conservative target-table estimate preflight for v2 "
            "compression plus decompression output/intermediate-layer allocation "
            "guards for v1/v2 files. Indexed and streaming v2 also have explicit "
            "experimental chunked target-table paths verified on deterministic "
            "fixtures. This is not full RSS containment, not natural-corpus proof, "
            "and not production readiness."
        ),
        "stop_rule": (
            "Do not extend planted scale, broaden search, or market bounded-memory "
            "operation until chunked target tables are verified on promoted workloads "
            "with full RSS evidence."
        ),
    }
    checks = gate_checks(summary, markers)
    summary["gate_met_count"] = sum(1 for check in checks if check["met"])
    summary["gate_count"] = len(checks)
    summary["blocking_gates"] = [check["gate"] for check in checks if not check["met"]]
    return {
        "generated_by": GENERATED_BY,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "scope": {
            "kind": "bounded streaming memory gate",
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
        "markers": markers,
        "gate_checks": checks,
    }


def write_report(payload: dict[str, Any]) -> None:
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary = payload["summary"]
    lines = [
        "# Telomere Bounded Streaming Memory Gate",
        "",
        f"Generated by `{GENERATED_BY}` from scale telemetry, results, frontier gates, and v2 memory-guard code/tests.",
        "This is a No Seed Search memory-boundary gate: it performs no seed search, performs no replay, makes no compression claim, is not natural-corpus proof, and is not production proof.",
        "",
        "## Summary",
        "",
        f"- Gate status: `{summary['gate_status']}`",
        f"- Target-table preflight present: `{summary['target_table_preflight_present']}`",
        f"- Tests cover preflight: `{summary['tests_cover_preflight']}`",
        f"- Decompression limit guard present: `{summary['decompression_limit_guard_present']}`",
        f"- Tests cover decompression limit: `{summary['tests_cover_decompression_limit']}`",
        f"- v2 layer allocation limit present: `{summary['v2_layer_allocation_limit_present']}`",
        f"- Full RSS containment: `{summary['full_rss_containment']}`",
        f"- Chunked target tables implemented: `{summary['chunked_target_tables_implemented']}`",
        f"- Streaming chunked fixture evidence: `{summary['streaming_chunked_fixture_evidence']}`",
        f"- Indexed chunked fixture evidence: `{summary['indexed_chunked_fixture_evidence']}`",
        f"- Bounded-memory production ready: `{summary['bounded_memory_production_ready']}`",
        f"- Largest planted scale: `{summary['largest_scale_mib']}` MiB",
        f"- Largest peak memory: `{summary['largest_peak_memory_mib']}` MiB",
        f"- Largest estimated target table: `{summary['largest_estimated_target_table_mib']}` MiB",
        f"- Largest peak/estimated-table ratio: `{summary['largest_peak_to_estimated_table_ratio']}`",
        f"- Next doubled peak estimate: `{summary['next_double_peak_memory_mib_at_current_ratio']}` MiB",
        f"- Streaming v2 result rows: `{summary['streaming_v2_case_count']}`",
        f"- Broad depth search allowed: `{summary['broad_depth_search_allowed']}`",
        f"- Selected span total: `{summary['selected_span_total']}`",
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
    lines.extend(["", "## Stop Rule", "", f"- {summary['stop_rule']}"])
    lines.extend(["", "## Source Artifacts", ""])
    for name, digest in payload["source_hashes"].items():
        lines.append(f"- `{name}`: `{digest}`")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not REPORT_JSON.exists() or not REPORT_MD.exists():
        raise SystemExit("generated bounded streaming memory gate files are missing")
    payload = load_json(REPORT_JSON)
    if payload.get("generated_by") != GENERATED_BY:
        raise SystemExit("bounded_streaming_memory_gate.json has wrong generated_by marker")
    expected = build_report()
    if stable_projection(payload) != stable_projection(expected):
        raise SystemExit("bounded streaming memory gate is stale; regenerate it")
    text = REPORT_MD.read_text(encoding="utf-8")
    for phrase in (
        "Telomere Bounded Streaming Memory Gate",
        "No Seed Search memory-boundary gate",
        "chunked_target_table_fixture_evidence_no_rss",
        "Decompression limit guard present",
        "decompression output/intermediate-layer allocation",
        "Streaming chunked fixture evidence",
        "Indexed chunked fixture evidence",
        "not full RSS containment",
        "Stop Rule",
    ):
        if phrase not in text:
            raise SystemExit(f"BOUNDED_STREAMING_MEMORY_GATE.md missing phrase: {phrase}")


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
