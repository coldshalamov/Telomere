#!/usr/bin/env python3
"""Search record/context-aware reversible transforms across structured corpora."""

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

import generate_corpus_generalization_probe
import generate_corpus_matrix
import generate_manifold_report
import generate_structural_transform_search


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
RECORD_CONTEXT_JSON = DOCS / "record_context_transform_search.json"
RECORD_CONTEXT_MD = DOCS / "RECORD_CONTEXT_TRANSFORM_SEARCH.md"

HASHER = "sha256"
MAX_SEED_LEN = 2
SPAN_LEN = 8
SPAN_STEP = 1
PREFIX_LADDER = (3, 4, 5, 6)
SEED_RECORD_OVERHEAD_BYTES = 4
TOP_LIMIT = 32

CORPUS_MATRIX: list[dict[str, Any]] = [
    {
        "name": "json",
        "kind": "record-structured",
        "note": "Generated JSON corpus from the main structured matrix.",
    },
    {
        "name": "csv",
        "kind": "field-delimited",
        "note": "CSV corpus with repeated field positions.",
    },
    {
        "name": "log",
        "kind": "record-log",
        "note": "Line-oriented log corpus with repeated context fields.",
    },
    {
        "name": "yaml",
        "kind": "record-structured",
        "note": "YAML corpus with indentation and colon-delimited fields.",
    },
    {
        "name": "toml",
        "kind": "record-structured",
        "note": "TOML corpus with repeated key/value record shape.",
    },
    {
        "name": "binary-tlv",
        "kind": "binary-record",
        "note": "Binary TLV control where text delimiter transforms should not overfit.",
    },
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_hashes() -> dict[str, str]:
    return {
        "corpus_matrix_sha256": sha256(DOCS / "corpus_matrix.json"),
        "corpus_generalization_probe_sha256": sha256(
            DOCS / "corpus_generalization_probe.json"
        ),
        "structural_transform_search_sha256": sha256(
            DOCS / "structural_transform_search.json"
        ),
    }


def transform_manifest() -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = [
        {
            "name": "identity",
            "family": "identity",
            "parameter": None,
            "description": "No transform baseline.",
        }
    ]
    candidates.extend(
        {
            "name": f"record-transpose-g{group_size}",
            "family": "record-transpose",
            "parameter": {"group_size": group_size},
            "description": "Column-major byte transpose across groups of records.",
        }
        for group_size in (4, 8, 16)
    )
    candidates.extend(
        {
            "name": f"field-column-{label}",
            "family": "field-column",
            "parameter": {"delimiter_hex": delimiter.hex(), "label": label},
            "description": "Group same-position delimiter fields column-major.",
        }
        for label, delimiter in (
            ("comma", b","),
            ("colon", b":"),
            ("equals", b"="),
            ("space", b" "),
            ("pipe", b"|"),
        )
    )
    candidates.extend(
        {
            "name": f"fixed-width-column-w{width}",
            "family": "fixed-width-column",
            "parameter": {"width": width},
            "description": "Column-major transpose over fixed-width records.",
        }
        for width in (16, 32, 64)
    )
    candidates.extend(
        {
            "name": f"record-delta-lag{lag}",
            "family": "record-delta",
            "parameter": {"lag": lag},
            "description": "Delimiter-preserving byte deltas against previous records.",
        }
        for lag in (1, 2)
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
        "match_rule": "generated seed prefixes are compared directly against transformed bytes",
        "metadata_policy": "each transform row carries an estimated metadata byte cost before promotion",
        "scope": "record/context-aware transform research artifact only; not .tlmr format support",
    }


def search_manifest_hash() -> str:
    payload = json.dumps(search_manifest(), sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def corpus_bytes(name: str) -> bytes:
    return generate_corpus_matrix.corpus_bytes(name)


def split_records(data: bytes) -> list[bytes]:
    if not data:
        return []
    return data.splitlines(keepends=True)


def split_line_ending(record: bytes) -> tuple[bytes, bytes]:
    if record.endswith(b"\r\n"):
        return record[:-2], b"\r\n"
    if record.endswith(b"\n"):
        return record[:-1], b"\n"
    if record.endswith(b"\r"):
        return record[:-1], b"\r"
    return record, b""


def metadata_len_prefix_bytes(lengths: list[int]) -> int:
    return sum(2 if length <= 0xFFFF else 4 for length in lengths)


def record_transpose(data: bytes, group_size: int) -> tuple[bytes, bytes, int]:
    records = split_records(data)
    lengths = [len(record) for record in records]
    out = bytearray()
    for offset in range(0, len(records), group_size):
        group = records[offset : offset + group_size]
        max_len = max((len(record) for record in group), default=0)
        for pos in range(max_len):
            for record in group:
                if pos < len(record):
                    out.append(record[pos])
    payload = bytes(out)
    restored = invert_record_transpose(payload, lengths, group_size)
    metadata_bytes = metadata_len_prefix_bytes(lengths) + math.ceil(
        len(records) / max(1, group_size)
    )
    return payload, restored, metadata_bytes


def invert_record_transpose(payload: bytes, lengths: list[int], group_size: int) -> bytes:
    records: list[bytes] = []
    cursor = 0
    for offset in range(0, len(lengths), group_size):
        group_lengths = lengths[offset : offset + group_size]
        buffers = [bytearray() for _ in group_lengths]
        max_len = max(group_lengths, default=0)
        for pos in range(max_len):
            for idx, length in enumerate(group_lengths):
                if pos < length:
                    buffers[idx].append(payload[cursor])
                    cursor += 1
        records.extend(bytes(buffer) for buffer in buffers)
    if cursor != len(payload):
        raise RuntimeError("record transpose inverse did not consume payload")
    return b"".join(records)


def field_column(data: bytes, delimiter: bytes) -> tuple[bytes, bytes, int]:
    records = split_records(data)
    field_rows: list[list[bytes]] = []
    endings: list[bytes] = []
    for record in records:
        body, ending = split_line_ending(record)
        field_rows.append(body.split(delimiter))
        endings.append(ending)

    max_fields = max((len(row) for row in field_rows), default=0)
    out = bytearray()
    field_lengths: list[list[int]] = [[len(field) for field in row] for row in field_rows]
    for field_idx in range(max_fields):
        for row in field_rows:
            if field_idx < len(row):
                out.extend(row[field_idx])

    payload = bytes(out)
    restored = invert_field_column(payload, delimiter, field_lengths, endings)
    metadata_bytes = (
        metadata_len_prefix_bytes([length for row in field_lengths for length in row])
        + len(field_rows)
        + len(endings)
    )
    return payload, restored, metadata_bytes


def invert_field_column(
    payload: bytes,
    delimiter: bytes,
    field_lengths: list[list[int]],
    endings: list[bytes],
) -> bytes:
    max_fields = max((len(row) for row in field_lengths), default=0)
    fields = [[b"" for _ in row] for row in field_lengths]
    cursor = 0
    for field_idx in range(max_fields):
        for row_idx, row_lengths in enumerate(field_lengths):
            if field_idx >= len(row_lengths):
                continue
            length = row_lengths[field_idx]
            fields[row_idx][field_idx] = payload[cursor : cursor + length]
            cursor += length
    if cursor != len(payload):
        raise RuntimeError("field-column inverse did not consume payload")
    return b"".join(delimiter.join(row) + ending for row, ending in zip(fields, endings))


def fixed_width_column(data: bytes, width: int) -> tuple[bytes, bytes, int]:
    full_len = (len(data) // width) * width
    rows = [data[offset : offset + width] for offset in range(0, full_len, width)]
    remainder = data[full_len:]
    out = bytearray()
    for col in range(width):
        for row in rows:
            out.append(row[col])
    out.extend(remainder)
    payload = bytes(out)
    restored = invert_fixed_width_column(payload, width, len(rows), len(remainder))
    metadata_bytes = 5
    return payload, restored, metadata_bytes


def invert_fixed_width_column(
    payload: bytes, width: int, row_count: int, remainder_len: int
) -> bytes:
    matrix_len = width * row_count
    matrix_payload = payload[:matrix_len]
    remainder = payload[matrix_len : matrix_len + remainder_len]
    rows = [bytearray(width) for _ in range(row_count)]
    cursor = 0
    for col in range(width):
        for row in rows:
            row[col] = matrix_payload[cursor]
            cursor += 1
    if cursor != len(matrix_payload):
        raise RuntimeError("fixed-width inverse did not consume matrix payload")
    return b"".join(bytes(row) for row in rows) + remainder


def record_delta(data: bytes, lag: int) -> tuple[bytes, bytes, int]:
    records = split_records(data)
    lengths = [len(record) for record in records]
    out = bytearray()
    for idx, record in enumerate(records):
        if idx < lag:
            out.extend(record)
            continue
        previous = records[idx - lag]
        for pos, value in enumerate(record):
            if pos < len(previous):
                out.append((value - previous[pos]) & 0xFF)
            else:
                out.append(value)
    payload = bytes(out)
    restored = invert_record_delta(payload, lengths, lag)
    metadata_bytes = metadata_len_prefix_bytes(lengths) + 1
    return payload, restored, metadata_bytes


def invert_record_delta(payload: bytes, lengths: list[int], lag: int) -> bytes:
    records: list[bytes] = []
    cursor = 0
    for idx, length in enumerate(lengths):
        encoded = payload[cursor : cursor + length]
        cursor += length
        if idx < lag:
            records.append(encoded)
            continue
        previous = records[idx - lag]
        restored = bytearray()
        for pos, value in enumerate(encoded):
            if pos < len(previous):
                restored.append((value + previous[pos]) & 0xFF)
            else:
                restored.append(value)
        records.append(bytes(restored))
    if cursor != len(payload):
        raise RuntimeError("record-delta inverse did not consume payload")
    return b"".join(records)


def apply_transform(candidate: dict[str, Any], data: bytes) -> tuple[bytes, int]:
    family = candidate["family"]
    parameter = candidate["parameter"]
    if family == "identity":
        return data, 0
    if family == "record-transpose":
        payload, restored, metadata_bytes = record_transpose(data, parameter["group_size"])
    elif family == "field-column":
        payload, restored, metadata_bytes = field_column(
            data, bytes.fromhex(parameter["delimiter_hex"])
        )
    elif family == "fixed-width-column":
        payload, restored, metadata_bytes = fixed_width_column(data, parameter["width"])
    elif family == "record-delta":
        payload, restored, metadata_bytes = record_delta(data, parameter["lag"])
    else:
        raise ValueError(family)
    if restored != data:
        raise RuntimeError(f"{candidate['name']} failed reversibility proof")
    return payload, metadata_bytes


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
        "total_exact_hits": sum(row["exact_hit_count"] for row in rows),
        "total_positive_exact_hits": sum(row["positive_exact_hit_count"] for row in rows),
        "total_selected_spans": sum(row["selected_span_count"] for row in rows),
        "best_net_case": f"{best['corpus']}::{best['transform']}",
        "best_net_delta_bytes": best["net_with_metadata_bytes"],
        "best_prefix_case": f"{best_prefix['corpus']}::{best_prefix['transform']}",
        "best_prefix_observed": best_prefix["max_prefix_observed"],
        "best_prefix_ge_5_count": best_prefix["prefix_ge_5_count"],
        "conclusion": (
            "Record/context transforms produced a metadata-positive negative-delta row."
            if negative_after_metadata
            else (
                "Record/context transforms produced exact hits, but metadata still dominates."
                if exact
                else "Record/context transforms did not produce exact seed-span rows."
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
        "generated_by": "scripts/generate_record_context_transform_search.py",
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
    RECORD_CONTEXT_JSON.write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    summary = payload["summary"]
    lines = [
        "# Telomere Record Context Transform Search",
        "",
        "Generated by `scripts/generate_record_context_transform_search.py`.",
        "This is a record/context-aware reversible transform probe, not `.tlmr` format support.",
        "",
        f"Corpora: `{summary['corpus_count']}`.",
        f"Transforms: `{summary['transform_count']}`.",
        f"Rows: `{summary['row_count']}`.",
        f"Target spans scanned: `{summary['target_span_count']}`.",
        f"Rows with prefix >=5: `{summary['rows_with_prefix_ge_5']}`.",
        f"Rows with exact hits: `{summary['rows_with_exact_hits']}`.",
        f"Rows with selected spans: `{summary['rows_with_selected_spans']}`.",
        f"Rows negative after metadata: `{summary['rows_negative_after_metadata']}`.",
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
        "- Every row proves transform reversibility before search metrics are accepted.",
        "- Promotion requires negative delta after metadata, or a clear prefix/exact-hit separation from existing transform families.",
        "",
        "## Top Rows",
        "",
        "| corpus | transform | family | bytes | metadata | p4 | p5 | p6 | exact | selected | net+metadata |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in top_rows(payload["rows"]):
        lines.append(
            "| {corpus} | {transform} | {transform_family} | {transformed_bytes} | "
            "{metadata_bytes} | {prefix_ge_4_count} | {prefix_ge_5_count} | "
            "{prefix_ge_6_count} | {exact_hit_count} | {selected_span_count} | "
            "{net_with_metadata_bytes} |".format(**row)
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- These transforms are deliberately record/context-aware: line transposes, field-column grouping, fixed-width columns, and delimiter-preserving record deltas.",
            "- Metadata is charged per row so a transform must overcome its own descriptor cost before it can become an engine candidate.",
            "- This artifact is separate from the structural/affine/periodic/fifth-byte lanes to avoid double-counting the same transform family.",
            "- Null exact-hit results mean the next move should be new corpus hypotheses or better record descriptors, not broader claims.",
        ]
    )
    RECORD_CONTEXT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not RECORD_CONTEXT_JSON.exists() or not RECORD_CONTEXT_MD.exists():
        raise SystemExit("generated record context transform search files are missing")
    payload = load_json(RECORD_CONTEXT_JSON)
    if payload.get("generated_by") != "scripts/generate_record_context_transform_search.py":
        raise SystemExit("record_context_transform_search.json has wrong generated_by marker")
    if payload.get("artifact_hashes") != artifact_hashes():
        raise SystemExit("record context transform search artifact hashes are stale")
    if payload.get("corpus_manifest_sha256") != corpus_manifest_hash():
        raise SystemExit("record context transform search corpus manifest hash is stale")
    if payload.get("transform_manifest_sha256") != transform_manifest_hash():
        raise SystemExit("record context transform search transform manifest hash is stale")
    if payload.get("search_manifest_sha256") != search_manifest_hash():
        raise SystemExit("record context transform search search manifest hash is stale")
    if len(payload.get("rows", [])) != len(CORPUS_MATRIX) * len(transform_manifest()):
        raise SystemExit("record context transform search row count is stale")
    text = RECORD_CONTEXT_MD.read_text(encoding="utf-8")
    for phrase in (
        "Telomere Record Context Transform Search",
        "record/context-aware reversible transform probe",
        "Target block hashing: `false`",
        "proves transform reversibility",
        "Metadata is charged per row",
    ):
        if phrase not in text:
            raise SystemExit(f"RECORD_CONTEXT_TRANSFORM_SEARCH.md missing phrase: {phrase}")


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
