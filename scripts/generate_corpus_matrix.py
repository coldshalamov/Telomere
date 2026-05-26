#!/usr/bin/env python3
"""Generate a structured-corpus Telomere search matrix."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import tempfile
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import generate_results
import generate_sweeps


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
MEMORY_LIMIT = "100%"
TELEMETRY_LIMIT = "64"


CORPUS_MATRIX: list[dict[str, Any]] = [
    {"name": "json-depth2", "corpus": "json", "seed_depth": 2},
    {"name": "markdown-depth2", "corpus": "markdown", "seed_depth": 2},
    {"name": "csv-depth2", "corpus": "csv", "seed_depth": 2},
    {"name": "rust-like-depth2", "corpus": "rust-like", "seed_depth": 2},
    {"name": "html-depth2", "corpus": "html", "seed_depth": 2},
    {"name": "python-like-depth2", "corpus": "python-like", "seed_depth": 2},
    {"name": "sql-depth2", "corpus": "sql", "seed_depth": 2},
    {"name": "toml-depth2", "corpus": "toml", "seed_depth": 2},
    {"name": "xml-depth2", "corpus": "xml", "seed_depth": 2},
    {"name": "log-depth2", "corpus": "log", "seed_depth": 2},
    {"name": "yaml-depth2", "corpus": "yaml", "seed_depth": 2},
    {"name": "css-depth2", "corpus": "css", "seed_depth": 2},
    {"name": "javascript-like-depth2", "corpus": "javascript-like", "seed_depth": 2},
    {"name": "graphql-depth2", "corpus": "graphql", "seed_depth": 2},
    {"name": "nginx-conf-depth2", "corpus": "nginx-conf", "seed_depth": 2},
    {"name": "ini-depth2", "corpus": "ini", "seed_depth": 2},
    {"name": "fasta-depth2", "corpus": "fasta", "seed_depth": 2},
    {"name": "svg-depth2", "corpus": "svg", "seed_depth": 2},
    {"name": "http-headers-depth2", "corpus": "http-headers", "seed_depth": 2},
    {"name": "shadow-json-depth2", "corpus": "shadow-json", "seed_depth": 2},
    {"name": "binary-tlv-depth2", "corpus": "binary-tlv", "seed_depth": 2},
    {"name": "binary-varint-depth2", "corpus": "binary-varint", "seed_depth": 2},
]

for case in CORPUS_MATRIX:
    case.setdefault("hasher", "sha256")
    case.setdefault("block_size", 4)
    case.setdefault("span_step", 1)
    case.setdefault("max_span_len", 8)
    case.setdefault("passes", 1)
    case.setdefault("control_kind", "ordinary-structured")
    case.setdefault("paired_with", None)
    case.setdefault("encoding_kind", "text")
    case.setdefault("vocabulary_group", "native")
    case.setdefault("trainable", False)
    case.setdefault("note", "Deterministic structured corpus control.")

case_by_corpus = {case["corpus"]: case for case in CORPUS_MATRIX}
case_by_corpus["shadow-json"].update(
    {
        "control_kind": "shadow-vocab",
        "paired_with": "json",
        "encoding_kind": "text-json",
        "vocabulary_group": "shadow-a",
        "note": "Vocabulary-disjoint JSON-shaped control paired with the ordinary JSON corpus.",
    }
)
case_by_corpus["binary-tlv"].update(
    {
        "control_kind": "binary-tlv",
        "paired_with": None,
        "encoding_kind": "binary-tlv-fixed",
        "vocabulary_group": "none",
        "note": "Binary TLV control with deterministic tags, lengths, and payloads.",
    }
)
case_by_corpus["binary-varint"].update(
    {
        "control_kind": "binary-varint",
        "paired_with": None,
        "encoding_kind": "binary-varint",
        "vocabulary_group": "none",
        "note": "Binary varint control with packed field keys and mixed numeric/payload records.",
    }
)


def markdown_bytes() -> bytes:
    sections = []
    for idx in range(90):
        sections.append(
            "\n".join(
                [
                    f"## Experiment {idx:03d}",
                    "",
                    f"- status: {'queued' if idx % 3 == 0 else 'verified'}",
                    f"- corpus: rx-{idx % 11:02d}",
                    f"- delta: {(idx * 17) % 1000} bytes",
                    "",
                    "The matcher records selected spans, literal bytes, and seed length distribution.",
                    "Every generated claim must be reproducible from scripts.",
                    "",
                ]
            )
        )
    return "\n".join(sections).encode("utf-8")


def csv_bytes() -> bytes:
    rows = ["id,sku,status,amount_cents,region"]
    statuses = ("queued", "paid", "fulfilled", "refunded")
    regions = ("north", "south", "east", "west")
    for idx in range(260):
        rows.append(
            f"{idx},rx-{idx % 17:02d},{statuses[idx % len(statuses)]},{2499 + (idx % 13) * 125},{regions[idx % len(regions)]}"
        )
    return ("\n".join(rows) + "\n").encode("utf-8")


def rust_like_bytes() -> bytes:
    chunks = [
        "pub struct SpanRecord {",
        "    pub start: usize,",
        "    pub span_len: usize,",
        "    pub seed_index: u64,",
        "}",
        "",
    ]
    for idx in range(120):
        chunks.extend(
            [
                f"pub fn generated_case_{idx:03d}(input: &[u8]) -> usize {{",
                f"    let block_size = {1 + idx % 16};",
                f"    let seed_depth = {1 + idx % 3};",
                "    input.len().saturating_sub(block_size * seed_depth)",
                "}",
                "",
            ]
        )
    return "\n".join(chunks).encode("utf-8")


def html_bytes() -> bytes:
    cards = []
    for idx in range(120):
        cards.append(
            f'<article class="case" data-id="{idx:03d}"><h2>Case {idx:03d}</h2>'
            f'<p>Status {"verified" if idx % 2 else "queued"}</p>'
            f'<span data-sku="rx-{idx % 19:02d}">{2499 + idx}</span></article>'
        )
    return (
        "<!doctype html><html><body><main>"
        + "".join(cards)
        + "</main></body></html>"
    ).encode("utf-8")


def python_like_bytes() -> bytes:
    chunks = [
        "from __future__ import annotations",
        "",
        "class SpanLedger:",
        "    def __init__(self) -> None:",
        "        self.rows: list[dict[str, int | str]] = []",
        "",
    ]
    for idx in range(96):
        chunks.extend(
            [
                f"def score_candidate_{idx:03d}(start: int, span_len: int) -> int:",
                f"    seed_depth = {1 + idx % 3}",
                f"    overhead = {5 + idx % 7}",
                "    selected = max(0, span_len - overhead)",
                "    return selected * seed_depth + start % 17",
                "",
            ]
        )
    return "\n".join(chunks).encode("utf-8")


def sql_bytes() -> bytes:
    lines = [
        "CREATE TABLE span_records (id INTEGER PRIMARY KEY, corpus TEXT, span_len INTEGER, selected INTEGER);",
        "BEGIN TRANSACTION;",
    ]
    statuses = ("candidate", "selected", "literal", "rejected")
    for idx in range(180):
        lines.append(
            "INSERT INTO span_records (id, corpus, span_len, selected) "
            f"VALUES ({idx}, 'corpus_{idx % 13:02d}_{statuses[idx % len(statuses)]}', "
            f"{4 + (idx % 5) * 4}, {1 if idx % 7 == 0 else 0});"
        )
    lines.append("COMMIT;")
    return ("\n".join(lines) + "\n").encode("utf-8")


def toml_bytes() -> bytes:
    lines = [
        'title = "Telomere generated configuration corpus"',
        'profile = "heldout"',
        "",
    ]
    for idx in range(120):
        lines.extend(
            [
                f"[experiment.case_{idx:03d}]",
                f'name = "case-{idx:03d}"',
                f"block_size = {4 + (idx % 4) * 4}",
                f"seed_depth = {1 + idx % 3}",
                f"span_step = {1 if idx % 5 == 0 else 4}",
                f'enabled = {"true" if idx % 2 == 0 else "false"}',
                "",
            ]
        )
    return "\n".join(lines).encode("utf-8")


def xml_bytes() -> bytes:
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', "<experiments>"]
    for idx in range(120):
        lines.extend(
            [
                f'  <experiment id="{idx:03d}" corpus="heldout-{idx % 9:02d}">',
                f"    <status>{'verified' if idx % 2 else 'queued'}</status>",
                f"    <span length=\"{4 + (idx % 5) * 4}\" step=\"{1 if idx % 4 == 0 else 4}\" />",
                f"    <seed depth=\"{1 + idx % 3}\" index=\"{idx * 257}\" />",
                "  </experiment>",
            ]
        )
    lines.append("</experiments>")
    return ("\n".join(lines) + "\n").encode("utf-8")


def log_bytes() -> bytes:
    lines = []
    levels = ("INFO", "DEBUG", "WARN", "TRACE")
    for idx in range(260):
        lines.append(
            f"2026-05-24T12:{idx % 60:02d}:{(idx * 7) % 60:02d}Z "
            f"{levels[idx % len(levels)]} telomere.worker "
            f"case={idx:04d} corpus=heldout-{idx % 17:02d} "
            f"span_len={4 + (idx % 5) * 4} selected={idx % 11 == 0} "
            f"delta_bytes={(idx * 37) % 997 - 421}"
        )
    return ("\n".join(lines) + "\n").encode("utf-8")


def yaml_bytes() -> bytes:
    lines = [
        "version: 1",
        "suite: telomere-heldout",
        "experiments:",
    ]
    for idx in range(130):
        lines.extend(
            [
                f"  - id: case-{idx:03d}",
                f"    corpus: yaml-{idx % 17:02d}",
                f"    status: {'verified' if idx % 3 else 'queued'}",
                "    search:",
                f"      block_size: {4 + (idx % 4) * 4}",
                f"      seed_depth: {1 + idx % 3}",
                f"      span_step: {1 if idx % 5 == 0 else 4}",
                "    telemetry:",
                f"      selected: {idx % 11 == 0}",
                f"      delta_bytes: {(idx * 41) % 1201 - 600}",
            ]
        )
    return ("\n".join(lines) + "\n").encode("utf-8")


def css_bytes() -> bytes:
    lines = [
        ":root {",
        "  --telomere-ink: #15231f;",
        "  --telomere-paper: #f8f3e8;",
        "}",
        "",
    ]
    states = ("idle", "searching", "selected", "literal", "verified")
    for idx in range(140):
        state = states[idx % len(states)]
        lines.extend(
            [
                f".span-card[data-state=\"{state}\"][data-case=\"{idx:03d}\"] {{",
                f"  --seed-depth: {1 + idx % 3};",
                f"  --span-len: {4 + (idx % 5) * 4}px;",
                f"  border-inline-start: {1 + idx % 7}px solid hsl({(idx * 23) % 360} 52% 42%);",
                f"  padding: {8 + idx % 9}px {12 + idx % 11}px;",
                "}",
                "",
            ]
        )
    return "\n".join(lines).encode("utf-8")


def javascript_like_bytes() -> bytes:
    chunks = [
        "const TELM_VERSION = 2;",
        "const states = ['literal', 'candidate', 'selected', 'verified'];",
        "",
    ]
    for idx in range(110):
        chunks.extend(
            [
                f"export function scoreCase{idx:03d}(span, telemetry) {{",
                f"  const seedDepth = {1 + idx % 3};",
                f"  const spanLen = {4 + (idx % 5) * 4};",
                f"  const lane = states[{idx % 4}];",
                "  const base = Math.max(0, span.length - telemetry.recordBytes);",
                f"  return {{ id: 'case-{idx:03d}', lane, score: base * seedDepth + spanLen }};",
                "}",
                "",
            ]
        )
    return "\n".join(chunks).encode("utf-8")


def graphql_bytes() -> bytes:
    lines = [
        "schema { query: Query mutation: Mutation }",
        "",
        "type Query {",
        "  experiment(id: ID!): Experiment",
        "  experiments(status: Status): [Experiment!]!",
        "}",
        "",
        "enum Status { QUEUED VERIFIED LITERAL SELECTED }",
        "",
    ]
    for idx in range(90):
        lines.extend(
            [
                f"type ExperimentCase{idx:03d} {{",
                "  id: ID!",
                "  corpus: String!",
                "  seedDepth: Int!",
                "  spanLen: Int!",
                "  selected: Boolean!",
                "}",
                "",
                f"query CaseQuery{idx:03d} {{",
                f"  experiment(id: \"case-{idx:03d}\") {{ id corpus seedDepth spanLen selected }}",
                "}",
                "",
            ]
        )
    return "\n".join(lines).encode("utf-8")


def nginx_conf_bytes() -> bytes:
    lines = [
        "worker_processes auto;",
        "events { worker_connections 1024; }",
        "http {",
        "  log_format telomere '$time_iso8601 $status $request_time $uri';",
    ]
    for idx in range(110):
        lines.extend(
            [
                f"  upstream telomere_case_{idx:03d} {{",
                f"    server 127.0.{idx % 32}.{10 + idx % 200}:{8000 + idx % 300};",
                "    keepalive 16;",
                "  }",
                f"  server {{ listen {9000 + idx % 200}; server_name case-{idx:03d}.local; }}",
            ]
        )
    lines.append("}")
    return ("\n".join(lines) + "\n").encode("utf-8")


def ini_bytes() -> bytes:
    lines = [
        "; deterministic INI corpus for held-out configuration syntax",
        "[global]",
        "suite=telomere-heldout",
        "format=ini",
        "",
    ]
    for idx in range(180):
        lines.extend(
            [
                f"[case.{idx:03d}]",
                f"name=case-{idx:03d}",
                f"corpus=ini-{idx % 23:02d}",
                f"status={'verified' if idx % 4 else 'queued'}",
                f"block_size={4 + (idx % 4) * 4}",
                f"seed_depth={1 + idx % 3}",
                f"span_step={1 if idx % 6 == 0 else 4}",
                f"delta_bytes={(idx * 53) % 1409 - 704}",
                "",
            ]
        )
    return "\n".join(lines).encode("utf-8")


def fasta_bytes() -> bytes:
    alphabet = "ACGTN"
    lines: list[str] = []
    for idx in range(120):
        lines.append(
            f">telomere_case_{idx:03d}|corpus=fasta-{idx % 17:02d}|span={4 + (idx % 5) * 4}"
        )
        sequence = "".join(
            alphabet[(idx * 11 + pos * 7 + (pos // 13)) % len(alphabet)]
            for pos in range(96 + (idx % 5) * 8)
        )
        for start in range(0, len(sequence), 48):
            lines.append(sequence[start : start + 48])
    return ("\n".join(lines) + "\n").encode("ascii")


def svg_bytes() -> bytes:
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 800">',
        "  <defs>",
        '    <style>.case{fill:none;stroke-width:2}</style>',
        "  </defs>",
    ]
    for idx in range(150):
        x = (idx * 37) % 1180
        y = (idx * 53) % 780
        width = 18 + (idx % 11) * 3
        height = 14 + (idx % 7) * 5
        hue = (idx * 29) % 360
        lines.extend(
            [
                f'  <g id="case-{idx:03d}" data-corpus="svg-{idx % 19:02d}">',
                f'    <rect class="case" x="{x}" y="{y}" width="{width}" height="{height}" stroke="hsl({hue},55%,42%)" />',
                f'    <path d="M{x},{y} l{width},{height} l{-width // 2},{height // 2} z" data-span="{4 + (idx % 5) * 4}" />',
                "  </g>",
            ]
        )
    lines.append("</svg>")
    return ("\n".join(lines) + "\n").encode("utf-8")


def http_headers_bytes() -> bytes:
    methods = ("GET", "POST", "PUT", "PATCH")
    content_types = (
        "application/json",
        "text/plain",
        "application/telomere",
        "application/octet-stream",
    )
    blocks: list[str] = []
    for idx in range(220):
        block = [
            f"{methods[idx % len(methods)]} /v2/cases/{idx:04d}/spans/{idx % 17:02d} HTTP/1.1",
            f"Host: corpus-{idx % 13:02d}.example.test",
            f"X-Telomere-Case: case-{idx:04d}",
            f"X-Seed-Depth: {1 + idx % 3}",
            f"X-Span-Len: {4 + (idx % 5) * 4}",
            f"X-Delta-Bytes: {(idx * 67) % 1601 - 800}",
            f"Content-Type: {content_types[idx % len(content_types)]}",
            f"Content-Length: {128 + (idx * 19) % 4096}",
        ]
        blocks.append("\r\n".join(block) + "\r\n\r\n")
    return "".join(blocks).encode("ascii")


def shadow_json_bytes() -> bytes:
    rows = []
    keys = [f"k{idx:02x}{hashlib.sha256(f'key:{idx}'.encode()).hexdigest()[:4]}" for idx in range(9)]
    atoms = [
        hashlib.sha256(f"atom:{idx}".encode()).hexdigest()[:14]
        for idx in range(17)
    ]
    for idx in range(180):
        record = {
            keys[0]: idx,
            keys[1]: atoms[idx % len(atoms)],
            keys[2]: atoms[(idx * 3 + 1) % len(atoms)],
            keys[3]: (idx * 131) % 65521,
            keys[4]: [atoms[(idx + offset) % len(atoms)] for offset in range(3)],
            keys[5]: {
                keys[6]: (idx * 17) % 251,
                keys[7]: atoms[(idx * 5 + 2) % len(atoms)],
                keys[8]: idx % 2 == 0,
            },
        }
        rows.append(json.dumps(record, sort_keys=True, separators=(",", ":")).encode("ascii"))
    return b"\n".join(rows) + b"\n"


def binary_tlv_bytes() -> bytes:
    out = bytearray()
    for idx in range(420):
        tag = (idx * 37) % 4096
        value_len = 3 + (idx % 11)
        value = hashlib.sha256(f"tlv:{idx % 53}:{idx // 7}".encode()).digest()[:value_len]
        out.extend(tag.to_bytes(2, "big"))
        out.extend(value_len.to_bytes(2, "big"))
        out.extend(value)
    return bytes(out)


def encode_varint(value: int) -> bytes:
    out = bytearray()
    while value >= 0x80:
        out.append((value & 0x7F) | 0x80)
        value >>= 7
    out.append(value)
    return bytes(out)


def binary_varint_bytes() -> bytes:
    out = bytearray()
    for idx in range(900):
        field = 1 + (idx % 13)
        wire_type = idx % 4
        key = (field << 3) | wire_type
        out.extend(encode_varint(key))
        if wire_type == 2:
            payload = hashlib.blake2s(f"varint:{idx % 41}:{idx}".encode()).digest()[
                : 1 + (idx % 9)
            ]
            out.extend(encode_varint(len(payload)))
            out.extend(payload)
        else:
            out.extend(encode_varint((idx * 7919 + field * 97) % 1_000_003))
    return bytes(out)


def corpus_bytes(name: str) -> bytes:
    if name == "json":
        return generate_results.structured_json_bytes()
    if name == "markdown":
        return markdown_bytes()
    if name == "csv":
        return csv_bytes()
    if name == "rust-like":
        return rust_like_bytes()
    if name == "html":
        return html_bytes()
    if name == "python-like":
        return python_like_bytes()
    if name == "sql":
        return sql_bytes()
    if name == "toml":
        return toml_bytes()
    if name == "xml":
        return xml_bytes()
    if name == "log":
        return log_bytes()
    if name == "yaml":
        return yaml_bytes()
    if name == "css":
        return css_bytes()
    if name == "javascript-like":
        return javascript_like_bytes()
    if name == "graphql":
        return graphql_bytes()
    if name == "nginx-conf":
        return nginx_conf_bytes()
    if name == "ini":
        return ini_bytes()
    if name == "fasta":
        return fasta_bytes()
    if name == "svg":
        return svg_bytes()
    if name == "http-headers":
        return http_headers_bytes()
    if name == "shadow-json":
        return shadow_json_bytes()
    if name == "binary-tlv":
        return binary_tlv_bytes()
    if name == "binary-varint":
        return binary_varint_bytes()
    raise ValueError(name)


def text_lexemes(data: bytes) -> set[str]:
    text = data.decode("utf-8", errors="ignore")
    return set(re.findall(r"[A-Za-z_][A-Za-z0-9_-]*", text))


def byte_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = Counter(data)
    total = len(data)
    return round(
        -sum((count / total) * math.log2(count / total) for count in counts.values()),
        4,
    )


def ascii_printable_ratio(data: bytes) -> float:
    if not data:
        return 0.0
    printable = sum(1 for value in data if value in (9, 10, 13) or 32 <= value <= 126)
    return round(printable / len(data), 6)


def count_varints(data: bytes) -> int:
    count = 0
    in_varint = False
    for value in data:
        if not in_varint:
            count += 1
        in_varint = bool(value & 0x80)
    return count


def corpus_profile(case: dict[str, Any], data: bytes) -> dict[str, Any]:
    lexemes = text_lexemes(data)
    paired_with = case.get("paired_with")
    if paired_with:
        paired_lexemes = text_lexemes(corpus_bytes(paired_with))
        overlap = lexemes & paired_lexemes
        lexeme_overlap_rate = round(len(overlap) / len(lexemes), 6) if lexemes else 0.0
    else:
        lexeme_overlap_rate = 0.0
    return {
        "control_kind": case["control_kind"],
        "paired_with": paired_with,
        "encoding_kind": case["encoding_kind"],
        "vocabulary_group": case["vocabulary_group"],
        "trainable": case["trainable"],
        "lexeme_count": len(lexemes),
        "lexeme_overlap_rate": lexeme_overlap_rate,
        "unique_byte_count": len(set(data)),
        "byte_entropy": byte_entropy(data),
        "ascii_printable_ratio": ascii_printable_ratio(data),
        "varint_count": count_varints(data)
        if case["control_kind"] == "binary-varint"
        else 0,
        "tlv_record_count": 420 if case["control_kind"] == "binary-tlv" else 0,
    }


def corpus_manifest() -> list[dict[str, Any]]:
    fields = (
        "name",
        "corpus",
        "seed_depth",
        "hasher",
        "block_size",
        "span_step",
        "max_span_len",
        "passes",
        "control_kind",
        "paired_with",
        "encoding_kind",
        "vocabulary_group",
        "trainable",
        "note",
    )
    return [{field: case[field] for field in fields} for case in CORPUS_MATRIX]


def corpus_manifest_hash() -> str:
    payload = json.dumps(corpus_manifest(), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def summarize_telemetry(summary: dict[str, Any]) -> dict[str, Any]:
    telemetry = summary.get("engine_telemetry", {})
    return {
        "candidate_count": telemetry.get("candidate_count", 0),
        "selected_count": telemetry.get("selected_count", 0),
        "literal_bytes": telemetry.get("literal_bytes", 0),
        "bundle_count": telemetry.get("bundle_count", 0),
        "container_bytes": telemetry.get("container_bytes", 0),
        "layer_count": len(telemetry.get("layers", [])),
    }


def case_by_name(name: str) -> dict[str, Any]:
    for case in CORPUS_MATRIX:
        if case["name"] == name:
            return case
    raise KeyError(name)


def run_case(case: dict[str, Any], temp: Path, exe: Path) -> dict[str, Any]:
    data = corpus_bytes(case["corpus"])
    profile = corpus_profile(case, data)
    input_path = temp / f"{case['name']}.bin"
    output_path = temp / f"{case['name']}.tlmr"
    restored_path = temp / f"{case['name']}.restored"
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
    generate_sweeps.run([str(exe), "decompress", str(output_path), str(restored_path), "--force"])
    if restored_path.read_bytes() != data:
        raise RuntimeError(f"{case['name']}: decompressed bytes did not match input")

    input_bytes = len(data)
    output_bytes = output_path.stat().st_size
    return {
        "name": case["name"],
        "corpus": case["corpus"],
        "input_sha256": hashlib.sha256(data).hexdigest(),
        "output_sha256": hashlib.sha256(output_path.read_bytes()).hexdigest(),
        "input_bytes": input_bytes,
        "output_bytes": output_bytes,
        "delta_bytes": output_bytes - input_bytes,
        "delta_pct": ((output_bytes - input_bytes) / input_bytes * 100.0)
        if input_bytes
        else 0.0,
        "seed_depth": case["seed_depth"],
        "span_step": case["span_step"],
        "max_span_len": case["max_span_len"],
        "compress_ms": compress_ms,
        "peak_memory_bytes": peak_memory_bytes,
        "peak_memory_mib": round(peak_memory_bytes / (1024 * 1024), 3)
        if peak_memory_bytes is not None
        else None,
        **profile,
        "telemetry": summarize_telemetry(summary),
    }


def write_artifacts(cases: list[dict[str, Any]], results: list[dict[str, Any]]) -> None:
    payload = {
        "generated_by": "scripts/generate_corpus_matrix.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "corpus_manifest_sha256": corpus_manifest_hash(),
        "corpus_matrix": corpus_manifest(),
        "selected_case_names": [case["name"] for case in cases],
        "environment": generate_results.environment_metadata(),
        "results": results,
    }
    (DOCS / "corpus_matrix.json").write_text(json.dumps(payload, indent=2) + "\n")

    lines = [
        "# Telomere Structured Corpus Matrix",
        "",
        "Generated by `scripts/generate_corpus_matrix.py` from release-binary CLI runs.",
        "This matrix broadens raw structured-corpus controls beyond JSON.",
        "",
        f"Corpus manifest SHA-256: `{corpus_manifest_hash()}`.",
        "",
        "| case | corpus | kind | paired | encoding | entropy | lexeme overlap | ascii | seed depth | span | step | input bytes | output bytes | delta bytes | delta | selected | candidates | compress ms | peak MiB |",
        "| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in results:
        peak = row["peak_memory_mib"] if row["peak_memory_mib"] is not None else "-"
        display_row = dict(row)
        display_row["paired_with"] = row["paired_with"] if row["paired_with"] is not None else "-"
        lines.append(
            "| {name} | {corpus} | {control_kind} | {paired_with} | {encoding_kind} | "
            "{byte_entropy} | {lexeme_overlap_rate:.3f} | {ascii_printable_ratio:.3f} | "
            "{seed_depth} | {max_span_len} | {span_step} | {input_bytes} | {output_bytes} | "
            "{delta_bytes:+} | {delta_pct:+.2f}% | {selected_count} | {candidate_count} | {compress_ms} | {peak} |".format(
                selected_count=row["telemetry"]["selected_count"],
                candidate_count=row["telemetry"]["candidate_count"],
                peak=peak,
                **display_row,
            )
        )

    lines.extend(
        [
            "",
            "Interpretation:",
            "",
            "- These are raw structured controls: no transform, no dictionary, no external corpus model.",
            "- vocabulary-disjoint shadow corpora preserve syntax shape while changing semantic lexemes; TLV/varint controls remove text vocabulary entirely.",
            "- A useful raw structured win requires selected spans and negative delta, not merely small overhead.",
            "- Null rows here are falsification evidence for the current search window and corpus family.",
        ]
    )
    (DOCS / "CORPUS_MATRIX.md").write_text("\n".join(lines) + "\n")


def check_artifacts() -> None:
    json_path = DOCS / "corpus_matrix.json"
    md_path = DOCS / "CORPUS_MATRIX.md"
    if not json_path.exists() or not md_path.exists():
        raise SystemExit("generated corpus matrix files are missing")
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    if payload.get("generated_by") != "scripts/generate_corpus_matrix.py":
        raise SystemExit("corpus_matrix.json has wrong generated_by marker")
    if payload.get("corpus_manifest_sha256") != corpus_manifest_hash():
        raise SystemExit("corpus_matrix.json corpus manifest hash is stale")
    expected_names = [case["name"] for case in CORPUS_MATRIX]
    result_names = [result["name"] for result in payload.get("results", [])]
    if result_names != expected_names:
        raise SystemExit("corpus_matrix.json does not contain the full corpus matrix")
    control_kinds = {result.get("control_kind") for result in payload.get("results", [])}
    for required in ("shadow-vocab", "binary-tlv", "binary-varint"):
        if required not in control_kinds:
            raise SystemExit(f"corpus_matrix.json missing {required} control")
    shadow_rows = [
        result
        for result in payload.get("results", [])
        if result.get("control_kind") == "shadow-vocab"
    ]
    if any(result.get("lexeme_overlap_rate", 1.0) != 0.0 for result in shadow_rows):
        raise SystemExit("shadow-vocab corpus has non-zero semantic lexeme overlap")
    text = md_path.read_text(encoding="utf-8")
    missing = [name for name in expected_names if name not in text]
    if missing:
        raise SystemExit(f"CORPUS_MATRIX.md missing cases: {', '.join(missing)}")
    for phrase in ("vocabulary-disjoint", "TLV/varint controls"):
        if phrase not in text:
            raise SystemExit(f"CORPUS_MATRIX.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", action="append", help="run one named corpus case; repeatable")
    parser.add_argument("--list", action="store_true", help="list corpus cases and exit")
    parser.add_argument("--manifest-sha", action="store_true", help="print corpus manifest hash and exit")
    parser.add_argument("--check", action="store_true", help="validate generated corpus matrix")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.list:
        for case in CORPUS_MATRIX:
            print(case["name"])
        return
    if args.manifest_sha:
        print(corpus_manifest_hash())
        return
    if args.check:
        check_artifacts()
        return

    if args.case:
        try:
            cases = [case_by_name(name) for name in args.case]
        except KeyError as exc:
            raise SystemExit(f"unknown corpus matrix case: {exc.args[0]}") from exc
    else:
        cases = CORPUS_MATRIX

    exe = generate_results.build_release_binary()
    with tempfile.TemporaryDirectory() as tmp:
        temp = Path(tmp)
        results = [run_case(case, temp, exe) for case in cases]
    write_artifacts(cases, results)


if __name__ == "__main__":
    main()
