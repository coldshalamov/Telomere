#!/usr/bin/env python3
"""Generate an alignment and arity match-discovery matrix."""

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

import generate_manifold_report
import generate_match_discovery


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
ALIGNMENT_JSON = DOCS / "alignment_arity_discovery.json"
ALIGNMENT_MD = DOCS / "ALIGNMENT_ARITY_DISCOVERY.md"

HASHER = "sha256"
HASH_DIGEST_BYTES = 32
MAX_SEED_LEN = 2
BLOCK_SIZES = (3, 4, 5, 6, 8)
ARITIES = (1, 2, 3, 4, 5)
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
        "match_discovery_sha256": sha256(DOCS / "match_discovery.json"),
        "packed_sidecar_replication_sha256": sha256(
            DOCS / "packed_sidecar_replication.json"
        ),
    }


def policy_manifest(block_size: int) -> list[dict[str, Any]]:
    policies = [
        {
            "name": "sliding-step1",
            "kind": "sliding-step1",
            "span_step": 1,
            "phase": 0,
        }
    ]
    for phase in range(2):
        policies.append(
            {
                "name": f"step2-phase{phase}",
                "kind": "step2",
                "span_step": 2,
                "phase": phase,
            }
        )
    for phase in range(block_size):
        policies.append(
            {
                "name": f"block-phase{phase}",
                "kind": "block-phase",
                "span_step": block_size,
                "phase": phase,
            }
        )
    return policies


def all_configs() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    supported: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for block_size in BLOCK_SIZES:
        for policy in policy_manifest(block_size):
            for arity in ARITIES:
                span_len = block_size * arity
                config = {
                    "name": f"b{block_size}-{policy['name']}-arity{arity}",
                    "block_size": block_size,
                    "policy": policy["name"],
                    "policy_kind": policy["kind"],
                    "span_step": policy["span_step"],
                    "phase": policy["phase"],
                    "arity": arity,
                    "span_len": span_len,
                }
                if span_len > HASH_DIGEST_BYTES:
                    skipped.append(
                        {
                            **config,
                            "reason": "span_len exceeds SHA-256 digest bytes",
                        }
                    )
                    continue
                supported.append(config)
    return supported, skipped


