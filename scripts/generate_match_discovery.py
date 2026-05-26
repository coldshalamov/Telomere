#!/usr/bin/env python3
"""Generate a pre-sidecar exact match-discovery report."""

from __future__ import annotations

import argparse
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
import generate_packed_sidecar_replication
import generate_transform_validation


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
MATCH_JSON = DOCS / "match_discovery.json"
MATCH_MD = DOCS / "MATCH_DISCOVERY.md"

HASHER = "sha256"
MAX_SEED_LEN = 2
BASE_BLOCK_BYTES = 4
ARITIES = (1, 2, 3, 4, 5)
PREFIX_LADDER = (3, 4, 5, 6)
SEARCH_POLICIES = (
    {"name": "sliding-step1", "span_step": 1, "phase": 0},
    {"name": "block-phase0", "span_step": BASE_BLOCK_BYTES, "phase": 0},
    {"name": "block-phase1", "span_step": BASE_BLOCK_BYTES, "phase": 1},
    {"name": "block-phase2", "span_step": BASE_BLOCK_BYTES, "phase": 2},
    {"name": "block-phase3", "span_step": BASE_BLOCK_BYTES, "phase": 3},
)
SEED_RECORD_OVERHEAD_BYTES = 4
TOP_LIMIT = 32


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_hashes() -> dict[str, str]:
    return {
        "corpus_matrix_sha256": sha256(DOCS / "corpus_matrix.json"),
        "transform_validation_sha256": sha256(DOCS / "transform_validation.json"),
        "packed_sidecar_replication_sha256": sha256(
            DOCS / "packed_sidecar_replication.json"
        ),
    }


