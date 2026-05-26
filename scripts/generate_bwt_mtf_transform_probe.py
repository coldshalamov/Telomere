#!/usr/bin/env python3
"""Probe reversible BWT/MTF/RLE preconditioners for seed-span evidence."""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import generate_corpus_matrix
import generate_manifold_report


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
REPORT_JSON = DOCS / "bwt_mtf_transform_probe.json"
REPORT_MD = DOCS / "BWT_MTF_TRANSFORM_PROBE.md"

HASHER = "sha256"
MAX_SEED_LEN = 2
SPAN_LEN = 8
SPAN_STEP = 1
PREFIX_LADDER = (3, 4, 5, 6)
SEED_RECORD_OVERHEAD_BYTES = 4
TOP_LIMIT = 32

CORPUS_MATRIX: list[dict[str, Any]] = [
    {"name": "json", "kind": "structured-text"},
    {"name": "markdown", "kind": "prose-markup"},
    {"name": "csv", "kind": "field-delimited"},
    {"name": "rust-like", "kind": "source-like"},
    {"name": "log", "kind": "record-log"},
    {"name": "yaml", "kind": "config"},
    {"name": "fasta", "kind": "biological-text"},
    {"name": "http-headers", "kind": "protocol-records"},
    {"name": "shadow-json", "kind": "shadow-vocab-control"},
    {"name": "binary-varint", "kind": "binary-control"},
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_hashes() -> dict[str, str]:
    return {
        "corpus_matrix_sha256": sha256(DOCS / "corpus_matrix.json"),
    }


def transform_manifest() -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = [
        {
            "name": "identity",
            "family": "identity",
            "parameter": None,
            "description": "No transform baseline.",
        },
        {
            "name": "mtf",
            "family": "mtf",
            "parameter": None,
            "description": "Move-to-front byte ranks with a fixed 0..255 initial alphabet.",
        },
        {
            "name": "mtf-zero-rle",
            "family": "mtf-zero-rle",
            "parameter": None,
            "description": "Move-to-front ranks followed by reversible zero-run packing.",
        },
    ]
    for block_size in (64, 128):
        candidates.extend(
            [
                {
                    "name": f"bwt-b{block_size}",
                    "family": "bwt",
                    "parameter": {"block_size": block_size},
                    "description": "Block-local Burrows-Wheeler transform.",
                },
                {
                    "name": f"bwt-mtf-b{block_size}",
                    "family": "bwt-mtf",
                    "parameter": {"block_size": block_size},
                    "description": "Block-local BWT followed by MTF ranks.",
                },
                {
                    "name": f"bwt-mtf-zero-rle-b{block_size}",
                    "family": "bwt-mtf-zero-rle",
                    "parameter": {"block_size": block_size},
                    "description": "Block-local BWT, MTF ranks, and reversible zero-run packing.",
                },
            ]
        )
    return candidates


def corpus_manifest_hash() -> str:
    payload = json.dumps(CORPUS_MATRIX, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def transform_manifest_hash() -> str:
    payload = json.dumps(
        transform_manifest(), sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def search_manifest() -> dict[str, Any]:
    return {
        "hasher": HASHER,
        "max_seed_len": MAX_SEED_LEN,
        "seed_order": "1-byte seeds first, then 2-byte seeds, each bucket big-endian",
        "span_len": SPAN_LEN,
        "span_step": SPAN_STEP,
        "prefix_ladder": PREFIX_LADDER,
        "seed_record_overhead_bytes": SEED_RECORD_OVERHEAD_BYTES,
        "target_block_hashing": False,
        "match_rule": "generated seed prefixes are compared directly against BWT/MTF/RLE-transformed bytes",
        "metadata_policy": "BWT primary indexes and transform descriptors are charged before promotion; transform-only shortening is reported but not counted as a Telomere seed-span win",
        "scope": "classic preconditioner research artifact only; not .tlmr format support",
    }


def search_manifest_hash() -> str:
    payload = json.dumps(search_manifest(), sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def corpus_bytes(name: str) -> bytes:
    return generate_corpus_matrix.corpus_bytes(name)


def bwt_block(block: bytes) -> tuple[bytes, int]:
    if not block:
        return b"", 0
    rotations = sorted((block[index:] + block[:index], index) for index in range(len(block)))
    primary = next(row for row, (_rotation, index) in enumerate(rotations) if index == 0)
    return bytes(rotation[-1] for rotation, _index in rotations), primary


def inverse_bwt_block(last: bytes, primary: int) -> bytes:
    if not last:
        return b""
    table = [b""] * len(last)
    for _ in last:
        table = sorted(bytes((last[index],)) + table[index] for index in range(len(last)))
    return table[primary]


def bwt_blocks(data: bytes, block_size: int) -> tuple[bytes, bytes, int]:
    out = bytearray()
    primaries: list[int] = []
    lengths: list[int] = []
    for offset in range(0, len(data), block_size):
        block = data[offset : offset + block_size]
        transformed, primary = bwt_block(block)
        out.extend(transformed)
        primaries.append(primary)
        lengths.append(len(block))
    payload = bytes(out)
    restored = inverse_bwt_blocks(payload, block_size, primaries, lengths)
    metadata_bytes = 3 + (2 * len(primaries))
    return payload, restored, metadata_bytes


def inverse_bwt_blocks(
    payload: bytes, block_size: int, primaries: list[int], lengths: list[int]
) -> bytes:
    out = bytearray()
    cursor = 0
    for primary, length in zip(primaries, lengths, strict=True):
        block = payload[cursor : cursor + length]
        cursor += length
        out.extend(inverse_bwt_block(block, primary))
    if cursor != len(payload):
        raise RuntimeError("BWT inverse did not consume payload")
    if any(length > block_size for length in lengths):
        raise RuntimeError("BWT inverse length exceeds block size")
    return bytes(out)


def mtf_encode(data: bytes) -> bytes:
    alphabet = list(range(256))
    out = bytearray()
    for value in data:
        index = alphabet.index(value)
        out.append(index)
        alphabet.pop(index)
        alphabet.insert(0, value)
    return bytes(out)


def mtf_decode(data: bytes) -> bytes:
    alphabet = list(range(256))
    out = bytearray()
    for index in data:
        value = alphabet[index]
        out.append(value)
        alphabet.pop(index)
        alphabet.insert(0, value)
    return bytes(out)


def zero_rle_encode(data: bytes) -> bytes:
    out = bytearray()
    cursor = 0
    while cursor < len(data):
        if data[cursor] != 0:
            out.append(data[cursor])
            cursor += 1
            continue
        run_len = 1
        while cursor + run_len < len(data) and data[cursor + run_len] == 0 and run_len < 255:
            run_len += 1
        out.extend((0, run_len))
        cursor += run_len
    return bytes(out)


def zero_rle_decode(data: bytes) -> bytes:
    out = bytearray()
    cursor = 0
    while cursor < len(data):
        value = data[cursor]
        cursor += 1
        if value != 0:
            out.append(value)
            continue
        if cursor >= len(data):
            raise RuntimeError("zero-run marker missing length byte")
        run_len = data[cursor]
        cursor += 1
        if run_len == 0:
            raise RuntimeError("zero-run length must be nonzero")
        out.extend(b"\x00" * run_len)
    return bytes(out)


def apply_transform(transform: dict[str, Any], data: bytes) -> tuple[bytes, int]:
    family = transform["family"]
    parameter = transform["parameter"]
    if family == "identity":
        return data, 0
    if family == "mtf":
        payload = mtf_encode(data)
        restored = mtf_decode(payload)
        metadata_bytes = 1
    elif family == "mtf-zero-rle":
        mtf = mtf_encode(data)
        payload = zero_rle_encode(mtf)
        restored = mtf_decode(zero_rle_decode(payload))
        metadata_bytes = 2
    elif family == "bwt":
        payload, restored, metadata_bytes = bwt_blocks(data, parameter["block_size"])
    elif family == "bwt-mtf":
        bwt, bwt_restored, bwt_metadata = bwt_blocks(data, parameter["block_size"])
        if bwt_restored != data:
            raise RuntimeError("BWT pre-pass failed reversibility proof")
        payload = mtf_encode(bwt)
        restored = inverse_bwt_blocks(
            mtf_decode(payload),
            parameter["block_size"],
            block_primaries(data, parameter["block_size"]),
            block_lengths(data, parameter["block_size"]),
        )
        metadata_bytes = bwt_metadata + 1
    elif family == "bwt-mtf-zero-rle":
        bwt, bwt_restored, bwt_metadata = bwt_blocks(data, parameter["block_size"])
        if bwt_restored != data:
            raise RuntimeError("BWT pre-pass failed reversibility proof")
        mtf = mtf_encode(bwt)
        payload = zero_rle_encode(mtf)
        restored = inverse_bwt_blocks(
            mtf_decode(zero_rle_decode(payload)),
            parameter["block_size"],
            block_primaries(data, parameter["block_size"]),
            block_lengths(data, parameter["block_size"]),
        )
        metadata_bytes = bwt_metadata + 2
    else:
        raise ValueError(family)
    if restored != data:
        raise RuntimeError(f"{transform['name']} failed reversibility proof")
    return payload, metadata_bytes


def block_primaries(data: bytes, block_size: int) -> list[int]:
    return [bwt_block(data[offset : offset + block_size])[1] for offset in range(0, len(data), block_size)]


def block_lengths(data: bytes, block_size: int) -> list[int]:
    return [len(data[offset : offset + block_size]) for offset in range(0, len(data), block_size)]


def byte_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = Counter(data)
    total = len(data)
    return round(
        -sum((count / total) * math.log2(count / total) for count in counts.values()),
        4,
    )


def candidate_span_count(data_len: int) -> int:
    return generate_manifold_report.candidate_span_count(data_len, SPAN_LEN, SPAN_STEP)


@lru_cache(maxsize=1)
def seed_digests() -> tuple[tuple[int, bytes, bytes], ...]:
    output = []
    for seed_index, seed in enumerate(generate_manifold_report.iter_seed_bytes(MAX_SEED_LEN)):
        output.append((seed_index, seed, hashlib.sha256(seed).digest()))
    return tuple(output)


@lru_cache(maxsize=None)
def generated_prefix_map(prefix_len: int) -> dict[bytes, dict[str, Any]]:
    mapping: dict[bytes, dict[str, Any]] = {}
    for seed_index, seed, digest in seed_digests():
        mapping.setdefault(
            digest[:prefix_len],
            {
                "seed_index": seed_index,
                "seed_len": len(seed),
                "seed_hex": seed.hex(),
            },
        )
    return mapping


def weighted_interval_selection(opportunities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = [
        row
        for row in opportunities
        if row["savings_bytes"] > 0 and row["start_offset"] < row["end_offset"]
    ]
    candidates.sort(
        key=lambda row: (
            row["end_offset"],
            row["start_offset"],
            -row["savings_bytes"],
            row["seed_index"],
        )
    )
    ends = [row["end_offset"] for row in candidates]
    previous = [
        bisect.bisect_right(ends, row["start_offset"]) - 1 for row in candidates
    ]
    dp = [0] * (len(candidates) + 1)
    take = [False] * len(candidates)
    for index, row in enumerate(candidates):
        take_value = row["savings_bytes"] + dp[previous[index] + 1]
        skip_value = dp[index]
        if take_value > skip_value:
            dp[index + 1] = take_value
            take[index] = True
        else:
            dp[index + 1] = skip_value
    selected: list[dict[str, Any]] = []
    index = len(candidates) - 1
    while index >= 0:
        row = candidates[index]
        take_value = row["savings_bytes"] + dp[previous[index] + 1]
        if take[index] and take_value > dp[index]:
            selected.append(row)
            index = previous[index]
        else:
            index -= 1
    return sorted(selected, key=lambda row: (row["start_offset"], row["end_offset"]))


def analyze_case(corpus: dict[str, Any], transform: dict[str, Any]) -> dict[str, Any]:
    original = corpus_bytes(corpus["name"])
    transformed, metadata_bytes = apply_transform(transform, original)
    prefix_counts = {prefix_len: 0 for prefix_len in PREFIX_LADDER}
    max_prefix = 0
    dedup_spans: set[bytes] = set()
    exact_hits: list[dict[str, Any]] = []

    for start in range(0, max(0, len(transformed) - SPAN_LEN + 1), SPAN_STEP):
        span = transformed[start : start + SPAN_LEN]
        dedup_spans.add(span)
        for prefix_len in PREFIX_LADDER:
            if span[:prefix_len] in generated_prefix_map(prefix_len):
                prefix_counts[prefix_len] += 1
        for prefix_len in sorted(PREFIX_LADDER, reverse=True):
            if span[:prefix_len] in generated_prefix_map(prefix_len):
                max_prefix = max(max_prefix, prefix_len)
                break
        hit = generated_prefix_map(SPAN_LEN).get(span)
        if hit is None:
            continue
        regenerated = hashlib.sha256(bytes.fromhex(hit["seed_hex"])).digest()[:SPAN_LEN]
        if regenerated != span:
            raise RuntimeError("generated-prefix map produced an unverified hit")
        encoded_len = SEED_RECORD_OVERHEAD_BYTES + int(hit["seed_len"])
        exact_hits.append(
            {
                "start_offset": start,
                "end_offset": start + SPAN_LEN,
                "span_len": SPAN_LEN,
                "seed_index": hit["seed_index"],
                "seed_len": hit["seed_len"],
                "seed_hex": hit["seed_hex"],
                "encoded_len": encoded_len,
                "savings_bytes": SPAN_LEN - encoded_len,
                "regeneration_verified": True,
            }
        )

    selected = weighted_interval_selection(exact_hits)
    selected_seed_bytes = sum(row["encoded_len"] for row in selected)
    selected_literal_bytes = sum(row["span_len"] for row in selected)
    selected_delta = selected_seed_bytes - selected_literal_bytes
    return {
        "corpus": corpus["name"],
        "corpus_kind": corpus["kind"],
        "transform": transform["name"],
        "transform_family": transform["family"],
        "input_bytes": len(original),
        "transformed_bytes": len(transformed),
        "transform_length_delta_bytes": len(transformed) - len(original),
        "input_sha256": hashlib.sha256(original).hexdigest(),
        "transformed_sha256": hashlib.sha256(transformed).hexdigest(),
        "byte_entropy": byte_entropy(transformed),
        "ascii_printable_ratio": generate_corpus_matrix.ascii_printable_ratio(transformed),
        "target_span_count": candidate_span_count(len(transformed)),
        "dedup_span_count": len(dedup_spans),
        "prefix_ge_3_count": prefix_counts[3],
        "prefix_ge_4_count": prefix_counts[4],
        "prefix_ge_5_count": prefix_counts[5],
        "prefix_ge_6_count": prefix_counts[6],
        "max_prefix_observed": max_prefix,
        "exact_hit_count": len(exact_hits),
        "positive_exact_hit_count": sum(
            1 for row in exact_hits if row["savings_bytes"] > 0
        ),
        "selected_span_count": len(selected),
        "literal_bytes_replaced": selected_literal_bytes,
        "encoded_seed_bytes": selected_seed_bytes,
        "metadata_bytes": metadata_bytes,
        "net_seed_delta_bytes": selected_delta,
        "net_with_metadata_bytes": selected_delta + metadata_bytes,
        "reversibility_verified": True,
        "selected_records": selected[:8],
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    prefix5 = [row for row in rows if row["prefix_ge_5_count"] > 0]
    exact = [row for row in rows if row["exact_hit_count"] > 0]
    selected = [row for row in rows if row["selected_span_count"] > 0]
    negative_after_metadata = [
        row
        for row in rows
        if row["selected_span_count"] > 0 and row["net_with_metadata_bytes"] < 0
    ]
    shorter_payload = [row for row in rows if row["transform_length_delta_bytes"] < 0]
    best = min(
        rows,
        key=lambda row: (
            row["net_with_metadata_bytes"],
            -row["selected_span_count"],
            -row["max_prefix_observed"],
            row["corpus"],
            row["transform"],
        ),
    )
    best_prefix = max(
        rows,
        key=lambda row: (
            row["max_prefix_observed"],
            row["prefix_ge_5_count"],
            row["prefix_ge_4_count"],
            row["corpus"],
            row["transform"],
        ),
    )
    return {
        "corpus_count": len(CORPUS_MATRIX),
        "transform_count": len(transform_manifest()),
        "row_count": len(rows),
        "target_span_count": sum(row["target_span_count"] for row in rows),
        "rows_with_prefix_ge_5": len(prefix5),
        "rows_with_exact_hits": len(exact),
        "rows_with_selected_spans": len(selected),
        "rows_negative_after_metadata": len(negative_after_metadata),
        "rows_with_shorter_transformed_payload": len(shorter_payload),
        "total_exact_hits": sum(row["exact_hit_count"] for row in rows),
        "total_positive_exact_hits": sum(row["positive_exact_hit_count"] for row in rows),
        "total_selected_spans": sum(row["selected_span_count"] for row in rows),
        "best_net_case": f"{best['corpus']}::{best['transform']}",
        "best_net_delta_bytes": best["net_with_metadata_bytes"],
        "best_prefix_case": f"{best_prefix['corpus']}::{best_prefix['transform']}",
        "best_prefix_observed": best_prefix["max_prefix_observed"],
        "best_prefix_ge_5_count": best_prefix["prefix_ge_5_count"],
        "conclusion": (
            "BWT/MTF preconditioners produced a metadata-positive negative-delta seed-span row."
            if negative_after_metadata
            else (
                "BWT/MTF preconditioners produced exact hits, but metadata still dominates."
                if exact
                else "BWT/MTF preconditioners did not produce exact seed-span rows."
            )
        ),
    }


def top_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            row["net_with_metadata_bytes"],
            -row["selected_span_count"],
            -row["exact_hit_count"],
            -row["max_prefix_observed"],
            -row["prefix_ge_5_count"],
            row["corpus"],
            row["transform"],
        ),
    )[:TOP_LIMIT]


def build_report() -> dict[str, Any]:
    transforms = transform_manifest()
    rows = [
        analyze_case(corpus, transform)
        for corpus in CORPUS_MATRIX
        for transform in transforms
    ]
    return {
        "generated_by": "scripts/generate_bwt_mtf_transform_probe.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "artifact_hashes": artifact_hashes(),
        "corpus_manifest_sha256": corpus_manifest_hash(),
        "transform_manifest_sha256": transform_manifest_hash(),
        "search_manifest_sha256": search_manifest_hash(),
        "search_manifest": search_manifest(),
        "corpora": CORPUS_MATRIX,
        "transforms": transforms,
        "rows": rows,
        "summary": summarize(rows),
    }


def write_report(payload: dict[str, Any]) -> None:
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary = payload["summary"]
    lines = [
        "# Telomere BWT/MTF Transform Probe",
        "",
        "Generated by `scripts/generate_bwt_mtf_transform_probe.py`.",
        "This is a bounded classic-preconditioner probe, not `.tlmr` format support.",
        "",
        f"Corpora: `{summary['corpus_count']}`.",
        f"Transforms: `{summary['transform_count']}`.",
        f"Rows: `{summary['row_count']}`.",
        f"Target spans scanned: `{summary['target_span_count']}`.",
        f"Rows with prefix >=5: `{summary['rows_with_prefix_ge_5']}`.",
        f"Rows with exact hits: `{summary['rows_with_exact_hits']}`.",
        f"Rows with selected spans: `{summary['rows_with_selected_spans']}`.",
        f"Rows negative after metadata: `{summary['rows_negative_after_metadata']}`.",
        f"Rows with shorter transformed payload: `{summary['rows_with_shorter_transformed_payload']}`.",
        f"Total exact hits: `{summary['total_exact_hits']}`.",
        f"Total selected spans: `{summary['total_selected_spans']}`.",
        f"Best net case: `{summary['best_net_case']}`.",
        f"Best net delta bytes: `{summary['best_net_delta_bytes']}`.",
        f"Best prefix case: `{summary['best_prefix_case']}`.",
        f"Best prefix observed: `{summary['best_prefix_observed']}`.",
        "",
        "## Summary",
        "",
        summary["conclusion"],
        "",
        "## Search Contract",
        "",
        f"- Hasher: `{HASHER}`.",
        f"- Max seed length: `{MAX_SEED_LEN}`.",
        f"- Span length: `{SPAN_LEN}`.",
        f"- Span step: `{SPAN_STEP}`.",
        "- Target block hashing: `false`.",
        "- Generated seed prefixes are compared directly against transformed bytes.",
        "- Every row proves BWT/MTF/RLE reversibility before search metrics are accepted.",
        "- Transform-only shortening is reported separately and is not counted as a Telomere seed-span win.",
        "- Promotion requires negative delta after metadata, or a clear prefix/exact-hit separation from existing transform families.",
        "",
        "## Top Rows",
        "",
        "| corpus | transform | family | transformed bytes | transform delta | metadata | p4 | p5 | p6 | exact | selected | net+metadata |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in top_rows(payload["rows"]):
        lines.append(
            "| {corpus} | {transform} | {transform_family} | {transformed_bytes} | "
            "{transform_length_delta_bytes} | {metadata_bytes} | {prefix_ge_4_count} | "
            "{prefix_ge_5_count} | {prefix_ge_6_count} | {exact_hit_count} | "
            "{selected_span_count} | {net_with_metadata_bytes} |".format(**row)
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- This artifact tests BWT/MTF/RLE as classic reversible preconditioners against the finite seed-output manifold.",
            "- BWT primary indexes and transform descriptors are charged as metadata before any promotion claim.",
            "- Shorter transformed payloads are ordinary transform effects; they are useful diagnostics, but not Lotus seed-span compression evidence.",
            "- Null exact-hit results mean the next move should be a genuinely new representation family or stronger controls, not format support.",
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not REPORT_JSON.exists() or not REPORT_MD.exists():
        raise SystemExit("generated BWT/MTF transform probe files are missing")
    payload = load_json(REPORT_JSON)
    if payload.get("generated_by") != "scripts/generate_bwt_mtf_transform_probe.py":
        raise SystemExit("bwt_mtf_transform_probe.json has wrong generated_by marker")
    if payload.get("artifact_hashes") != artifact_hashes():
        raise SystemExit("BWT/MTF transform probe artifact hashes are stale")
    if payload.get("corpus_manifest_sha256") != corpus_manifest_hash():
        raise SystemExit("BWT/MTF transform probe corpus manifest hash is stale")
    if payload.get("transform_manifest_sha256") != transform_manifest_hash():
        raise SystemExit("BWT/MTF transform probe transform manifest hash is stale")
    if payload.get("search_manifest_sha256") != search_manifest_hash():
        raise SystemExit("BWT/MTF transform probe search manifest hash is stale")
    if len(payload.get("rows", [])) != len(CORPUS_MATRIX) * len(transform_manifest()):
        raise SystemExit("BWT/MTF transform probe row count is stale")
    text = REPORT_MD.read_text(encoding="utf-8")
    for phrase in (
        "Telomere BWT/MTF Transform Probe",
        "classic-preconditioner probe",
        "Target block hashing: `false`",
        "proves BWT/MTF/RLE reversibility",
        "Transform-only shortening is reported separately",
    ):
        if phrase not in text:
            raise SystemExit(f"BWT_MTF_TRANSFORM_PROBE.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate generated report")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.check:
        check_report()
        return
    write_report(build_report())


if __name__ == "__main__":
    main()
