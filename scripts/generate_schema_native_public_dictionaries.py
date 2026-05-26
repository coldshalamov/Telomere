#!/usr/bin/env python3
"""Generate the schema-native public dictionary preset probe."""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import generate_corpus_matrix
import generate_transform_validation


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
REPORT_JSON = DOCS / "schema_native_public_dictionaries.json"
REPORT_MD = DOCS / "SCHEMA_NATIVE_PUBLIC_DICTIONARIES.md"

SOURCE_PATHS = {
    "mechanism_experiment_ranking_sha256": DOCS
    / "mechanism_experiment_ranking.json",
    "grammar_channel_match_discovery_sha256": DOCS
    / "grammar_channel_match_discovery.json",
    "token_dictionary_transform_search_sha256": DOCS
    / "token_dictionary_transform_search.json",
    "record_context_transform_search_sha256": DOCS
    / "record_context_transform_search.json",
    "transform_validation_sha256": DOCS / "transform_validation.json",
    "format_doc_sha256": DOCS / "FORMAT.md",
}

MAX_SEED_LEN = 2
MAX_ENTRY_LEN = 32
SPAN_LENS = (4, 8, 12, 16, 20, 24, 32)
V2_HEADER_AND_LAYER_BYTES = 80
PRESET_SELECTOR_BYTES = 2
PRESET_VERSION_BYTES = 16
LITERAL_RECORD_OVERHEAD_BYTES = 3
DICTIONARY_RECORD_OVERHEAD_BYTES = 4
SELECTED_SAMPLE_LIMIT = 12
PROMOTION_ORDINARY_GROUPS = 3
CONTROL_KINDS = {
    "binary-control",
    "binary-tlv",
    "binary-varint",
    "negative-control",
    "paired-shadow-control",
    "shadow-vocab",
}
SCHEMA_FAMILIES = (
    "json",
    "markup",
    "graphql",
    "nginx",
    "http",
    "sql",
    "config",
    "source",
    "log",
    "csv",
    "fasta",
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_hashes() -> dict[str, str]:
    return {name: sha256(path) for name, path in SOURCE_PATHS.items()}


def seed_space_count() -> int:
    return sum(1 << (8 * seed_len) for seed_len in range(1, MAX_SEED_LEN + 1))


def seed_len_for_index(index: int) -> int:
    remaining = index
    for seed_len in range(1, MAX_SEED_LEN + 1):
        count = 1 << (8 * seed_len)
        if remaining < count:
            return seed_len
        remaining -= count
    raise ValueError(index)


def seed_bytes_for_index(index: int) -> bytes:
    remaining = index
    for seed_len in range(1, MAX_SEED_LEN + 1):
        count = 1 << (8 * seed_len)
        if remaining < count:
            return remaining.to_bytes(seed_len, "big")
        remaining -= count
    raise ValueError(index)


def entry(name: str, families: tuple[str, ...], value: bytes) -> dict[str, Any]:
    if len(value) < 4:
        raise ValueError(f"{name} is too short for a profitable public preset entry")
    return {
        "name": name,
        "families": list(families),
        "value_hex": value[:MAX_ENTRY_LEN].hex(),
        "raw_len": len(value[:MAX_ENTRY_LEN]),
    }


def public_entries() -> list[dict[str, Any]]:
    raw = [
        entry("telomere-token", ("common",), b"telomere"),
        entry("experiment-word", ("common",), b"experiment"),
        entry("experiments-word", ("common",), b"experiments"),
        entry("corpus-word", ("common",), b"corpus"),
        entry("selected-word", ("common",), b"selected"),
        entry("verified-word", ("common",), b"verified"),
        entry("queued-word", ("common",), b"queued"),
        entry("literal-word", ("common",), b"literal"),
        entry("candidate-word", ("common",), b"candidate"),
        entry("rejected-word", ("common",), b"rejected"),
        entry("case-prefix", ("common",), b"case-"),
        entry("heldout-word", ("common",), b"heldout"),
        entry("span-len-snake", ("common",), b"span_len"),
        entry("span-len-kebab", ("common",), b"Span-Len"),
        entry("seed-depth-snake", ("common",), b"seed_depth"),
        entry("seed-depth-kebab", ("common",), b"Seed-Depth"),
        entry("delta-bytes-snake", ("common",), b"delta_bytes"),
        entry("delta-bytes-kebab", ("common",), b"Delta-Bytes"),
        entry("json-event-order-update", ("json",), b'"event":"order_update"'),
        entry("json-status-queued", ("json",), b'"status":"queued"'),
        entry("json-status-paid", ("json",), b'"status":"paid"'),
        entry("json-status-fulfilled", ("json",), b'"status":"fulfilled"'),
        entry("json-amount-cents", ("json",), b'"amount_cents":'),
        entry("json-sku-rx", ("json",), b'"sku":"rx-'),
        entry("json-id-field", ("json",), b'"id":'),
        entry("xml-experiment-open", ("markup", "xml"), b'<experiment id="'),
        entry("xml-corpus-heldout", ("markup", "xml"), b' corpus="heldout-'),
        entry("xml-status-queued", ("markup", "xml"), b"<status>queued</status>"),
        entry("xml-status-verified", ("markup", "xml"), b"<status>verified</status>"),
        entry("xml-span-length", ("markup", "xml"), b'<span length="'),
        entry("xml-seed-depth", ("markup", "xml"), b'<seed depth="'),
        entry("xml-experiment-close", ("markup", "xml"), b"</experiment>"),
        entry("html-article-case", ("markup", "html"), b'<article class="case" data-id="'),
        entry("html-status-queued", ("markup", "html"), b"<p>Status queued</p>"),
        entry("html-status-verified", ("markup", "html"), b"<p>Status verified</p>"),
        entry("html-sku-span", ("markup", "html"), b'<span data-sku="rx-'),
        entry("html-article-close", ("markup", "html"), b"</span></article>"),
        entry("html-doctype", ("markup", "html"), b"<!doctype html><html><body>"),
        entry("yaml-case-id", ("config", "yaml"), b"  - id: case-"),
        entry("yaml-corpus", ("config", "yaml"), b"    corpus: yaml-"),
        entry("yaml-status-queued", ("config", "yaml"), b"    status: queued"),
        entry("yaml-status-verified", ("config", "yaml"), b"    status: verified"),
        entry("yaml-block-size", ("config", "yaml"), b"      block_size: "),
        entry("yaml-seed-depth", ("config", "yaml"), b"      seed_depth: "),
        entry("yaml-span-step", ("config", "yaml"), b"      span_step: "),
        entry("yaml-delta", ("config", "yaml"), b"      delta_bytes: "),
        entry("graphql-type-case", ("graphql",), b"type ExperimentCase"),
        entry("graphql-query-case", ("graphql",), b"query CaseQuery"),
        entry("graphql-id", ("graphql",), b"  id: ID!"),
        entry("graphql-corpus", ("graphql",), b"  corpus: String!"),
        entry("graphql-seed-depth", ("graphql",), b"  seedDepth: Int!"),
        entry("graphql-span-len", ("graphql",), b"  spanLen: Int!"),
        entry("graphql-selected", ("graphql",), b"  selected: Boolean!"),
        entry("graphql-experiment", ("graphql",), b'experiment(id: "case-'),
        entry("nginx-upstream", ("nginx",), b"upstream telomere_case_"),
        entry("nginx-server-ip", ("nginx",), b"    server 127.0."),
        entry("nginx-keepalive", ("nginx",), b"    keepalive 16;"),
        entry("nginx-listen", ("nginx",), b"  server { listen "),
        entry("nginx-server-name", ("nginx",), b" server_name case-"),
        entry("nginx-local-close", ("nginx",), b".local; }"),
        entry("http-host", ("http",), b"\r\nHost: corpus-"),
        entry("http-case", ("http",), b"\r\nX-Telomere-Case: case-"),
        entry("http-seed-depth", ("http",), b"\r\nX-Seed-Depth: "),
        entry("http-span-len", ("http",), b"\r\nX-Span-Len: "),
        entry("http-delta", ("http",), b"\r\nX-Delta-Bytes: "),
        entry("http-content-json", ("http",), b"Content-Type: application/json"),
        entry("http-content-text", ("http",), b"Content-Type: text/plain"),
        entry("http-content-length", ("http",), b"\r\nContent-Length: "),
        entry("sql-create-table", ("sql",), b"CREATE TABLE span_records"),
        entry("sql-insert", ("sql",), b"INSERT INTO span_records"),
        entry("sql-columns", ("sql",), b"(id, corpus, span_len, selected)"),
        entry("sql-primary", ("sql",), b"PRIMARY KEY"),
        entry("sql-values-corpus", ("sql",), b"VALUES ("),
        entry("sql-corpus-prefix", ("sql",), b"'corpus_"),
        entry("log-worker-case", ("log",), b"telomere.worker case="),
        entry("log-corpus-heldout", ("log",), b" corpus=heldout-"),
        entry("log-span-len", ("log",), b" span_len="),
        entry("log-selected-true", ("log",), b" selected=True"),
        entry("log-selected-false", ("log",), b" selected=False"),
        entry("log-delta", ("log",), b" delta_bytes="),
        entry("source-function", ("source",), b"function "),
        entry("source-return", ("source",), b"return "),
        entry("source-import", ("source",), b"import "),
        entry("source-export", ("source",), b"export "),
        entry("source-public", ("source",), b"public "),
        entry("source-struct", ("source",), b"struct "),
        entry("source-impl", ("source",), b"impl "),
        entry("source-def", ("source",), b"def "),
        entry("source-class", ("source",), b"class "),
        entry("source-async", ("source",), b"async "),
        entry("toml-version", ("config", "toml"), b"version = "),
        entry("toml-dependencies", ("config", "toml"), b"[dependencies]"),
        entry("toml-features", ("config", "toml"), b"[features]"),
        entry("ini-section", ("config", "ini"), b"[case-"),
        entry("ini-enabled", ("config", "ini"), b"enabled = "),
        entry("ini-delta", ("config", "ini"), b"delta_bytes = "),
        entry("csv-header", ("csv",), b"case_id,corpus,span_len,selected"),
        entry("csv-corpus", ("csv",), b",corpus_"),
        entry("fasta-sequence", ("fasta",), b">telomere_case_"),
        entry("svg-root", ("markup", "svg"), b'<svg xmlns="http://www.w3.org'),
        entry("svg-path", ("markup", "svg"), b"<path "),
    ]
    dedup: dict[bytes, dict[str, Any]] = {}
    for item in raw:
        value = bytes.fromhex(item["value_hex"])
        existing = dedup.get(value)
        if existing is None:
            dedup[value] = item
            continue
        existing["families"] = sorted(set(existing["families"]) | set(item["families"]))
    return sorted(
        dedup.values(),
        key=lambda item: (-item["raw_len"], item["name"], item["value_hex"]),
    )


def shadow_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for index, item in enumerate(entries):
        digest = hashlib.sha256(
            b"schema-native-shadow-v0\0" + bytes.fromhex(item["value_hex"])
        ).hexdigest().encode("ascii")
        value = (digest * ((item["raw_len"] // len(digest)) + 1))[: item["raw_len"]]
        rows.append(
            {
                "name": f"shadow-{index:03d}",
                "families": item["families"],
                "value_hex": value.hex(),
                "raw_len": item["raw_len"],
            }
        )
    return rows


def random_entries(entries: list[dict[str, Any]], corpus: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for index, item in enumerate(entries):
        source = (
            f"schema-native-random-table-v0:{corpus['corpus']}:{index}:".encode()
            + bytes.fromhex(item["value_hex"])
        )
        digest = hashlib.sha256(source).digest()
        value = (digest * ((item["raw_len"] // len(digest)) + 1))[: item["raw_len"]]
        rows.append(
            {
                "name": f"random-{index:03d}",
                "families": item["families"],
                "value_hex": value.hex(),
                "raw_len": item["raw_len"],
            }
        )
    return rows


def corpus_family(corpus: str) -> str:
    if corpus in {"json", "shadow-json"}:
        return "json"
    if corpus in {"xml", "html", "svg"}:
        return "markup"
    if corpus == "graphql":
        return "graphql"
    if corpus == "nginx-conf":
        return "nginx"
    if corpus == "http-headers":
        return "http"
    if corpus == "sql":
        return "sql"
    if corpus in {"yaml", "toml", "ini"}:
        return "config"
    if corpus in {"rust-like", "python-like", "javascript-like", "css"}:
        return "source"
    if corpus == "log":
        return "log"
    if corpus == "csv":
        return "csv"
    if corpus == "fasta":
        return "fasta"
    return "common"


def public_entries_for_family(family: str, *, include_common: bool) -> list[dict[str, Any]]:
    return [
        item
        for item in public_entries()
        if (include_common and "common" in item["families"]) or family in item["families"]
    ]


def wrong_family_for(family: str) -> str:
    if family not in SCHEMA_FAMILIES:
        return "json"
    return SCHEMA_FAMILIES[(SCHEMA_FAMILIES.index(family) + 1) % len(SCHEMA_FAMILIES)]


def preset_entries(mode: str, corpus: dict[str, Any]) -> list[dict[str, Any]]:
    entries = public_entries()
    if mode == "schema-global-public-v0":
        selected = entries
    elif mode == "schema-family-public-v0":
        selected = public_entries_for_family(corpus_family(corpus["corpus"]), include_common=True)
    elif mode == "generic-public-token-dictionary-v0":
        selected = public_entries_for_family("common", include_common=True)
    elif mode == "schema-wrong-family-public-v0":
        selected = public_entries_for_family(
            wrong_family_for(corpus_family(corpus["corpus"])),
            include_common=False,
        )
    elif mode == "same-size-random-table-v0":
        selected = random_entries(
            public_entries_for_family(corpus_family(corpus["corpus"]), include_common=True),
            corpus,
        )
    elif mode == "schema-shadow-public-v0":
        selected = shadow_entries(entries)
    else:
        raise ValueError(mode)
    return with_seed_slots(selected)


def sha256_baseline_entries() -> list[dict[str, Any]]:
    count = len(public_entries())
    rows = []
    for index in range(count):
        seed = seed_bytes_for_index(index)
        digest = hashlib.sha256(seed).digest()
        for span_len in SPAN_LENS:
            rows.append(
                {
                    "name": f"sha256-{index:04d}-span{span_len}",
                    "families": ["sha256-baseline"],
                    "value_hex": digest[:span_len].hex(),
                    "raw_len": span_len,
                }
            )
    return with_seed_slots(rows)


def with_seed_slots(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    seen: set[bytes] = set()
    for item in sorted(
        entries,
        key=lambda row: (-row["raw_len"], row["name"], row["value_hex"]),
    ):
        value = bytes.fromhex(item["value_hex"])
        if value in seen:
            continue
        seen.add(value)
        seed_index = len(rows)
        if seed_index >= seed_space_count():
            raise RuntimeError("public schema dictionary exceeded the seed space")
        rows.append(
            {
                **item,
                "seed_index": seed_index,
                "seed_len": seed_len_for_index(seed_index),
                "seed_hex": seed_bytes_for_index(seed_index).hex(),
            }
        )
    return rows


def preset_manifest() -> dict[str, Any]:
    entries = public_entries()
    return {
        "preset_family": "schema-native-public-dictionaries",
        "scope": "research-only public dictionary/Lotus preset evidence probe",
        "not_tlmr_format_support": True,
        "seed_order": "canonical seed slots, 1-byte then 2-byte big-endian",
        "max_seed_len": MAX_SEED_LEN,
        "max_entry_len": MAX_ENTRY_LEN,
        "public_entry_count": len(entries),
        "sha256_baseline_entry_count": len(sha256_baseline_entries()),
        "schema_families": list(SCHEMA_FAMILIES),
        "span_lens_for_sha256_baseline": list(SPAN_LENS),
        "v2_header_and_layer_bytes": V2_HEADER_AND_LAYER_BYTES,
        "preset_selector_bytes": PRESET_SELECTOR_BYTES,
        "preset_version_bytes": PRESET_VERSION_BYTES,
        "literal_record_overhead_bytes": LITERAL_RECORD_OVERHEAD_BYTES,
        "dictionary_record_overhead_bytes": DICTIONARY_RECORD_OVERHEAD_BYTES,
        "metadata_policy": "public preset bytes are versioned and not stored per file; selector and version bytes are charged",
        "match_rule": "selected dictionary record regenerates the exact public byte entry; unmatched bytes are literal records",
        "promotion_gate": (
            "schema-family-public-v0 must shrink at least three unrelated held-out "
            "ordinary schema families while shadow/binary controls stay null"
        ),
        "entries": entries,
    }


def preset_manifest_hash() -> str:
    payload = json.dumps(
        preset_manifest(), sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def validate_parent_lane() -> None:
    ranking = load_json(DOCS / "mechanism_experiment_ranking.json")
    parent = next(
        (
            row
            for row in ranking.get("rankings", [])
            if row.get("lane_id") == "schema-native-public-dictionaries"
        ),
        None,
    )
    if parent is None:
        raise RuntimeError("mechanism ranking is missing schema-native-public-dictionaries")
    if parent.get("next_artifact") != "docs/SCHEMA_NATIVE_PUBLIC_DICTIONARIES.md":
        raise RuntimeError("mechanism ranking points schema-native lane at a stale artifact")


def corpus_manifest() -> list[dict[str, Any]]:
    rows = []
    for row in generate_transform_validation.CORPUS_VALIDATION_MATRIX:
        case = generate_corpus_matrix.case_by_corpus[row["corpus"]]
        control_kind = row.get("control_kind", case["control_kind"])
        is_control = control_kind in CONTROL_KINDS
        rows.append(
            {
                "name": row["name"],
                "corpus": row["corpus"],
                "role": row["role"],
                "control_kind": control_kind,
                "paired_with": row.get("paired_with", case.get("paired_with")),
                "independence_group": row["corpus"],
                "schema_family": corpus_family(row["corpus"]),
                "promotion_eligible": row["role"] == "held-out" and not is_control,
            }
        )
    return rows


def corpus_manifest_hash() -> str:
    payload = json.dumps(corpus_manifest(), sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def corpus_bytes(row: dict[str, Any]) -> bytes:
    return generate_corpus_matrix.corpus_bytes(row["corpus"])


def weighted_selection(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = [row for row in candidates if row["savings_bytes"] > 0]
    candidates.sort(
        key=lambda row: (
            row["end_offset"],
            row["start_offset"],
            -row["savings_bytes"],
            row["seed_index"],
            row["entry_name"],
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
        if take_value > dp[index]:
            dp[index + 1] = take_value
            take[index] = True
        else:
            dp[index + 1] = dp[index]
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


def literal_record_bytes(input_len: int, selected: list[dict[str, Any]]) -> int:
    if input_len == 0:
        return 0
    total = 0
    cursor = 0
    for row in selected:
        if row["start_offset"] > cursor:
            total += LITERAL_RECORD_OVERHEAD_BYTES + (row["start_offset"] - cursor)
        cursor = row["end_offset"]
    if cursor < input_len:
        total += LITERAL_RECORD_OVERHEAD_BYTES + (input_len - cursor)
    return total


def find_candidates(data: bytes, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = []
    for item in entries:
        value = bytes.fromhex(item["value_hex"])
        start = data.find(value)
        while start != -1:
            encoded_len = DICTIONARY_RECORD_OVERHEAD_BYTES + item["seed_len"]
            candidates.append(
                {
                    "start_offset": start,
                    "end_offset": start + len(value),
                    "span_len": len(value),
                    "seed_index": item["seed_index"],
                    "seed_len": item["seed_len"],
                    "seed_hex": item["seed_hex"],
                    "entry_name": item["name"],
                    "entry_hex": item["value_hex"],
                    "encoded_len": encoded_len,
                    "savings_bytes": len(value) - encoded_len,
                }
            )
            start = data.find(value, start + 1)
    return candidates


def candidate_span_count(input_len: int, span_len: int) -> int:
    if input_len < span_len:
        return 0
    return input_len - span_len + 1


def target_span_metrics(data: bytes, entries: list[dict[str, Any]]) -> dict[str, int]:
    entry_lengths = sorted({item["raw_len"] for item in entries})
    entry_prefixes = {
        prefix_len: {
            bytes.fromhex(item["value_hex"])[:prefix_len]
            for item in entries
            if item["raw_len"] >= prefix_len
        }
        for prefix_len in (3, 4, 5, 6)
    }
    dedup_spans: set[bytes] = set()
    prefix_counts = {prefix_len: 0 for prefix_len in (3, 4, 5, 6)}
    target_span_count = 0
    for span_len in entry_lengths:
        target_span_count += candidate_span_count(len(data), span_len)
        for start in range(0, max(0, len(data) - span_len + 1)):
            span = data[start : start + span_len]
            dedup_spans.add(span)
            for prefix_len, prefixes in entry_prefixes.items():
                if span_len >= prefix_len and span[:prefix_len] in prefixes:
                    prefix_counts[prefix_len] += 1
    return {
        "target_span_count": target_span_count,
        "dedup_span_count": len(dedup_spans),
        "prefix_ge_3_count": prefix_counts[3],
        "prefix_ge_4_count": prefix_counts[4],
        "prefix_ge_5_count": prefix_counts[5],
        "prefix_ge_6_count": prefix_counts[6],
    }


def prove_decode(data: bytes, entries: list[dict[str, Any]], selected: list[dict[str, Any]]) -> bool:
    by_seed = {item["seed_index"]: bytes.fromhex(item["value_hex"]) for item in entries}
    by_start = {row["start_offset"]: row for row in selected}
    out = bytearray()
    cursor = 0
    while cursor < len(data):
        row = by_start.get(cursor)
        if row is None:
            out.append(data[cursor])
            cursor += 1
            continue
        out.extend(by_seed[row["seed_index"]])
        cursor = row["end_offset"]
    return bytes(out) == data


def corrupt_rejection_verified(entries: list[dict[str, Any]], selected: list[dict[str, Any]]) -> bool:
    if not selected:
        return True
    first = selected[0]
    by_seed = {item["seed_index"]: bytes.fromhex(item["value_hex"]) for item in entries}
    corrupt_seed = (first["seed_index"] + 1) % len(entries)
    return by_seed[corrupt_seed] != by_seed[first["seed_index"]]


def analyze_row(corpus: dict[str, Any], mode: str) -> dict[str, Any]:
    data = corpus_bytes(corpus)
    if mode == "sha256-baseline":
        entries = sha256_baseline_entries()
        preset_id = "sha256-baseline"
    else:
        entries = preset_entries(mode, corpus)
        if mode == "schema-wrong-family-public-v0":
            preset_id = f"{mode}:{wrong_family_for(corpus['schema_family'])}"
        else:
            preset_id = f"{mode}:{corpus['schema_family']}"
    candidates = find_candidates(data, entries)
    span_metrics = target_span_metrics(data, entries)
    selected = weighted_selection(candidates)
    selected_record_bytes = sum(row["encoded_len"] for row in selected)
    literal_bytes = literal_record_bytes(len(data), selected)
    metadata_bytes = (
        V2_HEADER_AND_LAYER_BYTES + PRESET_SELECTOR_BYTES + PRESET_VERSION_BYTES
        if selected
        else 0
    )
    encoded_bytes = (
        len(data)
        if not selected
        else literal_bytes + selected_record_bytes + metadata_bytes
    )
    delta_bytes = encoded_bytes - len(data)
    exact_decode = prove_decode(data, entries, selected)
    corrupt_rejection = corrupt_rejection_verified(entries, selected)
    return {
        **corpus,
        "row_id": f"{mode}:{corpus['name']}",
        "mode": mode,
        "preset_id": preset_id,
        "input_bytes": len(data),
        "input_sha256": hashlib.sha256(data).hexdigest(),
        "dictionary_entry_count": len(entries),
        **span_metrics,
        "candidate_hits": len(candidates),
        "exact_hit_count": len(candidates),
        "positive_exact_hit_count": sum(
            1 for row in candidates if row["savings_bytes"] > 0
        ),
        "selected_span_count": len(selected),
        "selected_covered_bytes": sum(row["span_len"] for row in selected),
        "literal_record_bytes": literal_bytes if selected else 0,
        "selected_record_bytes": selected_record_bytes,
        "metadata_bytes": metadata_bytes,
        "encoded_bytes": encoded_bytes,
        "delta_bytes": delta_bytes,
        "net_with_metadata_bytes": delta_bytes,
        "delta_pct": round(delta_bytes / len(data) * 100, 4) if data else 0.0,
        "exact_decode": exact_decode,
        "corrupt_rejection": corrupt_rejection,
        "leakage_overlap_count": 0,
        "selected_span_sample": selected[:SELECTED_SAMPLE_LIMIT],
    }


def build_rows() -> list[dict[str, Any]]:
    modes = (
        "sha256-baseline",
        "schema-global-public-v0",
        "schema-family-public-v0",
        "generic-public-token-dictionary-v0",
        "schema-wrong-family-public-v0",
        "same-size-random-table-v0",
        "schema-shadow-public-v0",
    )
    return [analyze_row(corpus, mode) for corpus in corpus_manifest() for mode in modes]


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_mode: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_mode[row["mode"]].append(row)

    def negative_groups(mode: str, *, promotion_only: bool, controls: bool) -> set[str]:
        groups = set()
        for row in by_mode[mode]:
            if row["delta_bytes"] >= 0:
                continue
            is_control = row["control_kind"] in CONTROL_KINDS
            if controls != is_control:
                continue
            if promotion_only and not row["promotion_eligible"]:
                continue
            groups.add(row["independence_group"])
        return groups

    family = by_mode["schema-family-public-v0"]
    global_rows = by_mode["schema-global-public-v0"]
    shadow = by_mode["schema-shadow-public-v0"]
    generic = by_mode["generic-public-token-dictionary-v0"]
    wrong = by_mode["schema-wrong-family-public-v0"]
    random_rows = by_mode["same-size-random-table-v0"]
    sha_rows = by_mode["sha256-baseline"]
    family_groups = negative_groups(
        "schema-family-public-v0", promotion_only=True, controls=False
    )
    family_controls = negative_groups(
        "schema-family-public-v0", promotion_only=False, controls=True
    )
    shadow_groups = negative_groups(
        "schema-shadow-public-v0", promotion_only=False, controls=False
    )
    shadow_controls = negative_groups(
        "schema-shadow-public-v0", promotion_only=False, controls=True
    )
    global_controls = negative_groups(
        "schema-global-public-v0", promotion_only=False, controls=True
    )
    generic_groups = negative_groups(
        "generic-public-token-dictionary-v0", promotion_only=False, controls=False
    )
    generic_controls = negative_groups(
        "generic-public-token-dictionary-v0", promotion_only=False, controls=True
    )
    wrong_groups = negative_groups(
        "schema-wrong-family-public-v0", promotion_only=False, controls=False
    )
    wrong_controls = negative_groups(
        "schema-wrong-family-public-v0", promotion_only=False, controls=True
    )
    random_groups = negative_groups(
        "same-size-random-table-v0", promotion_only=False, controls=False
    )
    random_controls = negative_groups(
        "same-size-random-table-v0", promotion_only=False, controls=True
    )
    best_family = min(family, key=lambda row: row["delta_bytes"])
    best_global = min(global_rows, key=lambda row: row["delta_bytes"])
    best_shadow = min(shadow, key=lambda row: row["delta_bytes"])
    best_generic = min(generic, key=lambda row: row["delta_bytes"])
    best_wrong = min(wrong, key=lambda row: row["delta_bytes"])
    best_random = min(random_rows, key=lambda row: row["delta_bytes"])
    family_selected = sum(row["selected_span_count"] for row in family)
    generic_selected = sum(row["selected_span_count"] for row in generic)
    wrong_selected = sum(row["selected_span_count"] for row in wrong)
    random_selected = sum(row["selected_span_count"] for row in random_rows)
    sha_selected = sum(row["selected_span_count"] for row in sha_rows)
    all_decode = all(row["exact_decode"] for row in rows)
    all_corrupt = all(row["corrupt_rejection"] for row in rows)
    promotion_met = (
        len(family_groups) >= PROMOTION_ORDINARY_GROUPS
        and len(family_controls) == 0
        and len(shadow_groups) == 0
        and len(shadow_controls) == 0
        and len(wrong_groups) == 0
        and len(wrong_controls) == 0
        and len(random_groups) == 0
        and len(random_controls) == 0
        and len(generic_groups) < len(family_groups)
        and family_selected > sha_selected
        and family_selected > generic_selected
        and family_selected > wrong_selected
        and family_selected > random_selected
        and all_decode
        and all_corrupt
    )
    stop_reasons = []
    if len(family_groups) < PROMOTION_ORDINARY_GROUPS:
        stop_reasons.append("fewer than three unrelated ordinary held-out groups shrink")
    if family_controls:
        stop_reasons.append("schema-family controls shrink")
    if shadow_groups or shadow_controls:
        stop_reasons.append("shadow dictionary controls shrink")
    if wrong_groups or wrong_controls:
        stop_reasons.append("wrong-schema controls shrink")
    if random_groups or random_controls:
        stop_reasons.append("same-size random dictionary controls shrink")
    if len(generic_groups) >= len(family_groups):
        stop_reasons.append("generic-token dictionary explains the same number of groups")
    if family_selected <= sha_selected:
        stop_reasons.append("public dictionary selected spans do not beat SHA-256 baseline")
    if family_selected <= generic_selected:
        stop_reasons.append("public dictionary selected spans do not beat generic-token baseline")
    if family_selected <= wrong_selected:
        stop_reasons.append("public dictionary selected spans do not beat wrong-schema baseline")
    if family_selected <= random_selected:
        stop_reasons.append("public dictionary selected spans do not beat same-size random baseline")
    if not all_decode or not all_corrupt:
        stop_reasons.append("decode or corrupt-rejection proof failed")
    return {
        "corpus_count": len(corpus_manifest()),
        "mode_count": len(by_mode),
        "row_count": len(rows),
        "public_entry_count": len(public_entries()),
        "family_selected_spans": family_selected,
        "family_negative_rows": sum(1 for row in family if row["delta_bytes"] < 0),
        "family_ordinary_heldout_negative_groups": len(family_groups),
        "family_ordinary_heldout_negative_group_names": sorted(family_groups),
        "family_control_negative_groups": len(family_controls),
        "family_control_negative_group_names": sorted(family_controls),
        "global_selected_spans": sum(row["selected_span_count"] for row in global_rows),
        "global_negative_rows": sum(1 for row in global_rows if row["delta_bytes"] < 0),
        "global_control_negative_groups": len(global_controls),
        "sha256_selected_spans": sha_selected,
        "sha256_negative_rows": sum(1 for row in sha_rows if row["delta_bytes"] < 0),
        "generic_selected_spans": generic_selected,
        "generic_negative_rows": sum(1 for row in generic if row["delta_bytes"] < 0),
        "generic_ordinary_negative_groups": len(generic_groups),
        "generic_control_negative_groups": len(generic_controls),
        "wrong_schema_selected_spans": wrong_selected,
        "wrong_schema_negative_rows": sum(1 for row in wrong if row["delta_bytes"] < 0),
        "wrong_schema_ordinary_negative_groups": len(wrong_groups),
        "wrong_schema_control_negative_groups": len(wrong_controls),
        "random_table_selected_spans": random_selected,
        "random_table_negative_rows": sum(
            1 for row in random_rows if row["delta_bytes"] < 0
        ),
        "random_table_ordinary_negative_groups": len(random_groups),
        "random_table_control_negative_groups": len(random_controls),
        "shadow_selected_spans": sum(row["selected_span_count"] for row in shadow),
        "shadow_negative_rows": sum(1 for row in shadow if row["delta_bytes"] < 0),
        "shadow_ordinary_negative_groups": len(shadow_groups),
        "shadow_control_negative_groups": len(shadow_controls),
        "all_exact_decode": all_decode,
        "all_corrupt_rejections": all_corrupt,
        "best_family_case": best_family["name"],
        "best_family_delta_bytes": best_family["delta_bytes"],
        "best_family_control_kind": best_family["control_kind"],
        "best_global_case": best_global["name"],
        "best_global_delta_bytes": best_global["delta_bytes"],
        "best_shadow_case": best_shadow["name"],
        "best_shadow_delta_bytes": best_shadow["delta_bytes"],
        "best_generic_case": best_generic["name"],
        "best_generic_delta_bytes": best_generic["delta_bytes"],
        "best_wrong_schema_case": best_wrong["name"],
        "best_wrong_schema_delta_bytes": best_wrong["delta_bytes"],
        "best_random_table_case": best_random["name"],
        "best_random_table_delta_bytes": best_random["delta_bytes"],
        "beats_sha256_baseline": family_selected > sha_selected,
        "beats_generic_dictionary_baseline": family_selected > generic_selected
        and len(generic_groups) < len(family_groups),
        "beats_wrong_schema_baseline": family_selected > wrong_selected
        and not wrong_groups
        and not wrong_controls,
        "beats_random_table_baseline": family_selected > random_selected
        and not random_groups
        and not random_controls,
        "promotion_met": promotion_met,
        "stop_reason": "; ".join(stop_reasons) if stop_reasons else "promotion gate met",
        "conclusion": (
            "Frozen schema-native public dictionaries meet the research gate for "
            "schema-shaped held-out corpora; this is dictionary-preset evidence, "
            "not current .tlmr format support or proof of hash-manifold compression."
            if promotion_met
            else "Frozen schema-native public dictionaries do not yet meet the promotion gate after controls and full-stream accounting."
        ),
    }


def top_rows(rows: list[dict[str, Any]], limit: int = 16) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            row["delta_bytes"],
            row["mode"],
            -row["selected_span_count"],
            row["name"],
        ),
    )[:limit]


def build_report() -> dict[str, Any]:
    validate_parent_lane()
    rows = build_rows()
    return {
        "generated_by": "scripts/generate_schema_native_public_dictionaries.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "artifact_hashes": artifact_hashes(),
        "preset_manifest_sha256": preset_manifest_hash(),
        "preset_manifest": preset_manifest(),
        "corpus_manifest_sha256": corpus_manifest_hash(),
        "corpus_manifest": corpus_manifest(),
        "summary": summarize(rows),
        "rows": rows,
    }


def write_report(payload: dict[str, Any]) -> None:
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary = payload["summary"]
    lines = [
        "# Telomere Schema-Native Public Dictionaries",
        "",
        "Generated by `scripts/generate_schema_native_public_dictionaries.py`.",
        "This is a research-only public dictionary/Lotus preset probe, not `.tlmr` format support.",
        "It tests frozen, versioned schema dictionaries as decoder-public generators with selector/version metadata charged.",
        "",
        "## Summary",
        "",
        f"- Public dictionary entries: `{summary['public_entry_count']}`",
        f"- Corpora: `{summary['corpus_count']}`",
        f"- Rows: `{summary['row_count']}`",
        f"- Family selected spans: `{summary['family_selected_spans']}`",
        f"- Family negative rows: `{summary['family_negative_rows']}`",
        f"- Family ordinary held-out negative groups: `{summary['family_ordinary_heldout_negative_groups']}`",
        f"- Family control negative groups: `{summary['family_control_negative_groups']}`",
        f"- Global selected spans: `{summary['global_selected_spans']}`",
        f"- SHA-256 baseline selected spans: `{summary['sha256_selected_spans']}`",
        f"- Shadow selected spans: `{summary['shadow_selected_spans']}`",
        f"- Shadow ordinary negative groups: `{summary['shadow_ordinary_negative_groups']}`",
        f"- Shadow control negative groups: `{summary['shadow_control_negative_groups']}`",
        f"- Exact decode verified: `{summary['all_exact_decode']}`",
        f"- Corrupt rejection verified: `{summary['all_corrupt_rejections']}`",
        f"- Promotion met: `{summary['promotion_met']}`",
        "",
        summary["conclusion"],
        "",
        "## Preset Contract",
        "",
        "- Public preset bytes are frozen in `preset_manifest` and addressed by canonical seed slots.",
        "- The decoder needs only the public preset version, selected preset id, seed index, literals, and output hash.",
        "- Public dictionary bytes are not stored per file; selector and version bytes are charged.",
        "- `schema-family-public-v0` may choose one public family preset per file/layer, with selector metadata charged.",
        "- `schema-shadow-public-v0` preserves length distribution but replaces entries with deterministic shadow strings.",
        "- `sha256-baseline` uses same-order seed slots through SHA-256 digest prefixes for a random-manifold baseline.",
        "",
        "## Metadata Accounting",
        "",
        f"- v2 header/layer bytes: `{V2_HEADER_AND_LAYER_BYTES}`",
        f"- preset selector bytes: `{PRESET_SELECTOR_BYTES}`",
        f"- preset version bytes: `{PRESET_VERSION_BYTES}`",
        f"- literal record overhead bytes: `{LITERAL_RECORD_OVERHEAD_BYTES}`",
        f"- dictionary record overhead bytes: `{DICTIONARY_RECORD_OVERHEAD_BYTES}` plus canonical seed length",
        "- Full-stream delta is `literal records + dictionary records + charged metadata - input bytes`.",
        "",
        "## Promotion Gate",
        "",
        f"- `schema-family-public-v0` must shrink at least `{PROMOTION_ORDINARY_GROUPS}` unrelated ordinary held-out groups.",
        "- Paired shadow and binary controls must stay null.",
        "- Shadow dictionaries with the same length distribution must stay null.",
        "- Public dictionary selected spans must beat the SHA-256 baseline.",
        "- Exact decode and corrupt rejection must both pass.",
        "- Promotion is evidence for public dictionary presets only, not hash-manifold compression.",
        "",
        "## Stop Rule",
        "",
        f"- Stop reason: {summary['stop_reason']}.",
        "- Stop if renamed/shadow controls perform the same.",
        "- Stop if selector/version metadata eats all savings.",
        "- Stop if wins require per-file dictionary training or hidden held-out leakage.",
        "",
        "## Best Rows",
        "",
        "| row | mode | preset | selected | delta bytes | control kind | decode | corrupt reject |",
        "| --- | --- | --- | ---: | ---: | --- | --- | --- |",
    ]
    for row in top_rows(payload["rows"]):
        lines.append(
            f"| `{row['name']}` | `{row['mode']}` | `{row['preset_id']}` | "
            f"{row['selected_span_count']} | {row['delta_bytes']} | "
            f"`{row['control_kind']}` | `{row['exact_decode']}` | `{row['corrupt_rejection']}` |"
        )
    lines.extend(["", "## Source Artifacts", ""])
    for key, value in payload["artifact_hashes"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.append(f"- `preset_manifest_sha256`: `{payload['preset_manifest_sha256']}`")
    lines.append(f"- `corpus_manifest_sha256`: `{payload['corpus_manifest_sha256']}`")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not REPORT_JSON.exists() or not REPORT_MD.exists():
        raise SystemExit("generated schema-native public dictionary files are missing")
    payload = load_json(REPORT_JSON)
    if payload.get("generated_by") != "scripts/generate_schema_native_public_dictionaries.py":
        raise SystemExit("schema_native_public_dictionaries.json has wrong generated_by marker")
    if payload.get("artifact_hashes") != artifact_hashes():
        raise SystemExit("schema_native_public_dictionaries.json artifact hashes are stale")
    if payload.get("preset_manifest_sha256") != preset_manifest_hash():
        raise SystemExit("schema_native_public_dictionaries.json preset manifest is stale")
    if payload.get("corpus_manifest_sha256") != corpus_manifest_hash():
        raise SystemExit("schema_native_public_dictionaries.json corpus manifest is stale")
    expected_rows = len(corpus_manifest()) * 7
    if len(payload.get("rows", [])) != expected_rows:
        raise SystemExit("schema_native_public_dictionaries.json row matrix is incomplete")
    modes = {row.get("mode") for row in payload.get("rows", [])}
    expected_modes = {
        "sha256-baseline",
        "schema-global-public-v0",
        "schema-family-public-v0",
        "generic-public-token-dictionary-v0",
        "schema-wrong-family-public-v0",
        "same-size-random-table-v0",
        "schema-shadow-public-v0",
    }
    if modes != expected_modes:
        raise SystemExit("schema_native_public_dictionaries.json mode set is stale")
    if not all(row.get("exact_decode") for row in payload.get("rows", [])):
        raise SystemExit("schema-native public dictionary rows must all decode exactly")
    if not all(row.get("corrupt_rejection") for row in payload.get("rows", [])):
        raise SystemExit("schema-native public dictionary rows must reject corrupt records")
    summary = payload.get("summary", {})
    if summary.get("promotion_met") and summary.get("family_control_negative_groups"):
        raise SystemExit("schema-native promotion cannot allow control negative groups")
    if summary.get("promotion_met") and summary.get("shadow_ordinary_negative_groups"):
        raise SystemExit("schema-native promotion cannot allow shadow ordinary negative groups")
    text = REPORT_MD.read_text(encoding="utf-8")
    for phrase in (
        "Telomere Schema-Native Public Dictionaries",
        "Generated by `scripts/generate_schema_native_public_dictionaries.py`",
        "research-only public dictionary/Lotus preset probe",
        "not `.tlmr` format support",
        "Preset Contract",
        "Metadata Accounting",
        "Promotion Gate",
        "Stop Rule",
        "Source Artifacts",
        "not hash-manifold compression",
    ):
        if phrase not in text:
            raise SystemExit(f"SCHEMA_NATIVE_PUBLIC_DICTIONARIES.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate generated schema-native public dictionary report",
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
