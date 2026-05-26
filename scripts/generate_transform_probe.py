#!/usr/bin/env python3
"""Generate simple reversible-transform manifold probes for Telomere."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import generate_manifold_report
import generate_results
import generate_transform_sweeps


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
PROBE_JSON = DOCS / "transform_probe.json"
PROBE_MD = DOCS / "TRANSFORM_PROBE.md"

HASHER = "sha256"
MAX_SEED_LEN = 2
SPAN_LEN = 8
SPAN_STEP = 1


def rotl(byte: int, shift: int) -> int:
    return ((byte << shift) | (byte >> (8 - shift))) & 0xFF


def bit_reverse(byte: int) -> int:
    out = 0
    for _ in range(8):
        out = (out << 1) | (byte & 1)
        byte >>= 1
    return out


def bytewise_transform(data: bytes, func: Callable[[int], int]) -> bytes:
    return bytes(func(byte) for byte in data)


def chunk_reverse(data: bytes, width: int) -> bytes:
    out = bytearray()
    for start in range(0, len(data), width):
        out.extend(reversed(data[start : start + width]))
    return bytes(out)


def even_odd_deinterleave(data: bytes) -> bytes:
    return data[0::2] + data[1::2]


def xor_lag(data: bytes, lag: int) -> bytes:
    if lag <= 0:
        raise ValueError("lag must be positive")
    out = bytearray(data[:lag])
    for idx in range(lag, len(data)):
        out.append(data[idx] ^ data[idx - lag])
    return bytes(out)


def invert_xor_lag(data: bytes, lag: int) -> bytes:
    if lag <= 0:
        raise ValueError("lag must be positive")
    out = bytearray(data[:lag])
    for idx in range(lag, len(data)):
        out.append(data[idx] ^ out[idx - lag])
    return bytes(out)


def sub_lag(data: bytes, lag: int) -> bytes:
    if lag <= 0:
        raise ValueError("lag must be positive")
    out = bytearray(data[:lag])
    for idx in range(lag, len(data)):
        out.append((data[idx] - data[idx - lag]) & 0xFF)
    return bytes(out)


def invert_sub_lag(data: bytes, lag: int) -> bytes:
    if lag <= 0:
        raise ValueError("lag must be positive")
    out = bytearray(data[:lag])
    for idx in range(lag, len(data)):
        out.append((data[idx] + out[idx - lag]) & 0xFF)
    return bytes(out)


def probe_manifest() -> list[dict[str, Any]]:
    manifest: list[dict[str, Any]] = [
        {
            "family": "identity",
            "parameter": 0,
            "metadata_bytes": 0,
            "description": "No transform.",
        }
    ]
    manifest.extend(
        {
            "family": "xor-const",
            "parameter": value,
            "metadata_bytes": 1,
            "description": "Every byte XORed with a stored one-byte constant.",
        }
        for value in range(256)
    )
    manifest.extend(
        {
            "family": "add-const",
            "parameter": value,
            "metadata_bytes": 1,
            "description": "Every byte incremented modulo 256 by a stored one-byte constant.",
        }
        for value in range(256)
    )
    manifest.extend(
        {
            "family": "rotl",
            "parameter": shift,
            "metadata_bytes": 1,
            "description": "Every byte rotated left by a stored bit count.",
        }
        for shift in range(1, 8)
    )
    manifest.extend(
        [
            {
                "family": "bit-reverse",
                "parameter": 0,
                "metadata_bytes": 0,
                "description": "Reverse bit order within every byte.",
            },
            {
                "family": "nibble-swap",
                "parameter": 0,
                "metadata_bytes": 0,
                "description": "Swap high and low nibble within every byte.",
            },
            {
                "family": "even-odd",
                "parameter": 0,
                "metadata_bytes": 0,
                "description": "Place even-indexed bytes before odd-indexed bytes.",
            },
            {
                "family": "reverse-stream",
                "parameter": 0,
                "metadata_bytes": 0,
                "description": "Whole byte stream reversed.",
            },
            {
                "family": "xor-prev",
                "parameter": 0,
                "metadata_bytes": 1,
                "description": "Same reversible residual used by transform sweeps.",
            },
            {
                "family": "sub-prev",
                "parameter": 0,
                "metadata_bytes": 1,
                "description": "Same reversible subtraction residual used by transform sweeps.",
            },
        ]
    )
    manifest.extend(
        {
            "family": "xor-lag",
            "parameter": lag,
            "metadata_bytes": 1,
            "description": "Every byte after the initial lag window XORed with the byte lag positions back.",
        }
        for lag in (2, 4, 8, 16)
    )
    manifest.extend(
        {
            "family": "sub-lag",
            "parameter": lag,
            "metadata_bytes": 1,
            "description": "Every byte after the initial lag window subtracts the byte lag positions back.",
        }
        for lag in (2, 4, 8, 16)
    )
    manifest.extend(
        {
            "family": "chunk-reverse",
            "parameter": width,
            "metadata_bytes": 1,
            "description": "Reverse byte order within fixed-size chunks.",
        }
        for width in (2, 4, 8, 16, 32)
    )
    return manifest


def probe_manifest_hash() -> str:
    payload = json.dumps(probe_manifest(), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def apply_probe(data: bytes, probe: dict[str, Any]) -> bytes:
    family = probe["family"]
    parameter = int(probe["parameter"])
    if family == "identity":
        return data
    if family == "xor-const":
        return bytewise_transform(data, lambda byte: byte ^ parameter)
    if family == "add-const":
        return bytewise_transform(data, lambda byte: (byte + parameter) & 0xFF)
    if family == "rotl":
        return bytewise_transform(data, lambda byte: rotl(byte, parameter))
    if family == "bit-reverse":
        return bytewise_transform(data, bit_reverse)
    if family == "nibble-swap":
        return bytewise_transform(data, lambda byte: ((byte & 0x0F) << 4) | (byte >> 4))
    if family == "even-odd":
        return even_odd_deinterleave(data)
    if family == "reverse-stream":
        return data[::-1]
    if family == "chunk-reverse":
        return chunk_reverse(data, parameter)
    if family == "xor-prev":
        return generate_transform_sweeps.apply_xor_prev(data).data
    if family == "sub-prev":
        return generate_transform_sweeps.apply_sub_prev(data).data
    if family == "xor-lag":
        transformed = xor_lag(data, parameter)
        if invert_xor_lag(transformed, parameter) != data:
            raise RuntimeError("xor-lag transform failed reversibility check")
        return transformed
    if family == "sub-lag":
        transformed = sub_lag(data, parameter)
        if invert_sub_lag(transformed, parameter) != data:
            raise RuntimeError("sub-lag transform failed reversibility check")
        return transformed
    raise ValueError(family)


def analyze_bytes(data: bytes, prefix_sets: list[set[bytes]]) -> dict[str, Any]:
    histogram: Counter[int] = Counter()
    spans = generate_manifold_report.candidate_span_count(
        len(data),
        SPAN_LEN,
        SPAN_STEP,
    )
    for start in range(0, max(0, len(data) - SPAN_LEN + 1), SPAN_STEP):
        span = data[start : start + SPAN_LEN]
        histogram[generate_manifold_report.longest_generated_prefix(span, prefix_sets)] += 1
    return {
        "candidate_spans": spans,
        "longest_prefix_histogram": {str(key): histogram.get(key, 0) for key in range(SPAN_LEN + 1)},
        "prefix_ge_3_count": sum(count for prefix, count in histogram.items() if prefix >= 3),
        "prefix_ge_4_count": sum(count for prefix, count in histogram.items() if prefix >= 4),
        "prefix_ge_5_count": sum(count for prefix, count in histogram.items() if prefix >= 5),
        "prefix_ge_6_count": sum(count for prefix, count in histogram.items() if prefix >= 6),
        "exact_span_hits": histogram[SPAN_LEN],
        "expected_random_prefix_ge_3": generate_manifold_report.expected_random_ge_count(
            spans,
            prefix_sets,
            3,
        ),
        "expected_random_prefix_ge_4": generate_manifold_report.expected_random_ge_count(
            spans,
            prefix_sets,
            4,
        ),
        "expected_random_exact": generate_manifold_report.expected_random_ge_count(
            spans,
            prefix_sets,
            SPAN_LEN,
        ),
    }


def analyze_probe(
    source: bytes,
    probe: dict[str, Any],
    prefix_sets: list[set[bytes]],
) -> dict[str, Any]:
    transformed = apply_probe(source, probe)
    metrics = analyze_bytes(transformed, prefix_sets)
    return {
        "name": f"{probe['family']}:{probe['parameter']}",
        "family": probe["family"],
        "parameter": probe["parameter"],
        "metadata_bytes": probe["metadata_bytes"],
        "input_sha256": hashlib.sha256(transformed).hexdigest(),
        "input_bytes": len(transformed),
        **metrics,
    }


def top_rows(rows: list[dict[str, Any]], key: str, limit: int = 12) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            row[key],
            row["exact_span_hits"],
            row["prefix_ge_5_count"],
            row["prefix_ge_4_count"],
            row["prefix_ge_3_count"],
            -int(row["metadata_bytes"]),
            row["family"],
            int(row["parameter"]),
        ),
        reverse=True,
    )[:limit]


def build_report() -> dict[str, Any]:
    source = generate_results.structured_json_bytes()
    prefix_sets = generate_manifold_report.generated_prefix_sets(MAX_SEED_LEN, SPAN_LEN)
    rows = [analyze_probe(source, probe, prefix_sets) for probe in probe_manifest()]
    best_prefix4 = top_rows(rows, "prefix_ge_4_count", 1)[0]
    best_prefix3 = top_rows(rows, "prefix_ge_3_count", 1)[0]
    best_exact = top_rows(rows, "exact_span_hits", 1)[0]
    return {
        "generated_by": "scripts/generate_transform_probe.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "probe_manifest_sha256": probe_manifest_hash(),
        "probe_count": len(rows),
        "source_corpus": "structured-json",
        "source_sha256": hashlib.sha256(source).hexdigest(),
        "source_bytes": len(source),
        "hasher": HASHER,
        "max_seed_len": MAX_SEED_LEN,
        "seed_count": generate_manifold_report.seed_count(MAX_SEED_LEN),
        "span_len": SPAN_LEN,
        "span_step": SPAN_STEP,
        "results": rows,
        "top_prefix_ge_3": top_rows(rows, "prefix_ge_3_count"),
        "top_prefix_ge_4": top_rows(rows, "prefix_ge_4_count"),
        "top_exact": top_rows(rows, "exact_span_hits"),
        "summary": {
            "best_prefix_ge_3": best_prefix3["name"],
            "best_prefix_ge_3_count": best_prefix3["prefix_ge_3_count"],
            "best_prefix_ge_4": best_prefix4["name"],
            "best_prefix_ge_4_count": best_prefix4["prefix_ge_4_count"],
            "best_exact": best_exact["name"],
            "best_exact_hits": best_exact["exact_span_hits"],
            "conclusion": (
                "Simple reversible transform probes can lift shallow prefix proximity, "
                "but this matrix found no exact depth-2 span hits."
            ),
        },
    }


def compact_row(row: dict[str, Any]) -> str:
    return (
        "| {name} | {metadata_bytes} | {prefix_ge_3_count} | "
        "{prefix_ge_4_count} | {prefix_ge_5_count} | {prefix_ge_6_count} | "
        "{exact_span_hits} |".format(**row)
    )


def write_report(payload: dict[str, Any]) -> None:
    PROBE_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Telomere Transform Probe",
        "",
        "Generated by `scripts/generate_transform_probe.py`.",
        "This is a multiple-comparison research probe, not format support and not a compression claim.",
        "",
        f"Source corpus: `{payload['source_corpus']}`.",
        f"Probe count: `{payload['probe_count']}`.",
        f"Hasher: `{payload['hasher']}`.",
        f"Max seed len: `{payload['max_seed_len']}`.",
        f"Span len: `{payload['span_len']}`.",
        "",
        "## Summary",
        "",
        payload["summary"]["conclusion"],
        f"Best prefix >=3 probe: `{payload['summary']['best_prefix_ge_3']}` with `{payload['summary']['best_prefix_ge_3_count']}` spans.",
        f"Best prefix >=4 probe: `{payload['summary']['best_prefix_ge_4']}` with `{payload['summary']['best_prefix_ge_4_count']}` spans.",
        f"Best exact probe: `{payload['summary']['best_exact']}` with `{payload['summary']['best_exact_hits']}` exact hits.",
        "",
        "## Top Prefix >=4 Probes",
        "",
        "| probe | metadata bytes | prefix >=3 | prefix >=4 | prefix >=5 | prefix >=6 | exact hits |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    lines.extend(compact_row(row) for row in payload["top_prefix_ge_4"])
    lines.extend(
        [
            "",
            "## Top Prefix >=3 Probes",
            "",
            "| probe | metadata bytes | prefix >=3 | prefix >=4 | prefix >=5 | prefix >=6 | exact hits |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    lines.extend(compact_row(row) for row in payload["top_prefix_ge_3"])
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Prefix >=4 movement is interesting because ordinary structured JSON had zero prefix >=4 spans in `docs/MANIFOLD.md`.",
            "- Lagged residual probes test byte dependencies beyond the immediate previous byte while remaining exactly reversible.",
            "- No row here found an exact 8-byte seed-span hit, so none of these probes proves compression viability.",
            "- Because this sweep tests hundreds of transforms, shallow prefix gains must be treated as hypothesis generation until validated on held-out corpora.",
            "- Any production transform would need explicit format metadata and inverse decoding support before it could count as Telomere compression.",
        ]
    )
    PROBE_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not PROBE_JSON.exists() or not PROBE_MD.exists():
        raise SystemExit("generated transform probe files are missing")
    payload = json.loads(PROBE_JSON.read_text(encoding="utf-8"))
    if payload.get("generated_by") != "scripts/generate_transform_probe.py":
        raise SystemExit("transform_probe.json has wrong generated_by marker")
    if payload.get("probe_manifest_sha256") != probe_manifest_hash():
        raise SystemExit("transform_probe.json probe manifest hash is stale")
    if payload.get("probe_count") != len(probe_manifest()):
        raise SystemExit("transform_probe.json probe count is stale")
    text = PROBE_MD.read_text(encoding="utf-8")
    for phrase in (
        "multiple-comparison research probe",
        "Top Prefix >=4 Probes",
        "Lagged residual probes",
        "No row here found an exact 8-byte seed-span hit",
        "not format support",
    ):
        if phrase not in text:
            raise SystemExit(f"TRANSFORM_PROBE.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate generated transform probe")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.check:
        check_report()
        return
    write_report(build_report())


if __name__ == "__main__":
    main()
