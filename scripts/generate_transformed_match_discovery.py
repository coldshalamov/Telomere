#!/usr/bin/env python3
"""Generate exact match discovery after frozen reversible transforms."""

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
import generate_match_discovery
import generate_transform_probe
import generate_transform_validation


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
TRANSFORMED_JSON = DOCS / "transformed_match_discovery.json"
TRANSFORMED_MD = DOCS / "TRANSFORMED_MATCH_DISCOVERY.md"

HASHER = "sha256"
MAX_SEED_LEN = 2
SPAN_LEN = 8
SPAN_STEP = 1
PREFIX_LADDER = (3, 4, 5, 6)
SEED_RECORD_OVERHEAD_BYTES = 4
TOP_LIMIT = 40

FOCUS_REPLICATION_CORPORA = (
    "proto-schema-heldout",
    "openapi-spec-heldout",
    "terraform-hcl-heldout",
    "kubernetes-yaml-heldout",
    "hl7-v2-heldout",
    "unified-diff-heldout",
    "http-transcript-heldout",
    "fixed-width-heldout",
    "shadow-openapi-control",
    "binary-fixed-record-control",
    "binary-hash-payload-control",
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_hashes() -> dict[str, str]:
    return {
        "corpus_matrix_sha256": sha256(DOCS / "corpus_matrix.json"),
        "packed_sidecar_replication_sha256": sha256(
            DOCS / "packed_sidecar_replication.json"
        ),
        "transform_validation_sha256": sha256(DOCS / "transform_validation.json"),
    }


def transform_manifest() -> list[dict[str, Any]]:
    return list(generate_transform_validation.TRANSFORM_VALIDATION_MATRIX)


def validation_corpora() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in generate_transform_validation.CORPUS_VALIDATION_MATRIX:
        rows.append(
            {
                "name": row["name"],
                "corpus": row["corpus"],
                "family": "validation",
                "role": row["role"],
                "control_kind": row.get("control_kind", "ordinary-structured"),
                "independence_group": row.get("paired_with", row["corpus"]),
                "paired_with": row.get("paired_with"),
            }
        )
    return rows


def replication_corpora() -> list[dict[str, Any]]:
    replication = {row["name"]: row for row in generate_match_discovery.replication_corpora()}
    rows: list[dict[str, Any]] = []
    for name in FOCUS_REPLICATION_CORPORA:
        if name not in replication:
            raise RuntimeError(f"unknown focus corpus: {name}")
        rows.append({**replication[name], "selection_reason": "transformed-match-focus"})
    return rows


def corpus_manifest() -> list[dict[str, Any]]:
    return validation_corpora() + replication_corpora()


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
        "match_rule": "generated seed prefixes are compared directly against transformed raw target bytes",
        "transform_count": len(transform_manifest()),
        "corpus_count": len(corpus_manifest()),
        "focus_replication_corpus_names": FOCUS_REPLICATION_CORPORA,
        "scope": "pre-sidecar transformed match discovery only; not `.tlmr` transform metadata support",
    }


