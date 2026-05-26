#!/usr/bin/env python3
"""Generate opt-in deep-search Telomere sweep artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import generate_results
import generate_sweeps


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
MEMORY_LIMIT = "100%"
TELEMETRY_LIMIT = "64"
THREE_BYTE_SEED = b"\x01\x00\x00"
STRUCTURED_JSON_LEN = len(generate_results.structured_json_bytes())


DEEP_SWEEP_MATRIX: list[dict[str, Any]] = [
    {
        "name": "seed3-planted-depth2",
        "group": "seed-depth-3",
        "corpus": "planted-seed3",
        "span_len": 8,
        "input_bytes": 1024,
        "passes": 1,
        "block_size": 4,
        "span_step": 4,
        "max_span_len": 8,
        "seed_depth": 2,
        "hasher": "sha256",
        "note": "Control run: a three-byte-seed planted span searched only through depth 2.",
    },
    {
        "name": "seed3-planted-depth3",
        "group": "seed-depth-3",
        "corpus": "planted-seed3",
        "span_len": 8,
        "input_bytes": 1024,
        "passes": 1,
        "block_size": 4,
        "span_step": 4,
        "max_span_len": 8,
        "seed_depth": 3,
        "hasher": "sha256",
        "note": "Bounded depth-3 proof: the same planted span becomes searchable with a three-byte seed.",
    },
    {
        "name": "structured-json-depth3-span8-step1-pass1",
        "group": "seed-depth-3",
        "corpus": "structured-json",
        "span_len": 8,
        "input_bytes": STRUCTURED_JSON_LEN,
        "passes": 1,
        "block_size": 4,
        "span_step": 1,
        "max_span_len": 8,
        "seed_depth": 3,
        "hasher": "sha256",
        "note": "Non-planted structured JSON searched at depth 3 with byte-step starts.",
    },
]


def deep_manifest() -> list[dict[str, Any]]:
    fields = (
        "name",
        "group",
        "corpus",
        "span_len",
        "input_bytes",
        "passes",
        "block_size",
        "span_step",
        "max_span_len",
        "seed_depth",
        "hasher",
        "note",
    )
    return [{field: case[field] for field in fields} for case in DEEP_SWEEP_MATRIX]


def deep_manifest_hash() -> str:
    payload = json.dumps(deep_manifest(), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def case_by_name(name: str) -> dict[str, Any]:
    for case in DEEP_SWEEP_MATRIX:
        if case["name"] == name:
            return case
    raise KeyError(name)


def write_input(case: dict[str, Any], temp: Path) -> Path:
    path = temp / f"{case['name']}.bin"
    if case["corpus"] == "planted-seed3":
        span = hashlib.sha256(THREE_BYTE_SEED).digest()[: case["span_len"]]
        repetitions = int(case["input_bytes"]) // len(span)
        data = (span * repetitions)[: int(case["input_bytes"])]
    elif case["corpus"] == "structured-json":
        data = generate_results.structured_json_bytes()
    else:
        raise ValueError(case["corpus"])
    path.write_bytes(data)
    return path


def summarize_telemetry(summary: dict[str, Any]) -> dict[str, Any]:
    telemetry = summary.get("engine_telemetry", {})
    layers = telemetry.get("layers", [])
    return {
        "candidate_count": telemetry.get("candidate_count", 0),
        "selected_count": telemetry.get("selected_count", 0),
        "literal_bytes": telemetry.get("literal_bytes", 0),
        "bundle_count": telemetry.get("bundle_count", 0),
        "layer_count": len(layers),
        "layer_payload_bytes": [layer.get("payload_bytes", 0) for layer in layers],
        "layer_selected_counts": [layer.get("selected_count", 0) for layer in layers],
        "stop_reason": telemetry.get("stop_reason", ""),
        "container_bytes": telemetry.get("container_bytes", 0),
    }


def run_case(case: dict[str, Any], temp: Path, exe: Path) -> dict[str, Any]:
    input_path = write_input(case, temp)
    output_path = temp / f"{case['name']}.tlmr"
    restored_path = temp / f"{case['name']}.restored"
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
        case["hasher"],
        "--block-size",
        str(case["block_size"]),
        "--span-step",
        str(case["span_step"]),
        "--seed-depth",
        str(case["seed_depth"]),
        "--passes",
        str(case["passes"]),
        "--max-span-len",
        str(case["max_span_len"]),
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
    compress_ms = round((time.perf_counter() - started) * 1000, 3)
    summary = json.loads(proc.stdout)

    started = time.perf_counter()
    generate_sweeps.run([str(exe), "decompress", str(output_path), str(restored_path), "--force"])
    decompress_ms = round((time.perf_counter() - started) * 1000, 3)
    if restored_path.read_bytes() != input_path.read_bytes():
        raise RuntimeError(f"{case['name']}: decompressed bytes did not match input")

    input_bytes = input_path.stat().st_size
    output_bytes = output_path.stat().st_size
    return {
        "name": case["name"],
        "group": case["group"],
        "span_len": case["span_len"],
        "span_step": case["span_step"],
        "seed_depth": case["seed_depth"],
        "passes": case["passes"],
        "input_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
        "output_sha256": hashlib.sha256(output_path.read_bytes()).hexdigest(),
        "input_bytes": input_bytes,
        "output_bytes": output_bytes,
        "delta_bytes": output_bytes - input_bytes,
        "delta_pct": ((output_bytes - input_bytes) / input_bytes * 100.0)
        if input_bytes
        else 0.0,
        "compress_ms": compress_ms,
        "throughput_mib_s": round(
            (input_bytes / (1024 * 1024)) / (compress_ms / 1000),
            3,
        )
        if compress_ms > 0
        else 0.0,
        "decompress_ms": decompress_ms,
        "memory_limit": MEMORY_LIMIT,
        "peak_memory_bytes": peak_memory_bytes,
        "peak_memory_mib": round(peak_memory_bytes / (1024 * 1024), 3)
        if peak_memory_bytes is not None
        else None,
        "telemetry": summarize_telemetry(summary),
    }


def write_artifacts(cases: list[dict[str, Any]], results: list[dict[str, Any]]) -> None:
    payload = {
        "generated_by": "scripts/generate_deep_sweeps.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "deep_manifest_sha256": deep_manifest_hash(),
        "deep_sweep_matrix": deep_manifest(),
        "selected_case_names": [case["name"] for case in cases],
        "environment": generate_results.environment_metadata(),
        "results": results,
    }
    (DOCS / "deep_sweeps.json").write_text(json.dumps(payload, indent=2) + "\n")

    lines = [
        "# Telomere Deep Search Sweeps",
        "",
        "Generated by `scripts/generate_deep_sweeps.py` from opt-in release-binary CLI runs.",
        "These cases are intentionally outside the default sweep because depth 3 is expensive.",
        "",
        f"Deep manifest SHA-256: `{deep_manifest_hash()}`.",
        "",
        "| case | group | span | step | seed depth | passes | input bytes | output bytes | delta bytes | delta | selected | candidates | compress ms | MiB/s | peak MiB | memory limit |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in results:
        display_row = dict(row)
        display_row["peak_memory_mib"] = (
            row["peak_memory_mib"] if row["peak_memory_mib"] is not None else "-"
        )
        lines.append(
            "| {name} | {group} | {span_len} | {span_step} | {seed_depth} | {passes} | {input_bytes} | {output_bytes} | "
            "{delta_bytes:+} | {delta_pct:+.2f}% | {selected_count} | {candidate_count} | {compress_ms} | {throughput_mib_s} | {peak_memory_mib} | {memory_limit} |".format(
                selected_count=row["telemetry"]["selected_count"],
                candidate_count=row["telemetry"]["candidate_count"],
                **display_row,
            )
        )

    lines.extend(
        [
            "",
            "Interpretation:",
            "",
            "- The depth-3 planted control isolates the compute premise: a span generated by a three-byte seed should bloat at depth 2 and become selectable at depth 3.",
            "- The structured depth-3 control asks whether simply searching farther finds seed-addressable spans in generated JSON.",
            "- These rows are evidence for economics and falsification. They are not normal unit-test inputs and should be regenerated deliberately.",
        ]
    )
    (DOCS / "DEEP_SWEEPS.md").write_text("\n".join(lines) + "\n")


def check_artifacts() -> None:
    json_path = DOCS / "deep_sweeps.json"
    md_path = DOCS / "DEEP_SWEEPS.md"
    if not json_path.exists() or not md_path.exists():
        raise SystemExit("generated deep-sweep files are missing")
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    if payload.get("generated_by") != "scripts/generate_deep_sweeps.py":
        raise SystemExit("deep_sweeps.json has wrong generated_by marker")
    if payload.get("deep_manifest_sha256") != deep_manifest_hash():
        raise SystemExit("deep_sweeps.json deep manifest hash is stale")
    expected_names = [case["name"] for case in DEEP_SWEEP_MATRIX]
    result_names = [result["name"] for result in payload.get("results", [])]
    if result_names != expected_names:
        raise SystemExit("deep_sweeps.json does not contain the full deep sweep matrix")
    text = md_path.read_text(encoding="utf-8")
    missing = [name for name in expected_names if name not in text]
    if missing:
        raise SystemExit(f"DEEP_SWEEPS.md missing cases: {', '.join(missing)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", action="append", help="run one named deep sweep case; repeatable")
    parser.add_argument("--list", action="store_true", help="list deep sweep case names and exit")
    parser.add_argument("--manifest-sha", action="store_true", help="print deep sweep manifest hash and exit")
    parser.add_argument("--check", action="store_true", help="validate generated deep sweeps without running them")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.list:
        for case in DEEP_SWEEP_MATRIX:
            print(case["name"])
        return
    if args.manifest_sha:
        print(deep_manifest_hash())
        return
    if args.check:
        check_artifacts()
        return

    if args.case:
        try:
            cases = [case_by_name(name) for name in args.case]
        except KeyError as exc:
            raise SystemExit(f"unknown deep sweep case: {exc.args[0]}") from exc
    else:
        cases = DEEP_SWEEP_MATRIX

    exe = generate_results.build_release_binary()
    with tempfile.TemporaryDirectory() as tmp:
        temp = Path(tmp)
        results = [run_case(case, temp, exe) for case in cases]
    write_artifacts(cases, results)


if __name__ == "__main__":
    main()
