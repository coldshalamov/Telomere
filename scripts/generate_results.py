#!/usr/bin/env python3
"""Generate target/generated-docs/results.json and docs/RESULTS.md from real CLI runs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
RESULTS_JSON = ROOT / "target" / "generated-docs" / "results.json"


CASE_MATRIX: list[dict[str, Any]] = [
    {
        "name": "deterministic-bytes",
        "kind": "null-ordinary",
        "corpus": "deterministic-bytes",
        "engine": "brute-force",
        "format": "v1",
        "hasher": "blake3",
        "block_size": 4,
        "seed_depth": 1,
        "passes": 1,
        "max_span_len": None,
        "expected": "bloat",
        "note": "`deterministic-bytes` is ordinary non-planted data and is expected to bloat at seed depth 1.",
    },
    {
        "name": "planted-sha256-arity2",
        "kind": "mechanism-planted",
        "corpus": "planted-sha256-arity2",
        "engine": "brute-force",
        "format": "v1",
        "hasher": "sha256",
        "block_size": 2,
        "seed_depth": 1,
        "passes": 1,
        "max_span_len": None,
        "expected": "negative",
        "note": "`planted-sha256-arity2` repeats `SHA256([0x00])[0..4]` spans; it proves v1 can produce negative delta when short seeds are deliberately present.",
    },
    {
        "name": "streaming-planted-span4-control",
        "kind": "arity-planted",
        "corpus": "planted-span4-full",
        "engine": "streaming",
        "format": "v2",
        "hasher": "sha256",
        "block_size": 4,
        "seed_depth": 1,
        "passes": 1,
        "max_span_len": 4,
        "expected": "negative",
        "note": "`streaming-planted-span4-control` plants arity-1 generated 4-byte spans; corrected v2 fixed-span records are emitted when their compact encoding beats literals.",
    },
    {
        "name": "indexed-planted-span8",
        "kind": "mechanism-planted",
        "corpus": "planted-span8-full",
        "engine": "indexed",
        "format": "v2",
        "hasher": "sha256",
        "block_size": 4,
        "seed_depth": 1,
        "passes": 1,
        "max_span_len": 8,
        "expected": "negative",
        "note": "`indexed-planted-span8` builds an exact-prefix index and uses `.tlmr` v2 indexed lookup on planted 8-byte spans.",
    },
    {
        "name": "streaming-planted-span8",
        "kind": "mechanism-planted",
        "corpus": "planted-span8-full",
        "engine": "streaming",
        "format": "v2",
        "hasher": "sha256",
        "block_size": 4,
        "seed_depth": 1,
        "passes": 1,
        "max_span_len": 8,
        "expected": "negative",
        "note": "`streaming-planted-span8` uses the CPU stratified target-span streaming matcher on the same planted 8-byte corpus.",
    },
    {
        "name": "streaming-planted-span12",
        "kind": "arity-planted",
        "corpus": "planted-span12-full",
        "engine": "streaming",
        "format": "v2",
        "hasher": "sha256",
        "block_size": 4,
        "seed_depth": 1,
        "passes": 1,
        "max_span_len": 12,
        "expected": "negative",
        "note": "`streaming-planted-span12` plants arity-3 generated 12-byte spans to show how longer spans amortize the fixed v2 seed-span record overhead.",
    },
    {
        "name": "streaming-random-null-1k",
        "kind": "null-random",
        "corpus": "random-null-1k",
        "engine": "streaming",
        "format": "v2",
        "hasher": "sha256",
        "block_size": 4,
        "seed_depth": 1,
        "passes": 1,
        "max_span_len": 8,
        "expected": "bloat",
        "note": "`streaming-random-null-1k` is a deterministic pseudorandom control; any negative delta here would need investigation.",
    },
    {
        "name": "streaming-planted-density10",
        "kind": "density-planted",
        "corpus": "planted-density10",
        "engine": "streaming",
        "format": "v2",
        "hasher": "sha256",
        "block_size": 4,
        "seed_depth": 1,
        "passes": 1,
        "max_span_len": 8,
        "expected": "near-break-even-or-bloat",
        "note": "`streaming-planted-density10` plants a small contiguous generated region, showing that sparse hits can still lose to container and literal overhead.",
    },
    {
        "name": "streaming-planted-density50",
        "kind": "density-planted",
        "corpus": "planted-density50",
        "engine": "streaming",
        "format": "v2",
        "hasher": "sha256",
        "block_size": 4,
        "seed_depth": 1,
        "passes": 1,
        "max_span_len": 8,
        "expected": "negative",
        "note": "`streaming-planted-density50` plants a larger contiguous generated region and records the break-even direction under the same v2 overhead.",
    },
    {
        "name": "streaming-planted-offset1",
        "kind": "alignment-control",
        "corpus": "planted-offset1",
        "engine": "streaming",
        "format": "v2",
        "hasher": "sha256",
        "block_size": 4,
        "seed_depth": 1,
        "passes": 1,
        "max_span_len": 8,
        "expected": "bloat",
        "note": "`streaming-planted-offset1` shifts planted spans off the block grid to quantify the current alignment penalty.",
    },
    {
        "name": "streaming-recursive-offset-pass2",
        "kind": "recursive-planted",
        "corpus": "planted-offset1",
        "engine": "streaming",
        "format": "v2",
        "hasher": "sha256",
        "block_size": 4,
        "seed_depth": 1,
        "passes": 2,
        "max_span_len": 8,
        "expected": "bloat",
        "note": "`streaming-recursive-offset-pass2` uses the same off-grid planted corpus as the alignment control; the current streaming path stops after a non-compressive first layer.",
    },
    {
        "name": "streaming-structured-json-control",
        "kind": "structured-control",
        "corpus": "structured-json",
        "engine": "streaming",
        "format": "v2",
        "hasher": "sha256",
        "block_size": 4,
        "seed_depth": 1,
        "passes": 1,
        "max_span_len": 8,
        "expected": "unknown-control",
        "note": "`streaming-structured-json-control` is generated non-planted structured text; it is a control, not a viability claim.",
    },
    {
        "name": "kolyma-pdf-streaming-control",
        "kind": "binary-control",
        "corpus": "kolyma-pdf",
        "engine": "streaming",
        "format": "v2",
        "hasher": "sha256",
        "block_size": 4,
        "seed_depth": 1,
        "passes": 1,
        "max_span_len": 4,
        "expected": "bloat",
        "note": "`kolyma-pdf-streaming-control` runs the streaming path on the symbolic `kolyma.pdf` corpus as a binary/PDF control case.",
    },
]


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )


def read_cmd(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
    return (proc.stdout or proc.stderr).strip()


def deterministic_bytes(label: str, length: int) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < length:
        out.extend(hashlib.sha256(f"{label}:{counter}".encode("utf-8")).digest())
        counter += 1
    return bytes(out[:length])


def planted_span(length: int) -> bytes:
    return hashlib.sha256(b"\x00").digest()[:length]


def structured_json_bytes() -> bytes:
    rows = []
    for idx in range(80):
        rows.append(
            json.dumps(
                {
                    "event": "order_update",
                    "id": idx,
                    "sku": f"rx-{idx % 7:02d}",
                    "status": ["queued", "paid", "fulfilled"][idx % 3],
                    "amount_cents": 2499 + (idx % 11) * 125,
                },
                separators=(",", ":"),
            ).encode("utf-8")
            + b"\n"
        )
    return b"".join(rows)


def case_manifest() -> list[dict[str, Any]]:
    fields = (
        "name",
        "kind",
        "corpus",
        "engine",
        "format",
        "hasher",
        "block_size",
        "seed_depth",
        "passes",
        "max_span_len",
        "expected",
        "note",
    )
    return [{field: case[field] for field in fields} for case in CASE_MATRIX]


def case_manifest_hash() -> str:
    payload = json.dumps(case_manifest(), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def case_by_name(name: str) -> dict[str, Any]:
    for case in CASE_MATRIX:
        if case["name"] == name:
            return case
    raise KeyError(name)


def build_release_binary() -> Path:
    run(["cargo", "build", "--release", "--bin", "telomere"])
    name = "telomere.exe" if os.name == "nt" else "telomere"
    exe = ROOT / "target" / "release" / name
    if not exe.exists():
        raise FileNotFoundError(f"release binary was not built: {exe}")
    return exe


def environment_metadata() -> dict[str, object]:
    status = read_cmd(["git", "status", "--short"])
    return {
        "os": platform.platform(),
        "python": platform.python_version(),
        "rustc": read_cmd(["rustc", "--version"]),
        "cargo": read_cmd(["cargo", "--version"]),
        "git_commit": read_cmd(["git", "rev-parse", "--short", "HEAD"]),
        "git_dirty": bool(status),
        "rayon_num_threads": os.environ.get("RAYON_NUM_THREADS"),
    }


def write_case_input(case: dict[str, Any], temp: Path) -> Path:
    path = temp / f"{case['name']}.bin"
    corpus = case["corpus"]
    if corpus == "deterministic-bytes":
        path.write_bytes(bytes(range(64)))
    elif corpus == "planted-sha256-arity2":
        block = hashlib.sha256(b"\x00").digest()[:4]
        path.write_bytes(block * 64)
    elif corpus == "planted-span4-full":
        path.write_bytes(planted_span(4) * 256)
    elif corpus == "planted-span8-full":
        path.write_bytes(planted_span(8) * 128)
    elif corpus == "planted-span12-full":
        path.write_bytes(planted_span(12) * 85)
    elif corpus == "random-null-1k":
        path.write_bytes(deterministic_bytes(corpus, 1024))
    elif corpus == "planted-density10":
        planted = planted_span(8) * 13
        path.write_bytes(planted + deterministic_bytes(corpus, 1024 - len(planted)))
    elif corpus == "planted-density50":
        planted = planted_span(8) * 64
        path.write_bytes(planted + deterministic_bytes(corpus, 1024 - len(planted)))
    elif corpus == "planted-offset1":
        path.write_bytes(b"\xAA" + planted_span(8) * 128)
    elif corpus == "structured-json":
        path.write_bytes(structured_json_bytes())
    elif corpus == "kolyma-pdf":
        source = ROOT / "kolyma.pdf"
        if not source.exists():
            raise FileNotFoundError("kolyma.pdf is required for the symbolic corpus case")
        path.write_bytes(source.read_bytes())
    else:
        raise ValueError(corpus)
    return path


def run_case(case: dict[str, Any], temp: Path, exe: Path) -> dict[str, object]:
    input_path = write_case_input(case, temp)
    output_path = temp / f"{case['name']}.tlmr"
    restored_path = temp / f"{case['name']}.restored"
    index_build_ms = None

    compress_cmd = [
        str(exe),
        "compress",
        str(input_path),
        str(output_path),
        "--block-size",
        str(case["block_size"]),
        "--seed-depth",
        str(case["seed_depth"]),
        "--passes",
        str(case["passes"]),
        "--hasher",
        case["hasher"],
        "--memory-limit",
        "100%",
        "--json",
        "--verify",
        "--force",
    ]
    if case["engine"] == "indexed":
        index_path = temp / f"{case['name']}.idx"
        build_cmd = [
            str(exe),
            "index",
            "build",
            "--output",
            str(index_path),
            "--hasher",
            case["hasher"],
            "--max-seed-len",
            str(case["seed_depth"]),
            "--max-span-len",
            str(case["max_span_len"]),
            "--block-size",
            str(case["block_size"]),
        ]
        t0 = time.perf_counter()
        run(build_cmd)
        index_build_ms = round((time.perf_counter() - t0) * 1000, 3)
        compress_cmd.extend(
            [
                "--engine",
                "indexed",
                "--format",
                "v2",
                "--index",
                str(index_path),
                "--max-span-len",
                str(case["max_span_len"]),
            ]
        )
    elif case["engine"] == "streaming":
        compress_cmd.extend(
            [
                "--engine",
                "streaming",
                "--format",
                "v2",
                "--max-span-len",
                str(case["max_span_len"]),
            ]
        )

    t0 = time.perf_counter()
    proc = run(compress_cmd)
    compress_ms = round((time.perf_counter() - t0) * 1000, 3)
    summary = json.loads(proc.stdout)

    t0 = time.perf_counter()
    run(
        [
            str(exe),
            "decompress",
            str(output_path),
            str(restored_path),
            "--force",
        ]
    )
    decompress_ms = round((time.perf_counter() - t0) * 1000, 3)
    if restored_path.read_bytes() != input_path.read_bytes():
        raise RuntimeError(f"{case['name']}: decompressed bytes did not match input")

    input_bytes = input_path.stat().st_size
    output_bytes = output_path.stat().st_size
    return {
        "name": case["name"],
        "kind": case["kind"],
        "expected": case["expected"],
        "input_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
        "output_sha256": hashlib.sha256(output_path.read_bytes()).hexdigest(),
        "input_bytes": input_bytes,
        "output_bytes": output_bytes,
        "delta_bytes": output_bytes - input_bytes,
        "delta_pct": ((output_bytes - input_bytes) / input_bytes * 100.0)
        if input_bytes
        else 0.0,
        "block_size": int(case["block_size"]),
        "seed_depth": int(case["seed_depth"]),
        "passes": int(case["passes"]),
        "hasher": case["hasher"],
        "engine": case["engine"],
        "format": case["format"],
        "max_span_len": case["max_span_len"],
        "index_build_ms": index_build_ms,
        "lookup_compress_ms": compress_ms,
        "decompress_ms": decompress_ms,
        "summary": summary,
    }


def write_results(
    cases: list[dict[str, Any]],
    results: list[dict[str, object]],
    environment: dict[str, object],
) -> None:
    DOCS.mkdir(exist_ok=True)
    payload = {
        "generated_by": "scripts/generate_results.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 2,
        "case_manifest_sha256": case_manifest_hash(),
        "case_matrix": case_manifest(),
        "selected_case_names": [case["name"] for case in cases],
        "environment": environment,
        "results": results,
    }
    RESULTS_JSON.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_JSON.write_text(json.dumps(payload, indent=2) + "\n")

    lines = [
        "# Telomere Results",
        "",
        "Generated by `scripts/generate_results.py` from real release-binary CLI compress/decompress runs.",
        "Do not hand-edit benchmark tables; regenerate this file instead.",
        "",
        f"Case matrix manifest SHA-256: `{case_manifest_hash()}`.",
        "",
        "| case | kind | engine | format | hasher | block size | span limit | seed depth | passes | input bytes | output bytes | delta bytes | delta | index build ms | compress ms | decompress ms |",
        "| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in results:
        span = item["max_span_len"] if item["max_span_len"] is not None else "-"
        display_item = dict(item)
        display_item["index_build_ms"] = (
            item["index_build_ms"] if item["index_build_ms"] is not None else "-"
        )
        lines.append(
            "| {name} | {kind} | {engine} | {format} | {hasher} | {block_size} | {span} | {seed_depth} | {passes} | {input_bytes} | "
            "{output_bytes} | {delta_bytes:+} | {delta_pct:+.2f}% | {index_build_ms} | {lookup_compress_ms} | {decompress_ms} |".format(
                span=span, **display_item
            )
        )
    lines.extend(
        [
            "",
            "Interpretation:",
            "",
        ]
    )
    lines.extend(f"- {case['note']}" for case in cases)
    lines.append("- These are correctness, mechanism, and control checks, not production performance claims.")
    (DOCS / "RESULTS.md").write_text("\n".join(lines) + "\n")


def check_results() -> None:
    results_path = RESULTS_JSON
    results_md = DOCS / "RESULTS.md"
    if not results_path.exists() or not results_md.exists():
        raise SystemExit("generated result files are missing")
    payload = json.loads(results_path.read_text(encoding="utf-8"))
    if payload.get("generated_by") != "scripts/generate_results.py":
        raise SystemExit("results.json has wrong generated_by marker")
    if payload.get("case_manifest_sha256") != case_manifest_hash():
        raise SystemExit("results.json case manifest hash is stale")
    expected_names = [case["name"] for case in CASE_MATRIX]
    result_names = [result["name"] for result in payload.get("results", [])]
    if result_names != expected_names:
        raise SystemExit("results.json does not contain the full default case matrix")
    text = results_md.read_text(encoding="utf-8")
    missing = [name for name in expected_names if name not in text]
    if missing:
        raise SystemExit(f"RESULTS.md missing cases: {', '.join(missing)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", action="append", help="run one named case; repeatable")
    parser.add_argument("--list", action="store_true", help="list case names and exit")
    parser.add_argument("--manifest-sha", action="store_true", help="print case manifest hash and exit")
    parser.add_argument("--check", action="store_true", help="validate checked-in generated results without running benchmarks")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.list:
        for case in CASE_MATRIX:
            print(case["name"])
        return
    if args.manifest_sha:
        print(case_manifest_hash())
        return
    if args.check:
        check_results()
        return

    if args.case:
        try:
            cases = [case_by_name(name) for name in args.case]
        except KeyError as exc:
            raise SystemExit(f"unknown case: {exc.args[0]}") from exc
    else:
        cases = CASE_MATRIX

    exe = build_release_binary()
    environment = environment_metadata()
    with tempfile.TemporaryDirectory() as tmp:
        temp = Path(tmp)
        results = [run_case(case, temp, exe) for case in cases]
    write_results(cases, results, environment)


if __name__ == "__main__":
    main()
