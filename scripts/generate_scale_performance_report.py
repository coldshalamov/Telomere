#!/usr/bin/env python3
"""Generate a scale-performance decision report from current sweep telemetry."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
SWEEPS_JSON = DOCS / "sweeps.json"
REPORT_JSON = DOCS / "scale_performance_report.json"
REPORT_MD = DOCS / "SCALE_PERFORMANCE.md"
GENERATED_BY = "scripts/generate_scale_performance_report.py"

SOURCE_PATHS = {
    "sweeps_sha256": SWEEPS_JSON,
    "sweeps_doc_sha256": DOCS / "SWEEPS.md",
    "sweep_generator_sha256": ROOT / "scripts" / "generate_sweeps.py",
    "streaming_engine_sha256": ROOT / "src" / "streaming.rs",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes() -> dict[str, str]:
    return {name: sha256(path) for name, path in SOURCE_PATHS.items()}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def mib(value: float | int) -> float:
    return round(float(value) / (1024 * 1024), 3)


def memory_rows(sweeps: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [
        row
        for row in sweeps.get("results", [])
        if row.get("group") == "memory-scaling"
    ]
    return sorted(rows, key=lambda row: row["input_bytes"])


def ratio(numerator: float | int | None, denominator: float | int | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return round(float(numerator) / float(denominator), 3)


def row_summary(row: dict[str, Any]) -> dict[str, Any]:
    telemetry = row.get("telemetry", {})
    estimated_mib = telemetry.get("tier_estimated_target_table_mib_total")
    peak_mib = row.get("peak_memory_mib")
    return {
        "name": row["name"],
        "input_bytes": row["input_bytes"],
        "input_mib": mib(row["input_bytes"]),
        "output_bytes": row["output_bytes"],
        "delta_bytes": row["delta_bytes"],
        "delta_pct": round(row["delta_pct"], 4),
        "compress_ms": row["compress_ms"],
        "throughput_mib_s": row["throughput_mib_s"],
        "decompress_ms": row["decompress_ms"],
        "selected_count": telemetry.get("selected_count", 0),
        "seed_expansions": telemetry.get("seed_expansions", 0),
        "target_windows": telemetry.get("tier_target_windows_total", 0),
        "lookup_count": telemetry.get("tier_lookup_count_total", 0),
        "unique_spans": telemetry.get("tier_unique_spans_total", 0),
        "candidate_hits_raw": telemetry.get("candidate_hits_raw_total", 0),
        "candidate_hits_profitable": telemetry.get("candidate_hits_profitable_total", 0),
        "estimated_target_table_mib": estimated_mib,
        "peak_memory_mib": peak_mib,
        "peak_to_estimated_table_ratio": ratio(peak_mib, estimated_mib),
        "selected_per_mib": ratio(telemetry.get("selected_count", 0), mib(row["input_bytes"])),
        "target_windows_per_mib": ratio(
            telemetry.get("tier_target_windows_total", 0), mib(row["input_bytes"])
        ),
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "row_count": 0,
            "recommendation": "missing_sweep_rows",
            "promotion_met": False,
            "stop_rule": "Regenerate docs/sweeps.json before making scale decisions.",
        }
    largest = max(rows, key=lambda row: row["input_bytes"])
    largest_telemetry = largest.get("telemetry", {})
    plateau = [row for row in rows if row["input_bytes"] >= 1_048_576]
    plateau_ratios = [
        ratio(
            row.get("peak_memory_mib"),
            row.get("telemetry", {}).get("tier_estimated_target_table_mib_total"),
        )
        for row in plateau
    ]
    plateau_ratios = [value for value in plateau_ratios if value is not None]
    plateau_throughputs = [row["throughput_mib_s"] for row in plateau]
    ratio_min = min(plateau_ratios, default=0.0)
    ratio_max = max(plateau_ratios, default=0.0)
    ratio_spread_pct = (
        round((ratio_max - ratio_min) / ratio_min * 100, 3) if ratio_min else 0.0
    )
    largest_estimated_mib = largest_telemetry.get("tier_estimated_target_table_mib_total", 0.0)
    largest_peak_mib = largest.get("peak_memory_mib", 0.0)
    next_input_mib = mib(largest["input_bytes"] * 2)
    next_estimated_target_table_mib = round(largest_estimated_mib * 2, 3)
    next_peak_mib = round((largest_peak_mib or 0.0) * 2, 3)
    promotion_met = (
        largest["delta_bytes"] < 0
        and largest_peak_mib is not None
        and ratio_spread_pct <= 15.0
        and ratio_max <= 30.0
        and min(plateau_throughputs, default=0.0) >= 1.0
    )
    return {
        "row_count": len(rows),
        "largest_scale_mib": mib(largest["input_bytes"]),
        "largest_input_bytes": largest["input_bytes"],
        "largest_output_bytes": largest["output_bytes"],
        "largest_delta_bytes": largest["delta_bytes"],
        "largest_delta_pct": round(largest["delta_pct"], 4),
        "largest_compress_ms": largest["compress_ms"],
        "largest_throughput_mib_s": largest["throughput_mib_s"],
        "largest_peak_memory_mib": largest_peak_mib,
        "largest_estimated_target_table_mib": largest_estimated_mib,
        "largest_peak_to_estimated_table_ratio": ratio(
            largest_peak_mib, largest_estimated_mib
        ),
        "plateau_row_count": len(plateau),
        "plateau_ratio_min": ratio_min,
        "plateau_ratio_max": ratio_max,
        "plateau_ratio_mean": round(mean(plateau_ratios), 3) if plateau_ratios else 0.0,
        "plateau_ratio_spread_pct": ratio_spread_pct,
        "plateau_throughput_min_mib_s": min(plateau_throughputs, default=0.0),
        "plateau_throughput_max_mib_s": max(plateau_throughputs, default=0.0),
        "next_double_input_mib": next_input_mib,
        "next_double_estimated_target_table_mib": next_estimated_target_table_mib,
        "next_double_peak_memory_mib_at_current_ratio": next_peak_mib,
        "promotion_met": promotion_met,
        "recommendation": (
            "bounded_scale_interpretable_not_production"
            if promotion_met
            else "scale_work_requires_new_memory_strategy"
        ),
        "stop_rule": (
            "Do not extend planted-density scale runs unless peak/estimated-table "
            "ratio stays near the observed plateau or chunked target tables reduce "
            "the working set."
        ),
        "conclusion": (
            "Current 16 MiB planted-density scaling is explainable but memory-heavy."
            if promotion_met
            else "Current scaling telemetry is not stable enough to extend blindly."
        ),
    }


def build_report() -> dict[str, Any]:
    rows = [row_summary(row) for row in memory_rows(load_json(SWEEPS_JSON))]
    return {
        "generated_by": GENERATED_BY,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "source_hashes": source_hashes(),
        "summary": summarize(memory_rows(load_json(SWEEPS_JSON))),
        "rows": rows,
    }


def write_report(payload: dict[str, Any]) -> None:
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary = payload["summary"]
    lines = [
        "# Telomere Scale Performance Report",
        "",
        f"Generated by `{GENERATED_BY}` from `docs/sweeps.json` memory-scaling rows.",
        "This is a planted-density scale decision artifact, not natural-corpus proof.",
        "",
        "## Summary",
        "",
        f"- Rows: `{summary['row_count']}`",
        f"- Largest scale: `{summary['largest_scale_mib']}` MiB",
        f"- Largest delta: `{summary['largest_delta_bytes']}` bytes (`{summary['largest_delta_pct']}`%)",
        f"- Largest-scale throughput: `{summary['largest_throughput_mib_s']}` MiB/s",
        f"- Largest peak memory: `{summary['largest_peak_memory_mib']}` MiB",
        f"- Largest estimated target table: `{summary['largest_estimated_target_table_mib']}` MiB",
        f"- Largest peak/estimated-table ratio: `{summary['largest_peak_to_estimated_table_ratio']}`",
        f"- Plateau ratio spread: `{summary['plateau_ratio_spread_pct']}`%",
        f"- Next doubled input estimate: `{summary['next_double_input_mib']}` MiB input, `{summary['next_double_peak_memory_mib_at_current_ratio']}` MiB peak if current ratio holds",
        f"- Promotion met: `{summary['promotion_met']}`",
        f"- Recommendation: `{summary['recommendation']}`",
        "",
        summary["conclusion"],
        "",
        "## Scale Rows",
        "",
        "| case | input MiB | delta % | MiB/s | peak MiB | estimated table MiB | peak/table | selected | target windows |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in payload["rows"]:
        lines.append(
            f"| `{row['name']}` | {row['input_mib']} | {row['delta_pct']} | "
            f"{row['throughput_mib_s']} | {row['peak_memory_mib']} | "
            f"{row['estimated_target_table_mib']} | {row['peak_to_estimated_table_ratio']} | "
            f"{row['selected_count']} | {row['target_windows']} |"
        )
    lines.extend(["", "## Stop Rule", ""])
    lines.append(f"- {summary['stop_rule']}")
    lines.extend(["", "## Source Artifacts", ""])
    for name, digest in payload["source_hashes"].items():
        lines.append(f"- `{name}`: `{digest}`")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not REPORT_JSON.exists() or not REPORT_MD.exists():
        raise SystemExit("generated scale performance files are missing")
    payload = load_json(REPORT_JSON)
    if payload.get("generated_by") != GENERATED_BY:
        raise SystemExit("scale_performance_report.json has wrong generated_by marker")
    if payload.get("source_hashes") != source_hashes():
        raise SystemExit("scale performance source hashes are stale")
    expected_rows = memory_rows(load_json(SWEEPS_JSON))
    if len(payload.get("rows", [])) != len(expected_rows):
        raise SystemExit("scale performance row matrix is incomplete")
    summary = payload.get("summary", {})
    if summary.get("largest_scale_mib") != mib(max(expected_rows, key=lambda row: row["input_bytes"])["input_bytes"]):
        raise SystemExit("scale performance largest scale is stale")
    text = REPORT_MD.read_text(encoding="utf-8")
    for phrase in (
        "Telomere Scale Performance Report",
        f"Generated by `{GENERATED_BY}`",
        "planted-density scale decision artifact",
        "Largest-scale throughput",
        "Plateau ratio spread",
        "Stop Rule",
        "peak/estimated-table",
    ):
        if phrase not in text:
            raise SystemExit(f"SCALE_PERFORMANCE.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate generated scale report")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.check:
        check_report()
        return
    write_report(build_report())


if __name__ == "__main__":
    main()
