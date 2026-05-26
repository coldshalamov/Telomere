#!/usr/bin/env python3
"""Replicate the schema-native public dictionary signal on frozen held-out corpora."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import generate_packed_sidecar_replication
import generate_schema_native_public_dictionaries as schema_native


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
REPORT_JSON = DOCS / "schema_native_public_dictionary_replication.json"
REPORT_MD = DOCS / "SCHEMA_NATIVE_PUBLIC_DICTIONARY_REPLICATION.md"
GENERATED_BY = "scripts/generate_schema_native_public_dictionary_replication.py"

SOURCE_PATHS = {
    "schema_native_public_dictionaries_sha256": DOCS
    / "schema_native_public_dictionaries.json",
    "heldout_corpus_expansion_sha256": DOCS / "heldout_corpus_expansion.json",
    "packed_sidecar_replication_sha256": DOCS / "packed_sidecar_replication.json",
    "packed_sidecar_replication_generator_sha256": ROOT
    / "scripts"
    / "generate_packed_sidecar_replication.py",
    "format_doc_sha256": DOCS / "FORMAT.md",
}

PROMOTION_ORDINARY_GROUPS = 3
CONTROL_KINDS = {
    "binary-control",
    "negative-control",
    "paired-shadow-control",
}
MODES = (
    "sha256-baseline",
    "schema-v0-family-on-replication",
    "generic-public-token-dictionary-v1",
    "standards-public-v1",
    "wrong-family-public-v1",
    "same-size-random-table-v1",
    "shadow-public-v1",
)
STANDARDS_FAMILIES = (
    "source",
    "proto",
    "openapi",
    "terraform",
    "kubernetes",
    "hl7",
    "edi",
    "ics",
    "email",
    "bibtex",
    "ledger",
    "diff",
    "http",
    "fixed",
)
PROJECT_LEAKAGE_TOKENS = (
    b"telomere",
    b"span_len",
    b"seed_depth",
    b"seed_index",
    b"selected",
    b"corpus",
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_artifact_hashes() -> dict[str, str]:
    return {name: sha256(path) for name, path in SOURCE_PATHS.items()}


def entry(name: str, families: tuple[str, ...], value: bytes) -> dict[str, Any]:
    return schema_native.entry(name, families, value)


def common_entries() -> list[dict[str, Any]]:
    return [
        item
        for item in schema_native.public_entries()
        if "common" in item["families"]
    ]


def standards_entries() -> list[dict[str, Any]]:
    rows = [
        entry("proto-syntax", ("proto",), b'syntax = "proto3";'),
        entry("proto-package", ("proto",), b"package "),
        entry("proto-message", ("proto",), b"message "),
        entry("proto-service", ("proto",), b"service "),
        entry("proto-rpc", ("proto",), b"  rpc "),
        entry("proto-returns", ("proto",), b" returns "),
        entry("proto-string-field", ("proto",), b"  string "),
        entry("proto-uint32-field", ("proto",), b"  uint32 "),
        entry("proto-uint64-field", ("proto",), b"  uint64 "),
        entry("proto-bool-field", ("proto",), b"  bool "),
        entry("openapi-version", ("openapi",), b'"openapi":"3.1.0"'),
        entry("openapi-operation", ("openapi",), b'"operationId":'),
        entry("openapi-responses", ("openapi",), b'"responses":'),
        entry("openapi-json-content", ("openapi",), b'"application/json"'),
        entry("openapi-schema-ref", ("openapi",), b'"$ref":"#/components/schemas/'),
        entry("openapi-components", ("openapi",), b'"components":{"schemas":'),
        entry("openapi-object", ("openapi",), b'"type":"object"'),
        entry("openapi-properties", ("openapi",), b'"properties":'),
        entry("terraform-required", ("terraform",), b'terraform { required_version = '),
        entry("terraform-variable", ("terraform",), b'variable "'),
        entry("terraform-resource", ("terraform",), b'resource "'),
        entry("terraform-name", ("terraform",), b"  name = "),
        entry("terraform-span-len", ("terraform",), b"  span_len = "),
        entry("terraform-seed-depth", ("terraform",), b"  seed_depth = "),
        entry("terraform-selected", ("terraform",), b"  selected = "),
        entry("k8s-api-version", ("kubernetes",), b"apiVersion: apps/v1"),
        entry("k8s-deployment", ("kubernetes",), b"kind: Deployment"),
        entry("k8s-metadata", ("kubernetes",), b"metadata:"),
        entry("k8s-spec", ("kubernetes",), b"spec:"),
        entry("k8s-selector", ("kubernetes",), b"  selector:"),
        entry("k8s-matchlabels", ("kubernetes",), b"    matchLabels:"),
        entry("k8s-containers", ("kubernetes",), b"      containers:"),
        entry("hl7-msh", ("hl7",), b"MSH|^~\\&|"),
        entry("hl7-oru", ("hl7",), b"ORU^R01"),
        entry("hl7-pid", ("hl7",), b"PID|1||"),
        entry("hl7-obr", ("hl7",), b"OBR|1|"),
        entry("hl7-obx", ("hl7",), b"OBX|1|NM|"),
        entry("edi-isa", ("edi",), b"ISA*00*"),
        entry("edi-st837", ("edi",), b"ST*837*"),
        entry("edi-bht", ("edi",), b"BHT*0019*"),
        entry("edi-nm1", ("edi",), b"NM1*IL*1*"),
        entry("edi-sv1", ("edi",), b"SV1*HC:"),
        entry("edi-se", ("edi",), b"SE*4*"),
        entry("ics-vcalendar", ("ics",), b"BEGIN:VCALENDAR"),
        entry("ics-version", ("ics",), b"VERSION:2.0"),
        entry("ics-vevent", ("ics",), b"BEGIN:VEVENT"),
        entry("ics-end-event", ("ics",), b"END:VEVENT"),
        entry("ics-uid", ("ics",), b"UID:"),
        entry("ics-dtstamp", ("ics",), b"DTSTAMP:"),
        entry("ics-dtstart", ("ics",), b"DTSTART:"),
        entry("ics-summary", ("ics",), b"SUMMARY:"),
        entry("email-from", ("email",), b"From: "),
        entry("email-to", ("email",), b"To: "),
        entry("email-subject", ("email",), b"Subject: "),
        entry("email-message-id", ("email",), b"Message-ID: "),
        entry("email-date", ("email",), b"Date: "),
        entry("bibtex-article", ("bibtex",), b"@article{"),
        entry("bibtex-title", ("bibtex",), b"  title = {"),
        entry("bibtex-author", ("bibtex",), b"  author = {"),
        entry("bibtex-journal", ("bibtex",), b"  journal = {"),
        entry("bibtex-year", ("bibtex",), b"  year = {"),
        entry("bibtex-pages", ("bibtex",), b"  pages = {"),
        entry("ledger-option", ("ledger",), b'option "title" '),
        entry("ledger-assets", ("ledger",), b"Assets:Cash"),
        entry("ledger-expenses", ("ledger",), b"Expenses:Compute"),
        entry("ledger-income", ("ledger",), b"Income:Research"),
        entry("ledger-liabilities", ("ledger",), b"Liabilities:Cloud"),
        entry("diff-header", ("diff",), b"diff --git "),
        entry("diff-index", ("diff",), b"index "),
        entry("diff-old", ("diff",), b"--- a/"),
        entry("diff-new", ("diff",), b"+++ b/"),
        entry("diff-hunk", ("diff",), b"@@ -1,4 +1,4 @@"),
        entry("diff-minus-span", ("diff",), b"-span_len="),
        entry("diff-plus-span", ("diff",), b"+span_len="),
        entry("http-request", ("http",), b"GET /api/cases/"),
        entry("http-version", ("http",), b" HTTP/1.1"),
        entry("http-host", ("http",), b"Host: "),
        entry("http-ok", ("http",), b"HTTP/1.1 200 OK"),
        entry("http-json", ("http",), b"Content-Type: application/json"),
        entry("fixed-queued", ("fixed",), b"QUEUED  "),
        entry("fixed-select", ("fixed",), b"SELECT  "),
        entry("fixed-literal", ("fixed",), b"LITERAL "),
        entry("fixed-verify", ("fixed",), b"VERIFY  "),
        entry("fixed-span", ("fixed",), b"SPAN"),
        entry("fixed-seed", ("fixed",), b"SEED"),
        entry("fixed-amount", ("fixed",), b"AMOUNT"),
        entry("source-interface", ("source",), b"interface "),
        entry("source-function", ("source",), b"function "),
        entry("source-return", ("source",), b"return "),
        entry("source-struct", ("source",), b"struct "),
        entry("source-class", ("source",), b"class "),
        entry("source-public", ("source",), b"public "),
        entry("source-const", ("source",), b"const "),
        entry("source-package", ("source",), b"package "),
    ]
    dedup: dict[bytes, dict[str, Any]] = {}
    for item in rows:
        value = bytes.fromhex(item["value_hex"])
        existing = dedup.get(value)
        if existing is None:
            dedup[value] = item
        else:
            existing["families"] = sorted(set(existing["families"]) | set(item["families"]))
    return sorted(dedup.values(), key=lambda row: (-row["raw_len"], row["name"]))


def family_for_corpus(corpus: str) -> str:
    mapping = {
        "typescript-like": "source",
        "go-like": "source",
        "php-like": "source",
        "proto-schema": "proto",
        "shadow-proto": "proto",
        "openapi-spec": "openapi",
        "shadow-openapi": "openapi",
        "terraform-hcl": "terraform",
        "kubernetes-yaml": "kubernetes",
        "hl7-v2": "hl7",
        "edi-x12": "edi",
        "ics-calendar": "ics",
        "rfc822-email": "email",
        "bibtex": "bibtex",
        "ledger-beancount": "ledger",
        "unified-diff": "diff",
        "http-transcript": "http",
        "fixed-width-mainframe": "fixed",
        "binary-fixed-record": "binary",
        "binary-hash-payload": "binary",
    }
    return mapping.get(corpus, "common")


def v0_family_for_replication(corpus: str) -> str:
    family = family_for_corpus(corpus)
    if family in {"openapi"}:
        return "json"
    if family in {"terraform", "kubernetes"}:
        return "config"
    if family in {"proto", "source"}:
        return "source"
    if family in {"http"}:
        return "http"
    return "common"


def next_family(family: str) -> str:
    if family not in STANDARDS_FAMILIES:
        return "source"
    return STANDARDS_FAMILIES[(STANDARDS_FAMILIES.index(family) + 1) % len(STANDARDS_FAMILIES)]


def entries_for_family(family: str, *, include_common: bool) -> list[dict[str, Any]]:
    rows = []
    if include_common:
        rows.extend(common_entries())
    rows.extend(
        item
        for item in standards_entries()
        if family in item["families"]
    )
    return rows


def replication_corpus_manifest() -> list[dict[str, Any]]:
    rows = []
    for row in generate_packed_sidecar_replication.REPLICATION_CORPORA:
        control_kind = row["control_kind"]
        data = generate_packed_sidecar_replication.corpus_bytes(row["corpus"])
        rows.append(
            {
                "name": row["name"],
                "corpus": row["corpus"],
                "role": row["role"],
                "control_kind": control_kind,
                "paired_with": row.get("paired_with"),
                "independence_group": row["independence_group"],
                "schema_family": family_for_corpus(row["corpus"]),
                "promotion_eligible": control_kind == "ordinary-structured",
                "diagnostic_only": control_kind == "near-family-code",
                "input_bytes": len(data),
                "input_sha256": hashlib.sha256(data).hexdigest(),
                "in_original_transform_validation": False,
                "replication_source": "generate_packed_sidecar_replication.REPLICATION_CORPORA",
            }
        )
    return rows


def corpus_manifest_hash() -> str:
    payload = json.dumps(
        replication_corpus_manifest(), sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def preset_manifest() -> dict[str, Any]:
    return {
        "scope": "schema-native public dictionary replication and hardening probe",
        "not_tlmr_format_support": True,
        "parent_artifact": "docs/SCHEMA_NATIVE_PUBLIC_DICTIONARIES.md",
        "frozen_corpus_bank": "generate_packed_sidecar_replication.REPLICATION_CORPORA",
        "modes": list(MODES),
        "standards_families": list(STANDARDS_FAMILIES),
        "v0_public_entry_count": len(schema_native.public_entries()),
        "standards_public_entry_count": len(standards_entries()),
        "common_entry_count": len(common_entries()),
        "metadata_policy": "public preset bytes are versioned and not stored per file; selector and version bytes are charged",
        "promotion_gate": (
            "standards-public-v1 must shrink at least three unrelated ordinary "
            "replication groups, controls and wrong/random/shadow baselines must stay null, "
            "and generic tokens must not explain the same groups"
        ),
    }


def preset_manifest_hash() -> str:
    payload = json.dumps(
        preset_manifest(), sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def replication_manifest_hash() -> str:
    payload = {
        "preset_manifest_sha256": preset_manifest_hash(),
        "corpus_manifest_sha256": corpus_manifest_hash(),
        "source_artifact_hashes": source_artifact_hashes(),
        "modes": list(MODES),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def selected_entries(mode: str, corpus: dict[str, Any]) -> list[dict[str, Any]]:
    family = corpus["schema_family"]
    if mode == "sha256-baseline":
        return schema_native.sha256_baseline_entries()
    if mode == "schema-v0-family-on-replication":
        return schema_native.with_seed_slots(
            schema_native.public_entries_for_family(
                v0_family_for_replication(corpus["corpus"]),
                include_common=True,
            )
        )
    if mode == "generic-public-token-dictionary-v1":
        return schema_native.with_seed_slots(common_entries())
    if mode == "standards-public-v1":
        return schema_native.with_seed_slots(entries_for_family(family, include_common=True))
    if mode == "wrong-family-public-v1":
        return schema_native.with_seed_slots(
            entries_for_family(next_family(family), include_common=False)
        )
    if mode == "same-size-random-table-v1":
        return schema_native.with_seed_slots(
            schema_native.random_entries(entries_for_family(family, include_common=True), corpus)
        )
    if mode == "shadow-public-v1":
        return schema_native.with_seed_slots(
            schema_native.shadow_entries(entries_for_family(family, include_common=True))
        )
    raise ValueError(mode)


def corpus_bytes(row: dict[str, Any]) -> bytes:
    return generate_packed_sidecar_replication.corpus_bytes(row["corpus"])


def entry_lookup(entries: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {item["name"]: item for item in entries}


def selected_entry_family_counts(
    entries: list[dict[str, Any]], selected: list[dict[str, Any]]
) -> dict[str, int]:
    by_name = entry_lookup(entries)
    counts: dict[str, int] = defaultdict(int)
    for row in selected:
        for family in by_name.get(row["entry_name"], {}).get("families", ()):
            counts[family] += 1
    return dict(sorted(counts.items()))


def leakage_audit(
    entries: list[dict[str, Any]], selected: list[dict[str, Any]]
) -> tuple[int, list[str]]:
    by_name = entry_lookup(entries)
    token_hits = 0
    flags = set()
    for row in selected:
        entry = by_name.get(row["entry_name"])
        value_hex = entry["value_hex"] if entry else row["entry_hex"]
        value = bytes.fromhex(value_hex).lower()
        for token in PROJECT_LEAKAGE_TOKENS:
            if token in value:
                token_hits += 1
                flags.add(f"project-token:{token.decode('ascii')}")
    return token_hits, sorted(flags)


def analyze_row(corpus: dict[str, Any], mode: str) -> dict[str, Any]:
    data = corpus_bytes(corpus)
    entries = selected_entries(mode, corpus)
    candidates = schema_native.find_candidates(data, entries)
    span_metrics = schema_native.target_span_metrics(data, entries)
    selected = schema_native.weighted_selection(candidates)
    selected_record_bytes = sum(row["encoded_len"] for row in selected)
    literal_bytes = schema_native.literal_record_bytes(len(data), selected)
    metadata_bytes = (
        schema_native.V2_HEADER_AND_LAYER_BYTES
        + schema_native.PRESET_SELECTOR_BYTES
        + schema_native.PRESET_VERSION_BYTES
        if selected
        else 0
    )
    encoded_bytes = (
        len(data)
        if not selected
        else literal_bytes + selected_record_bytes + metadata_bytes
    )
    delta_bytes = encoded_bytes - len(data)
    exact_decode = schema_native.prove_decode(data, entries, selected)
    corrupt_rejection = schema_native.corrupt_rejection_verified(entries, selected)
    telomere_project_token_hits, leakage_flags = leakage_audit(entries, selected)
    return {
        **corpus,
        "row_id": f"{mode}:{corpus['name']}",
        "mode": mode,
        "preset_id": (
            f"{mode}:{next_family(corpus['schema_family'])}"
            if mode == "wrong-family-public-v1"
            else f"{mode}:{corpus['schema_family']}"
        ),
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
        "selected_span_sample": selected[: schema_native.SELECTED_SAMPLE_LIMIT],
        "selected_entry_family_counts": selected_entry_family_counts(entries, selected),
        "telomere_project_token_hits": telomere_project_token_hits,
        "leakage_flags": leakage_flags,
    }


def build_rows() -> list[dict[str, Any]]:
    return [
        analyze_row(corpus, mode)
        for corpus in replication_corpus_manifest()
        for mode in MODES
    ]


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

    standards_groups = negative_groups(
        "standards-public-v1", promotion_only=True, controls=False
    )
    standards_controls = negative_groups(
        "standards-public-v1", promotion_only=False, controls=True
    )
    generic_groups = negative_groups(
        "generic-public-token-dictionary-v1", promotion_only=True, controls=False
    )
    wrong_groups = negative_groups(
        "wrong-family-public-v1", promotion_only=True, controls=False
    )
    wrong_controls = negative_groups(
        "wrong-family-public-v1", promotion_only=False, controls=True
    )
    random_groups = negative_groups(
        "same-size-random-table-v1", promotion_only=True, controls=False
    )
    random_controls = negative_groups(
        "same-size-random-table-v1", promotion_only=False, controls=True
    )
    shadow_groups = negative_groups(
        "shadow-public-v1", promotion_only=True, controls=False
    )
    shadow_controls = negative_groups(
        "shadow-public-v1", promotion_only=False, controls=True
    )
    v0_groups = negative_groups(
        "schema-v0-family-on-replication", promotion_only=True, controls=False
    )
    standards = by_mode["standards-public-v1"]
    v0_rows = by_mode["schema-v0-family-on-replication"]
    generic = by_mode["generic-public-token-dictionary-v1"]
    wrong = by_mode["wrong-family-public-v1"]
    random_rows = by_mode["same-size-random-table-v1"]
    shadow = by_mode["shadow-public-v1"]
    sha_rows = by_mode["sha256-baseline"]
    standards_selected = sum(row["selected_span_count"] for row in standards)
    v0_selected = sum(row["selected_span_count"] for row in v0_rows)
    generic_selected = sum(row["selected_span_count"] for row in generic)
    wrong_selected = sum(row["selected_span_count"] for row in wrong)
    random_selected = sum(row["selected_span_count"] for row in random_rows)
    shadow_selected = sum(row["selected_span_count"] for row in shadow)
    sha_selected = sum(row["selected_span_count"] for row in sha_rows)
    standards_project_token_hits = sum(
        row["telomere_project_token_hits"] for row in standards
    )
    standards_project_token_rows = sum(
        1 for row in standards if row["telomere_project_token_hits"]
    )
    all_decode = all(row["exact_decode"] for row in rows)
    all_corrupt = all(row["corrupt_rejection"] for row in rows)
    beats_generic = (
        standards_selected > generic_selected
        and len(generic_groups) < len(standards_groups)
    )
    beats_sha256 = standards_selected > sha_selected
    beats_v0 = standards_selected > v0_selected
    leakage_dominates = (
        standards_selected > 0
        and standards_project_token_hits / standards_selected >= 0.5
    )
    promotion_met = (
        len(standards_groups) >= PROMOTION_ORDINARY_GROUPS
        and not standards_controls
        and not wrong_groups
        and not wrong_controls
        and not random_groups
        and not random_controls
        and not shadow_groups
        and not shadow_controls
        and beats_generic
        and beats_sha256
        and not leakage_dominates
        and all_decode
        and all_corrupt
    )
    stop_reasons = []
    if len(standards_groups) < PROMOTION_ORDINARY_GROUPS:
        stop_reasons.append("fewer than three ordinary replication groups shrink")
    if standards_controls:
        stop_reasons.append("standards controls shrink")
    if wrong_groups or wrong_controls:
        stop_reasons.append("wrong-family controls shrink")
    if random_groups or random_controls:
        stop_reasons.append("same-size random tables shrink")
    if shadow_groups or shadow_controls:
        stop_reasons.append("shadow dictionaries shrink")
    if not beats_generic:
        stop_reasons.append("generic dictionary explains too much of the signal")
    if not beats_sha256:
        stop_reasons.append("standards dictionary does not beat SHA-256 baseline")
    if leakage_dominates:
        stop_reasons.append("project/generator vocabulary dominates selected standards spans")
    if not all_decode or not all_corrupt:
        stop_reasons.append("decode or corrupt-rejection proof failed")
    if promotion_met:
        claim_level = "replicated_on_frozen_synthetic_schema_corpora"
    elif standards_controls or wrong_groups or wrong_controls or random_groups or random_controls or shadow_groups or shadow_controls:
        claim_level = "control_failed_on_frozen_expansion_corpora"
    elif generic_groups and not beats_generic:
        claim_level = "generic_token_dictionary_explains_signal"
    elif len(standards_groups) == 0:
        claim_level = "not_replicated_on_frozen_expansion_corpora"
    else:
        claim_level = "qualified_hardening_signal_not_promoted"
    best_standards = min(standards, key=lambda row: row["delta_bytes"])
    best_v0 = min(v0_rows, key=lambda row: row["delta_bytes"])
    best_generic = min(generic, key=lambda row: row["delta_bytes"])
    return {
        "corpus_count": len(replication_corpus_manifest()),
        "ordinary_corpus_count": sum(
            1 for row in replication_corpus_manifest() if row["promotion_eligible"]
        ),
        "mode_count": len(MODES),
        "row_count": len(rows),
        "standards_public_entry_count": len(standards_entries()),
        "v0_selected_spans": v0_selected,
        "v0_ordinary_negative_groups": len(v0_groups),
        "v0_ordinary_negative_group_names": sorted(v0_groups),
        "standards_selected_spans": standards_selected,
        "standards_negative_rows": sum(1 for row in standards if row["delta_bytes"] < 0),
        "standards_ordinary_negative_groups": len(standards_groups),
        "standards_ordinary_negative_group_names": sorted(standards_groups),
        "standards_control_negative_groups": len(standards_controls),
        "standards_control_negative_group_names": sorted(standards_controls),
        "generic_selected_spans": generic_selected,
        "generic_ordinary_negative_groups": len(generic_groups),
        "generic_ordinary_negative_group_names": sorted(generic_groups),
        "wrong_family_selected_spans": wrong_selected,
        "wrong_family_ordinary_negative_groups": len(wrong_groups),
        "wrong_family_ordinary_negative_group_names": sorted(wrong_groups),
        "wrong_family_control_negative_groups": len(wrong_controls),
        "wrong_family_control_negative_group_names": sorted(wrong_controls),
        "random_table_selected_spans": random_selected,
        "random_table_ordinary_negative_groups": len(random_groups),
        "random_table_ordinary_negative_group_names": sorted(random_groups),
        "random_table_control_negative_groups": len(random_controls),
        "random_table_control_negative_group_names": sorted(random_controls),
        "shadow_selected_spans": shadow_selected,
        "shadow_ordinary_negative_groups": len(shadow_groups),
        "shadow_ordinary_negative_group_names": sorted(shadow_groups),
        "shadow_control_negative_groups": len(shadow_controls),
        "shadow_control_negative_group_names": sorted(shadow_controls),
        "sha256_selected_spans": sha_selected,
        "all_exact_decode": all_decode,
        "all_corrupt_rejections": all_corrupt,
        "standards_project_token_hit_rows": standards_project_token_rows,
        "standards_project_token_hits": standards_project_token_hits,
        "standards_project_token_hit_share": round(
            standards_project_token_hits / standards_selected, 6
        )
        if standards_selected
        else 0.0,
        "leakage_dominates": leakage_dominates,
        "best_standards_case": best_standards["name"],
        "best_standards_delta_bytes": best_standards["delta_bytes"],
        "best_v0_case": best_v0["name"],
        "best_v0_delta_bytes": best_v0["delta_bytes"],
        "best_generic_case": best_generic["name"],
        "best_generic_delta_bytes": best_generic["delta_bytes"],
        "beats_original_schema_v0": beats_v0,
        "beats_sha256_baseline": beats_sha256,
        "beats_generic_dictionary_baseline": beats_generic,
        "promotion_met": promotion_met,
        "claim_level": claim_level,
        "stop_reason": "; ".join(stop_reasons) if stop_reasons else "promotion gate met",
        "conclusion": (
            "Schema-native public dictionary replication survives on the frozen replication bank."
            if promotion_met
            else "Schema-native public dictionary replication does not yet survive the harder control gate."
        ),
    }


def top_rows(rows: list[dict[str, Any]], limit: int = 18) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            row["delta_bytes"],
            row["mode"],
            -row["selected_span_count"],
            row["name"],
        ),
    )[:limit]


def control_summary(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "standards_control_negative_groups": summary["standards_control_negative_groups"],
        "wrong_family_ordinary_negative_groups": summary[
            "wrong_family_ordinary_negative_groups"
        ],
        "wrong_family_control_negative_groups": summary[
            "wrong_family_control_negative_groups"
        ],
        "same_size_random_negative_groups": summary[
            "random_table_ordinary_negative_groups"
        ],
        "same_size_random_control_negative_groups": summary[
            "random_table_control_negative_groups"
        ],
        "shadow_ordinary_negative_groups": summary["shadow_ordinary_negative_groups"],
        "shadow_control_negative_groups": summary["shadow_control_negative_groups"],
        "generic_ordinary_negative_groups": summary["generic_ordinary_negative_groups"],
        "standards_project_token_hits": summary["standards_project_token_hits"],
        "leakage_dominates": summary["leakage_dominates"],
    }


def promotion_summary(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "required_ordinary_negative_groups": PROMOTION_ORDINARY_GROUPS,
        "standards_ordinary_negative_groups": summary[
            "standards_ordinary_negative_groups"
        ],
        "standards_ordinary_negative_group_names": summary[
            "standards_ordinary_negative_group_names"
        ],
        "standards_control_negative_groups": summary["standards_control_negative_groups"],
        "generic_ordinary_negative_groups": summary["generic_ordinary_negative_groups"],
        "wrong_schema_ordinary_negative_groups": summary[
            "wrong_family_ordinary_negative_groups"
        ],
        "same_size_random_negative_groups": summary[
            "random_table_ordinary_negative_groups"
        ],
        "shadow_ordinary_negative_groups": summary["shadow_ordinary_negative_groups"],
        "beats_sha256_baseline": summary["beats_sha256_baseline"],
        "beats_generic_dictionary_baseline": summary[
            "beats_generic_dictionary_baseline"
        ],
        "all_exact_decode": summary["all_exact_decode"],
        "all_corrupt_rejections": summary["all_corrupt_rejections"],
        "promotion_met": summary["promotion_met"],
        "claim_level": summary["claim_level"],
    }


def build_report() -> dict[str, Any]:
    parent = load_json(DOCS / "schema_native_public_dictionaries.json")
    if not parent["summary"].get("promotion_met"):
        raise RuntimeError("schema replication should run only after the parent positive")
    rows = build_rows()
    summary = summarize(rows)
    return {
        "generated_by": GENERATED_BY,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "source_artifact_hashes": source_artifact_hashes(),
        "preset_manifest_sha256": preset_manifest_hash(),
        "preset_manifest": preset_manifest(),
        "corpus_manifest_sha256": corpus_manifest_hash(),
        "corpus_manifest": replication_corpus_manifest(),
        "replication_manifest_sha256": replication_manifest_hash(),
        "metadata_policy": preset_manifest()["metadata_policy"],
        "summary": summary,
        "control_summary": control_summary(summary),
        "promotion_summary": promotion_summary(summary),
        "stop_reason": summary["stop_reason"],
        "rows": rows,
    }


def write_report(payload: dict[str, Any]) -> None:
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary = payload["summary"]
    lines = [
        "# Telomere Schema-Native Public Dictionary Replication",
        "",
        f"Generated by `{GENERATED_BY}`.",
        "This is a hardening probe for the schema-native public dictionary result, not `.tlmr` format support.",
        "It applies the public-dictionary preset idea to the frozen replication corpus bank and charges selector/version metadata.",
        "",
        "## Summary",
        "",
        f"- Replication corpora: `{summary['corpus_count']}`",
        f"- Ordinary replication corpora: `{summary['ordinary_corpus_count']}`",
        f"- Standards public entries: `{summary['standards_public_entry_count']}`",
        f"- Original v0 selected spans: `{summary['v0_selected_spans']}`",
        f"- Original v0 ordinary negative groups: `{summary['v0_ordinary_negative_groups']}`",
        f"- Standards selected spans: `{summary['standards_selected_spans']}`",
        f"- Standards ordinary negative groups: `{summary['standards_ordinary_negative_groups']}`",
        f"- Standards control negative groups: `{summary['standards_control_negative_groups']}`",
        f"- Generic dictionary ordinary negative groups: `{summary['generic_ordinary_negative_groups']}`",
        f"- Wrong-family ordinary negative groups: `{summary['wrong_family_ordinary_negative_groups']}`",
        f"- Same-size random ordinary negative groups: `{summary['random_table_ordinary_negative_groups']}`",
        f"- Shadow ordinary negative groups: `{summary['shadow_ordinary_negative_groups']}`",
        f"- Beats original schema v0: `{summary['beats_original_schema_v0']}`",
        f"- Beats SHA-256 baseline: `{summary['beats_sha256_baseline']}`",
        f"- Beats generic dictionary baseline: `{summary['beats_generic_dictionary_baseline']}`",
        f"- Project/generator token hits: `{summary['standards_project_token_hits']}`",
        f"- Claim level: `{summary['claim_level']}`",
        f"- Promotion met: `{summary['promotion_met']}`",
        "",
        summary["conclusion"],
        "",
        "## Replication Contract",
        "",
        "- The parent `SCHEMA_NATIVE_PUBLIC_DICTIONARIES` artifact is treated as upstream evidence.",
        "- The corpus bank is frozen in `generate_packed_sidecar_replication.REPLICATION_CORPORA`.",
        "- `schema-v0-family-on-replication` tests whether the first 101-entry dictionary reproduces outside its original corpus matrix.",
        "- `standards-public-v1` tests a broader frozen standards registry for protocol/schema/config formats.",
        "- `generic-public-token-dictionary-v1`, `wrong-family-public-v1`, `same-size-random-table-v1`, and `shadow-public-v1` are mandatory controls.",
        "- Public preset bytes are not stored per file; selector and version bytes are charged.",
        "",
        "## Promotion Gate",
        "",
        f"- `standards-public-v1` must shrink at least `{PROMOTION_ORDINARY_GROUPS}` unrelated ordinary replication groups.",
        "- Paired shadow, binary, wrong-family, same-size random, and shadow dictionary controls must stay null.",
        "- The standards registry must beat SHA-256 and generic-token dictionary baselines.",
        "- Exact decode and corrupt rejection must pass for every row.",
        "- Promotion is evidence for a public dictionary-preset registry only, not hash-manifold compression.",
        "",
        "## Stop Rule",
        "",
        f"- Stop reason: {summary['stop_reason']}.",
        "- Downgrade the parent positive if the original v0 preset does not reproduce and standards wins are explained by generic or wrong-family controls.",
        "- Do not add `.tlmr` registry metadata until this survives non-synthetic or externally sourced corpora.",
        "",
        "## Best Rows",
        "",
        "| row | mode | selected | delta bytes | control kind | decode | corrupt reject |",
        "| --- | --- | ---: | ---: | --- | --- | --- |",
    ]
    for row in top_rows(payload["rows"]):
        lines.append(
            f"| `{row['name']}` | `{row['mode']}` | {row['selected_span_count']} | "
            f"{row['delta_bytes']} | `{row['control_kind']}` | "
            f"`{row['exact_decode']}` | `{row['corrupt_rejection']}` |"
        )
    lines.extend(["", "## Source Artifacts", ""])
    for key, value in payload["source_artifact_hashes"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.append(f"- `preset_manifest_sha256`: `{payload['preset_manifest_sha256']}`")
    lines.append(f"- `corpus_manifest_sha256`: `{payload['corpus_manifest_sha256']}`")
    lines.append(
        f"- `replication_manifest_sha256`: `{payload['replication_manifest_sha256']}`"
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not REPORT_JSON.exists() or not REPORT_MD.exists():
        raise SystemExit(
            "generated schema-native public dictionary replication files are missing"
        )
    payload = load_json(REPORT_JSON)
    if payload.get("generated_by") != GENERATED_BY:
        raise SystemExit(
            "schema_native_public_dictionary_replication.json has wrong generated_by marker"
        )
    if payload.get("source_artifact_hashes") != source_artifact_hashes():
        raise SystemExit(
            "schema_native_public_dictionary_replication.json source artifact hashes are stale"
        )
    if payload.get("preset_manifest_sha256") != preset_manifest_hash():
        raise SystemExit(
            "schema_native_public_dictionary_replication.json preset manifest is stale"
        )
    if payload.get("corpus_manifest_sha256") != corpus_manifest_hash():
        raise SystemExit(
            "schema_native_public_dictionary_replication.json corpus manifest is stale"
        )
    if payload.get("replication_manifest_sha256") != replication_manifest_hash():
        raise SystemExit(
            "schema_native_public_dictionary_replication.json replication manifest is stale"
        )
    expected_rows = len(replication_corpus_manifest()) * len(MODES)
    if len(payload.get("rows", [])) != expected_rows:
        raise SystemExit(
            "schema_native_public_dictionary_replication.json row matrix is incomplete"
        )
    modes = {row.get("mode") for row in payload.get("rows", [])}
    if modes != set(MODES):
        raise SystemExit(
            "schema_native_public_dictionary_replication.json mode set is stale"
        )
    if not all(row.get("exact_decode") for row in payload.get("rows", [])):
        raise SystemExit("schema-native replication rows must all decode exactly")
    if not all(row.get("corrupt_rejection") for row in payload.get("rows", [])):
        raise SystemExit("schema-native replication rows must reject corrupt records")
    summary = payload.get("summary", {})
    if summary.get("promotion_met") and summary.get("standards_control_negative_groups"):
        raise SystemExit("schema-native replication promotion cannot allow control groups")
    if summary.get("promotion_met") and summary.get("wrong_family_ordinary_negative_groups"):
        raise SystemExit("schema-native replication promotion cannot allow wrong-family wins")
    text = REPORT_MD.read_text(encoding="utf-8")
    for phrase in (
        "Telomere Schema-Native Public Dictionary Replication",
        f"Generated by `{GENERATED_BY}`",
        "hardening probe",
        "not `.tlmr` format support",
        "Replication Contract",
        "Promotion Gate",
        "Stop Rule",
        "Source Artifacts",
        "not hash-manifold compression",
        "Claim level",
    ):
        if phrase not in text:
            raise SystemExit(
                f"SCHEMA_NATIVE_PUBLIC_DICTIONARY_REPLICATION.md missing phrase: {phrase}"
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate generated schema-native replication report",
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