def manifest_hash() -> str:
    payload = json.dumps(search_manifest(), sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def byte_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = Counter(data)
    total = len(data)
    return round(
        -sum((count / total) * math.log2(count / total) for count in counts.values()),
        4,
    )


def corpus_bytes(row: dict[str, Any]) -> bytes:
    if row["family"] == "validation":
        return generate_corpus_matrix.corpus_bytes(row["corpus"])
    if row["family"] == "replication":
        return generate_match_discovery.corpus_bytes(row)
    raise ValueError(row["family"])


def apply_transform(data: bytes, transform: dict[str, Any]) -> bytes:
    return generate_transform_probe.apply_probe(
        data,
        generate_transform_validation.probe_from_validation_transform(transform),
    )


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


def analyze_row(corpus: dict[str, Any], transform: dict[str, Any]) -> dict[str, Any]:
    source = corpus_bytes(corpus)
    transformed = apply_transform(source, transform)
    starts = range(0, max(0, len(transformed) - SPAN_LEN + 1), SPAN_STEP)
    prefix_counts = {prefix_len: 0 for prefix_len in PREFIX_LADDER}
    max_prefix = 0
    dedup_spans: set[bytes] = set()
    exact_hits: list[dict[str, Any]] = []

    for start in starts:
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
            }
        )

    selected = weighted_interval_selection(exact_hits)
    literal_bytes_replaced = sum(row["span_len"] for row in selected)
    encoded_seed_bytes = sum(row["encoded_len"] for row in selected)
    net_seed_delta = encoded_seed_bytes - literal_bytes_replaced
    net_with_transform_metadata = net_seed_delta + int(transform["metadata_bytes"])
    return {
        "name": f"{corpus['name']}::{transform['name']}",
        "family": corpus["family"],
        "corpus": corpus["corpus"],
        "role": corpus["role"],
        "control_kind": corpus["control_kind"],
        "independence_group": corpus["independence_group"],
        "paired_with": corpus.get("paired_with"),
        "transform": transform["name"],
        "transform_family": transform["family"],
        "transform_parameter": transform["parameter"],
        "transform_reason": transform["reason"],
        "metadata_bytes": transform["metadata_bytes"],
        "input_bytes": len(source),
        "input_sha256": hashlib.sha256(source).hexdigest(),
        "transformed_sha256": hashlib.sha256(transformed).hexdigest(),
        "byte_entropy": byte_entropy(transformed),
        "target_span_count": max(0, len(transformed) - SPAN_LEN + 1),
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
        "literal_bytes_replaced": literal_bytes_replaced,
        "encoded_seed_bytes": encoded_seed_bytes,
        "net_seed_delta_bytes": net_seed_delta,
        "net_with_transform_metadata_bytes": net_with_transform_metadata,
        "metadata_profitable": bool(selected) and net_with_transform_metadata < 0,
        "selected_records": selected[:8],
    }


def build_rows() -> list[dict[str, Any]]:
    return [
        analyze_row(corpus, transform)
        for corpus in corpus_manifest()
        for transform in transform_manifest()
    ]


def count_by(rows: list[dict[str, Any]], field: str) -> dict[str, int]:
    return {str(key): value for key, value in sorted(Counter(row[field] for row in rows).items())}


def sum_by(rows: list[dict[str, Any]], field: str, value_field: str) -> dict[str, int]:
    output: dict[str, int] = {}
    for row in rows:
        key = str(row[field])
        output[key] = output.get(key, 0) + int(row[value_field])
    return dict(sorted(output.items()))


