#!/usr/bin/env python3
"""Generate recursive v2 structured-fixture evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import generate_results


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
REPORT_JSON = DOCS / "recursive_structured_fixtures.json"
REPORT_MD = DOCS / "RECURSIVE_STRUCTURED_FIXTURES.md"
GENERATED_BY = "scripts/generate_recursive_structured_fixtures.py"

SOURCE_PATHS = {
    "format_doc_sha256": DOCS / "FORMAT.md",
    "results_sha256": DOCS / "results.json",
    "sweeps_sha256": DOCS / "sweeps.json",
    "mechanism_experiment_ranking_sha256": DOCS / "mechanism_experiment_ranking.json",
    "streaming_engine_sha256": ROOT / "src" / "streaming.rs",
    "v2_format_sha256": ROOT / "src" / "tlmr_v2.rs",
    "streaming_tests_sha256": ROOT / "tests" / "streaming.rs",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_artifact_hashes() -> dict[str, str]:
    return {name: sha256_path(path) for name, path in SOURCE_PATHS.items()}


def planted_span(span_len: int = 8) -> bytes:
    return hashlib.sha256(b"\x00").digest()[:span_len]


def csv_bytes() -> bytes:
    lines = ["case_id,corpus,span_len,seed_depth,status,delta_bytes"]
    for idx in range(240):
        status = ("queued", "literal", "selected", "verified")[idx % 4]
        lines.append(
            f"case-{idx:04d},csv-{idx % 17:02d},{4 + (idx % 5) * 4},"
            f"{1 + idx % 3},{status},{(idx * 41) % 1301 - 650}"
        )
    return ("\n".join(lines) + "\n").encode("utf-8")


def http_transcript_bytes() -> bytes:
    blocks: list[str] = []
    for idx in range(160):
        blocks.extend(
            [
                f"GET /v2/cases/{idx:04d}/spans/{idx % 19:02d} HTTP/1.1",
                f"Host: fixture-{idx % 11:02d}.example.test",
                f"X-Seed-Depth: {1 + idx % 3}",
                f"X-Span-Len: {4 + (idx % 5) * 4}",
                "Accept: application/json",
                "",
                "HTTP/1.1 200 OK",
                "Content-Type: application/json",
                f"X-Case-Status: {('literal', 'candidate', 'selected', 'verified')[idx % 4]}",
                "",
            ]
        )
    return ("\r\n".join(blocks) + "\r\n").encode("utf-8")


def fixture_manifest() -> list[dict[str, Any]]:
    return [
        {
            "name": "planted-offset-pass2-control",
            "family": "offset-control",
            "role": "planted-offset-control",
            "promotion_eligible": False,
            "passes": [1, 2, 3],
            "data_hex": (b"\xAA" + planted_span() * 128).hex(),
            "block_size": 4,
            "max_span_len": 8,
            "span_step": 4,
            "seed_depth": 1,
            "note": "Known positive control: a literal wrapper shifts an off-grid planted span stream onto the second-pass grid.",
        },
        {
            "name": "aligned-planted-pass1-control",
            "family": "aligned-control",
            "role": "planted-control",
            "promotion_eligible": False,
            "passes": [1, 2],
            "data_hex": (planted_span() * 128).hex(),
            "block_size": 4,
            "max_span_len": 8,
            "span_step": 4,
            "seed_depth": 1,
            "note": "Positive first-pass control; recursion should not claim extra gain after the first selected layer.",
        },
        {
            "name": "structured-json-recursive",
            "family": "json",
            "role": "ordinary-structured",
            "promotion_eligible": True,
            "passes": [1, 2],
            "data_hex": generate_results.structured_json_bytes().hex(),
            "block_size": 4,
            "max_span_len": 16,
            "span_step": 1,
            "seed_depth": 1,
            "note": "Generated structured JSON control with byte-step starts and two recursive passes.",
        },
        {
            "name": "structured-csv-recursive",
            "family": "csv",
            "role": "ordinary-structured",
            "promotion_eligible": True,
            "passes": [1, 2],
            "data_hex": csv_bytes().hex(),
            "block_size": 4,
            "max_span_len": 16,
            "span_step": 1,
            "seed_depth": 1,
            "note": "Generated structured CSV control with byte-step starts and two recursive passes.",
        },
        {
            "name": "structured-http-recursive",
            "family": "http",
            "role": "ordinary-structured",
            "promotion_eligible": True,
            "passes": [1, 2],
            "data_hex": http_transcript_bytes().hex(),
            "block_size": 4,
            "max_span_len": 16,
            "span_step": 1,
            "seed_depth": 1,
            "note": "Generated structured HTTP transcript control with byte-step starts and two recursive passes.",
        },
    ]


def manifest_for_hash() -> list[dict[str, Any]]:
    return [
        {
            key: value
            for key, value in fixture.items()
            if key != "data_hex"
        }
        | {
            "input_bytes": len(bytes.fromhex(fixture["data_hex"])),
            "input_sha256": sha256_bytes(bytes.fromhex(fixture["data_hex"])),
        }
        for fixture in fixture_manifest()
    ]


def fixture_manifest_hash() -> str:
    payload = json.dumps(manifest_for_hash(), sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )


def cli_exe() -> Path:
    run(["cargo", "build", "--quiet"])
    exe = ROOT / "target" / "debug" / ("telomere.exe" if os.name == "nt" else "telomere")
    if not exe.exists():
        raise FileNotFoundError(f"expected CLI binary at {exe}")
    return exe


def summarize_telemetry(summary: dict[str, Any]) -> dict[str, Any]:
    telemetry = summary.get("engine_telemetry", {})
    layers = telemetry.get("layers", [])
    return {
        "layer_count": len(layers),
        "layer_payload_bytes": [layer.get("payload_bytes", 0) for layer in layers],
        "layer_selected_counts": [layer.get("selected_count", 0) for layer in layers],
        "layer_literal_bytes": [layer.get("literal_bytes", 0) for layer in layers],
        "selected_count": telemetry.get("selected_count", 0),
        "candidate_count": telemetry.get("candidate_count", 0),
        "literal_bytes": telemetry.get("literal_bytes", 0),
        "container_bytes": telemetry.get("container_bytes", 0),
        "stop_reason": telemetry.get("stop_reason", ""),
    }


def run_fixture_pass(
    fixture: dict[str, Any], pass_count: int, temp: Path, exe: Path
) -> dict[str, Any]:
    input_path = temp / f"{fixture['name']}.bin"
    output_path = temp / f"{fixture['name']}-pass{pass_count}.tlmr"
    restored_path = temp / f"{fixture['name']}-pass{pass_count}.restored"
    data = bytes.fromhex(fixture["data_hex"])
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
        "sha256",
        "--block-size",
        str(fixture["block_size"]),
        "--span-step",
        str(fixture["span_step"]),
        "--seed-depth",
        str(fixture["seed_depth"]),
        "--passes",
        str(pass_count),
        "--max-span-len",
        str(fixture["max_span_len"]),
        "--memory-limit",
        "100%",
        "--json",
        "--telemetry-limit",
        "64",
        "--verify",
        "--force",
    ]
    started = time.perf_counter()
    proc = run(cmd)
    compress_ms = round((time.perf_counter() - started) * 1000, 3)
    summary = json.loads(proc.stdout)

    run([str(exe), "decompress", str(output_path), str(restored_path), "--force"])
    decoded_exact = restored_path.read_bytes() == data
    output_bytes = output_path.stat().st_size
    return {
        "passes": pass_count,
        "output_bytes": output_bytes,
        "delta_bytes": output_bytes - len(data),
        "delta_pct": round((output_bytes - len(data)) / len(data) * 100, 4),
        "decoded_exact": decoded_exact,
        "output_sha256": sha256_path(output_path),
        "compress_ms": compress_ms,
        "telemetry": summarize_telemetry(summary),
    }


def analyze_fixture(fixture: dict[str, Any], temp: Path, exe: Path) -> dict[str, Any]:
    data = bytes.fromhex(fixture["data_hex"])
    runs = [run_fixture_pass(fixture, passes, temp, exe) for passes in fixture["passes"]]
    baseline = runs[0]
    best = min(runs, key=lambda run_row: run_row["output_bytes"])
    later_runs = [row for row in runs if row["passes"] > baseline["passes"]]
    later_selected = any(
        any(count > 0 for count in row["telemetry"]["layer_selected_counts"][1:])
        for row in later_runs
    )
    later_smaller_than_pass1 = any(
        row["output_bytes"] < baseline["output_bytes"] for row in later_runs
    )
    later_negative_vs_input = any(row["delta_bytes"] < 0 for row in later_runs)
    return {
        "name": fixture["name"],
        "family": fixture["family"],
        "role": fixture["role"],
        "promotion_eligible": fixture["promotion_eligible"],
        "note": fixture["note"],
        "input_bytes": len(data),
        "input_sha256": sha256_bytes(data),
        "block_size": fixture["block_size"],
        "max_span_len": fixture["max_span_len"],
        "span_step": fixture["span_step"],
        "seed_depth": fixture["seed_depth"],
        "runs": runs,
        "best_passes": best["passes"],
        "best_output_bytes": best["output_bytes"],
        "best_delta_bytes": best["delta_bytes"],
        "pass1_output_bytes": baseline["output_bytes"],
        "later_selected": later_selected,
        "later_smaller_than_pass1": later_smaller_than_pass1,
        "later_negative_vs_input": later_negative_vs_input,
        "all_decoded_exact": all(row["decoded_exact"] for row in runs),
    }


def build_rows() -> list[dict[str, Any]]:
    exe = cli_exe()
    with tempfile.TemporaryDirectory(prefix="telomere-recursive-fixtures-") as tmp:
        temp = Path(tmp)
        return [analyze_fixture(fixture, temp, exe) for fixture in fixture_manifest()]


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ordinary_success = {
        row["family"]
        for row in rows
        if row["promotion_eligible"]
        and row["later_selected"]
        and row["later_smaller_than_pass1"]
        and row["later_negative_vs_input"]
    }
    offset_success = {
        row["family"]
        for row in rows
        if row["role"] == "planted-offset-control"
        and row["later_selected"]
        and row["later_smaller_than_pass1"]
    }
    first_pass_control_success = {
        row["family"]
        for row in rows
        if row["role"] == "planted-control" and row["best_delta_bytes"] < 0
    }
    all_decoded = all(row["all_decoded_exact"] for row in rows)
    promotion_met = len(ordinary_success) >= 2 and all_decoded
    if promotion_met:
        claim_level = "recursive_gain_replicated_on_structured_fixtures"
    elif offset_success and not ordinary_success:
        claim_level = "recursive_gain_only_in_planted_offset_controls"
    else:
        claim_level = "recursive_structured_fixtures_not_promoted"
    stop_reasons = []
    if len(ordinary_success) < 2:
        stop_reasons.append("fewer than two ordinary structured fixture families have later-layer wins")
    if offset_success and len(ordinary_success) < 2:
        stop_reasons.append("later-layer gain remains isolated to planted offset controls")
    if not all_decoded:
        stop_reasons.append("one or more recursive fixture outputs failed decode verification")
    return {
        "fixture_count": len(rows),
        "ordinary_fixture_count": sum(1 for row in rows if row["promotion_eligible"]),
        "ordinary_later_win_families": len(ordinary_success),
        "ordinary_later_win_family_names": sorted(ordinary_success),
        "planted_offset_later_win_families": len(offset_success),
        "planted_offset_later_win_family_names": sorted(offset_success),
        "first_pass_control_win_families": len(first_pass_control_success),
        "first_pass_control_win_family_names": sorted(first_pass_control_success),
        "all_decoded_exact": all_decoded,
        "promotion_met": promotion_met,
        "claim_level": claim_level,
        "stop_reason": "; ".join(stop_reasons) if stop_reasons else "promotion gate met",
        "conclusion": (
            "Recursive v2 passes produced independent structured later-layer wins."
            if promotion_met
            else "Recursive v2 later-layer gains remain unpromoted outside planted/alignment controls."
        ),
    }


def build_report() -> dict[str, Any]:
    rows = build_rows()
    return {
        "generated_by": GENERATED_BY,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "source_artifact_hashes": source_artifact_hashes(),
        "fixture_manifest_sha256": fixture_manifest_hash(),
        "fixture_manifest": manifest_for_hash(),
        "summary": summarize(rows),
        "fixtures": rows,
    }


def write_report(payload: dict[str, Any]) -> None:
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary = payload["summary"]
    lines = [
        "# Telomere Recursive Structured Fixtures",
        "",
        f"Generated by `{GENERATED_BY}`.",
        "This is a recursive v2 fixture artifact built from real CLI compression/decompression runs.",
        "It is not evidence for open-ended recursive convergence unless ordinary structured families pass the promotion gate.",
        "",
        "## Summary",
        "",
        f"- Fixtures: `{summary['fixture_count']}`",
        f"- Ordinary structured fixtures: `{summary['ordinary_fixture_count']}`",
        f"- Ordinary later-win families: `{summary['ordinary_later_win_families']}`",
        f"- Planted offset later-win families: `{summary['planted_offset_later_win_families']}`",
        f"- First-pass control win families: `{summary['first_pass_control_win_families']}`",
        f"- All decoded exactly: `{summary['all_decoded_exact']}`",
        f"- Promotion met: `{summary['promotion_met']}`",
        f"- Claim level: `{summary['claim_level']}`",
        "",
        summary["conclusion"],
        "",
        "## Promotion Gate",
        "",
        "- At least two ordinary, non-offset structured fixture families must produce smaller verified later layers after v2 layer metadata is charged.",
        "- Planted offset controls are diagnostic only and cannot promote recursion.",
        "- Every emitted file must decompress exactly.",
        "- Later-layer wins must survive at the container level, not merely inside an uncharged layer payload.",
        "",
        "## Fixture Results",
        "",
        "| fixture | role | pass1 bytes | best pass | best bytes | later selected | later smaller | decoded |",
        "| --- | --- | ---: | ---: | ---: | --- | --- | --- |",
    ]
    for row in payload["fixtures"]:
        lines.append(
            f"| `{row['name']}` | `{row['role']}` | {row['pass1_output_bytes']} | "
            f"{row['best_passes']} | {row['best_output_bytes']} | "
            f"`{row['later_selected']}` | `{row['later_smaller_than_pass1']}` | "
            f"`{row['all_decoded_exact']}` |"
        )
    lines.extend(
        [
            "",
            "## Layer Details",
            "",
            "| fixture | passes | output bytes | layer selected counts | stop reason |",
            "| --- | ---: | ---: | --- | --- |",
        ]
    )
    for row in payload["fixtures"]:
        for run_row in row["runs"]:
            layer_counts = ",".join(
                str(count) for count in run_row["telemetry"]["layer_selected_counts"]
            )
            lines.append(
                f"| `{row['name']}` | {run_row['passes']} | {run_row['output_bytes']} | "
                f"`{layer_counts}` | `{run_row['telemetry']['stop_reason']}` |"
            )
    lines.extend(["", "## Stop Rule", ""])
    lines.append(f"- Stop reason: {summary['stop_reason']}.")
    lines.append(
        "- Do not generalize recursive gains if later layers help only planted offset controls."
    )
    lines.extend(["", "## Source Artifacts", ""])
    for key, value in payload["source_artifact_hashes"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.append(f"- `fixture_manifest_sha256`: `{payload['fixture_manifest_sha256']}`")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def check_report() -> None:
    if not REPORT_JSON.exists() or not REPORT_MD.exists():
        raise SystemExit("generated recursive structured fixture files are missing")
    payload = load_json(REPORT_JSON)
    if payload.get("generated_by") != GENERATED_BY:
        raise SystemExit("recursive_structured_fixtures.json has wrong generated_by marker")
    if payload.get("source_artifact_hashes") != source_artifact_hashes():
        raise SystemExit("recursive structured fixture source hashes are stale")
    if payload.get("fixture_manifest_sha256") != fixture_manifest_hash():
        raise SystemExit("recursive structured fixture manifest is stale")
    expected_rows = len(fixture_manifest())
    if len(payload.get("fixtures", [])) != expected_rows:
        raise SystemExit("recursive structured fixture matrix is incomplete")
    if not all(row.get("all_decoded_exact") for row in payload.get("fixtures", [])):
        raise SystemExit("recursive structured fixture outputs must decode exactly")
    summary = payload.get("summary", {})
    if summary.get("promotion_met") and summary.get("ordinary_later_win_families", 0) < 2:
        raise SystemExit("recursive structured fixture promotion needs two ordinary families")
    text = REPORT_MD.read_text(encoding="utf-8")
    for phrase in (
        "Telomere Recursive Structured Fixtures",
        f"Generated by `{GENERATED_BY}`",
        "real CLI compression/decompression runs",
        "not evidence for open-ended recursive convergence",
        "Promotion Gate",
        "Planted offset controls are diagnostic only",
        "Stop Rule",
    ):
        if phrase not in text:
            raise SystemExit(f"RECURSIVE_STRUCTURED_FIXTURES.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate generated recursive structured fixture report",
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
