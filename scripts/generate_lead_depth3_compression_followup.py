#!/usr/bin/env python3
"""Run bounded depth-3 compression on lead-depth3 promoted rows."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import generate_lead_depth3_prefix_probe
import generate_lead_exact_discovery
import generate_results
import generate_sweeps


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
PREFIX_PROBE_JSON = DOCS / "lead_depth3_prefix_probe.json"
FOLLOWUP_JSON = DOCS / "lead_depth3_compression_followup.json"
FOLLOWUP_MD = DOCS / "LEAD_DEPTH3_COMPRESSION_FOLLOWUP.md"

HASHER = "sha256"
BASELINE_DEPTH = 2
FOLLOWUP_DEPTH = 3
BLOCK_SIZE = 4
SPAN_LEN = 8
SPAN_STEP = 1
PASSES = 1
MEMORY_LIMIT = "100%"
TELEMETRY_LIMIT = "32"
MAX_PROMOTED_ROWS = 4


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def slug(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", text).strip("-")[:96]


def artifact_hashes() -> dict[str, str]:
    return {
        "lead_depth3_prefix_probe_sha256": sha256(PREFIX_PROBE_JSON),
    }


def promoted_rows(prefix_probe: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [
        row
        for row in prefix_probe.get("results", [])
        if row.get("prefix_ge_5_delta_vs_depth2", 0) > 0
        or row.get("depth3_exact_hits", 0) > 0
    ]
    return rows[:MAX_PROMOTED_ROWS]


def selected_manifest() -> list[dict[str, Any]]:
    fields = (
        "name",
        "family",
        "corpus",
        "role",
        "control_kind",
        "independence_group",
        "lead_source",
        "lead_name",
        "input_sha256",
        "transformed_sha256",
        "baseline_prefix_ge_4",
        "depth3_prefix_ge_4",
        "baseline_prefix_ge_5",
        "depth3_prefix_ge_5",
        "prefix_ge_5_delta_vs_depth2",
        "depth3_exact_hits",
    )
    return [
        {field: row[field] for field in fields}
        for row in promoted_rows(load_json(PREFIX_PROBE_JSON))
    ]


def selected_manifest_hash() -> str:
    payload = json.dumps(selected_manifest(), sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def transformed_bytes_for_row(row: dict[str, Any]) -> bytes:
    corpus = {
        "family": row["family"],
        "corpus": row["corpus"],
        "role": row["role"],
        "control_kind": row["control_kind"],
        "independence_group": row["independence_group"],
    }
    lead = generate_lead_depth3_prefix_probe.lead_by_key()[
        (row["lead_source"], row["lead_name"])
    ]
    source = generate_lead_exact_discovery.corpus_bytes(corpus)
    if hashlib.sha256(source).hexdigest() != row["input_sha256"]:
        raise RuntimeError(f"{row['name']}: input hash changed")
    transformed = generate_lead_exact_discovery.apply_lead(source, lead)
    if hashlib.sha256(transformed).hexdigest() != row["transformed_sha256"]:
        raise RuntimeError(f"{row['name']}: transformed hash changed")
    return transformed


def physical_inputs(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        digest = row["transformed_sha256"]
        grouped.setdefault(
            digest,
            {
                "transformed_sha256": digest,
                "representative": row,
                "aliases": [],
            },
        )["aliases"].append(row)
    return sorted(grouped.values(), key=lambda item: item["transformed_sha256"])


def summarize_telemetry(summary: dict[str, Any]) -> dict[str, Any]:
    telemetry = summary.get("engine_telemetry", {})
    layers = telemetry.get("layers", [])
    return {
        "candidate_count": telemetry.get("candidate_count", 0),
        "selected_count": telemetry.get("selected_count", 0),
        "literal_bytes": telemetry.get("literal_bytes", 0),
        "bundle_count": telemetry.get("bundle_count", 0),
        "container_bytes": telemetry.get("container_bytes", 0),
        "seed_len_counts": telemetry.get("seed_len_counts", []),
        "layer_count": len(layers),
        "layer_payload_bytes": [layer.get("payload_bytes", 0) for layer in layers],
        "layer_selected_counts": [layer.get("selected_count", 0) for layer in layers],
        "selected_spans": telemetry.get("selected_spans", []),
        "stop_reason": telemetry.get("stop_reason", ""),
    }


def run_depth(row: dict[str, Any], seed_depth: int, temp: Path, exe: Path) -> dict[str, Any]:
    data = transformed_bytes_for_row(row)
    safe_name = slug(row["name"])
    input_path = temp / f"{safe_name}-depth{seed_depth}.bin"
    output_path = temp / f"{safe_name}-depth{seed_depth}.tlmr"
    restored_path = temp / f"{safe_name}-depth{seed_depth}.restored"
    input_path.write_bytes(data)
    cmd = [
        str(exe),
        "compress",
        str(input_path),
        str(output_path),
        "--engine",
        "streaming",
        "--format",
        "v2",
        "--hasher",
        HASHER,
        "--block-size",
        str(BLOCK_SIZE),
        "--span-step",
        str(SPAN_STEP),
        "--seed-depth",
        str(seed_depth),
        "--passes",
        str(PASSES),
        "--max-span-len",
        str(SPAN_LEN),
        "--memory-limit",
        MEMORY_LIMIT,
        "--json",
        "--telemetry-limit",
        TELEMETRY_LIMIT,
        "--verify",
        "--force",
    ]
    started = time.perf_counter()
    proc, peak_memory_bytes = generate_sweeps.run_measured(cmd)
    compress_ms = round((time.perf_counter() - started) * 1000.0, 3)
    summary = json.loads(proc.stdout)

    started = time.perf_counter()
    generate_sweeps.run([str(exe), "decompress", str(output_path), str(restored_path), "--force"])
    decompress_ms = round((time.perf_counter() - started) * 1000.0, 3)
    if restored_path.read_bytes() != data:
        raise RuntimeError(f"{row['name']} depth {seed_depth}: roundtrip mismatch")

    input_bytes = len(data)
    output_bytes = output_path.stat().st_size
    return {
        "row_name": row["name"],
        "family": row["family"],
        "corpus": row["corpus"],
        "role": row["role"],
        "lead_source": row["lead_source"],
        "lead_name": row["lead_name"],
        "seed_depth": seed_depth,
        "input_sha256": hashlib.sha256(data).hexdigest(),
        "output_sha256": hashlib.sha256(output_path.read_bytes()).hexdigest(),
        "input_bytes": input_bytes,
        "output_bytes": output_bytes,
        "delta_bytes": output_bytes - input_bytes,
        "delta_pct": ((output_bytes - input_bytes) / input_bytes * 100.0)
        if input_bytes
        else 0.0,
        "compress_ms": compress_ms,
        "decompress_ms": decompress_ms,
        "memory_limit": MEMORY_LIMIT,
        "peak_memory_bytes": peak_memory_bytes,
        "peak_memory_mib": round(peak_memory_bytes / (1024 * 1024), 3)
        if peak_memory_bytes is not None
        else None,
        "telemetry": summarize_telemetry(summary),
    }


def alias_summary(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": row["name"],
        "family": row["family"],
        "corpus": row["corpus"],
        "role": row["role"],
        "lead_source": row["lead_source"],
        "lead_name": row["lead_name"],
        "prefix_probe": {
            "baseline_prefix_ge_4": row["baseline_prefix_ge_4"],
            "depth3_prefix_ge_4": row["depth3_prefix_ge_4"],
            "baseline_prefix_ge_5": row["baseline_prefix_ge_5"],
            "depth3_prefix_ge_5": row["depth3_prefix_ge_5"],
            "prefix_ge_5_delta_vs_depth2": row["prefix_ge_5_delta_vs_depth2"],
            "depth3_exact_hits": row["depth3_exact_hits"],
        },
    }


def input_result(input_group: dict[str, Any], temp: Path, exe: Path) -> dict[str, Any]:
    row = input_group["representative"]
    baseline = run_depth(row, BASELINE_DEPTH, temp, exe)
    followup = run_depth(row, FOLLOWUP_DEPTH, temp, exe)
    selected_delta = (
        followup["telemetry"]["selected_count"] - baseline["telemetry"]["selected_count"]
    )
    output_delta = followup["output_bytes"] - baseline["output_bytes"]
    promoted = followup["delta_bytes"] < 0 or selected_delta > 0
    return {
        "transformed_sha256": input_group["transformed_sha256"],
        "alias_count": len(input_group["aliases"]),
        "aliases": [alias_summary(alias) for alias in input_group["aliases"]],
        "representative_name": row["name"],
        "family": row["family"],
        "corpus": row["corpus"],
        "role": row["role"],
        "lead_source": row["lead_source"],
        "lead_name": row["lead_name"],
        "baseline_depth2": baseline,
        "followup_depth3": followup,
        "selected_delta_depth3_vs_depth2": selected_delta,
        "output_delta_depth3_vs_depth2": output_delta,
        "promotion_met": promoted,
    }


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    depth3_selected_rows = [
        row for row in results if row["followup_depth3"]["telemetry"]["selected_count"] > 0
    ]
    negative_rows = [row for row in results if row["followup_depth3"]["delta_bytes"] < 0]
    promoted_rows_count = sum(1 for row in results if row["promotion_met"])
    best = min(
        results,
        key=lambda row: (
            row["followup_depth3"]["delta_bytes"],
            row["followup_depth3"]["output_bytes"],
            row["representative_name"],
        ),
        default=None,
    )
    conclusion = (
        "Bounded lead depth-3 compression promoted at least one prefix-frontier row into selected spans or negative delta."
        if promoted_rows_count
        else "Bounded lead depth-3 compression did not turn selected-lead prefix movement into selected spans or negative delta."
    )
    return {
        "promoted_prefix_rows": len(results),
        "logical_alias_rows": sum(row["alias_count"] for row in results),
        "depth3_rows_with_selected_spans": len(depth3_selected_rows),
        "depth3_rows_with_negative_delta": len(negative_rows),
        "promotion_met_rows": promoted_rows_count,
        "total_depth3_selected_spans": sum(
            row["followup_depth3"]["telemetry"]["selected_count"] for row in results
        ),
        "best_case": best["representative_name"] if best else None,
        "best_case_delta_bytes": best["followup_depth3"]["delta_bytes"] if best else None,
        "best_case_selected_spans": best["followup_depth3"]["telemetry"]["selected_count"]
        if best
        else 0,
        "conclusion": conclusion,
    }


def build_report() -> dict[str, Any]:
    prefix_probe = load_json(PREFIX_PROBE_JSON)
    rows = promoted_rows(prefix_probe)
    inputs = physical_inputs(rows)
    exe = generate_results.build_release_binary()
    with tempfile.TemporaryDirectory() as tmp:
        temp = Path(tmp)
        results = [input_result(input_group, temp, exe) for input_group in inputs]
    return {
        "generated_by": "scripts/generate_lead_depth3_compression_followup.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "artifact_hashes": artifact_hashes(),
        "selected_manifest_sha256": selected_manifest_hash(),
        "environment": generate_results.environment_metadata(),
        "hasher": HASHER,
        "baseline_depth": BASELINE_DEPTH,
        "followup_depth": FOLLOWUP_DEPTH,
        "block_size": BLOCK_SIZE,
        "span_len": SPAN_LEN,
        "span_step": SPAN_STEP,
        "passes": PASSES,
        "memory_limit": MEMORY_LIMIT,
        "telemetry_limit": int(TELEMETRY_LIMIT),
        "logical_rows": [alias_summary(row) for row in rows],
        "results": results,
        "summary": summarize(results),
    }


def write_report(payload: dict[str, Any]) -> None:
    FOLLOWUP_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary = payload["summary"]
    lines = [
        "# Telomere Lead Depth-3 Compression Follow-Up",
        "",
        "Generated by `scripts/generate_lead_depth3_compression_followup.py` from the lead depth-3 prefix probe.",
        "This artifact tests whether selected-lead prefix movement becomes actual `.tlmr` v2 selected spans or negative delta.",
        "",
        f"Promoted physical inputs: `{summary['promoted_prefix_rows']}`.",
        f"Logical alias rows: `{summary['logical_alias_rows']}`.",
        f"Depth-3 rows with selected spans: `{summary['depth3_rows_with_selected_spans']}`.",
        f"Depth-3 rows with negative delta: `{summary['depth3_rows_with_negative_delta']}`.",
        f"Promotion-met rows: `{summary['promotion_met_rows']}`.",
        f"Total depth-3 selected spans: `{summary['total_depth3_selected_spans']}`.",
        "",
        "## Summary",
        "",
        summary["conclusion"],
        f"Best case: `{summary['best_case']}` delta `{summary['best_case_delta_bytes']}` bytes with `{summary['best_case_selected_spans']}` selected spans.",
        "",
        "## Follow-Up Rows",
        "",
        "| physical input | aliases | depth2 p5 | depth3 p5 | p5 delta | exact hits | depth2 output | depth3 output | depth3 delta | depth3 selected | depth3 candidates | compress ms | peak MiB | promotion |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in payload["results"]:
        prefix = row["aliases"][0]["prefix_probe"]
        depth2 = row["baseline_depth2"]
        depth3 = row["followup_depth3"]
        peak = depth3["peak_memory_mib"] if depth3["peak_memory_mib"] is not None else "-"
        lines.append(
            "| {name} | {aliases} | {baseline_p5} | {depth3_p5} | {p5_delta:+} | {exact} | "
            "{depth2_output} | {depth3_output} | {depth3_delta:+} | {selected} | "
            "{candidates} | {compress_ms} | {peak} | {promotion} |".format(
                name=row["representative_name"],
                aliases=row["alias_count"],
                baseline_p5=prefix["baseline_prefix_ge_5"],
                depth3_p5=prefix["depth3_prefix_ge_5"],
                p5_delta=prefix["prefix_ge_5_delta_vs_depth2"],
                exact=prefix["depth3_exact_hits"],
                depth2_output=depth2["output_bytes"],
                depth3_output=depth3["output_bytes"],
                depth3_delta=depth3["delta_bytes"],
                selected=depth3["telemetry"]["selected_count"],
                candidates=depth3["telemetry"]["candidate_count"],
                compress_ms=depth3["compress_ms"],
                peak=peak,
                promotion="yes" if row["promotion_met"] else "no",
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Promotion requires depth-3 selected spans or negative delta, not prefix-only movement.",
            "- Logical aliases with the same transformed input are deduplicated by transformed SHA-256.",
            "- The run set is intentionally bounded to rows promoted by `docs/LEAD_DEPTH3_PREFIX_PROBE.md`; broad depth-3 sweeps remain gated.",
            "- Roundtrip verification is performed by the CLI and an explicit decompression byte check.",
        ]
    )
    FOLLOWUP_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not FOLLOWUP_JSON.exists() or not FOLLOWUP_MD.exists():
        raise SystemExit("generated lead depth-3 compression follow-up files are missing")
    payload = load_json(FOLLOWUP_JSON)
    if payload.get("generated_by") != "scripts/generate_lead_depth3_compression_followup.py":
        raise SystemExit("lead_depth3_compression_followup.json has wrong generated_by marker")
    if payload.get("artifact_hashes") != artifact_hashes():
        raise SystemExit("lead_depth3_compression_followup.json artifact hashes are stale")
    if payload.get("selected_manifest_sha256") != selected_manifest_hash():
        raise SystemExit("lead_depth3_compression_followup.json selected manifest hash is stale")
    if len(payload.get("logical_rows", [])) != len(selected_manifest()):
        raise SystemExit("lead_depth3_compression_followup.json logical row count is stale")
    if len(payload.get("results", [])) != len(physical_inputs(promoted_rows(load_json(PREFIX_PROBE_JSON)))):
        raise SystemExit("lead_depth3_compression_followup.json result count is stale")
    text = FOLLOWUP_MD.read_text(encoding="utf-8")
    for phrase in (
        "Lead Depth-3 Compression Follow-Up",
        "selected-lead prefix movement",
        "Promotion requires depth-3 selected spans or negative delta",
        "deduplicated by transformed SHA-256",
        "broad depth-3 sweeps remain gated",
    ):
        if phrase not in text:
            raise SystemExit(f"LEAD_DEPTH3_COMPRESSION_FOLLOWUP.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate generated follow-up")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.check:
        check_report()
        return
    write_report(build_report())


if __name__ == "__main__":
    main()