def control_kind_summary(rows: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    output = {}
    for kind in sorted({row["control_kind"] for row in rows}):
        scoped = [row for row in rows if row["control_kind"] == kind]
        output[kind] = {
            "row_count": len(scoped),
            "rows_with_prefix_ge_5": sum(1 for row in scoped if row["prefix_ge_5_count"] > 0),
            "rows_with_exact_hits": sum(1 for row in scoped if row["exact_hit_count"] > 0),
            "rows_with_selected_spans": sum(
                1 for row in scoped if row["selected_span_count"] > 0
            ),
            "metadata_profitable_rows": sum(
                1 for row in scoped if row["metadata_profitable"]
            ),
            "total_exact_hits": sum(row["exact_hit_count"] for row in scoped),
            "total_selected_spans": sum(row["selected_span_count"] for row in scoped),
            "max_prefix_observed": max(row["max_prefix_observed"] for row in scoped),
        }
    return output


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    rows_with_prefix5 = [row for row in rows if row["prefix_ge_5_count"] > 0]
    rows_with_exact = [row for row in rows if row["exact_hit_count"] > 0]
    rows_with_selected = [row for row in rows if row["selected_span_count"] > 0]
    metadata_profitable_rows = [row for row in rows if row["metadata_profitable"]]
    ordinary_selected_groups = {
        row["independence_group"]
        for row in rows_with_selected
        if row["role"] == "held-out" and row["control_kind"] == "ordinary-structured"
    }
    ordinary_metadata_groups = {
        row["independence_group"]
        for row in metadata_profitable_rows
        if row["role"] == "held-out" and row["control_kind"] == "ordinary-structured"
    }
    best_prefix = max(
        rows,
        key=lambda row: (
            row["max_prefix_observed"],
            row["prefix_ge_6_count"],
            row["prefix_ge_5_count"],
            row["prefix_ge_4_count"],
            row["name"],
        ),
    )
    best_selected = min(
        rows_with_selected,
        key=lambda row: row["net_with_transform_metadata_bytes"],
        default=None,
    )
    return {
        "row_count": len(rows),
        "corpus_count": len(corpus_manifest()),
        "validation_corpus_count": len(validation_corpora()),
        "replication_corpus_count": len(replication_corpora()),
        "transform_count": len(transform_manifest()),
        "target_span_count": sum(row["target_span_count"] for row in rows),
        "dedup_span_count": sum(row["dedup_span_count"] for row in rows),
        "rows_with_prefix_ge_5": len(rows_with_prefix5),
        "rows_with_exact_hits": len(rows_with_exact),
        "rows_with_selected_spans": len(rows_with_selected),
        "metadata_profitable_rows": len(metadata_profitable_rows),
        "total_exact_hits": sum(row["exact_hit_count"] for row in rows),
        "total_positive_exact_hits": sum(row["positive_exact_hit_count"] for row in rows),
        "total_selected_spans": sum(row["selected_span_count"] for row in rows),
        "ordinary_heldout_selected_groups": len(ordinary_selected_groups),
        "ordinary_heldout_metadata_profitable_groups": len(ordinary_metadata_groups),
        "best_prefix_case": best_prefix["name"],
        "best_prefix_observed": best_prefix["max_prefix_observed"],
        "best_selected_case": best_selected["name"] if best_selected else None,
        "best_selected_net_with_transform_metadata_bytes": (
            best_selected["net_with_transform_metadata_bytes"] if best_selected else None
        ),
        "rows_by_control_kind": count_by(rows, "control_kind"),
        "control_kind_summary": control_kind_summary(rows),
        "exact_hits_by_transform_family": sum_by(rows, "transform_family", "exact_hit_count"),
        "selected_spans_by_transform_family": sum_by(
            rows, "transform_family", "selected_span_count"
        ),
        "prefix5_rows_by_transform_family": count_by(rows_with_prefix5, "transform_family"),
        "conclusion": (
            "Frozen transforms produced metadata-profitable exact seed-span rows."
            if metadata_profitable_rows
            else (
                "Frozen transforms produced selected seed-span rows, but not after transform metadata."
                if rows_with_selected
                else "Frozen transforms did not produce selected exact seed-span rows."
            )
        ),
    }


def top_rows(rows: list[dict[str, Any]], limit: int = TOP_LIMIT) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            -row["metadata_profitable"],
            -row["selected_span_count"],
            -row["exact_hit_count"],
            -row["max_prefix_observed"],
            -row["prefix_ge_6_count"],
            -row["prefix_ge_5_count"],
            -row["prefix_ge_4_count"],
            row["name"],
        ),
    )[:limit]


def build_report() -> dict[str, Any]:
    rows = build_rows()
    return {
        "generated_by": "scripts/generate_transformed_match_discovery.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "artifact_hashes": artifact_hashes(),
        "manifest_sha256": manifest_hash(),
        "manifest": search_manifest(),
        "corpus_manifest": corpus_manifest(),
        "transform_manifest": transform_manifest(),
        "rows": rows,
        "summary": summarize(rows),
    }


