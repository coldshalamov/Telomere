#!/usr/bin/env python3
"""Run Telomere against public compression corpora with zlib baselines.

This is intentionally outside the generated docs pipeline. It writes measured
artifacts under target/thesis_runs so the thesis can be attacked without
staling proof-ledger hashes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
import urllib.request
import zipfile
import zlib
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "target"
DEFAULT_OUT = TARGET / "thesis_runs" / "public_corpus_benchmark" / "results.json"

CORPORA = {
    "canterbury": {
        "url": "https://corpus.canterbury.ac.nz/resources/cantrbry.zip",
        "description": "Standard Canterbury Corpus",
    },
    "calgary": {
        "url": "https://corpus.canterbury.ac.nz/resources/calgary.zip",
        "description": "Calgary Corpus zip mirrored by Canterbury Corpus site",
    },
    "silesia": {
        "url": "https://sun.aei.polsl.pl/~sdeor/corpus/silesia.zip",
        "description": "Silesia Corpus",
    },
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest: Path) -> None:
    if dest.exists():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=120) as response:
        data = response.read()
    dest.write_bytes(data)


def extract_zip(zip_path: Path, dest: Path) -> None:
    marker = dest / ".extracted"
    if marker.exists():
        return
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            if member.is_dir():
                continue
            target = dest / member.filename
            resolved = target.resolve()
            if not str(resolved).startswith(str(dest.resolve())):
                raise RuntimeError(f"refusing unsafe zip path: {member.filename}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(member))
    marker.write_text("ok\n", encoding="utf-8")


def corpus_files(corpus: str) -> tuple[dict[str, str], list[Path]]:
    spec = CORPORA[corpus]
    cache = TARGET / "public_corpora" / corpus
    zip_path = cache / Path(spec["url"]).name
    extract_dir = cache / "files"
    download(spec["url"], zip_path)
    extract_zip(zip_path, extract_dir)
    files = sorted(path for path in extract_dir.rglob("*") if path.is_file() and path.name != ".extracted")
    return {
        "name": corpus,
        "description": spec["description"],
        "url": spec["url"],
        "archive_path": str(zip_path),
        "archive_sha256": sha256_file(zip_path),
    }, files


def run_command(cmd: list[str], timeout: int) -> dict[str, Any]:
    started = time.perf_counter()
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    elapsed = time.perf_counter() - started
    return {
        "command": cmd,
        "returncode": proc.returncode,
        "elapsed_s": round(elapsed, 6),
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def telomere_exe() -> Path:
    exe = ROOT / "target" / "release" / ("telomere.exe" if is_windows() else "telomere")
    if exe.exists():
        return exe
    debug = ROOT / "target" / "debug" / ("telomere.exe" if is_windows() else "telomere")
    if debug.exists():
        return debug
    raise FileNotFoundError("telomere binary not found; run `cargo build --release --bin telomere`")


def is_windows() -> bool:
    return "\\" in str(ROOT)


def telomere_run(
    exe: Path,
    input_path: Path,
    output_path: Path,
    *,
    seed_bits: int,
    mode: str,
    target_chunk_bytes: str,
    timeout: int,
) -> dict[str, Any]:
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
        "--seed-bits",
        str(seed_bits),
        "--max-span-len",
        "16",
        "--block-size",
        "4",
        "--passes",
        "1",
        "--json",
        "--verify",
        "--force",
        "--telemetry-limit",
        "8",
        "--target-chunk-bytes",
        target_chunk_bytes,
    ]
    if mode == "native":
        cmd.extend(["--span-step", "4"])
    elif mode == "public-preset":
        cmd.extend(["--span-step", "1", "--transform", "public-preset-selective"])
    else:
        raise ValueError(mode)

    run = run_command(cmd, timeout)
    result: dict[str, Any] = {
        "mode": mode,
        "elapsed_s": run["elapsed_s"],
        "returncode": run["returncode"],
        "command": run["command"],
    }
    if run["returncode"] != 0:
        result["stderr_tail"] = run["stderr"][-2000:]
        return result

    payload = json.loads(run["stdout"])
    telemetry = payload.get("engine_telemetry", {})
    layer = (telemetry.get("layers") or [{}])[0]
    result.update(
        {
            "tlmr_bytes": output_path.stat().st_size,
            "delta_bytes": output_path.stat().st_size - input_path.stat().st_size,
            "ratio": round(output_path.stat().st_size / input_path.stat().st_size, 6),
            "candidate_count": layer.get("candidate_count"),
            "selected_count": layer.get("selected_count"),
            "literal_bytes": layer.get("literal_bytes"),
            "seed_len_counts": layer.get("seed_len_counts"),
            "seeds_scanned": layer.get("seeds_scanned"),
            "first_selected_spans": layer.get("selected_spans", []),
        }
    )
    if "transform" in telemetry:
        result["transform"] = telemetry["transform"]
    return result


def zlib_result(data: bytes, level: int) -> dict[str, Any]:
    started = time.perf_counter()
    encoded = zlib.compress(data, level)
    elapsed = time.perf_counter() - started
    return {
        "mode": f"zlib-{level}",
        "elapsed_s": round(elapsed, 6),
        "bytes": len(encoded),
        "delta_bytes": len(encoded) - len(data),
        "ratio": round(len(encoded) / len(data), 6),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", choices=sorted(CORPORA), default="canterbury")
    parser.add_argument("--seed-bits", type=int, default=8)
    parser.add_argument("--max-files", type=int, default=0, help="0 means all files")
    parser.add_argument("--max-file-bytes", type=int, default=0, help="0 means no size limit")
    parser.add_argument("--target-chunk-bytes", default="64MB")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    exe = telomere_exe()
    corpus_meta, files = corpus_files(args.corpus)
    if args.max_file_bytes:
        files = [path for path in files if path.stat().st_size <= args.max_file_bytes]
    if args.max_files:
        files = files[: args.max_files]

    out_dir = args.output.parent / args.corpus
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for path in files:
        data = path.read_bytes()
        rel = path.relative_to(TARGET / "public_corpora" / args.corpus / "files")
        row: dict[str, Any] = {
            "file": str(rel).replace("\\", "/"),
            "input_bytes": len(data),
            "sha256": sha256_bytes(data),
            "zlib": [zlib_result(data, 1), zlib_result(data, 9)],
            "telomere": [],
        }
        safe_name = "__".join(rel.parts)
        for mode in ("native", "public-preset"):
            output_path = out_dir / f"{safe_name}.{mode}.tlmr"
            row["telomere"].append(
                telomere_run(
                    exe,
                    path,
                    output_path,
                    seed_bits=args.seed_bits,
                    mode=mode,
                    target_chunk_bytes=args.target_chunk_bytes,
                    timeout=args.timeout,
                )
            )
        rows.append(row)
        best_telomere = min(
            (r for r in row["telomere"] if r.get("returncode") == 0),
            key=lambda r: r["tlmr_bytes"],
            default=None,
        )
        best_telomere_bytes = best_telomere["tlmr_bytes"] if best_telomere else None
        print(
            json.dumps(
                {
                    "file": row["file"],
                    "input_bytes": row["input_bytes"],
                    "best_telomere_bytes": best_telomere_bytes,
                    "zlib_1_bytes": row["zlib"][0]["bytes"],
                    "zlib_9_bytes": row["zlib"][1]["bytes"],
                },
                sort_keys=True,
            )
        )

    summary = summarize(rows)
    payload = {
        "generated_by": "scripts/run_public_corpus_benchmark.py",
        "corpus": corpus_meta,
        "params": {
            "seed_bits": args.seed_bits,
            "max_files": args.max_files,
            "max_file_bytes": args.max_file_bytes,
            "target_chunk_bytes": args.target_chunk_bytes,
            "timeout": args.timeout,
        },
        "summary": summary,
        "rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(f"WROTE {args.output}")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total_input = sum(row["input_bytes"] for row in rows)

    def total_for_telomere(mode: str) -> int | None:
        total = 0
        for row in rows:
            result = next(item for item in row["telomere"] if item["mode"] == mode)
            if result.get("returncode") != 0:
                return None
            total += result["tlmr_bytes"]
        return total

    totals: dict[str, Any] = {
        "files": len(rows),
        "input_bytes": total_input,
        "zlib_1_bytes": sum(row["zlib"][0]["bytes"] for row in rows),
        "zlib_9_bytes": sum(row["zlib"][1]["bytes"] for row in rows),
        "telomere_native_bytes": total_for_telomere("native"),
        "telomere_public_preset_bytes": total_for_telomere("public-preset"),
    }
    for key in (
        "zlib_1_bytes",
        "zlib_9_bytes",
        "telomere_native_bytes",
        "telomere_public_preset_bytes",
    ):
        value = totals[key]
        if value is None:
            continue
        totals[key.replace("_bytes", "_ratio")] = round(value / total_input, 6) if total_input else 0
        totals[key.replace("_bytes", "_delta_bytes")] = value - total_input
    return totals


if __name__ == "__main__":
    raise SystemExit(main())
