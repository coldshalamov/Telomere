#!/usr/bin/env python3
"""Replicate packed sidecar evidence on a frozen held-out corpus matrix."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import generate_affine_transform_search
import generate_generalized_packed_sidecar
import generate_seed_manifold_residual_steering


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
REPLICATION_JSON = DOCS / "packed_sidecar_replication.json"
REPLICATION_MD = DOCS / "PACKED_SIDECAR_REPLICATION.md"

SCHEME = {
    "name": "prefix4-suffix-xor",
    "min_prefix_len": 4,
    "sidecar_header_bytes": 1,
}
CODERS = ("zlib_level9", "lzma_preset9")
PROMOTION_ORDINARY_CASES = 3
REPLICATION_OFFSET_MODE_NAMES = ("delta_u16", "delta_uleb128", "tiered_delta")
REPLICATION_SEED_MODE_NAMES = ("global_u16", "seed_const_or_local_u8_dict_u16")


REPLICATION_CORPORA: list[dict[str, Any]] = [
    {
        "name": "typescript-like-near",
        "corpus": "typescript-like",
        "role": "held-out",
        "control_kind": "near-family-code",
        "independence_group": "source-code",
    },
    {
        "name": "go-like-near",
        "corpus": "go-like",
        "role": "held-out",
        "control_kind": "near-family-code",
        "independence_group": "source-code",
    },
    {
        "name": "php-like-near",
        "corpus": "php-like",
        "role": "held-out",
        "control_kind": "near-family-code",
        "independence_group": "source-code",
    },
    {
        "name": "proto-schema-heldout",
        "corpus": "proto-schema",
        "role": "held-out",
        "control_kind": "ordinary-structured",
        "independence_group": "schema-language",
    },
    {
        "name": "openapi-spec-heldout",
        "corpus": "openapi-spec",
        "role": "held-out",
        "control_kind": "ordinary-structured",
        "independence_group": "api-document",
    },
    {
        "name": "terraform-hcl-heldout",
        "corpus": "terraform-hcl",
        "role": "held-out",
        "control_kind": "ordinary-structured",
        "independence_group": "configuration",
    },
    {
        "name": "kubernetes-yaml-heldout",
        "corpus": "kubernetes-yaml",
        "role": "held-out",
        "control_kind": "ordinary-structured",
        "independence_group": "configuration",
    },
    {
        "name": "hl7-v2-heldout",
        "corpus": "hl7-v2",
        "role": "held-out",
        "control_kind": "ordinary-structured",
        "independence_group": "medical-records",
    },
    {
        "name": "edi-x12-heldout",
        "corpus": "edi-x12",
        "role": "held-out",
        "control_kind": "ordinary-structured",
        "independence_group": "business-records",
    },
    {
        "name": "ics-calendar-heldout",
        "corpus": "ics-calendar",
        "role": "held-out",
        "control_kind": "ordinary-structured",
        "independence_group": "calendar-records",
    },
    {
        "name": "rfc822-email-heldout",
        "corpus": "rfc822-email",
        "role": "held-out",
        "control_kind": "ordinary-structured",
        "independence_group": "message-records",
    },
    {
        "name": "bibtex-heldout",
        "corpus": "bibtex",
        "role": "held-out",
        "control_kind": "ordinary-structured",
        "independence_group": "citation-records",
    },
    {
        "name": "ledger-beancount-heldout",
        "corpus": "ledger-beancount",
        "role": "held-out",
        "control_kind": "ordinary-structured",
        "independence_group": "financial-records",
    },
    {
        "name": "unified-diff-heldout",
        "corpus": "unified-diff",
        "role": "held-out",
        "control_kind": "ordinary-structured",
        "independence_group": "patch-records",
    },
    {
        "name": "http-transcript-heldout",
        "corpus": "http-transcript",
        "role": "held-out",
        "control_kind": "ordinary-structured",
        "independence_group": "protocol-text",
    },
    {
        "name": "fixed-width-heldout",
        "corpus": "fixed-width-mainframe",
        "role": "held-out",
        "control_kind": "ordinary-structured",
        "independence_group": "fixed-width-records",
    },
    {
        "name": "shadow-openapi-control",
        "corpus": "shadow-openapi",
        "role": "held-out",
        "control_kind": "paired-shadow-control",
        "independence_group": "api-document-shadow",
        "paired_with": "openapi-spec",
    },
    {
        "name": "shadow-proto-control",
        "corpus": "shadow-proto",
        "role": "held-out",
        "control_kind": "paired-shadow-control",
        "independence_group": "schema-language-shadow",
        "paired_with": "proto-schema",
    },
    {
        "name": "binary-fixed-record-control",
        "corpus": "binary-fixed-record",
        "role": "held-out",
        "control_kind": "binary-control",
        "independence_group": "binary-fixed",
    },
    {
        "name": "binary-hash-payload-control",
        "corpus": "binary-hash-payload",
        "role": "held-out",
        "control_kind": "negative-control",
        "independence_group": "binary-high-entropy",
    },
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def artifact_hashes() -> dict[str, str]:
    return {
        "generalized_packed_sidecar_sha256": sha256(
            DOCS / "generalized_packed_sidecar.json"
        ),
        "residual_payload_compressibility_sha256": sha256(
            DOCS / "residual_payload_compressibility.json"
        ),
        "affine_transform_search_sha256": sha256(DOCS / "affine_transform_search.json"),
    }


def replication_manifest() -> dict[str, Any]:
    return {
        "corpora": REPLICATION_CORPORA,
        "scheme": SCHEME,
        "coders": CODERS,
        "offset_modes": [
            mode
            for mode in generate_generalized_packed_sidecar.OFFSET_MODES
            if mode["name"] in REPLICATION_OFFSET_MODE_NAMES
        ],
        "seed_modes": [
            mode
            for mode in generate_generalized_packed_sidecar.SEED_MODES
            if mode["name"] in REPLICATION_SEED_MODE_NAMES
        ],
        "transform_source": (
            "unique transforms that produced residual payload rows before this "
            "replication matrix"
        ),
        "promotion_ordinary_cases": PROMOTION_ORDINARY_CASES,
        "scope": "research replication artifact only; not .tlmr format support",
    }


def manifest_hash() -> str:
    payload = json.dumps(
        replication_manifest(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def replication_offset_modes() -> list[dict[str, Any]]:
    return [
        mode
        for mode in generate_generalized_packed_sidecar.OFFSET_MODES
        if mode["name"] in REPLICATION_OFFSET_MODE_NAMES
    ]


def replication_seed_modes() -> list[dict[str, Any]]:
    return [
        mode
        for mode in generate_generalized_packed_sidecar.SEED_MODES
        if mode["name"] in REPLICATION_SEED_MODE_NAMES
    ]


def hash_token(prefix: str, idx: int, size: int = 12) -> str:
    return hashlib.sha256(f"{prefix}:{idx}".encode("ascii")).hexdigest()[:size]


def typescript_like_bytes() -> bytes:
    lines = [
        "type CompressionState = 'literal' | 'candidate' | 'selected' | 'verified';",
        "interface SpanRecord { start: number; spanLen: number; seedIndex: number; }",
        "",
    ]
    for idx in range(180):
        lines.extend(
            [
                f"export function scoreSpan{idx:03d}(record: SpanRecord): number {{",
                f"  const blockSize = {4 + (idx % 7) * 4};",
                f"  const lane: CompressionState = '{('literal', 'candidate', 'selected', 'verified')[idx % 4]}';",
                "  const base = Math.max(0, record.spanLen - blockSize);",
                f"  return base * {1 + idx % 5} + record.start % {17 + idx % 13};",
                "}",
                "",
            ]
        )
    return "\n".join(lines).encode("utf-8")


def go_like_bytes() -> bytes:
    lines = [
        "package telomere",
        "",
        "type SpanRecord struct { Start int; SpanLen int; SeedIndex uint64 }",
        "",
    ]
    for idx in range(170):
        lines.extend(
            [
                f"func ScoreSpan{idx:03d}(record SpanRecord) int {{",
                f"\tblockSize := {4 + (idx % 6) * 4}",
                f"\tseedDepth := {1 + idx % 3}",
                "\tselected := record.SpanLen - blockSize",
                "\tif selected < 0 { selected = 0 }",
                f"\treturn selected*seedDepth + record.Start%{11 + idx % 17}",
                "}",
                "",
            ]
        )
    return "\n".join(lines).encode("utf-8")


def php_like_bytes() -> bytes:
    lines = ["<?php", "final class SpanLedger {", "    private array $rows = [];", ""]
    for idx in range(150):
        lines.extend(
            [
                f"    public function scoreCase{idx:03d}(array $record): int {{",
                f"        $blockSize = {4 + (idx % 5) * 4};",
                f"        $seedDepth = {1 + idx % 3};",
                "        $selected = max(0, $record['span_len'] - $blockSize);",
                f"        return $selected * $seedDepth + $record['start'] % {13 + idx % 19};",
                "    }",
                "",
            ]
        )
    lines.append("}")
    return "\n".join(lines).encode("utf-8")


def proto_schema_bytes() -> bytes:
    lines = ['syntax = "proto3";', "package telomere.replication;", ""]
    for idx in range(140):
        lines.extend(
            [
                f"message SpanCase{idx:03d} {{",
                "  string corpus = 1;",
                "  uint32 span_len = 2;",
                "  uint64 seed_index = 3;",
                "  bool selected = 4;",
                f"  string lane = 5; // lane-{idx % 9:02d}",
                "}",
                "",
            ]
        )
    for idx in range(24):
        lines.extend(
            [
                f"service SpanAudit{idx:02d} {{",
                f"  rpc VerifyCase{idx:02d}(SpanCase{idx % 140:03d}) returns (SpanCase{(idx * 7) % 140:03d});",
                "}",
                "",
            ]
        )
    return "\n".join(lines).encode("utf-8")


def openapi_spec_bytes() -> bytes:
    paths = {}
    for idx in range(130):
        paths[f"/v1/cases/{idx:03d}"] = {
            "get": {
                "operationId": f"getCase{idx:03d}",
                "tags": [f"lane-{idx % 11:02d}"],
                "responses": {
                    "200": {
                        "description": "deterministic case response",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": f"#/components/schemas/Case{idx % 17:02d}"}
                            }
                        },
                    }
                },
            }
        }
    schemas = {
        f"Case{idx:02d}": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "spanLen": {"type": "integer"},
                "seedIndex": {"type": "integer"},
                "selected": {"type": "boolean"},
            },
            "required": ["id", "spanLen", "seedIndex"],
        }
        for idx in range(17)
    }
    doc = {
        "openapi": "3.1.0",
        "info": {"title": "Telomere Replication API", "version": "1.0.0"},
        "paths": paths,
        "components": {"schemas": schemas},
    }
    return json.dumps(doc, sort_keys=True, separators=(",", ":")).encode("utf-8")


def terraform_hcl_bytes() -> bytes:
    lines = [
        'terraform { required_version = ">= 1.6.0" }',
        "",
        'variable "region" { type = string }',
        "",
    ]
    for idx in range(150):
        lines.extend(
            [
                f'resource "telomere_span" "case_{idx:03d}" {{',
                f'  name = "case-{idx:03d}"',
                f'  corpus = "heldout-{idx % 17:02d}"',
                f"  span_len = {4 + (idx % 5) * 4}",
                f"  seed_depth = {1 + idx % 3}",
                f"  selected = {str(idx % 7 == 0).lower()}",
                "}",
                "",
            ]
        )
    return "\n".join(lines).encode("utf-8")


def kubernetes_yaml_bytes() -> bytes:
    docs = []
    for idx in range(95):
        docs.append(
            "\n".join(
                [
                    "apiVersion: apps/v1",
                    "kind: Deployment",
                    "metadata:",
                    f"  name: telomere-case-{idx:03d}",
                    "spec:",
                    f"  replicas: {1 + idx % 3}",
                    "  selector:",
                    f"    matchLabels: {{ app: telomere-{idx % 13:02d} }}",
                    "  template:",
                    "    spec:",
                    "      containers:",
                    f"        - name: matcher-{idx % 7:02d}",
                    f"          image: example/telomere:{idx % 5}",
                ]
            )
        )
    return ("\n---\n".join(docs) + "\n").encode("utf-8")


def hl7_v2_bytes() -> bytes:
    lines = []
    for idx in range(260):
        patient = f"PT{idx:05d}"
        lines.extend(
            [
                f"MSH|^~\\&|TEL|LAB|EHR|RX|20260524{idx % 24:02d}{idx % 60:02d}00||ORU^R01|MSG{idx:06d}|P|2.5.1",
                f"PID|1||{patient}^^^MR||FAMILY{idx % 29:02d}^GIVEN{idx % 31:02d}||1970{idx % 12 + 1:02d}{idx % 27 + 1:02d}|U",
                f"OBR|1|ORD{idx:06d}|FILL{idx:06d}|SPAN^{4 + (idx % 5) * 4}^TEL",
                f"OBX|1|NM|SEED^{idx % 65521}^TEL||{(idx * 37) % 1000}|bytes|||||F",
            ]
        )
    return ("\r".join(lines) + "\r").encode("ascii")


def edi_x12_bytes() -> bytes:
    segments = ["ISA*00*          *00*          *ZZ*TELMERE        *ZZ*HELDOUT        *260524*1200*^*00501*000000905*0*T*:~"]
    for idx in range(360):
        segments.extend(
            [
                f"ST*837*{idx:04d}~",
                f"BHT*0019*00*{idx:06d}*20260524*{idx % 24:02d}{idx % 60:02d}*CH~",
                f"NM1*IL*1*FAMILY{idx % 37:02d}*GIVEN{idx % 41:02d}****MI*{idx:09d}~",
                f"SV1*HC:9921{idx % 10}*{100 + idx % 700}*UN*1***1~",
                f"SE*4*{idx:04d}~",
            ]
        )
    segments.append("IEA*1*000000905~")
    return "".join(segments).encode("ascii")


def ics_calendar_bytes() -> bytes:
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Telomere//Replication//EN"]
    for idx in range(220):
        day = 1 + idx % 28
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:case-{idx:04d}@telomere.local",
                f"DTSTAMP:20260524T{idx % 24:02d}{idx % 60:02d}00Z",
                f"DTSTART:202606{day:02d}T{8 + idx % 10:02d}0000Z",
                f"SUMMARY:Span review case {idx:04d}",
                f"LOCATION:Lane {idx % 13:02d}",
                "END:VEVENT",
            ]
        )
    lines.append("END:VCALENDAR")
    return ("\r\n".join(lines) + "\r\n").encode("utf-8")


def rfc822_email_bytes() -> bytes:
    messages = []
    for idx in range(180):
        messages.append(
            "\n".join(
                [
                    f"From: matcher-{idx % 17:02d}@telomere.local",
                    f"To: audit-{idx % 19:02d}@telomere.local",
                    f"Subject: Span case {idx:04d} verification",
                    f"Message-ID: <case-{idx:04d}-{hash_token('email', idx, 8)}@telomere.local>",
                    f"Date: Sun, 24 May 2026 {idx % 24:02d}:{idx % 60:02d}:00 -0400",
                    "",
                    "The selected span ledger was regenerated from deterministic inputs.",
                    f"case={idx:04d} span_len={4 + (idx % 5) * 4} seed_depth={1 + idx % 3}",
                ]
            )
        )
    return ("\n\n".join(messages) + "\n").encode("utf-8")


def bibtex_bytes() -> bytes:
    entries = []
    for idx in range(240):
        entries.append(
            "\n".join(
                [
                    f"@article{{telomere{idx:04d},",
                    f"  title = {{Deterministic Span Evidence {idx:04d}}},",
                    f"  author = {{Researcher, Case{idx % 43:02d}}},",
                    f"  journal = {{Generated Compression Notes {idx % 11:02d}}},",
                    f"  year = {{20{10 + idx % 17}}},",
                    f"  pages = {{{1 + idx % 90}--{91 + idx % 130}}},",
                    "}",
                ]
            )
        )
    return ("\n\n".join(entries) + "\n").encode("utf-8")


def ledger_beancount_bytes() -> bytes:
    lines = ['option "title" "Telomere deterministic ledger"', ""]
    accounts = ("Assets:Cash", "Expenses:Compute", "Income:Research", "Liabilities:Cloud")
    for idx in range(260):
        lines.extend(
            [
                f"2026-{1 + idx % 12:02d}-{1 + idx % 28:02d} * \"Case {idx:04d}\" \"span ledger\"",
                f"  {accounts[idx % len(accounts)]}  {10 + idx % 700}.00 USD",
                f"  {accounts[(idx + 1) % len(accounts)]}  -{10 + idx % 700}.00 USD",
                f"  ; seed_depth: {1 + idx % 3}",
                "",
            ]
        )
    return "\n".join(lines).encode("utf-8")


def unified_diff_bytes() -> bytes:
    chunks = []
    for idx in range(170):
        chunks.extend(
            [
                f"diff --git a/cases/case_{idx:03d}.txt b/cases/case_{idx:03d}.txt",
                f"index {hash_token('old', idx, 7)}..{hash_token('new', idx, 7)} 100644",
                f"--- a/cases/case_{idx:03d}.txt",
                f"+++ b/cases/case_{idx:03d}.txt",
                "@@ -1,4 +1,4 @@",
                f"-span_len={4 + (idx % 4) * 4}",
                f"+span_len={8 + (idx % 4) * 4}",
                f" seed_depth={1 + idx % 3}",
                f" corpus=heldout-{idx % 17:02d}",
                "",
            ]
        )
    return "\n".join(chunks).encode("utf-8")


def http_transcript_bytes() -> bytes:
    lines = []
    for idx in range(220):
        lines.extend(
            [
                f"GET /api/cases/{idx:04d}?span={4 + (idx % 5) * 4} HTTP/1.1",
                "Host: telomere.local",
                f"X-Request-Id: req-{idx:04d}-{hash_token('http', idx, 6)}",
                "Accept: application/json",
                "",
                "HTTP/1.1 200 OK",
                "Content-Type: application/json",
                f"ETag: \"{hash_token('etag', idx, 12)}\"",
                "",
                f'{{"case":"{idx:04d}","selected":{str(idx % 7 == 0).lower()},"lane":"{idx % 13:02d}"}}',
                "",
            ]
        )
    return "\r\n".join(lines).encode("utf-8")


def fixed_width_mainframe_bytes() -> bytes:
    rows = []
    statuses = ("QUEUED", "SELECT", "LITERAL", "VERIFY")
    for idx in range(900):
        rows.append(
            f"{idx:06d}{statuses[idx % len(statuses)]:<8}"
            f"CORP{idx % 37:03d}"
            f"SPAN{4 + (idx % 5) * 4:03d}"
            f"SEED{(idx * 7919) % 65536:05d}"
            f"AMT{(idx * 113) % 100000:05d}"
        )
    return ("\n".join(rows) + "\n").encode("ascii")


def shadow_openapi_bytes() -> bytes:
    paths = {}
    for idx in range(130):
        paths[f"/{hash_token('path', idx, 10)}/{idx:03d}"] = {
            "post": {
                "operationId": hash_token("op", idx, 16),
                "tags": [hash_token("tag", idx % 11, 10)],
                "responses": {
                    "200": {
                        "description": hash_token("desc", idx, 18),
                        "content": {
                            "application/octet-stream": {
                                "schema": {"$ref": f"#/components/schemas/{hash_token('schema', idx % 17, 12)}"}
                            }
                        },
                    }
                },
            }
        }
    doc = {
        "openapi": "3.1.0",
        "info": {"title": hash_token("title", 1, 18), "version": "1.0.0"},
        "paths": paths,
        "components": {"schemas": {hash_token("schema", idx, 12): {"type": "object"} for idx in range(17)}},
    }
    return json.dumps(doc, sort_keys=True, separators=(",", ":")).encode("ascii")


def shadow_proto_bytes() -> bytes:
    lines = [f"syntax = \"proto3\";", f"package {hash_token('pkg', 1, 12)};", ""]
    for idx in range(140):
        lines.extend(
            [
                f"message M{hash_token('msg', idx, 10)} {{",
                f"  string f{hash_token('field', idx, 6)} = 1;",
                f"  uint32 f{hash_token('field', idx + 1000, 6)} = 2;",
                f"  bool f{hash_token('field', idx + 2000, 6)} = 3;",
                "}",
                "",
            ]
        )
    return "\n".join(lines).encode("ascii")


def binary_fixed_record_bytes() -> bytes:
    out = bytearray()
    for idx in range(1200):
        out.extend(idx.to_bytes(4, "big"))
        out.extend(((idx * 257) % 65536).to_bytes(2, "big"))
        out.extend((4 + (idx % 5) * 4).to_bytes(1, "big"))
        out.extend(hashlib.blake2s(f"fixed:{idx % 73}".encode()).digest()[:9])
    return bytes(out)


def binary_hash_payload_bytes() -> bytes:
    out = bytearray()
    for idx in range(900):
        out.extend(hashlib.sha256(f"payload:{idx}:telomere".encode()).digest()[:24])
    return bytes(out)


def corpus_bytes(name: str) -> bytes:
    generators = {
        "typescript-like": typescript_like_bytes,
        "go-like": go_like_bytes,
        "php-like": php_like_bytes,
        "proto-schema": proto_schema_bytes,
        "openapi-spec": openapi_spec_bytes,
        "terraform-hcl": terraform_hcl_bytes,
        "kubernetes-yaml": kubernetes_yaml_bytes,
        "hl7-v2": hl7_v2_bytes,
        "edi-x12": edi_x12_bytes,
        "ics-calendar": ics_calendar_bytes,
        "rfc822-email": rfc822_email_bytes,
        "bibtex": bibtex_bytes,
        "ledger-beancount": ledger_beancount_bytes,
        "unified-diff": unified_diff_bytes,
        "http-transcript": http_transcript_bytes,
        "fixed-width-mainframe": fixed_width_mainframe_bytes,
        "shadow-openapi": shadow_openapi_bytes,
        "shadow-proto": shadow_proto_bytes,
        "binary-fixed-record": binary_fixed_record_bytes,
        "binary-hash-payload": binary_hash_payload_bytes,
    }
    return generators[name]()


def byte_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = Counter(data)
    total = len(data)
    return round(
        -sum((count / total) * math.log2(count / total) for count in counts.values()),
        4,
    )


def frozen_transform_names() -> list[str]:
    payload = load_json(DOCS / "residual_payload_compressibility.json")
    return sorted({row["transform"] for row in payload["payload_rows"]})


def frozen_transforms() -> list[dict[str, Any]]:
    selected = {
        row["name"]: row
        for row in generate_seed_manifold_residual_steering.selected_affine_candidates()
    }
    return [selected[name] for name in frozen_transform_names()]


def build_source_case(
    corpus: dict[str, Any],
    transform: dict[str, Any],
    maps: dict[int, dict[bytes, dict[str, Any]]],
) -> dict[str, Any]:
    original = corpus_bytes(corpus["corpus"])
    transformed = generate_affine_transform_search.apply_candidate(original, transform)
    opportunities = []
    span_len = generate_seed_manifold_residual_steering.SPAN_LEN
    for start in range(
        0,
        max(0, len(transformed) - span_len + 1),
        generate_seed_manifold_residual_steering.SPAN_STEP,
    ):
        opportunity = generate_seed_manifold_residual_steering.opportunity_for_span(
            transformed[start : start + span_len],
            start,
            SCHEME,
            maps,
        )
        if opportunity is not None:
            opportunities.append(opportunity)
    selected = generate_seed_manifold_residual_steering.select_non_overlapping(
        opportunities
    )
    residual_payload = bytes.fromhex("".join(row["residual_hex"] for row in selected))
    return {
        "name": f"{corpus['name']}::{transform['name']}::{SCHEME['name']}",
        "corpus": corpus,
        "transform": transform,
        "scheme": SCHEME,
        "original": original,
        "transformed": transformed,
        "selected": selected,
        "source_summary": {
            "name": f"{corpus['name']}::{transform['name']}::{SCHEME['name']}",
            "corpus": corpus["corpus"],
            "role": corpus["role"],
            "control_kind": corpus["control_kind"],
            "independence_group": corpus["independence_group"],
            "transform": transform["name"],
            "input_bytes": len(original),
            "input_sha256": hashlib.sha256(original).hexdigest(),
            "transformed_sha256": hashlib.sha256(transformed).hexdigest(),
            "byte_entropy": byte_entropy(original),
            "opportunity_count": len(opportunities),
            "selected_span_count": len(selected),
            "raw_residual_payload_bytes": len(residual_payload),
            "raw_residual_payload_sha256": hashlib.sha256(residual_payload).hexdigest(),
            "max_seed_index": max((row["seed_index"] for row in selected), default=None),
            "max_start_offset": max((row["start_offset"] for row in selected), default=None),
            "sample_selected_records": [
                {
                    "start_offset": row["start_offset"],
                    "prefix_len": row["prefix_len"],
                    "seed_index": row["seed_index"],
                    "seed_len": row["seed_len"],
                    "residual_len": row["residual_len"],
                }
                for row in selected[:8]
            ],
        },
    }


def descriptor_rows_for_source(case: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    source = case["source_summary"]
    for coder in CODERS:
        for offset_mode in replication_offset_modes():
            for seed_mode in replication_seed_modes():
                mode_pair = f"{offset_mode['name']}+{seed_mode['name']}"
                try:
                    descriptor = generate_generalized_packed_sidecar.encode_case(
                        case,
                        coder,
                        offset_mode,
                        seed_mode,
                    )
                except ValueError as exc:
                    rows.append(
                        {
                            "name": source["name"],
                            "corpus": source["corpus"],
                            "role": source["role"],
                            "control_kind": source["control_kind"],
                            "independence_group": source["independence_group"],
                            "transform": source["transform"],
                            "coder": coder,
                            "offset_mode": offset_mode["name"],
                            "seed_mode": seed_mode["name"],
                            "mode_pair": mode_pair,
                            "encoded": False,
                            "skip_reason": str(exc),
                            "input_bytes": source["input_bytes"],
                            "encoded_bytes": None,
                            "delta_bytes": None,
                            "selected_span_count": source["selected_span_count"],
                            "decode_verified": False,
                            "corrupt_rejections": {},
                        }
                    )
                    continue
                rows.append(
                    {
                        **descriptor,
                        "mode_pair": mode_pair,
                        "encoded": True,
                        "skip_reason": None,
                        "corpus": source["corpus"],
                        "role": source["role"],
                        "control_kind": source["control_kind"],
                        "independence_group": source["independence_group"],
                        "transform": source["transform"],
                    }
                )
    return rows


def build_rows() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    maps = generate_seed_manifold_residual_steering.seed_prefix_maps()
    source_cases: list[dict[str, Any]] = []
    descriptor_rows: list[dict[str, Any]] = []
    for corpus in REPLICATION_CORPORA:
        for transform in frozen_transforms():
            case = build_source_case(corpus, transform, maps)
            source_cases.append(case["source_summary"])
            descriptor_rows.extend(descriptor_rows_for_source(case))
    return source_cases, descriptor_rows


def best_by_source(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    best: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not row["encoded"]:
            continue
        current = best.get(row["name"])
        if current is None or row["delta_bytes"] < current["delta_bytes"]:
            best[row["name"]] = row
    return best


def summarize(
    source_cases: list[dict[str, Any]],
    descriptor_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    encoded = [row for row in descriptor_rows if row["encoded"]]
    negative = [row for row in encoded if row["delta_bytes"] < 0]
    best_sources = best_by_source(descriptor_rows)
    negative_sources = {
        name: row for name, row in best_sources.items() if row["delta_bytes"] < 0
    }
    ordinary_negative_sources = {
        name: row
        for name, row in negative_sources.items()
        if row["role"] == "held-out" and row["control_kind"] == "ordinary-structured"
    }
    ordinary_groups = {
        row["independence_group"] for row in ordinary_negative_sources.values()
    }
    best_row = min(encoded, key=lambda row: row["delta_bytes"]) if encoded else None
    source_counter = Counter(row["control_kind"] for row in source_cases)
    negative_source_counter = Counter(
        row["control_kind"] for row in negative_sources.values()
    )
    return {
        "corpus_count": len(REPLICATION_CORPORA),
        "ordinary_corpus_count": sum(
            1
            for row in REPLICATION_CORPORA
            if row["control_kind"] == "ordinary-structured"
        ),
        "transform_count": len(frozen_transform_names()),
        "source_case_count": len(source_cases),
        "descriptor_row_count": len(descriptor_rows),
        "encoded_rows": len(encoded),
        "skipped_rows": len(descriptor_rows) - len(encoded),
        "decode_verified_rows": sum(1 for row in encoded if row["decode_verified"]),
        "all_corrupt_rejections_passed": all(
            all(row["corrupt_rejections"].values()) for row in encoded
        ),
        "source_cases_with_selected_spans": sum(
            1 for row in source_cases if row["selected_span_count"] > 0
        ),
        "full_stream_negative_rows": len(negative),
        "unique_negative_source_cases": len(negative_sources),
        "ordinary_heldout_negative_cases": len(ordinary_negative_sources),
        "ordinary_heldout_negative_groups": len(ordinary_groups),
        "source_cases_by_control_kind": dict(source_counter),
        "negative_source_cases_by_control_kind": dict(negative_source_counter),
        "negative_rows_by_mode": dict(Counter(row["offset_mode"] for row in negative)),
        "negative_rows_by_seed_mode": dict(Counter(row["seed_mode"] for row in negative)),
        "negative_rows_by_mode_pair": dict(Counter(row["mode_pair"] for row in negative)),
        "negative_rows_by_coder": dict(Counter(row["coder"] for row in negative)),
        "best_case": best_row["name"] if best_row else None,
        "best_coder": best_row["coder"] if best_row else None,
        "best_offset_mode": best_row["offset_mode"] if best_row else None,
        "best_seed_mode": best_row["seed_mode"] if best_row else None,
        "best_delta_bytes": best_row["delta_bytes"] if best_row else None,
        "promotion_met": len(ordinary_groups) >= PROMOTION_ORDINARY_CASES,
        "conclusion": (
            "Packed sidecar replication produced multiple unrelated ordinary held-out wins."
            if len(ordinary_groups) >= PROMOTION_ORDINARY_CASES
            else "Packed sidecar replication did not yet produce enough unrelated ordinary held-out wins."
        ),
    }


def top_descriptor_rows(rows: list[dict[str, Any]], limit: int = 32) -> list[dict[str, Any]]:
    return sorted(
        [row for row in rows if row["encoded"]],
        key=lambda row: row["delta_bytes"],
    )[:limit]


def top_source_rows(rows: list[dict[str, Any]], limit: int = 32) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            -row["selected_span_count"],
            row["control_kind"],
            row["name"],
        ),
    )[:limit]


def build_report() -> dict[str, Any]:
    source_cases, descriptor_rows = build_rows()
    return {
        "generated_by": "scripts/generate_packed_sidecar_replication.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "artifact_hashes": artifact_hashes(),
        "manifest_sha256": manifest_hash(),
        "manifest": replication_manifest(),
        "source_cases": source_cases,
        "descriptor_rows": descriptor_rows,
        "summary": summarize(source_cases, descriptor_rows),
    }


def write_report(payload: dict[str, Any]) -> None:
    REPLICATION_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary = payload["summary"]
    lines = [
        "# Telomere Packed Sidecar Replication",
        "",
        "Generated by `scripts/generate_packed_sidecar_replication.py`.",
        "This is a frozen held-out replication matrix for packed sidecar descriptors, not `.tlmr` format support.",
        "",
        f"Corpora: `{summary['corpus_count']}`.",
        f"Ordinary held-out corpora: `{summary['ordinary_corpus_count']}`.",
        f"Frozen transform count: `{summary['transform_count']}`.",
        f"Source cases: `{summary['source_case_count']}`.",
        f"Descriptor rows: `{summary['descriptor_row_count']}`.",
        f"Encoded rows: `{summary['encoded_rows']}`.",
        f"Skipped rows: `{summary['skipped_rows']}`.",
        f"Decode verified rows: `{summary['decode_verified_rows']}`.",
        f"All corrupt rejections passed: `{summary['all_corrupt_rejections_passed']}`.",
        f"Source cases with selected spans: `{summary['source_cases_with_selected_spans']}`.",
        f"Full-stream negative rows: `{summary['full_stream_negative_rows']}`.",
        f"Unique negative source cases: `{summary['unique_negative_source_cases']}`.",
        f"Ordinary held-out negative cases: `{summary['ordinary_heldout_negative_cases']}`.",
        f"Ordinary held-out negative groups: `{summary['ordinary_heldout_negative_groups']}`.",
        f"Promotion met: `{summary['promotion_met']}`.",
        f"Best case: `{summary['best_case']}`.",
        f"Best mode: `{summary['best_offset_mode']}`.",
        f"Best seed mode: `{summary['best_seed_mode']}`.",
        f"Best delta bytes: `{summary['best_delta_bytes']}`.",
        "",
        summary["conclusion"],
        "",
        "## Control Summary",
        "",
        "| control kind | source cases | negative source cases |",
        "| --- | ---: | ---: |",
    ]
    for control_kind in sorted(summary["source_cases_by_control_kind"]):
        lines.append(
            f"| {control_kind} | "
            f"{summary['source_cases_by_control_kind'].get(control_kind, 0)} | "
            f"{summary['negative_source_cases_by_control_kind'].get(control_kind, 0)} |"
        )
    lines.extend(
        [
            "",
            "## Best Descriptor Rows",
            "",
            "| row | control | group | coder | offset | seed | input | encoded | delta | spans | table | dict | decode | corrupt rejected |",
            "| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
        ]
    )
    for row in top_descriptor_rows(payload["descriptor_rows"]):
        lines.append(
            "| {name} | {control_kind} | {independence_group} | {coder} | {offset_mode} | {seed_mode} | "
            "{input_bytes} | {encoded_bytes} | {delta_bytes} | {selected_span_count} | "
            "{table_bytes} | {seed_dictionary_bytes} | {decode_verified} | {corrupt} |".format(
                corrupt=all(row["corrupt_rejections"].values()),
                **row,
            )
        )
    lines.extend(
        [
            "",
            "## Span-Rich Source Cases",
            "",
            "| source case | control | group | input bytes | selected spans | opportunities | max seed index |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in top_source_rows(payload["source_cases"]):
        lines.append(
            "| {name} | {control_kind} | {independence_group} | {input_bytes} | "
            "{selected_span_count} | {opportunity_count} | {max_seed_index} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The corpus list and frozen transform set are declared in the generator manifest before evaluating descriptor rows.",
            "- Success counts unique ordinary held-out source cases by independence group; multiple coders, modes, or transforms over one source do not count as independent proof.",
            "- Near-family source-code rows are useful replication clues, but they do not count as unrelated ordinary held-out proof.",
            "- Paired shadow and binary controls are reported separately so vocabulary or binary-shape quirks do not inflate the claim.",
            "- Promotion requires at least three unrelated ordinary held-out groups with full-stream negative rows under the same descriptor assumptions.",
        ]
    )
    REPLICATION_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not REPLICATION_JSON.exists() or not REPLICATION_MD.exists():
        raise SystemExit("generated packed sidecar replication files are missing")
    payload = load_json(REPLICATION_JSON)
    if payload.get("generated_by") != "scripts/generate_packed_sidecar_replication.py":
        raise SystemExit("packed_sidecar_replication.json has wrong generated_by marker")
    if payload.get("artifact_hashes") != artifact_hashes():
        raise SystemExit("packed sidecar replication artifact hashes are stale")
    if payload.get("manifest_sha256") != manifest_hash():
        raise SystemExit("packed sidecar replication manifest hash is stale")
    summary = payload.get("summary", {})
    if summary.get("decode_verified_rows") != summary.get("encoded_rows"):
        raise SystemExit("packed sidecar replication decode verification failed")
    if not summary.get("all_corrupt_rejections_passed"):
        raise SystemExit("packed sidecar replication corrupt rejection failed")
    text = REPLICATION_MD.read_text(encoding="utf-8")
    for phrase in (
        "Packed Sidecar Replication",
        "frozen held-out replication matrix",
        "not `.tlmr` format support",
        "Promotion requires at least three unrelated ordinary held-out groups",
    ):
        if phrase not in text:
            raise SystemExit(f"PACKED_SIDECAR_REPLICATION.md missing phrase: {phrase}")


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
