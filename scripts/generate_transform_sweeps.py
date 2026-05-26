#!/usr/bin/env python3
"""Generate reversible-transform research sweeps for Telomere."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import generate_results
import generate_sweeps


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
MEMORY_LIMIT = "100%"
TELEMETRY_LIMIT = "64"
TOKEN_MARKER = 0
STATIC_JSON_TOKENS = [
    b'"event":"order_update"',
    b'"status":"fulfilled"',
    b'"amount_cents":',
    b'"status":"queued"',
    b'"status":"paid"',
    b'"sku":"rx-',
    b'"id":',
]


@dataclass
class TransformOutput:
    data: bytes
    overhead_bytes: int
    metadata: dict[str, Any]


TRANSFORM_MATRIX: list[dict[str, Any]] = [
    {
        "name": "structured-identity-depth2",
        "transform": "identity",
        "corpus": "structured-json",
        "seed_depth": 2,
        "max_span_len": 8,
        "span_step": 1,
        "block_size": 4,
        "passes": 1,
        "note": "Structured JSON baseline through the transform harness.",
    },
    {
        "name": "structured-xor-prev-depth2",
        "transform": "xor-prev",
        "corpus": "structured-json",
        "seed_depth": 2,
        "max_span_len": 8,
        "span_step": 1,
        "block_size": 4,
        "passes": 1,
        "note": "Same-length reversible XOR residual transform.",
    },
    {
        "name": "structured-sub-prev-depth2",
        "transform": "sub-prev",
        "corpus": "structured-json",
        "seed_depth": 2,
        "max_span_len": 8,
        "span_step": 1,
        "block_size": 4,
        "passes": 1,
        "note": "Same-length reversible byte-difference residual transform.",
    },
    {
        "name": "structured-line-transpose-depth2",
        "transform": "line-transpose",
        "corpus": "structured-json",
        "seed_depth": 2,
        "max_span_len": 8,
        "span_step": 1,
        "block_size": 4,
        "passes": 1,
        "note": "Reversible row/column transpose over JSON lines with length metadata.",
    },
    {
        "name": "structured-static-token-depth2",
        "transform": "static-json-token",
        "corpus": "structured-json",
        "seed_depth": 2,
        "max_span_len": 8,
        "span_step": 1,
        "block_size": 4,
        "passes": 1,
        "note": "Static domain-token preconditioner; any byte reduction is transform gain unless selected spans appear.",
    },
]


def transform_manifest() -> list[dict[str, Any]]:
    fields = (
        "name",
        "transform",
        "corpus",
        "seed_depth",
        "max_span_len",
        "span_step",
        "block_size",
        "passes",
        "note",
    )
    return [{field: case[field] for field in fields} for case in TRANSFORM_MATRIX]


def transform_manifest_hash() -> str:
    payload = json.dumps(transform_manifest(), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def case_by_name(name: str) -> dict[str, Any]:
    for case in TRANSFORM_MATRIX:
        if case["name"] == name:
            return case
    raise KeyError(name)


def corpus_bytes(corpus: str) -> bytes:
    if corpus == "structured-json":
        return generate_results.structured_json_bytes()
    raise ValueError(corpus)


def apply_identity(data: bytes) -> TransformOutput:
    return TransformOutput(data=data, overhead_bytes=0, metadata={})


def invert_identity(data: bytes, _metadata: dict[str, Any]) -> bytes:
    return data


def apply_xor_prev(data: bytes) -> TransformOutput:
    if not data:
        return TransformOutput(data=b"", overhead_bytes=1, metadata={})
    out = bytearray([data[0]])
    for idx in range(1, len(data)):
        out.append(data[idx] ^ data[idx - 1])
    return TransformOutput(data=bytes(out), overhead_bytes=1, metadata={})


def invert_xor_prev(data: bytes, _metadata: dict[str, Any]) -> bytes:
    if not data:
        return b""
    out = bytearray([data[0]])
    for idx in range(1, len(data)):
        out.append(data[idx] ^ out[idx - 1])
    return bytes(out)


def apply_sub_prev(data: bytes) -> TransformOutput:
    if not data:
        return TransformOutput(data=b"", overhead_bytes=1, metadata={})
    out = bytearray([data[0]])
    for idx in range(1, len(data)):
        out.append((data[idx] - data[idx - 1]) & 0xFF)
    return TransformOutput(data=bytes(out), overhead_bytes=1, metadata={})


def invert_sub_prev(data: bytes, _metadata: dict[str, Any]) -> bytes:
    if not data:
        return b""
    out = bytearray([data[0]])
    for idx in range(1, len(data)):
        out.append((data[idx] + out[idx - 1]) & 0xFF)
    return bytes(out)


def apply_line_transpose(data: bytes) -> TransformOutput:
    lines = data.splitlines(keepends=True)
    lengths = [len(line) for line in lines]
    width = max(lengths, default=0)
    out = bytearray()
    for col in range(width):
        for line in lines:
            if col < len(line):
                out.append(line[col])
    overhead = 3 + 2 * len(lengths)
    return TransformOutput(
        data=bytes(out),
        overhead_bytes=overhead,
        metadata={"lengths": lengths},
    )


def invert_line_transpose(data: bytes, metadata: dict[str, Any]) -> bytes:
    lengths = list(metadata["lengths"])
    width = max(lengths, default=0)
    lines = [bytearray() for _ in lengths]
    cursor = 0
    for col in range(width):
        for row, length in enumerate(lengths):
            if col < length:
                lines[row].append(data[cursor])
                cursor += 1
    if cursor != len(data):
        raise ValueError("line transpose metadata did not consume transformed bytes")
    return b"".join(bytes(line) for line in lines)


def apply_static_json_token(data: bytes) -> TransformOutput:
    out = bytearray()
    pos = 0
    while pos < len(data):
        matched = False
        for token_id, token in enumerate(STATIC_JSON_TOKENS, start=1):
            if data.startswith(token, pos):
                out.extend((TOKEN_MARKER, token_id))
                pos += len(token)
                matched = True
                break
        if matched:
            continue
        byte = data[pos]
        if byte == TOKEN_MARKER:
            out.extend((TOKEN_MARKER, TOKEN_MARKER))
        else:
            out.append(byte)
        pos += 1
    return TransformOutput(data=bytes(out), overhead_bytes=1, metadata={})


def invert_static_json_token(data: bytes, _metadata: dict[str, Any]) -> bytes:
    out = bytearray()
    pos = 0
    while pos < len(data):
        byte = data[pos]
        if byte != TOKEN_MARKER:
            out.append(byte)
            pos += 1
            continue
        if pos + 1 >= len(data):
            raise ValueError("truncated token marker")
        token_id = data[pos + 1]
        if token_id == TOKEN_MARKER:
            out.append(TOKEN_MARKER)
        elif 1 <= token_id <= len(STATIC_JSON_TOKENS):
            out.extend(STATIC_JSON_TOKENS[token_id - 1])
        else:
            raise ValueError(f"unknown token id {token_id}")
        pos += 2
    return bytes(out)


def apply_transform(name: str, data: bytes) -> TransformOutput:
    if name == "identity":
        return apply_identity(data)
    if name == "xor-prev":
        return apply_xor_prev(data)
    if name == "sub-prev":
        return apply_sub_prev(data)
    if name == "line-transpose":
        return apply_line_transpose(data)
    if name == "static-json-token":
        return apply_static_json_token(data)
    raise ValueError(name)


def invert_transform(name: str, data: bytes, metadata: dict[str, Any]) -> bytes:
    if name == "identity":
        return invert_identity(data, metadata)
    if name == "xor-prev":
        return invert_xor_prev(data, metadata)
    if name == "sub-prev":
        return invert_sub_prev(data, metadata)
    if name == "line-transpose":
        return invert_line_transpose(data, metadata)
    if name == "static-json-token":
        return invert_static_json_token(data, metadata)
    raise ValueError(name)


def self_test_transforms() -> None:
    samples = [
        b"",
        b"\x00",
        b"\x00\x00quoted\x00marker",
        generate_results.structured_json_bytes(),
        generate_results.deterministic_bytes("transform-self-test", 257),
    ]
    for transform in {case["transform"] for case in TRANSFORM_MATRIX}:
        for sample in samples:
            transformed = apply_transform(transform, sample)
            restored = invert_transform(transform, transformed.data, transformed.metadata)
            if restored != sample:
                raise AssertionError(f"{transform} failed roundtrip self-test")


def summarize_telemetry(summary: dict[str, Any]) -> dict[str, Any]:
    telemetry = summary.get("engine_telemetry", {})
    return {
        "candidate_count": telemetry.get("candidate_count", 0),
        "selected_count": telemetry.get("selected_count", 0),
        "container_bytes": telemetry.get("container_bytes", 0),
        "literal_bytes": telemetry.get("literal_bytes", 0),
        "layer_count": len(telemetry.get("layers", [])),
    }


def run_case(case: dict[str, Any], temp: Path, exe: Path) -> dict[str, Any]:
    original = corpus_bytes(case["corpus"])
    transformed = apply_transform(case["transform"], original)
    if invert_transform(case["transform"], transformed.data, transformed.metadata) != original:
        raise RuntimeError(f"{case['name']}: transform did not roundtrip before compression")

    input_path = temp / f"{case['name']}.transformed"
    output_path = temp / f"{case['name']}.tlmr"
    restored_path = temp / f"{case['name']}.restored"
    input_path.write_bytes(transformed.data)
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

    generate_sweeps.run([str(exe), "decompress", str(output_path), str(restored_path), "--force"])
    restored_transform = restored_path.read_bytes()
    if restored_transform != transformed.data:
        raise RuntimeError(f"{case['name']}: decompressed transform bytes did not match")
    if invert_transform(case["transform"], restored_transform, transformed.metadata) != original:
        raise RuntimeError(f"{case['name']}: inverse transform did not recover original")

    tlmr_bytes = output_path.stat().st_size
    effective_bytes = tlmr_bytes + transformed.overhead_bytes
    original_bytes = len(original)
    return {
        "name": case["name"],
        "transform": case["transform"],
        "corpus": case["corpus"],
        "seed_depth": case["seed_depth"],
        "span_step": case["span_step"],
        "max_span_len": case["max_span_len"],
        "original_sha256": hashlib.sha256(original).hexdigest(),
        "transformed_sha256": hashlib.sha256(transformed.data).hexdigest(),
        "original_bytes": original_bytes,
        "transformed_bytes": len(transformed.data),
        "transform_overhead_bytes": transformed.overhead_bytes,
        "tlmr_bytes": tlmr_bytes,
        "effective_bytes": effective_bytes,
        "effective_delta_bytes": effective_bytes - original_bytes,
        "effective_delta_pct": ((effective_bytes - original_bytes) / original_bytes * 100.0)
        if original_bytes
        else 0.0,
        "compress_ms": compress_ms,
        "peak_memory_bytes": peak_memory_bytes,
        "peak_memory_mib": round(peak_memory_bytes / (1024 * 1024), 3)
        if peak_memory_bytes is not None
        else None,
        "telemetry": summarize_telemetry(summary),
    }


def write_artifacts(cases: list[dict[str, Any]], results: list[dict[str, Any]]) -> None:
    payload = {
        "generated_by": "scripts/generate_transform_sweeps.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "transform_manifest_sha256": transform_manifest_hash(),
        "transform_matrix": transform_manifest(),
        "selected_case_names": [case["name"] for case in cases],
        "environment": generate_results.environment_metadata(),
        "results": results,
    }
    (DOCS / "transform_sweeps.json").write_text(json.dumps(payload, indent=2) + "\n")

    lines = [
        "# Telomere Transform Sweeps",
        "",
        "Generated by `scripts/generate_transform_sweeps.py` from release-binary CLI runs.",
        "These experiments measure reversible preconditioners before `.tlmr` v2 compression.",
        "",
        f"Transform manifest SHA-256: `{transform_manifest_hash()}`.",
        "",
        "| case | transform | seed depth | span | step | original bytes | transformed bytes | overhead | tlmr bytes | effective bytes | effective delta | selected | candidates | compress ms | peak MiB |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in results:
        display_row = dict(row)
        display_row["peak_memory_mib"] = (
            row["peak_memory_mib"] if row["peak_memory_mib"] is not None else "-"
        )
        lines.append(
            "| {name} | {transform} | {seed_depth} | {max_span_len} | {span_step} | {original_bytes} | {transformed_bytes} | "
            "{transform_overhead_bytes} | {tlmr_bytes} | {effective_bytes} | {effective_delta_pct:+.2f}% | "
            "{selected_count} | {candidate_count} | {compress_ms} | {peak_memory_mib} |".format(
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
            "- Identity, XOR-residual, subtraction-residual, and line-transpose are generic reversible transforms. They test whether cheap byte rearrangements create seed-addressable spans.",
            "- Static JSON tokens are a domain dictionary preconditioner. If they reduce effective bytes without selected spans, that is transform-only gain, not evidence of generative seed matching.",
            "- Any production transform would need a versioned `.tlmr` format extension before it could be treated as part of the codec contract.",
        ]
    )
    (DOCS / "TRANSFORM_SWEEPS.md").write_text("\n".join(lines) + "\n")


def check_artifacts() -> None:
    self_test_transforms()
    json_path = DOCS / "transform_sweeps.json"
    md_path = DOCS / "TRANSFORM_SWEEPS.md"
    if not json_path.exists() or not md_path.exists():
        raise SystemExit("generated transform-sweep files are missing")
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    if payload.get("generated_by") != "scripts/generate_transform_sweeps.py":
        raise SystemExit("transform_sweeps.json has wrong generated_by marker")
    if payload.get("transform_manifest_sha256") != transform_manifest_hash():
        raise SystemExit("transform_sweeps.json transform manifest hash is stale")
    expected_names = [case["name"] for case in TRANSFORM_MATRIX]
    result_names = [result["name"] for result in payload.get("results", [])]
    if result_names != expected_names:
        raise SystemExit("transform_sweeps.json does not contain the full transform matrix")
    text = md_path.read_text(encoding="utf-8")
    missing = [name for name in expected_names if name not in text]
    if missing:
        raise SystemExit(f"TRANSFORM_SWEEPS.md missing cases: {', '.join(missing)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", action="append", help="run one named transform sweep case; repeatable")
    parser.add_argument("--list", action="store_true", help="list transform sweep cases and exit")
    parser.add_argument("--manifest-sha", action="store_true", help="print transform manifest hash and exit")
    parser.add_argument("--check", action="store_true", help="validate generated transform sweeps")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.list:
        for case in TRANSFORM_MATRIX:
            print(case["name"])
        return
    if args.manifest_sha:
        print(transform_manifest_hash())
        return
    if args.check:
        check_artifacts()
        return

    self_test_transforms()

    if args.case:
        try:
            cases = [case_by_name(name) for name in args.case]
        except KeyError as exc:
            raise SystemExit(f"unknown transform sweep case: {exc.args[0]}") from exc
    else:
        cases = TRANSFORM_MATRIX

    exe = generate_results.build_release_binary()
    with tempfile.TemporaryDirectory() as tmp:
        temp = Path(tmp)
        results = [run_case(case, temp, exe) for case in cases]
    write_artifacts(cases, results)


if __name__ == "__main__":
    main()