def search_manifest() -> dict[str, Any]:
    return {
        "hasher": HASHER,
        "max_seed_len": MAX_SEED_LEN,
        "seed_order": "1-byte seeds first, then 2-byte seeds, each bucket big-endian",
        "base_block_bytes": BASE_BLOCK_BYTES,
        "arities": ARITIES,
        "span_lengths": [BASE_BLOCK_BYTES * arity for arity in ARITIES],
        "prefix_ladder": PREFIX_LADDER,
        "search_policies": SEARCH_POLICIES,
        "seed_record_overhead_bytes": SEED_RECORD_OVERHEAD_BYTES,
        "scope": "pre-sidecar match discovery only; not .tlmr format support",
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


def validation_corpora() -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for row in generate_transform_validation.CORPUS_VALIDATION_MATRIX:
        output.append(
            {
                "name": row["name"],
                "corpus": row["corpus"],
                "family": "validation",
                "role": row["role"],
                "control_kind": row.get("control_kind", "ordinary-structured"),
                "independence_group": row.get("corpus", row["name"]),
            }
        )
    return output


def replication_corpora() -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for row in generate_packed_sidecar_replication.REPLICATION_CORPORA:
        output.append(
            {
                "name": row["name"],
                "corpus": row["corpus"],
                "family": "replication",
                "role": row["role"],
                "control_kind": row["control_kind"],
                "independence_group": row["independence_group"],
            }
        )
    return output


def corpus_manifest() -> list[dict[str, Any]]:
    rows = validation_corpora() + replication_corpora()
    seen: set[tuple[str, str]] = set()
    output: list[dict[str, Any]] = []
    for row in rows:
        key = (row["family"], row["corpus"])
        if key in seen:
            continue
        seen.add(key)
        output.append(row)
    return output


def corpus_bytes(row: dict[str, Any]) -> bytes:
    if row["family"] == "validation":
        return generate_corpus_matrix.corpus_bytes(row["corpus"])
    if row["family"] == "replication":
        return generate_packed_sidecar_replication.corpus_bytes(row["corpus"])
    raise ValueError(row["family"])


@lru_cache(maxsize=1)
def seed_digests() -> tuple[tuple[int, bytes, bytes], ...]:
    output = []
    for seed_index, seed in enumerate(generate_manifold_report.iter_seed_bytes(MAX_SEED_LEN)):
        output.append((seed_index, seed, hashlib.sha256(seed).digest()))
    return tuple(output)


@lru_cache(maxsize=None)
def prefix_map(prefix_len: int) -> dict[bytes, dict[str, Any]]:
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


def candidate_starts(data_len: int, span_len: int, policy: dict[str, Any]) -> range:
    start = int(policy["phase"])
    step = int(policy["span_step"])
    if data_len < span_len or start > data_len - span_len:
        return range(0)
    return range(start, data_len - span_len + 1, step)


def selected_exact_hits(opportunities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    covered_until = -1
    for row in sorted(opportunities, key=lambda item: (-item["savings_bytes"], item["start_offset"])):
        if row["start_offset"] < covered_until:
            continue
        selected.append(row)
        covered_until = row["start_offset"] + row["span_len"]
    return sorted(selected, key=lambda item: item["start_offset"])


def analyze_row(corpus: dict[str, Any], policy: dict[str, Any], arity: int) -> dict[str, Any]:
    data = corpus_bytes(corpus)
    span_len = BASE_BLOCK_BYTES * arity
    starts = list(candidate_starts(len(data), span_len, policy))
    prefix_counts = {prefix_len: 0 for prefix_len in PREFIX_LADDER if prefix_len <= span_len}
    max_prefix = 0
    exact_hits: list[dict[str, Any]] = []
    for start in starts:
        span = data[start : start + span_len]
        for prefix_len in prefix_counts:
            if span[:prefix_len] in prefix_map(prefix_len):
                prefix_counts[prefix_len] += 1
        for prefix_len in sorted(
            [item for item in PREFIX_LADDER if item <= span_len],
            reverse=True,
        ):
            if span[:prefix_len] in prefix_map(prefix_len):
                max_prefix = max(max_prefix, prefix_len)
                break
        hit = prefix_map(span_len).get(span)
        if hit is None:
            continue
        encoded_len = SEED_RECORD_OVERHEAD_BYTES + int(hit["seed_len"])
        exact_hits.append(
            {
                "start_offset": start,
                "span_len": span_len,
                "arity": arity,
                "seed_index": hit["seed_index"],
                "seed_len": hit["seed_len"],
                "seed_hex": hit["seed_hex"],
                "encoded_len": encoded_len,
                "savings_bytes": span_len - encoded_len,
            }
        )
    selected = selected_exact_hits([row for row in exact_hits if row["savings_bytes"] > 0])
    literal_bytes_replaced = sum(row["span_len"] for row in selected)
    encoded_seed_bytes = sum(row["encoded_len"] for row in selected)
    row_name = f"{corpus['name']}::{policy['name']}::arity{arity}"
    return {
        "name": row_name,
        "family": corpus["family"],
        "corpus": corpus["corpus"],
        "role": corpus["role"],
        "control_kind": corpus["control_kind"],
        "independence_group": corpus["independence_group"],
        "policy": policy["name"],
        "span_step": policy["span_step"],
        "phase": policy["phase"],
        "arity": arity,
        "span_len": span_len,
        "input_bytes": len(data),
        "input_sha256": hashlib.sha256(data).hexdigest(),
        "byte_entropy": byte_entropy(data),
        "target_span_count": len(starts),
        "dedup_span_count": len({data[start : start + span_len] for start in starts}),
        "prefix_ge_3_count": prefix_counts.get(3, 0),
        "prefix_ge_4_count": prefix_counts.get(4, 0),
        "prefix_ge_5_count": prefix_counts.get(5, 0),
        "prefix_ge_6_count": prefix_counts.get(6, 0),
        "max_prefix_observed": max_prefix,
        "exact_hit_count": len(exact_hits),
        "positive_exact_hit_count": sum(1 for row in exact_hits if row["savings_bytes"] > 0),
        "selected_span_count": len(selected),
        "literal_bytes_replaced": literal_bytes_replaced,
        "encoded_seed_bytes": encoded_seed_bytes,
        "net_seed_delta_bytes": encoded_seed_bytes - literal_bytes_replaced,
        "selected_records": selected[:8],
    }


def build_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for corpus in corpus_manifest():
        for policy in SEARCH_POLICIES:
            for arity in ARITIES:
                rows.append(analyze_row(corpus, policy, arity))
    return rows


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    rows_with_prefix5 = [row for row in rows if row["prefix_ge_5_count"] > 0]
    rows_with_exact = [row for row in rows if row["exact_hit_count"] > 0]
    rows_with_selected = [row for row in rows if row["selected_span_count"] > 0]
    ordinary_selected_groups = {
        row["independence_group"]
        for row in rows_with_selected
        if row["role"] == "held-out" and row["control_kind"] == "ordinary-structured"
    }
    best_prefix = max(rows, key=lambda row: (row["max_prefix_observed"], row["prefix_ge_5_count"], row["prefix_ge_4_count"], row["name"]))
    best_selected = min(
        rows_with_selected,
        key=lambda row: row["net_seed_delta_bytes"],
        default=None,
    )
    return {
        "row_count": len(rows),
        "corpus_count": len(corpus_manifest()),
        "validation_corpus_count": len(validation_corpora()),
        "replication_corpus_count": len(replication_corpora()),
        "search_policy_count": len(SEARCH_POLICIES),
        "arity_count": len(ARITIES),
        "target_span_count": sum(row["target_span_count"] for row in rows),
        "dedup_span_count": sum(row["dedup_span_count"] for row in rows),
        "rows_with_prefix_ge_5": len(rows_with_prefix5),
        "rows_with_exact_hits": len(rows_with_exact),
        "rows_with_selected_spans": len(rows_with_selected),
        "total_exact_hits": sum(row["exact_hit_count"] for row in rows),
        "total_selected_spans": sum(row["selected_span_count"] for row in rows),
        "ordinary_heldout_selected_groups": len(ordinary_selected_groups),
        "best_prefix_case": best_prefix["name"],
        "best_prefix_observed": best_prefix["max_prefix_observed"],
        "best_selected_case": best_selected["name"] if best_selected else None,
        "best_selected_net_delta_bytes": best_selected["net_seed_delta_bytes"] if best_selected else None,
        "selected_rows_by_control_kind": dict(
            Counter(row["control_kind"] for row in rows_with_selected)
        ),
        "prefix5_rows_by_control_kind": dict(
            Counter(row["control_kind"] for row in rows_with_prefix5)
        ),
        "conclusion": (
            "Match discovery produced selected exact spans before sidecar packing."
            if rows_with_selected
            else "Match discovery did not produce selected exact spans before sidecar packing."
        ),
    }


def top_rows(rows: list[dict[str, Any]], limit: int = TOP_LIMIT) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            -row["selected_span_count"],
            -row["exact_hit_count"],
            -row["max_prefix_observed"],
            -row["prefix_ge_5_count"],
            -row["prefix_ge_4_count"],
            row["name"],
        ),
    )[:limit]