def write_report(payload: dict[str, Any]) -> None:
    TRANSFORMED_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary = payload["summary"]
    lines = [
        "# Telomere Transformed Match Discovery",
        "",
        "Generated by `scripts/generate_transformed_match_discovery.py`.",
        "This is a pre-sidecar transformed match discovery report, not `.tlmr` transform metadata support.",
        "",
        f"Rows: `{summary['row_count']}`.",
        f"Corpora: `{summary['corpus_count']}`.",
        f"Transforms: `{summary['transform_count']}`.",
        f"Target spans scanned: `{summary['target_span_count']}`.",
        f"Deduplicated spans scanned: `{summary['dedup_span_count']}`.",
        f"Rows with prefix >=5: `{summary['rows_with_prefix_ge_5']}`.",
        f"Rows with exact hits: `{summary['rows_with_exact_hits']}`.",
        f"Rows with selected spans: `{summary['rows_with_selected_spans']}`.",
        f"Metadata-profitable rows: `{summary['metadata_profitable_rows']}`.",
        f"Total exact hits: `{summary['total_exact_hits']}`.",
        f"Total selected spans: `{summary['total_selected_spans']}`.",
        f"Ordinary held-out selected groups: `{summary['ordinary_heldout_selected_groups']}`.",
        f"Ordinary held-out metadata-profitable groups: `{summary['ordinary_heldout_metadata_profitable_groups']}`.",
        f"Best prefix case: `{summary['best_prefix_case']}`.",
        f"Best prefix observed: `{summary['best_prefix_observed']}`.",
        f"Best selected case: `{summary['best_selected_case']}`.",
        f"Best selected net with transform metadata bytes: `{summary['best_selected_net_with_transform_metadata_bytes']}`.",
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
        "- Generated seed prefixes are compared directly against transformed raw target bytes.",
        "- Transform metadata bytes are charged once per row when reporting metadata-profitable rows.",
        "",
        "## Control Summary",
        "",
        "| control | rows | p5 rows | exact rows | selected rows | metadata-profitable rows | exact hits | selected spans | max prefix |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for control_kind, data in summary["control_kind_summary"].items():
        lines.append(
            "| {control_kind} | {row_count} | {rows_with_prefix_ge_5} | "
            "{rows_with_exact_hits} | {rows_with_selected_spans} | "
            "{metadata_profitable_rows} | {total_exact_hits} | "
            "{total_selected_spans} | {max_prefix_observed} |".format(
                control_kind=control_kind,
                **data,
            )
        )
    lines.extend(
        [
            "",
            "## Top Rows",
            "",
            "| row | control | transform | metadata | spans | p4 | p5 | p6 | exact | selected | net with metadata |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in top_rows(payload["rows"]):
        lines.append(
            "| {name} | {control_kind} | {transform} | {metadata_bytes} | "
            "{target_span_count} | {prefix_ge_4_count} | {prefix_ge_5_count} | "
            "{prefix_ge_6_count} | {exact_hit_count} | {selected_span_count} | "
            "{net_with_transform_metadata_bytes} |".format(**row)
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- This artifact applies the frozen transform-validation matrix before exact seed-span matching.",
            "- It verifies every exact hit by regenerating the seed expansion bytes.",
            "- Selected spans use deterministic weighted interval selection; transform metadata is then charged as row overhead.",
            "- Prefix-only rows remain steering evidence; they are not compression wins without exact generated-byte matches.",
            "- A promotion requires selected metadata-profitable spans in multiple ordinary held-out groups or repeatable prefix >=5 movement.",
        ]
    )
    TRANSFORMED_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def expected_row_count() -> int:
    return len(corpus_manifest()) * len(transform_manifest())


def check_report() -> None:
    if not TRANSFORMED_JSON.exists() or not TRANSFORMED_MD.exists():
        raise SystemExit("generated transformed match discovery files are missing")
    payload = load_json(TRANSFORMED_JSON)
    if payload.get("generated_by") != "scripts/generate_transformed_match_discovery.py":
        raise SystemExit("transformed_match_discovery.json has wrong generated_by marker")
    if payload.get("artifact_hashes") != artifact_hashes():
        raise SystemExit("transformed match discovery artifact hashes are stale")
    if payload.get("manifest_sha256") != manifest_hash():
        raise SystemExit("transformed match discovery manifest hash is stale")
    summary = payload.get("summary", {})
    if summary.get("row_count") != expected_row_count():
        raise SystemExit("transformed match discovery row count is stale")
    if len(payload.get("rows", [])) != summary.get("row_count"):
        raise SystemExit("transformed match discovery row payload is incomplete")
    text = TRANSFORMED_MD.read_text(encoding="utf-8")
    for phrase in (
        "Telomere Transformed Match Discovery",
        "pre-sidecar transformed match discovery report",
        "Target block hashing: `false`",
        "transformed raw target bytes",
        "weighted interval selection",
        "Transform metadata bytes are charged",
    ):
        if phrase not in text:
            raise SystemExit(f"TRANSFORMED_MATCH_DISCOVERY.md missing phrase: {phrase}")


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
