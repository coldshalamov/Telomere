#!/usr/bin/env python3
"""Validate top transform-probe leads on held-out structured corpora."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import generate_corpus_matrix
import generate_manifold_report
import generate_transform_probe


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
VALIDATION_JSON = DOCS / "transform_validation.json"
VALIDATION_MD = DOCS / "TRANSFORM_VALIDATION.md"

HASHER = "sha256"
MAX_SEED_LEN = 2
SPAN_LEN = 8
SPAN_STEP = 1


CORPUS_VALIDATION_MATRIX: list[dict[str, Any]] = [
    {"name": "json-discovery", "corpus": "json", "role": "discovery"},
    {"name": "markdown-heldout", "corpus": "markdown", "role": "held-out"},
    {"name": "csv-heldout", "corpus": "csv", "role": "held-out"},
    {"name": "rust-like-heldout", "corpus": "rust-like", "role": "held-out"},
    {"name": "html-heldout", "corpus": "html", "role": "held-out"},
    {"name": "python-like-heldout", "corpus": "python-like", "role": "held-out"},
    {"name": "sql-heldout", "corpus": "sql", "role": "held-out"},
    {"name": "toml-heldout", "corpus": "toml", "role": "held-out"},
    {"name": "xml-heldout", "corpus": "xml", "role": "held-out"},
    {"name": "log-heldout", "corpus": "log", "role": "held-out"},
    {"name": "yaml-heldout", "corpus": "yaml", "role": "held-out"},
    {"name": "css-heldout", "corpus": "css", "role": "held-out"},
    {"name": "javascript-like-heldout", "corpus": "javascript-like", "role": "held-out"},
    {"name": "graphql-heldout", "corpus": "graphql", "role": "held-out"},
    {"name": "nginx-conf-heldout", "corpus": "nginx-conf", "role": "held-out"},
    {"name": "ini-heldout", "corpus": "ini", "role": "held-out"},
    {"name": "fasta-heldout", "corpus": "fasta", "role": "held-out"},
    {"name": "svg-heldout", "corpus": "svg", "role": "held-out"},
    {"name": "http-headers-heldout", "corpus": "http-headers", "role": "held-out"},
    {
        "name": "shadow-json-heldout",
        "corpus": "shadow-json",
        "role": "held-out",
        "control_kind": "shadow-vocab",
        "paired_with": "json",
    },
    {
        "name": "binary-tlv-heldout",
        "corpus": "binary-tlv",
        "role": "held-out",
        "control_kind": "binary-tlv",
    },
    {
        "name": "binary-varint-heldout",
        "corpus": "binary-varint",
        "role": "held-out",
        "control_kind": "binary-varint",
    },
]

TRANSFORM_VALIDATION_MATRIX: list[dict[str, Any]] = [
    {
        "name": "identity",
        "family": "identity",
        "parameter": 0,
        "metadata_bytes": 0,
        "reason": "baseline",
    },
    {
        "name": "add-const-232",
        "family": "add-const",
        "parameter": 232,
        "metadata_bytes": 1,
        "reason": "best discovery prefix>=3 count",
    },
    {
        "name": "xor-const-213",
        "family": "xor-const",
        "parameter": 213,
        "metadata_bytes": 1,
        "reason": "best discovery prefix>=4 count",
    },
    {
        "name": "xor-const-205",
        "family": "xor-const",
        "parameter": 205,
        "metadata_bytes": 1,
        "reason": "second discovery prefix>=4 count",
    },
    {
        "name": "add-const-151",
        "family": "add-const",
        "parameter": 151,
        "metadata_bytes": 1,
        "reason": "third discovery prefix>=4 count",
    },
    {
        "name": "bit-reverse",
        "family": "bit-reverse",
        "parameter": 0,
        "metadata_bytes": 0,
        "reason": "structural byte bit-order probe",
    },
    {
        "name": "nibble-swap",
        "family": "nibble-swap",
        "parameter": 0,
        "metadata_bytes": 0,
        "reason": "structural byte nibble-order probe",
    },
    {
        "name": "even-odd",
        "family": "even-odd",
        "parameter": 0,
        "metadata_bytes": 0,
        "reason": "structural byte deinterleave probe",
    },
    {
        "name": "chunk-reverse-8",
        "family": "chunk-reverse",
        "parameter": 8,
        "metadata_bytes": 1,
        "reason": "structural fixed-chunk reorder probe",
    },
    {
        "name": "chunk-reverse-16",
        "family": "chunk-reverse",
        "parameter": 16,
        "metadata_bytes": 1,
        "reason": "wider structural fixed-chunk reorder probe",
    },
    {
        "name": "reverse-stream",
        "family": "reverse-stream",
        "parameter": 0,
        "metadata_bytes": 0,
        "reason": "whole-stream structural reorder probe",
    },
    {
        "name": "xor-prev",
        "family": "xor-prev",
        "parameter": 0,
        "metadata_bytes": 1,
        "reason": "byte residual transform from transform sweeps",
    },
    {
        "name": "sub-prev",
        "family": "sub-prev",
        "parameter": 0,
        "metadata_bytes": 1,
        "reason": "subtractive residual transform from transform sweeps",
    },
    {
        "name": "xor-lag-2",
        "family": "xor-lag",
        "parameter": 2,
        "metadata_bytes": 1,
        "reason": "lagged XOR residual transform",
    },
    {
        "name": "xor-lag-4",
        "family": "xor-lag",
        "parameter": 4,
        "metadata_bytes": 1,
        "reason": "lagged XOR residual transform",
    },
    {
        "name": "xor-lag-8",
        "family": "xor-lag",
        "parameter": 8,
        "metadata_bytes": 1,
        "reason": "lagged XOR residual transform",
    },
    {
        "name": "xor-lag-16",
        "family": "xor-lag",
        "parameter": 16,
        "metadata_bytes": 1,
        "reason": "lagged XOR residual transform",
    },
    {
        "name": "sub-lag-2",
        "family": "sub-lag",
        "parameter": 2,
        "metadata_bytes": 1,
        "reason": "lagged subtractive residual transform",
    },
    {
        "name": "sub-lag-4",
        "family": "sub-lag",
        "parameter": 4,
        "metadata_bytes": 1,
        "reason": "lagged subtractive residual transform",
    },
    {
        "name": "sub-lag-8",
        "family": "sub-lag",
        "parameter": 8,
        "metadata_bytes": 1,
        "reason": "lagged subtractive residual transform",
    },
    {
        "name": "sub-lag-16",
        "family": "sub-lag",
        "parameter": 16,
        "metadata_bytes": 1,
        "reason": "lagged subtractive residual transform",
    },
]


def validation_manifest() -> dict[str, Any]:
    return {
        "corpora": CORPUS_VALIDATION_MATRIX,
        "transforms": TRANSFORM_VALIDATION_MATRIX,
        "max_seed_len": MAX_SEED_LEN,
        "span_len": SPAN_LEN,
        "span_step": SPAN_STEP,
        "hasher": HASHER,
    }


def validation_manifest_hash() -> str:
    payload = json.dumps(validation_manifest(), sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def probe_from_validation_transform(transform: dict[str, Any]) -> dict[str, Any]:
    return {
        "family": transform["family"],
        "parameter": transform["parameter"],
        "metadata_bytes": transform["metadata_bytes"],
    }


def control_kind(corpus: dict[str, Any]) -> str:
    return corpus.get("control_kind", "ordinary-structured")


def analyze_case(
    corpus: dict[str, Any],
    transform: dict[str, Any],
    prefix_sets: list[set[bytes]],
) -> dict[str, Any]:
    data = generate_corpus_matrix.corpus_bytes(corpus["corpus"])
    transformed = generate_transform_probe.apply_probe(
        data,
        probe_from_validation_transform(transform),
    )
    metrics = generate_transform_probe.analyze_bytes(transformed, prefix_sets)
    return {
        "name": f"{corpus['name']}::{transform['name']}",
        "corpus": corpus["corpus"],
        "corpus_role": corpus["role"],
        "control_kind": control_kind(corpus),
        "paired_with": corpus.get("paired_with"),
        "transform": transform["name"],
        "transform_family": transform["family"],
        "transform_parameter": transform["parameter"],
        "transform_reason": transform["reason"],
        "metadata_bytes": transform["metadata_bytes"],
        "input_sha256": hashlib.sha256(transformed).hexdigest(),
        "input_bytes": len(transformed),
        **metrics,
    }


def identity_by_corpus(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {row["corpus"]: row for row in rows if row["transform"] == "identity"}


def best_non_identity_by_corpus(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    best: dict[str, dict[str, Any]] = {}
    for row in rows:
        if row["transform"] == "identity":
            continue
        current = best.get(row["corpus"])
        if current is None or row_score(row) > row_score(current):
            best[row["corpus"]] = row
    return best


def row_score(row: dict[str, Any]) -> tuple[int, int, int, int, int]:
    return (
        row["exact_span_hits"],
        row["prefix_ge_6_count"],
        row["prefix_ge_5_count"],
        row["prefix_ge_4_count"],
        row["prefix_ge_3_count"],
    )


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    identity_rows = identity_by_corpus(rows)
    best_rows = best_non_identity_by_corpus(rows)
    corpus_summaries = []
    heldout_exact_hits = 0
    heldout_prefix4_wins = 0
    shadow_prefix4_wins = 0
    shadow_prefix5_wins = 0
    shadow_exact_hits = 0
    binary_prefix4_wins = 0
    binary_prefix5_wins = 0
    binary_exact_hits = 0
    for corpus in CORPUS_VALIDATION_MATRIX:
        identity = identity_rows[corpus["corpus"]]
        best = best_rows[corpus["corpus"]]
        prefix4_delta = best["prefix_ge_4_count"] - identity["prefix_ge_4_count"]
        prefix5_delta = best["prefix_ge_5_count"] - identity["prefix_ge_5_count"]
        exact_delta = best["exact_span_hits"] - identity["exact_span_hits"]
        kind = control_kind(corpus)
        if corpus["role"] == "held-out":
            heldout_exact_hits += best["exact_span_hits"]
            if prefix4_delta > 0:
                heldout_prefix4_wins += 1
            if kind == "shadow-vocab":
                shadow_exact_hits += best["exact_span_hits"]
                if prefix4_delta > 0:
                    shadow_prefix4_wins += 1
                if prefix5_delta > 0:
                    shadow_prefix5_wins += 1
            if kind.startswith("binary-"):
                binary_exact_hits += best["exact_span_hits"]
                if prefix4_delta > 0:
                    binary_prefix4_wins += 1
                if prefix5_delta > 0:
                    binary_prefix5_wins += 1
        corpus_summaries.append(
            {
                "corpus": corpus["corpus"],
                "role": corpus["role"],
                "control_kind": kind,
                "paired_with": corpus.get("paired_with"),
                "identity_prefix_ge_4": identity["prefix_ge_4_count"],
                "identity_prefix_ge_5": identity["prefix_ge_5_count"],
                "identity_exact_hits": identity["exact_span_hits"],
                "best_transform": best["transform"],
                "best_prefix_ge_3": best["prefix_ge_3_count"],
                "best_prefix_ge_4": best["prefix_ge_4_count"],
                "best_prefix_ge_5": best["prefix_ge_5_count"],
                "best_exact_hits": best["exact_span_hits"],
                "prefix_ge_4_delta_vs_identity": prefix4_delta,
                "prefix_ge_5_delta_vs_identity": prefix5_delta,
                "exact_delta_vs_identity": exact_delta,
            }
        )
    return {
        "corpus_summaries": corpus_summaries,
        "heldout_prefix4_win_corpora": heldout_prefix4_wins,
        "heldout_exact_hits": heldout_exact_hits,
        "shadow_prefix4_win_corpora": shadow_prefix4_wins,
        "shadow_prefix5_win_corpora": shadow_prefix5_wins,
        "shadow_exact_hits": shadow_exact_hits,
        "binary_prefix4_win_corpora": binary_prefix4_wins,
        "binary_prefix5_win_corpora": binary_prefix5_wins,
        "binary_exact_hits": binary_exact_hits,
        "conclusion": (
            "Discovery-corpus transform leads do not yet generalize into exact "
            "held-out seed-span hits."
        ),
    }


def build_report() -> dict[str, Any]:
    prefix_sets = generate_manifold_report.generated_prefix_sets(MAX_SEED_LEN, SPAN_LEN)
    rows = [
        analyze_case(corpus, transform, prefix_sets)
        for corpus in CORPUS_VALIDATION_MATRIX
        for transform in TRANSFORM_VALIDATION_MATRIX
    ]
    return {
        "generated_by": "scripts/generate_transform_validation.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "validation_manifest_sha256": validation_manifest_hash(),
        "validation_manifest": validation_manifest(),
        "source_probe_sha256": hashlib.sha256((DOCS / "transform_probe.json").read_bytes()).hexdigest(),
        "hasher": HASHER,
        "max_seed_len": MAX_SEED_LEN,
        "seed_count": generate_manifold_report.seed_count(MAX_SEED_LEN),
        "span_len": SPAN_LEN,
        "span_step": SPAN_STEP,
        "results": rows,
        "summary": summarize(rows),
    }


def write_report(payload: dict[str, Any]) -> None:
    VALIDATION_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Telomere Transform Validation",
        "",
        "Generated by `scripts/generate_transform_validation.py`.",
        "This validates transform-probe leads on held-out structured corpora; it is not format support and not a compression claim.",
        "",
        f"Hasher: `{payload['hasher']}`.",
        f"Max seed len: `{payload['max_seed_len']}`.",
        f"Span len: `{payload['span_len']}`.",
        f"Transform-probe SHA-256: `{payload['source_probe_sha256']}`.",
        "",
        "## Corpus Summary",
        "",
        "| corpus | role | kind | paired | identity prefix >=4 | best transform | best prefix >=3 | best prefix >=4 | best prefix >=5 | prefix >=4 delta | prefix >=5 delta | best exact hits |",
        "| --- | --- | --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in payload["summary"]["corpus_summaries"]:
        display_row = dict(row)
        display_row["paired_with"] = row["paired_with"] if row["paired_with"] is not None else "-"
        lines.append(
            "| {corpus} | {role} | {control_kind} | {paired_with} | {identity_prefix_ge_4} | {best_transform} | "
            "{best_prefix_ge_3} | {best_prefix_ge_4} | {best_prefix_ge_5} | {prefix_ge_4_delta_vs_identity:+} | "
            "{prefix_ge_5_delta_vs_identity:+} | {best_exact_hits} |".format(
                **display_row,
            )
        )

    lines.extend(
        [
            "",
            "## Control Summary",
            "",
            "| control group | prefix >=4 win corpora | prefix >=5 win corpora | exact hits |",
            "| --- | ---: | ---: | ---: |",
            (
                f"| vocabulary-disjoint shadow | {payload['summary']['shadow_prefix4_win_corpora']} | "
                f"{payload['summary']['shadow_prefix5_win_corpora']} | {payload['summary']['shadow_exact_hits']} |"
            ),
            (
                f"| binary TLV/varint controls | {payload['summary']['binary_prefix4_win_corpora']} | "
                f"{payload['summary']['binary_prefix5_win_corpora']} | {payload['summary']['binary_exact_hits']} |"
            ),
            "",
            "## Full Matrix",
            "",
            "| case | role | kind | transform | prefix >=3 | prefix >=4 | prefix >=5 | prefix >=6 | exact hits |",
            "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in payload["results"]:
        lines.append(
            "| {corpus} | {corpus_role} | {control_kind} | {transform} | {prefix_ge_3_count} | "
            "{prefix_ge_4_count} | {prefix_ge_5_count} | {prefix_ge_6_count} | "
            "{exact_span_hits} |".format(**row)
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            payload["summary"]["conclusion"],
            f"Held-out corpora with prefix >=4 uplift: `{payload['summary']['heldout_prefix4_win_corpora']}`.",
            f"Held-out exact hits: `{payload['summary']['heldout_exact_hits']}`.",
            f"Vocabulary-disjoint shadow prefix >=5 win corpora: `{payload['summary']['shadow_prefix5_win_corpora']}`.",
            f"Binary TLV/varint exact hits: `{payload['summary']['binary_exact_hits']}`.",
            "",
            "- Shallow prefix uplift can be useful for designing future transforms, but exact span hits remain the hard compression requirement.",
            "- Vocabulary-disjoint and TLV/varint controls separate literal-token effects from syntax or binary-structure effects.",
            "- Held-out validation is required before promoting any transform into a format extension.",
            "- A transform that only wins on the discovery corpus should be treated as an overfit probe result.",
        ]
    )
    VALIDATION_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not VALIDATION_JSON.exists() or not VALIDATION_MD.exists():
        raise SystemExit("generated transform validation files are missing")
    payload = json.loads(VALIDATION_JSON.read_text(encoding="utf-8"))
    if payload.get("generated_by") != "scripts/generate_transform_validation.py":
        raise SystemExit("transform_validation.json has wrong generated_by marker")
    if payload.get("validation_manifest_sha256") != validation_manifest_hash():
        raise SystemExit("transform_validation.json validation manifest hash is stale")
    expected_count = len(CORPUS_VALIDATION_MATRIX) * len(TRANSFORM_VALIDATION_MATRIX)
    if len(payload.get("results", [])) != expected_count:
        raise SystemExit("transform_validation.json does not contain the full validation matrix")
    summaries = payload.get("summary", {}).get("corpus_summaries", [])
    kinds = {row.get("control_kind") for row in summaries}
    for required in ("shadow-vocab", "binary-tlv", "binary-varint"):
        if required not in kinds:
            raise SystemExit(f"transform_validation.json missing {required} controls")
    text = VALIDATION_MD.read_text(encoding="utf-8")
    for phrase in (
        "held-out structured corpora",
        "Corpus Summary",
        "Control Summary",
        "vocabulary-disjoint",
        "TLV/varint controls",
        "Held-out exact hits",
        "not format support",
    ):
        if phrase not in text:
            raise SystemExit(f"TRANSFORM_VALIDATION.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate generated transform validation")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.check:
        check_report()
        return
    write_report(build_report())


if __name__ == "__main__":
    main()