def build_report() -> dict[str, Any]:
    rows = build_rows()
    return {
        "generated_by": "scripts/generate_match_discovery.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "artifact_hashes": artifact_hashes(),
        "manifest_sha256": manifest_hash(),
        "manifest": search_manifest(),
        "corpus_manifest": corpus_manifest(),
        "rows": rows,
        "summary": summarize(rows),
    }


def write_report(payload: dict[str, Any]) -> None:
    MATCH_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary = payload["summary"]
    lines = [
        "# Telomere Match Discovery",
        "",
        "Generated by `scripts/generate_match_discovery.py`.",
        "This is a pre-sidecar match discovery report, not `.tlmr` format support.",
        "",
        f"Rows: `{summary['row_count']}`.",
        f"Corpora: `{summary['corpus_count']}`.",
        f"Target spans scanned: `{summary['target_span_count']}`.",
        f"Rows with prefix >=5: `{summary['rows_with_prefix_ge_5']}`.",
        f"Rows with exact hits: `{summary['rows_with_exact_hits']}`.",
        f"Rows with selected spans: `{summary['rows_with_selected_spans']}`.",
        f"Total exact hits: `{summary['total_exact_hits']}`.",
        f"Total selected spans: `{summary['total_selected_spans']}`.",
        f"Ordinary held-out selected groups: `{summary['ordinary_heldout_selected_groups']}`.",
        f"Best prefix case: `{summary['best_prefix_case']}`.",
        f"Best prefix observed: `{summary['best_prefix_observed']}`.",
        f"Best selected case: `{summary['best_selected_case']}`.",
        f"Best selected net delta bytes: `{summary['best_selected_net_delta_bytes']}`.",
        "",
        summary["conclusion"],
        "",
        "## Top Rows",
        "",
        "| row | control | policy | arity | spans | p4 | p5 | p6 | exact | selected | net seed delta |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in top_rows(payload["rows"]):
        lines.append(
            "| {name} | {control_kind} | {policy} | {arity} | {target_span_count} | "
            "{prefix_ge_4_count} | {prefix_ge_5_count} | {prefix_ge_6_count} | "
            "{exact_hit_count} | {selected_span_count} | {net_seed_delta_bytes} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- This artifact scans arity 1..5 spans with sliding and block-phase policies before any sidecar payload coding.",
            "- A promotion requires selected exact spans or repeatable prefix >=5 movement on ordinary held-out corpora.",
            "- Prefix-only rows are steering evidence; they are not compression wins without exact generated-byte matches.",
            "- If selected spans remain absent, descriptor packing and format work stay gated.",
        ]
    )
    MATCH_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not MATCH_JSON.exists() or not MATCH_MD.exists():
        raise SystemExit("generated match discovery files are missing")
    payload = load_json(MATCH_JSON)
    if payload.get("generated_by") != "scripts/generate_match_discovery.py":
        raise SystemExit("match_discovery.json has wrong generated_by marker")
    if payload.get("artifact_hashes") != artifact_hashes():
        raise SystemExit("match discovery artifact hashes are stale")
    if payload.get("manifest_sha256") != manifest_hash():
        raise SystemExit("match discovery manifest hash is stale")
    summary = payload.get("summary", {})
    if summary.get("row_count") != len(corpus_manifest()) * len(SEARCH_POLICIES) * len(ARITIES):
        raise SystemExit("match discovery row count is stale")
    text = MATCH_MD.read_text(encoding="utf-8")
    for phrase in (
        "Telomere Match Discovery",
        "pre-sidecar match discovery report",
        "arity 1..5 spans",
        "Prefix-only rows are steering evidence",
    ):
        if phrase not in text:
            raise SystemExit(f"MATCH_DISCOVERY.md missing phrase: {phrase}")


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
