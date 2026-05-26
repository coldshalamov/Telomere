#!/usr/bin/env python3
"""Search reversible token/dictionary transforms across text corpora."""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import math
import re
from collections import Counter
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import generate_corpus_matrix
import generate_manifold_report
import generate_record_context_transform_search


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
TOKEN_JSON = DOCS / "token_dictionary_transform_search.json"
TOKEN_MD = DOCS / "TOKEN_DICTIONARY_TRANSFORM_SEARCH.md"

HASHER = "sha256"
MAX_SEED_LEN = 2
SPAN_LEN = 8
SPAN_STEP = 1
PREFIX_LADDER = (3, 4, 5, 6)
SEED_RECORD_OVERHEAD_BYTES = 4
TOP_LIMIT = 32
TOKEN_RE = re.compile(rb"[A-Za-z_][A-Za-z0-9_-]*|\d+")
MARKER = b"\x00"

CORPUS_MATRIX: list[dict[str, Any]] = [
    {"name": "json", "kind": "structured-text"},
    {"name": "markdown", "kind": "prose-markup"},
    {"name": "csv", "kind": "field-delimited"},
    {"name": "rust-like", "kind": "source-like"},
    {"name": "html", "kind": "markup"},
    {"name": "python-like", "kind": "source-like"},
    {"name": "sql", "kind": "query"},
    {"name": "toml", "kind": "config"},
    {"name": "xml", "kind": "markup"},
    {"name": "log", "kind": "record-log"},
    {"name": "yaml", "kind": "config"},
    {"name": "javascript-like", "kind": "source-like"},
    {"name": "graphql", "kind": "schema-query"},
    {"name": "nginx-conf", "kind": "config"},
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_hashes() -> dict[str, str]:
    return {
        "corpus_matrix_sha256": sha256(DOCS / "corpus_matrix.json"),
        "record_context_transform_search_sha256": sha256(
            DOCS / "record_context_transform_search.json"
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
            "name": f"token-preserve-top{limit}",
            "family": "token-preserve",
            "parameter": {"limit": limit},
            "description": "Replace repeated lexemes with marker+dictionary-id while preserving separators in stream.",
        }
        for limit in (32, 64, 128)
    )
    candidates.extend(
        {
            "name": f"token-stream-top{limit}",
            "family": "token-stream",
            "parameter": {"limit": limit},
            "description": "Emit only dictionary token ids in token order; separators and unknown tokens are charged as metadata.",
        }
        for limit in (32, 64, 128)
    )
    candidates.extend(
        {
            "name": f"token-column-stream-top{limit}",
            "family": "token-column-stream",
            "parameter": {"limit": limit},
            "description": "Emit dictionary token ids column-major by line token position; row structure is charged as metadata.",
        }
        for limit in (32, 64)
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
        "match_rule": "generated seed prefixes are compared directly against token-transformed bytes",
        "metadata_policy": "dictionary, separators, unknown tokens, and row structure are charged before promotion",
        "scope": "token/dictionary transform research artifact only; not .tlmr format support",
    }


def search_manifest_hash() -> str:
    payload = json.dumps(search_manifest(), sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def corpus_bytes(name: str) -> bytes:
    return generate_corpus_matrix.corpus_bytes(name)


def token_segments(data: bytes) -> list[tuple[bool, bytes]]:
    segments: list[tuple[bool, bytes]] = []
    cursor = 0
    for match in TOKEN_RE.finditer(data):
        if match.start() > cursor:
            segments.append((False, data[cursor : match.start()]))
        segments.append((True, match.group(0)))
        cursor = match.end()
    if cursor < len(data):
        segments.append((False, data[cursor:]))
    return [(is_token, value) for is_token, value in segments if value]


def token_dictionary(data: bytes, limit: int) -> list[bytes]:
    counts = Counter(
        value for is_token, value in token_segments(data) if is_token and len(value) >= 2
    )
    return [
        token
        for token, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        if count >= 2
    ][:limit]


def dictionary_metadata_bytes(dictionary: list[bytes]) -> int:
    return sum(1 + len(token) for token in dictionary) + 1


def token_preserve(data: bytes, limit: int) -> tuple[bytes, bytes, int]:
    if MARKER in data:
        return data, data, 0
    dictionary = token_dictionary(data, limit)
    lookup = {token: idx for idx, token in enumerate(dictionary)}
    out = bytearray()
    for is_token, value in token_segments(data):
        if is_token and value in lookup:
            out.extend(MARKER)
            out.append(lookup[value])
        else:
            out.extend(value)
    payload = bytes(out)
    restored = invert_token_preserve(payload, dictionary)
    return payload, restored, dictionary_metadata_bytes(dictionary)


def invert_token_preserve(payload: bytes, dictionary: list[bytes]) -> bytes:
    out = bytearray()
    cursor = 0
    while cursor < len(payload):
        if payload[cursor : cursor + 1] == MARKER:
            cursor += 1
            out.extend(dictionary[payload[cursor]])
            cursor += 1
        else:
            out.append(payload[cursor])
            cursor += 1
    return bytes(out)


def token_stream(data: bytes, limit: int) -> tuple[bytes, bytes, int]:
    dictionary = token_dictionary(data, limit)
    lookup = {token: idx for idx, token in enumerate(dictionary)}
    payload = bytearray()
    metadata_bytes = dictionary_metadata_bytes(dictionary)
    restored = bytearray()
    for is_token, value in token_segments(data):
        if not is_token:
            metadata_bytes += len(value) + 2
            restored.extend(value)
            continue
        if value in lookup:
            payload.append(lookup[value])
            restored.extend(dictionary[lookup[value]])
        else:
            metadata_bytes += len(value) + 2
            restored.extend(value)
    metadata_bytes += math.ceil(len(token_segments(data)) / 8)
    return bytes(payload), bytes(restored), metadata_bytes


def split_lines(data: bytes) -> list[bytes]:
    return data.splitlines(keepends=True) if data else []


def token_column_stream(data: bytes, limit: int) -> tuple[bytes, bytes, int]:
    dictionary = token_dictionary(data, limit)
    lookup = {token: idx for idx, token in enumerate(dictionary)}
    rows = [token_segments(line) for line in split_lines(data)]
    token_rows = [
        [(value in lookup, lookup.get(value, -1), value) for is_token, value in row if is_token]
        for row in rows
    ]
    max_cols = max((len(row) for row in token_rows), default=0)
    payload = bytearray()
    for col in range(max_cols):
        for row in token_rows:
            if col < len(row) and row[col][0]:
                payload.append(row[col][1])

    metadata_bytes = dictionary_metadata_bytes(dictionary)
    metadata_bytes += sum(len(line) + 2 for line in split_lines(data))
    metadata_bytes += sum(len(value) + 2 for row in token_rows for known, _, value in row if not known)
    metadata_bytes += math.ceil(sum(len(row) for row in token_rows) / 8)
    restored = invert_token_column_stream(bytes(payload), rows, dictionary, lookup)
    return bytes(payload), restored, metadata_bytes


def invert_token_column_stream(
    payload: bytes,
    rows: list[list[tuple[bool, bytes]]],
    dictionary: list[bytes],
    lookup: dict[bytes, int],
) -> bytes:
    token_positions: list[list[tuple[int, bytes]]] = []
    for row in rows:
        token_positions.append(
            [(idx, value) for idx, (is_token, value) in enumerate(row) if is_token]
        )
    max_cols = max((len(row) for row in token_positions), default=0)
    replacements: dict[tuple[int, int], bytes] = {}
    cursor = 0
    for col in range(max_cols):
        for row_idx, row in enumerate(token_positions):
            if col >= len(row):
                continue
            segment_idx, original = row[col]
            if original in lookup:
                replacements[(row_idx, segment_idx)] = dictionary[payload[cursor]]
                cursor += 1
            else:
                replacements[(row_idx, segment_idx)] = original
    if cursor != len(payload):
        raise RuntimeError("token-column inverse did not consume payload")
    out = bytearray()
    for row_idx, row in enumerate(rows):
        for segment_idx, (_, value) in enumerate(row):
            out.extend(replacements.get((row_idx, segment_idx), value))
    return bytes(out)


def apply_transform(candidate: dict[str, Any], data: bytes) -> tuple[bytes, int]:
    family = candidate["family"]
    parameter = candidate["parameter"]
    if family == "identity":
        return data, 0
    if family == "token-preserve":
        payload, restored, metadata_bytes = token_preserve(data, parameter["limit"])
    elif family == "token-stream":
        payload, restored, metadata_bytes = token_stream(data, parameter["limit"])
    elif family == "token-column-stream":
        payload, restored, metadata_bytes = token_column_stream(data, parameter["limit"])
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
        "metadata_bytes": metadata_bytes,
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
            "Token dictionary transforms produced a metadata-positive negative-delta row."
            if negative_after_metadata
            else (
                "Token dictionary transforms produced exact hits, but metadata still dominates."
                if exact
                else "Token dictionary transforms did not produce exact seed-span rows."
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
        "generated_by": "scripts/generate_token_dictionary_transform_search.py",
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
    TOKEN_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary = payload["summary"]
    lines = [
        "# Telomere Token Dictionary Transform Search",
        "",
        "Generated by `scripts/generate_token_dictionary_transform_search.py`.",
        "This is a token/dictionary reversible transform probe, not `.tlmr` format support.",
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
        "- Generated seed prefixes are compared directly against token-transformed bytes.",
        "- Every row proves transform reversibility before search metrics are accepted.",
        "- Dictionary, separator, unknown-token, and row-structure metadata is charged before promotion.",
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
            "- These transforms test lexeme dictionary replacement and token-order streams, a different family from bytewise structural, affine, periodic, and record-layout transforms.",
            "- Metadata is deliberately charged because a dictionary transform must store enough information to invert exactly.",
            "- Null exact-hit results mean token canonicalization is not yet a compressor path, even if transformed bytes become shorter or more regular.",
        ]
    )
    TOKEN_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not TOKEN_JSON.exists() or not TOKEN_MD.exists():
        raise SystemExit("generated token dictionary transform search files are missing")
    payload = load_json(TOKEN_JSON)
    if payload.get("generated_by") != "scripts/generate_token_dictionary_transform_search.py":
        raise SystemExit("token_dictionary_transform_search.json has wrong generated_by marker")
    if payload.get("artifact_hashes") != artifact_hashes():
        raise SystemExit("token dictionary transform search artifact hashes are stale")
    if payload.get("corpus_manifest_sha256") != corpus_manifest_hash():
        raise SystemExit("token dictionary transform search corpus manifest hash is stale")
    if payload.get("transform_manifest_sha256") != transform_manifest_hash():
        raise SystemExit("token dictionary transform search transform manifest hash is stale")
    if payload.get("search_manifest_sha256") != search_manifest_hash():
        raise SystemExit("token dictionary transform search search manifest hash is stale")
    if len(payload.get("rows", [])) != len(CORPUS_MATRIX) * len(transform_manifest()):
        raise SystemExit("token dictionary transform search row count is stale")
    text = TOKEN_MD.read_text(encoding="utf-8")
    for phrase in (
        "Telomere Token Dictionary Transform Search",
        "token/dictionary reversible transform probe",
        "Target block hashing: `false`",
        "proves transform reversibility",
        "Dictionary, separator, unknown-token, and row-structure metadata is charged",
    ):
        if phrase not in text:
            raise SystemExit(f"TOKEN_DICTIONARY_TRANSFORM_SEARCH.md missing phrase: {phrase}")


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