def search_manifest() -> dict[str, Any]:
    supported, skipped = all_configs()
    return {
        "hasher": HASHER,
        "max_seed_len": MAX_SEED_LEN,
        "seed_order": "1-byte seeds first, then 2-byte seeds, each bucket big-endian",
        "block_sizes": BLOCK_SIZES,
        "arities": ARITIES,
        "prefix_ladder": PREFIX_LADDER,
        "hash_digest_bytes": HASH_DIGEST_BYTES,
        "seed_record_overhead_bytes": SEED_RECORD_OVERHEAD_BYTES,
        "target_block_hashing": False,
        "match_rule": "generated seed prefixes are compared directly against raw target bytes",
        "focus_replication_corpus_names": FOCUS_REPLICATION_CORPORA,
        "supported_config_count": len(supported),
        "skipped_config_count": len(skipped),
        "skipped_configs": skipped,
        "scope": "alignment and arity discovery only; not `.tlmr` format support",
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


def corpus_manifest() -> list[dict[str, Any]]:
    replication = {row["name"]: row for row in generate_match_discovery.replication_corpora()}
    rows = []
    for name in FOCUS_REPLICATION_CORPORA:
        if name not in replication:
            raise RuntimeError(f"unknown focus corpus: {name}")
        rows.append({**replication[name], "selection_reason": "alignment-arity-focus"})
    return rows


def corpus_bytes(row: dict[str, Any]) -> bytes:
    return generate_match_discovery.corpus_bytes(row)


@lru_cache(maxsize=1)
def seed_digests() -> tuple[tuple[int, bytes, bytes], ...]:
    output = []
    for seed_index, seed in enumerate(generate_manifold_report.iter_seed_bytes(MAX_SEED_LEN)):
        output.append((seed_index, seed, hashlib.sha256(seed).digest()))
    return tuple(output)


@lru_cache(maxsize=None)
def generated_prefix_map(prefix_len: int) -> dict[bytes, dict[str, Any]]:
    if prefix_len > HASH_DIGEST_BYTES:
        raise ValueError(f"prefix_len {prefix_len} exceeds digest bytes")
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


def candidate_starts(data_len: int, span_len: int, config: dict[str, Any]) -> range:
    start = int(config["phase"])
    step = int(config["span_step"])
    if data_len < span_len or start > data_len - span_len:
        return range(0)
    return range(start, data_len - span_len + 1, step)


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


def analyze_row(corpus: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    data = corpus_bytes(corpus)
    span_len = int(config["span_len"])
    starts = candidate_starts(len(data), span_len, config)
    prefix_lengths = [prefix_len for prefix_len in PREFIX_LADDER if prefix_len <= span_len]
    prefix_counts = {prefix_len: 0 for prefix_len in prefix_lengths}
    max_prefix = 0
    target_span_count = 0
    dedup_spans: set[bytes] = set()
    exact_hits: list[dict[str, Any]] = []

    for start in starts:
        target_span_count += 1
        span = data[start : start + span_len]
        dedup_spans.add(span)
        for prefix_len in prefix_lengths:
            if span[:prefix_len] in generated_prefix_map(prefix_len):
                prefix_counts[prefix_len] += 1
        for prefix_len in sorted(prefix_lengths, reverse=True):
            if span[:prefix_len] in generated_prefix_map(prefix_len):
                max_prefix = max(max_prefix, prefix_len)
                break
        hit = generated_prefix_map(span_len).get(span)
        if hit is None:
            continue
        regenerated = hashlib.sha256(bytes.fromhex(hit["seed_hex"])).digest()[:span_len]
        if regenerated != span:
            raise RuntimeError("generated-prefix map produced an unverified hit")
        encoded_len = SEED_RECORD_OVERHEAD_BYTES + int(hit["seed_len"])
        exact_hits.append(
            {
                "start_offset": start,
                "end_offset": start + span_len,
                "span_len": span_len,
                "block_size": config["block_size"],
                "start_mod_block": start % int(config["block_size"]),
                "span_step": config["span_step"],
                "phase": config["phase"],
                "arity": config["arity"],
                "seed_index": hit["seed_index"],
                "seed_len": hit["seed_len"],
                "seed_hex": hit["seed_hex"],
                "encoded_len": encoded_len,
                "savings_bytes": span_len - encoded_len,
            }
        )

    selected = weighted_interval_selection(exact_hits)
    literal_bytes_replaced = sum(row["span_len"] for row in selected)
    encoded_seed_bytes = sum(row["encoded_len"] for row in selected)
    row_name = f"{corpus['name']}::{config['name']}"
    return {
        "name": row_name,
        "family": corpus["family"],
        "corpus": corpus["corpus"],
        "role": corpus["role"],
        "control_kind": corpus["control_kind"],
        "independence_group": corpus["independence_group"],
        "block_size": config["block_size"],
        "policy": config["policy"],
        "policy_kind": config["policy_kind"],
        "span_step": config["span_step"],
        "phase": config["phase"],
        "arity": config["arity"],
        "span_len": span_len,
        "input_bytes": len(data),
        "input_sha256": hashlib.sha256(data).hexdigest(),
        "byte_entropy": byte_entropy(data),
        "target_span_count": target_span_count,
        "dedup_span_count": len(dedup_spans),
        "prefix_ge_3_count": prefix_counts.get(3, 0),
        "prefix_ge_4_count": prefix_counts.get(4, 0),
        "prefix_ge_5_count": prefix_counts.get(5, 0),
        "prefix_ge_6_count": prefix_counts.get(6, 0),
        "max_prefix_observed": max_prefix,
        "exact_hit_count": len(exact_hits),
        "positive_exact_hit_count": sum(
            1 for row in exact_hits if row["savings_bytes"] > 0
        ),
        "unprofitable_exact_hit_count": sum(
            1 for row in exact_hits if row["savings_bytes"] <= 0
        ),
        "selected_span_count": len(selected),
        "literal_bytes_replaced": literal_bytes_replaced,
        "encoded_seed_bytes": encoded_seed_bytes,
        "net_seed_delta_bytes": encoded_seed_bytes - literal_bytes_replaced,
        "selected_records": selected[:8],
    }


def build_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    configs, _skipped = all_configs()
    for corpus in corpus_manifest():
        for config in configs:
            rows.append(analyze_row(corpus, config))
    return rows


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
            "total_exact_hits": sum(row["exact_hit_count"] for row in scoped),
            "total_selected_spans": sum(row["selected_span_count"] for row in scoped),
            "max_prefix_observed": max(row["max_prefix_observed"] for row in scoped),
        }
    return output


def selected_start_mod_block(rows: list[dict[str, Any]]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for row in rows:
        for selected in row["selected_records"]:
            counter[str(selected["start_mod_block"])] += 1
    return dict(sorted(counter.items()))


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    configs, skipped = all_configs()
    rows_with_prefix5 = [row for row in rows if row["prefix_ge_5_count"] > 0]
    rows_with_prefix6 = [row for row in rows if row["prefix_ge_6_count"] > 0]
    rows_with_exact = [row for row in rows if row["exact_hit_count"] > 0]
    rows_with_selected = [row for row in rows if row["selected_span_count"] > 0]
    ordinary_selected_groups = {
        row["independence_group"]
        for row in rows_with_selected
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
        key=lambda row: row["net_seed_delta_bytes"],
        default=None,
    )
    return {
        "row_count": len(rows),
        "corpus_count": len(corpus_manifest()),
        "config_count": len(configs),
        "potential_config_count": len(configs) + len(skipped),
        "skipped_config_count": len(skipped),
        "skipped_row_count": len(skipped) * len(corpus_manifest()),
        "target_span_count": sum(row["target_span_count"] for row in rows),
        "dedup_span_count": sum(row["dedup_span_count"] for row in rows),
        "rows_with_prefix_ge_5": len(rows_with_prefix5),
        "rows_with_prefix_ge_6": len(rows_with_prefix6),
        "rows_with_exact_hits": len(rows_with_exact),
        "rows_with_selected_spans": len(rows_with_selected),
        "total_exact_hits": sum(row["exact_hit_count"] for row in rows),
        "total_positive_exact_hits": sum(row["positive_exact_hit_count"] for row in rows),
        "total_unprofitable_exact_hits": sum(
            row["unprofitable_exact_hit_count"] for row in rows
        ),
        "total_selected_spans": sum(row["selected_span_count"] for row in rows),
        "ordinary_heldout_selected_groups": len(ordinary_selected_groups),
        "prefix5_without_exact_rows": sum(
            1 for row in rows if row["prefix_ge_5_count"] > 0 and row["exact_hit_count"] == 0
        ),
        "best_prefix_case": best_prefix["name"],
        "best_prefix_observed": best_prefix["max_prefix_observed"],
        "best_selected_case": best_selected["name"] if best_selected else None,
        "best_selected_net_delta_bytes": (
            best_selected["net_seed_delta_bytes"] if best_selected else None
        ),
        "rows_by_control_kind": count_by(rows, "control_kind"),
        "control_kind_summary": control_kind_summary(rows),
        "exact_hits_by_block_size": sum_by(rows, "block_size", "exact_hit_count"),
        "selected_spans_by_block_size": sum_by(rows, "block_size", "selected_span_count"),
        "prefix5_rows_by_block_size": count_by(rows_with_prefix5, "block_size"),
        "exact_hits_by_policy_kind": sum_by(rows, "policy_kind", "exact_hit_count"),
        "selected_spans_by_policy_kind": sum_by(
            rows, "policy_kind", "selected_span_count"
        ),
        "exact_hits_by_arity": sum_by(rows, "arity", "exact_hit_count"),
        "selected_spans_by_arity": sum_by(rows, "arity", "selected_span_count"),
        "selected_start_mod_block": selected_start_mod_block(rows),
        "conclusion": (
            "Alignment and arity changes produced selected exact spans."
            if rows_with_selected
            else "Alignment and arity changes did not produce selected exact spans."
        ),
    }


def top_rows(rows: list[dict[str, Any]], limit: int = TOP_LIMIT) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
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
        "generated_by": "scripts/generate_alignment_arity_discovery.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "artifact_hashes": artifact_hashes(),
        "manifest_sha256": manifest_hash(),
        "manifest": search_manifest(),
        "corpus_manifest": corpus_manifest(),
        "rows": rows,
        "summary": summarize(rows),
    }


def write_report(payload: dict[str, Any]) -> None:
    ALIGNMENT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary = payload["summary"]
    manifest = payload["manifest"]
    lines = [
        "# Telomere Alignment And Arity Discovery",
        "",
        "Generated by `scripts/generate_alignment_arity_discovery.py`.",
        "This is a pre-sidecar alignment/arity discovery report, not `.tlmr` format support.",
        "",
        f"Rows: `{summary['row_count']}`.",
        f"Corpora: `{summary['corpus_count']}`.",
        f"Supported configs: `{summary['config_count']}`.",
        f"Skipped configs: `{summary['skipped_config_count']}`.",
        f"Skipped row slots: `{summary['skipped_row_count']}`.",
        f"Target spans scanned: `{summary['target_span_count']}`.",
        f"Rows with prefix >=5: `{summary['rows_with_prefix_ge_5']}`.",
        f"Rows with prefix >=6: `{summary['rows_with_prefix_ge_6']}`.",
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
        "## Search Contract",
        "",
        f"- Hasher: `{manifest['hasher']}`.",
        f"- Max seed length: `{manifest['max_seed_len']}`.",
        f"- Block sizes: `{', '.join(str(item) for item in manifest['block_sizes'])}`.",
        f"- Arity range: `{min(manifest['arities'])}..={max(manifest['arities'])}`.",
        "- Target block hashing: `false`.",
        "- Generated seed prefixes are compared directly against raw target bytes.",
        "- Spans longer than the SHA-256 digest are skipped rather than truncated.",
        "",
        "## Control Summary",
        "",
        "| control | rows | p5 rows | exact rows | selected rows | exact hits | selected spans | max prefix |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for control_kind, data in summary["control_kind_summary"].items():
        lines.append(
            "| {control_kind} | {row_count} | {rows_with_prefix_ge_5} | "
            "{rows_with_exact_hits} | {rows_with_selected_spans} | "
            "{total_exact_hits} | {total_selected_spans} | {max_prefix_observed} |".format(
                control_kind=control_kind,
                **data,
            )
        )
    lines.extend(
        [
            "",
            "## Top Rows",
            "",
            "| row | control | block | policy | arity | span | spans | p4 | p5 | p6 | exact | selected | net seed delta |",
            "| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in top_rows(payload["rows"]):
        lines.append(
            "| {name} | {control_kind} | {block_size} | {policy} | {arity} | {span_len} | "
            "{target_span_count} | {prefix_ge_4_count} | {prefix_ge_5_count} | "
            "{prefix_ge_6_count} | {exact_hit_count} | {selected_span_count} | "
            "{net_seed_delta_bytes} |".format(**row)
        )
    lines.extend(
        [
            "",
            "## Skipped Configs",
            "",
            "| config | span | reason |",
            "| --- | ---: | --- |",
        ]
    )
    for config in manifest["skipped_configs"]:
        lines.append(f"| {config['name']} | {config['span_len']} | {config['reason']} |")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- This artifact varies block size, step policy, phase, and arity to test whether the previous null result was an alignment artifact.",
            "- It uses weighted interval selection for profitable exact hits, but no selected record is emitted unless exact regenerated bytes match the raw target span.",
            "- Prefix-only rows remain steering evidence; they are not compression wins without exact generated-byte matches.",
            "- A promotion requires selected spans in at least two ordinary held-out groups or repeatable prefix >=5 movement before sidecar work resumes.",
        ]
    )
    ALIGNMENT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def expected_row_count() -> int:
    configs, _skipped = all_configs()
    return len(corpus_manifest()) * len(configs)


def check_report() -> None:
    if not ALIGNMENT_JSON.exists() or not ALIGNMENT_MD.exists():
        raise SystemExit("generated alignment/arity discovery files are missing")
    payload = load_json(ALIGNMENT_JSON)
    if payload.get("generated_by") != "scripts/generate_alignment_arity_discovery.py":
        raise SystemExit("alignment_arity_discovery.json has wrong generated_by marker")
    if payload.get("artifact_hashes") != artifact_hashes():
        raise SystemExit("alignment/arity discovery artifact hashes are stale")
    if payload.get("manifest_sha256") != manifest_hash():
        raise SystemExit("alignment/arity discovery manifest hash is stale")
    summary = payload.get("summary", {})
    if summary.get("row_count") != expected_row_count():
        raise SystemExit("alignment/arity discovery row count is stale")
    if summary.get("skipped_config_count") != len(all_configs()[1]):
        raise SystemExit("alignment/arity discovery skipped config count is stale")
    if len(payload.get("rows", [])) != summary.get("row_count"):
        raise SystemExit("alignment/arity discovery row payload is incomplete")
    text = ALIGNMENT_MD.read_text(encoding="utf-8")
    for phrase in (
        "Telomere Alignment And Arity Discovery",
        "Target block hashing: `false`",
        "Generated seed prefixes are compared directly against raw target bytes",
        "weighted interval selection",
        "Prefix-only rows remain steering evidence",
    ):
        if phrase not in text:
            raise SystemExit(f"ALIGNMENT_ARITY_DISCOVERY.md missing phrase: {phrase}")


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
