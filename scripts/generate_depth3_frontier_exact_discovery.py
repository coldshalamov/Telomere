#!/usr/bin/env python3
"""Generate bounded depth-3 exact discovery over current frontier rows."""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import math
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import generate_alignment_arity_discovery
import generate_lead_exact_discovery
import generate_manifold_report
import generate_match_discovery
import generate_transformed_match_discovery


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
FRONTIER_JSON = DOCS / "depth3_frontier_exact_discovery.json"
FRONTIER_MD = DOCS / "DEPTH3_FRONTIER_EXACT_DISCOVERY.md"

LEAD_EXACT_JSON = DOCS / "lead_exact_discovery.json"
TRANSFORMED_MATCH_JSON = DOCS / "transformed_match_discovery.json"
MATCH_DISCOVERY_JSON = DOCS / "match_discovery.json"
ALIGNMENT_ARITY_JSON = DOCS / "alignment_arity_discovery.json"

HASHER = "sha256"
BASELINE_MAX_SEED_LEN = 2
SEARCH_MAX_SEED_LEN = 3
PREFIX_LADDER = (3, 4, 5, 6)
SEED_RECORD_OVERHEAD_BYTES = 4
LEAD_ROW_LIMIT = 12
TRANSFORMED_ROW_LIMIT = 6
MATCH_CONTROL_LIMIT = 4
ALIGNMENT_CONTROL_LIMIT = 4
EXACT_RECORD_LIMIT = 16
TOP_LIMIT = 32


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_hashes() -> dict[str, str]:
    return {
        "lead_exact_discovery_sha256": sha256(LEAD_EXACT_JSON),
        "transformed_match_discovery_sha256": sha256(TRANSFORMED_MATCH_JSON),
        "match_discovery_sha256": sha256(MATCH_DISCOVERY_JSON),
        "alignment_arity_discovery_sha256": sha256(ALIGNMENT_ARITY_JSON),
    }


def search_manifest() -> dict[str, Any]:
    return {
        "hasher": HASHER,
        "baseline_max_seed_len": BASELINE_MAX_SEED_LEN,
        "search_max_seed_len": SEARCH_MAX_SEED_LEN,
        "seed_order": "1-byte seeds first, then 2-byte, then 3-byte, each bucket big-endian",
        "prefix_ladder": PREFIX_LADDER,
        "seed_record_overhead_bytes": SEED_RECORD_OVERHEAD_BYTES,
        "target_block_hashing": False,
        "match_rule": "generated SHA-256(seed) prefixes are compared directly against raw target bytes",
        "frontier_limits": {
            "lead_rows": LEAD_ROW_LIMIT,
            "transformed_rows": TRANSFORMED_ROW_LIMIT,
            "match_control_rows": MATCH_CONTROL_LIMIT,
            "alignment_control_rows": ALIGNMENT_CONTROL_LIMIT,
        },
        "selection_rule": "top depth-2 null/frontier rows by prefix>=4, with raw controls restricted to profitable span lengths",
        "scope": "bounded depth-3 exact discovery only; not `.tlmr` format support",
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


def row_priority(row: dict[str, Any]) -> tuple[int, int, int, int, str]:
    return (
        -int(row.get("prefix_ge_6_count", 0)),
        -int(row.get("prefix_ge_5_count", 0)),
        -int(row.get("prefix_ge_4_count", 0)),
        -int(row.get("prefix_ge_3_count", 0)),
        row["name"],
    )


def eligible_frontier_row(row: dict[str, Any]) -> bool:
    return (
        row.get("role") == "held-out"
        and int(row.get("selected_span_count", 0)) == 0
        and int(row.get("prefix_ge_4_count", 0)) > 0
    )


def eligible_control_row(row: dict[str, Any]) -> bool:
    return (
        row.get("role") == "held-out"
        and int(row.get("selected_span_count", 0)) == 0
        and int(row.get("prefix_ge_3_count", 0)) > 0
    )


def profitable_span_len(row: dict[str, Any]) -> bool:
    return int(row.get("span_len", 8)) > SEED_RECORD_OVERHEAD_BYTES + SEARCH_MAX_SEED_LEN


def manifest_row(
    source_artifact: str,
    row: dict[str, Any],
    selection_reason: str,
) -> dict[str, Any]:
    transformed_sha = row.get("transformed_sha256", row.get("input_sha256"))
    span_len = int(row.get("span_len", 8))
    span_step = int(row.get("span_step", 1))
    return {
        "frontier_name": f"{source_artifact}::{row['name']}",
        "source_artifact": source_artifact,
        "source_row_name": row["name"],
        "selection_reason": selection_reason,
        "family": row["family"],
        "corpus": row["corpus"],
        "role": row["role"],
        "control_kind": row["control_kind"],
        "independence_group": row["independence_group"],
        "paired_with": row.get("paired_with"),
        "transform": row.get("transform"),
        "transform_family": row.get("transform_family"),
        "lead_source": row.get("lead_source"),
        "lead_name": row.get("lead_name"),
        "policy": row.get("policy"),
        "policy_kind": row.get("policy_kind"),
        "phase": int(row.get("phase", 0)),
        "arity": row.get("arity"),
        "metadata_bytes": int(row.get("metadata_bytes", 0)),
        "input_bytes": int(row["input_bytes"]),
        "input_sha256": row["input_sha256"],
        "payload_sha256": transformed_sha,
        "transformed_sha256": transformed_sha,
        "span_len": span_len,
        "span_step": span_step,
        "baseline_target_span_count": int(row.get("target_span_count", 0)),
        "baseline_dedup_span_count": int(row.get("dedup_span_count", 0)),
        "baseline_max_prefix_observed": int(row.get("max_prefix_observed", 0)),
        "baseline_prefix_ge_3": int(row.get("prefix_ge_3_count", 0)),
        "baseline_prefix_ge_4": int(row.get("prefix_ge_4_count", 0)),
        "baseline_prefix_ge_5": int(row.get("prefix_ge_5_count", 0)),
        "baseline_prefix_ge_6": int(row.get("prefix_ge_6_count", 0)),
        "baseline_exact_hits": int(row.get("exact_hit_count", 0)),
        "baseline_positive_exact_hits": int(row.get("positive_exact_hit_count", 0)),
        "baseline_selected_span_count": int(row.get("selected_span_count", 0)),
    }


def lead_rows() -> list[dict[str, Any]]:
    payload = load_json(LEAD_EXACT_JSON)
    rows = [row for row in payload["rows"] if eligible_frontier_row(row)]
    rows.sort(key=row_priority)
    return [
        manifest_row("lead_exact_discovery", row, "selected-lead prefix frontier")
        for row in rows[:LEAD_ROW_LIMIT]
    ]


def transformed_rows() -> list[dict[str, Any]]:
    payload = load_json(TRANSFORMED_MATCH_JSON)
    rows = [row for row in payload["rows"] if eligible_frontier_row(row)]
    rows.sort(key=row_priority)
    return [
        manifest_row("transformed_match_discovery", row, "frozen-transform prefix frontier")
        for row in rows[:TRANSFORMED_ROW_LIMIT]
    ]


def match_control_rows() -> list[dict[str, Any]]:
    payload = load_json(MATCH_DISCOVERY_JSON)
    rows = [
        row
        for row in payload["rows"]
        if eligible_control_row(row) and profitable_span_len(row)
    ]
    rows.sort(key=row_priority)
    return [
        manifest_row("match_discovery", row, "raw exact-match null control")
        for row in rows[:MATCH_CONTROL_LIMIT]
    ]


def alignment_control_rows() -> list[dict[str, Any]]:
    payload = load_json(ALIGNMENT_ARITY_JSON)
    rows = [
        row
        for row in payload["rows"]
        if eligible_control_row(row) and profitable_span_len(row)
    ]
    rows.sort(key=row_priority)
    return [
        manifest_row("alignment_arity_discovery", row, "alignment/arity null control")
        for row in rows[:ALIGNMENT_CONTROL_LIMIT]
    ]


def frontier_manifest() -> list[dict[str, Any]]:
    rows = lead_rows() + transformed_rows() + match_control_rows() + alignment_control_rows()
    seen: set[tuple[str, str]] = set()
    output: list[dict[str, Any]] = []
    for row in rows:
        key = (row["source_artifact"], row["source_row_name"])
        if key in seen:
            continue
        seen.add(key)
        output.append(row)
    return output


def frontier_manifest_hash() -> str:
    payload = json.dumps(frontier_manifest(), sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def lead_by_key() -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (lead["lead_source"], lead["display_name"]): lead
        for lead in generate_lead_exact_discovery.lead_manifest()
    }


def transform_by_name() -> dict[str, dict[str, Any]]:
    return {
        transform["name"]: transform
        for transform in generate_transformed_match_discovery.transform_manifest()
    }


def corpus_descriptor(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "family": row["family"],
        "corpus": row["corpus"],
        "role": row["role"],
        "control_kind": row["control_kind"],
        "independence_group": row["independence_group"],
        "paired_with": row.get("paired_with"),
    }


def row_bytes(row: dict[str, Any]) -> bytes:
    source_artifact = row["source_artifact"]
    corpus = corpus_descriptor(row)
    if source_artifact == "lead_exact_discovery":
        source = generate_lead_exact_discovery.corpus_bytes(corpus)
        if hashlib.sha256(source).hexdigest() != row["input_sha256"]:
            raise RuntimeError(f"{row['frontier_name']}: input hash changed")
        lead = lead_by_key()[(row["lead_source"], row["lead_name"])]
        payload = generate_lead_exact_discovery.apply_lead(source, lead)
    elif source_artifact == "transformed_match_discovery":
        source = generate_transformed_match_discovery.corpus_bytes(corpus)
        if hashlib.sha256(source).hexdigest() != row["input_sha256"]:
            raise RuntimeError(f"{row['frontier_name']}: input hash changed")
        payload = generate_transformed_match_discovery.apply_transform(
            source,
            transform_by_name()[row["transform"]],
        )
    elif source_artifact == "match_discovery":
        payload = generate_match_discovery.corpus_bytes(corpus)
    elif source_artifact == "alignment_arity_discovery":
        payload = generate_alignment_arity_discovery.corpus_bytes(corpus)
    else:
        raise ValueError(source_artifact)
    if hashlib.sha256(payload).hexdigest() != row["payload_sha256"]:
        raise RuntimeError(f"{row['frontier_name']}: payload hash changed")
    return payload


def candidate_starts(data_len: int, span_len: int, span_step: int, phase: int) -> range:
    if data_len < span_len or phase > data_len - span_len:
        return range(0)
    return range(phase, data_len - span_len + 1, span_step)


def target_for_row(row: dict[str, Any]) -> dict[str, Any]:
    data = row_bytes(row)
    span_len = int(row["span_len"])
    span_step = int(row["span_step"])
    phase = int(row["phase"])
    starts = list(candidate_starts(len(data), span_len, span_step, phase))
    prefix_lengths = [prefix_len for prefix_len in PREFIX_LADDER if prefix_len <= span_len]
    counters: dict[int, Counter[bytes]] = {
        prefix_len: Counter() for prefix_len in prefix_lengths
    }
    span_occurrences: dict[bytes, list[int]] = {}
    for start in starts:
        span = data[start : start + span_len]
        span_occurrences.setdefault(span, []).append(start)
        for prefix_len in prefix_lengths:
            counters[prefix_len][span[:prefix_len]] += 1
    return {
        "row": row,
        "input_bytes": len(data),
        "payload_sha256": hashlib.sha256(data).hexdigest(),
        "byte_entropy": byte_entropy(data),
        "target_span_count": len(starts),
        "dedup_span_count": len(span_occurrences),
        "prefix_lengths": prefix_lengths,
        "counters": counters,
        "span_occurrences": span_occurrences,
    }


def build_targets(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [target_for_row(row) for row in rows]


def enumerate_depth3(
    targets: list[dict[str, Any]],
) -> tuple[dict[int, set[bytes]], dict[tuple[int, bytes], dict[str, Any]], int, float]:
    target_prefix_sets: dict[int, set[bytes]] = {}
    target_span_sets: dict[int, set[bytes]] = {}
    for target in targets:
        for prefix_len, counter in target["counters"].items():
            target_prefix_sets.setdefault(prefix_len, set()).update(counter.keys())
        span_len = target["row"]["span_len"]
        target_span_sets.setdefault(span_len, set()).update(target["span_occurrences"].keys())

    matched_prefixes: dict[int, set[bytes]] = {
        prefix_len: set() for prefix_len in target_prefix_sets
    }
    exact_seed_by_span: dict[tuple[int, bytes], dict[str, Any]] = {}

    target_prefix_items = tuple(sorted(target_prefix_sets.items()))
    target_span_items = tuple(sorted(target_span_sets.items()))
    started = time.perf_counter()
    seed_total = 0
    for seed_index, seed in enumerate(generate_manifold_report.iter_seed_bytes(SEARCH_MAX_SEED_LEN)):
        seed_total = seed_index + 1
        digest = hashlib.sha256(seed).digest()
        for prefix_len, prefixes in target_prefix_items:
            prefix = digest[:prefix_len]
            if prefix in prefixes:
                matched_prefixes[prefix_len].add(prefix)
        for span_len, spans in target_span_items:
            span = digest[:span_len]
            key = (span_len, span)
            if span in spans and key not in exact_seed_by_span:
                exact_seed_by_span[key] = {
                    "seed_index": seed_index,
                    "seed_len": len(seed),
                    "seed_hex": seed.hex(),
                }
    elapsed_ms = round((time.perf_counter() - started) * 1000.0, 3)
    return matched_prefixes, exact_seed_by_span, seed_total, elapsed_ms


def count_matches(counter: Counter[bytes], matched: set[bytes]) -> int:
    return sum(count for prefix, count in counter.items() if prefix in matched)


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


def exact_hits_for_target(
    target: dict[str, Any],
    exact_seed_by_span: dict[tuple[int, bytes], dict[str, Any]],
) -> list[dict[str, Any]]:
    row = target["row"]
    span_len = int(row["span_len"])
    exact_hits: list[dict[str, Any]] = []
    for span, starts in target["span_occurrences"].items():
        seed = exact_seed_by_span.get((span_len, span))
        if seed is None:
            continue
        regenerated = hashlib.sha256(bytes.fromhex(seed["seed_hex"])).digest()[:span_len]
        if regenerated != span:
            raise RuntimeError("generated depth-3 exact hit failed regeneration")
        encoded_len = SEED_RECORD_OVERHEAD_BYTES + int(seed["seed_len"])
        for start in starts:
            exact_hits.append(
                {
                    "start_offset": start,
                    "end_offset": start + span_len,
                    "span_len": span_len,
                    "seed_index": seed["seed_index"],
                    "seed_len": seed["seed_len"],
                    "seed_hex": seed["seed_hex"],
                    "encoded_len": encoded_len,
                    "savings_bytes": span_len - encoded_len,
                    "regeneration_verified": True,
                }
            )
    exact_hits.sort(key=lambda hit: (hit["start_offset"], hit["seed_index"]))
    return exact_hits


def analyze_targets(
    targets: list[dict[str, Any]],
    matched_prefixes: dict[int, set[bytes]],
    exact_seed_by_span: dict[tuple[int, bytes], dict[str, Any]],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for target in targets:
        row = target["row"]
        exact_hits = exact_hits_for_target(target, exact_seed_by_span)
        selected = weighted_interval_selection(exact_hits)
        literal_bytes_replaced = sum(hit["span_len"] for hit in selected)
        encoded_seed_bytes = sum(hit["encoded_len"] for hit in selected)
        net_seed_delta = encoded_seed_bytes - literal_bytes_replaced
        net_with_metadata = net_seed_delta + int(row["metadata_bytes"])

        result = {
            **{
                key: row[key]
                for key in (
                    "frontier_name",
                    "source_artifact",
                    "source_row_name",
                    "selection_reason",
                    "family",
                    "corpus",
                    "role",
                    "control_kind",
                    "independence_group",
                    "transform",
                    "lead_source",
                    "lead_name",
                    "policy",
                    "arity",
                    "metadata_bytes",
                    "input_sha256",
                    "payload_sha256",
                    "span_len",
                    "span_step",
                    "phase",
                    "baseline_max_prefix_observed",
                    "baseline_prefix_ge_3",
                    "baseline_prefix_ge_4",
                    "baseline_prefix_ge_5",
                    "baseline_prefix_ge_6",
                    "baseline_exact_hits",
                    "baseline_positive_exact_hits",
                    "baseline_selected_span_count",
                )
            },
            "input_bytes": target["input_bytes"],
            "byte_entropy": target["byte_entropy"],
            "target_span_count": target["target_span_count"],
            "dedup_span_count": target["dedup_span_count"],
            "depth3_prefix_ge_3": 0,
            "depth3_prefix_ge_4": 0,
            "depth3_prefix_ge_5": 0,
            "depth3_prefix_ge_6": 0,
            "depth3_exact_hits": len(exact_hits),
            "depth3_positive_exact_hits": sum(
                1 for hit in exact_hits if hit["savings_bytes"] > 0
            ),
            "depth3_selected_span_count": len(selected),
            "literal_bytes_replaced": literal_bytes_replaced,
            "encoded_seed_bytes": encoded_seed_bytes,
            "net_seed_delta_bytes": net_seed_delta,
            "net_with_metadata_bytes": net_with_metadata,
            "metadata_profitable": bool(selected) and net_with_metadata < 0,
            "exact_hit_records": exact_hits[:EXACT_RECORD_LIMIT],
            "selected_records": selected[:EXACT_RECORD_LIMIT],
        }
        for prefix_len in (3, 4, 5, 6):
            if prefix_len in target["counters"]:
                result[f"depth3_prefix_ge_{prefix_len}"] = count_matches(
                    target["counters"][prefix_len],
                    matched_prefixes.get(prefix_len, set()),
                )
            result[f"prefix_ge_{prefix_len}_delta_vs_depth2"] = (
                result[f"depth3_prefix_ge_{prefix_len}"]
                - result[f"baseline_prefix_ge_{prefix_len}"]
            )
        result["exact_hit_delta_vs_depth2"] = (
            result["depth3_exact_hits"] - result["baseline_exact_hits"]
        )
        result["selected_span_delta_vs_depth2"] = (
            result["depth3_selected_span_count"] - result["baseline_selected_span_count"]
        )
        result["promotion_flags"] = {
            "exact_hit": result["depth3_exact_hits"] > 0,
            "positive_exact_hit": result["depth3_positive_exact_hits"] > 0,
            "selected_span": result["depth3_selected_span_count"] > 0,
            "metadata_profitable": result["metadata_profitable"],
            "prefix_ge_5_uplift": result["prefix_ge_5_delta_vs_depth2"] > 0,
            "prefix_ge_6_uplift": result["prefix_ge_6_delta_vs_depth2"] > 0,
        }
        results.append(result)
    return sorted(results, key=result_sort_key, reverse=True)


def result_sort_key(row: dict[str, Any]) -> tuple[int, int, int, int, int, int, str]:
    return (
        int(row["metadata_profitable"]),
        row["depth3_selected_span_count"],
        row["depth3_positive_exact_hits"],
        row["depth3_exact_hits"],
        row["depth3_prefix_ge_6"],
        row["depth3_prefix_ge_5"],
        row["frontier_name"],
    )


def count_by(rows: list[dict[str, Any]], field: str) -> dict[str, int]:
    return {str(key): value for key, value in sorted(Counter(row[field] for row in rows).items())}


def summarize(
    rows: list[dict[str, Any]],
    seed_total: int,
    elapsed_ms: float,
) -> dict[str, Any]:
    prefix5_rows = [row for row in rows if row["depth3_prefix_ge_5"] > 0]
    prefix5_uplift_rows = [row for row in rows if row["prefix_ge_5_delta_vs_depth2"] > 0]
    prefix6_rows = [row for row in rows if row["depth3_prefix_ge_6"] > 0]
    exact_rows = [row for row in rows if row["depth3_exact_hits"] > 0]
    positive_exact_rows = [row for row in rows if row["depth3_positive_exact_hits"] > 0]
    selected_rows = [row for row in rows if row["depth3_selected_span_count"] > 0]
    metadata_rows = [row for row in rows if row["metadata_profitable"]]
    best = max(rows, key=result_sort_key, default=None)
    if metadata_rows:
        conclusion = "Depth-3 frontier exact discovery produced metadata-profitable selected seed-span rows."
    elif selected_rows:
        conclusion = "Depth-3 frontier exact discovery produced selected seed-span rows, but not after metadata."
    elif exact_rows:
        conclusion = "Depth-3 frontier exact discovery found exact generated spans, but none selected under current economics."
    elif prefix5_uplift_rows:
        conclusion = "Depth-3 frontier exact discovery found prefix movement only; exact seed-span records remain absent."
    else:
        conclusion = "Depth-3 frontier exact discovery stayed null on this frozen frontier manifest."
    return {
        "frontier_rows": len(rows),
        "physical_payload_count": len({row["payload_sha256"] for row in rows}),
        "source_artifact_counts": count_by(rows, "source_artifact"),
        "target_span_count": sum(row["target_span_count"] for row in rows),
        "dedup_span_count": sum(row["dedup_span_count"] for row in rows),
        "enumerated_seed_count": seed_total,
        "enumeration_ms": elapsed_ms,
        "rows_with_depth3_prefix5": len(prefix5_rows),
        "rows_with_depth3_prefix5_uplift": len(prefix5_uplift_rows),
        "rows_with_depth3_prefix6": len(prefix6_rows),
        "rows_with_exact_hits": len(exact_rows),
        "rows_with_positive_exact_hits": len(positive_exact_rows),
        "rows_with_selected_spans": len(selected_rows),
        "metadata_profitable_rows": len(metadata_rows),
        "total_exact_hits": sum(row["depth3_exact_hits"] for row in rows),
        "total_positive_exact_hits": sum(row["depth3_positive_exact_hits"] for row in rows),
        "total_selected_spans": sum(row["depth3_selected_span_count"] for row in rows),
        "best_case": best["frontier_name"] if best else None,
        "best_case_depth3_prefix_ge_5": best["depth3_prefix_ge_5"] if best else 0,
        "best_case_exact_hits": best["depth3_exact_hits"] if best else 0,
        "best_case_selected_spans": best["depth3_selected_span_count"] if best else 0,
        "best_case_net_with_metadata_bytes": best["net_with_metadata_bytes"] if best else None,
        "conclusion": conclusion,
    }


def build_report() -> dict[str, Any]:
    rows = frontier_manifest()
    targets = build_targets(rows)
    matched, exact_by_span, seed_total, elapsed_ms = enumerate_depth3(targets)
    results = analyze_targets(targets, matched, exact_by_span)
    return {
        "generated_by": "scripts/generate_depth3_frontier_exact_discovery.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "artifact_hashes": artifact_hashes(),
        "manifest_sha256": manifest_hash(),
        "frontier_manifest_sha256": frontier_manifest_hash(),
        "manifest": search_manifest(),
        "frontier_manifest": rows,
        "matched_unique_prefix_counts": {
            str(prefix_len): len(values) for prefix_len, values in matched.items()
        },
        "hasher": HASHER,
        "baseline_max_seed_len": BASELINE_MAX_SEED_LEN,
        "search_max_seed_len": SEARCH_MAX_SEED_LEN,
        "results": results,
        "summary": summarize(results, seed_total, elapsed_ms),
    }


def top_rows(rows: list[dict[str, Any]], limit: int = TOP_LIMIT) -> list[dict[str, Any]]:
    return sorted(rows, key=result_sort_key, reverse=True)[:limit]


def write_report(payload: dict[str, Any]) -> None:
    FRONTIER_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary = payload["summary"]
    manifest = payload["manifest"]
    lines = [
        "# Telomere Depth-3 Frontier Exact Discovery",
        "",
        "Generated by `scripts/generate_depth3_frontier_exact_discovery.py`.",
        "This artifact is a bounded depth-3 frontier exact discovery gate, not `.tlmr` format support and not a compression claim.",
        "",
        f"Frontier rows: `{summary['frontier_rows']}`.",
        f"Physical payloads: `{summary['physical_payload_count']}`.",
        f"Target spans scanned: `{summary['target_span_count']}`.",
        f"Deduplicated spans scanned: `{summary['dedup_span_count']}`.",
        f"Enumerated seeds: `{summary['enumerated_seed_count']}`.",
        f"Enumeration time: `{summary['enumeration_ms']}` ms.",
        f"Rows with depth-3 prefix >=5: `{summary['rows_with_depth3_prefix5']}`.",
        f"Rows with prefix >=5 uplift: `{summary['rows_with_depth3_prefix5_uplift']}`.",
        f"Rows with exact hits: `{summary['rows_with_exact_hits']}`.",
        f"Rows with selected spans: `{summary['rows_with_selected_spans']}`.",
        f"Metadata-profitable rows: `{summary['metadata_profitable_rows']}`.",
        "",
        "## Summary",
        "",
        summary["conclusion"],
        f"Best case: `{summary['best_case']}` with `{summary['best_case_exact_hits']}` exact hits, `{summary['best_case_selected_spans']}` selected spans, and net-with-metadata `{summary['best_case_net_with_metadata_bytes']}` bytes.",
        "",
        "## Search Contract",
        "",
        f"- Hasher: `{manifest['hasher']}`.",
        f"- Baseline max seed length: `{manifest['baseline_max_seed_len']}`.",
        f"- Search max seed length: `{manifest['search_max_seed_len']}`.",
        f"- Canonical seed order: `{manifest['seed_order']}`.",
        "- Target block hashing: `false`.",
        "- Generated SHA-256(seed) prefixes are compared directly against raw target bytes.",
        "- Promotion requires exact regenerated seed-span records; prefix movement alone only opens a follow-up gate.",
        "- Depth 4 remains gated unless this artifact finds prefix>=6 movement, exact hits, or selected spans.",
        "",
        "## Source Mix",
        "",
        "| source artifact | rows |",
        "| --- | ---: |",
    ]
    for source, count in summary["source_artifact_counts"].items():
        lines.append(f"| {source} | {count} |")
    lines.extend(
        [
            "",
            "## Top Frontier Rows",
            "",
            "| row | source | span | spans | p4 d2 | p4 d3 | p5 d2 | p5 d3 | p6 d3 | exact d3 | selected d3 | net metadata |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in top_rows(payload["results"]):
        lines.append(
            "| {frontier_name} | {source_artifact} | {span_len} | {target_span_count} | "
            "{baseline_prefix_ge_4} | {depth3_prefix_ge_4} | {baseline_prefix_ge_5} | "
            "{depth3_prefix_ge_5} | {depth3_prefix_ge_6} | {depth3_exact_hits} | "
            "{depth3_selected_span_count} | {net_with_metadata_bytes} |".format(**row)
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- This consumes lower-level null/frontier ledgers and must not consume the scorecard or experiment queue that summarize it.",
            "- Physical byte streams are deduplicated in the summary by payload SHA-256, but row-level metadata economics remain separate.",
            "- Every exact hit record stores a seed index, seed bytes, encoded length, savings, and regeneration verification.",
            "- If selected spans or negative net-with-metadata appear, only those rows should enter compression follow-up.",
            "- If the result is null, broad depth-3 and depth-4 work should stay behind explicit promotion gates.",
        ]
    )
    FRONTIER_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not FRONTIER_JSON.exists() or not FRONTIER_MD.exists():
        raise SystemExit("generated depth-3 frontier exact discovery files are missing")
    payload = load_json(FRONTIER_JSON)
    if payload.get("generated_by") != "scripts/generate_depth3_frontier_exact_discovery.py":
        raise SystemExit("depth3_frontier_exact_discovery.json has wrong generated_by marker")
    if payload.get("artifact_hashes") != artifact_hashes():
        raise SystemExit("depth3 frontier exact discovery artifact hashes are stale")
    if payload.get("manifest_sha256") != manifest_hash():
        raise SystemExit("depth3 frontier exact discovery manifest hash is stale")
    if payload.get("frontier_manifest_sha256") != frontier_manifest_hash():
        raise SystemExit("depth3 frontier exact discovery frontier manifest hash is stale")
    if len(payload.get("frontier_manifest", [])) != len(frontier_manifest()):
        raise SystemExit("depth3 frontier exact discovery manifest count is stale")
    if len(payload.get("results", [])) != payload.get("summary", {}).get("frontier_rows"):
        raise SystemExit("depth3 frontier exact discovery result count is stale")
    text = FRONTIER_MD.read_text(encoding="utf-8")
    for phrase in (
        "Telomere Depth-3 Frontier Exact Discovery",
        "bounded depth-3 frontier exact discovery gate",
        "Target block hashing: `false`",
        "Canonical seed order",
        "Promotion requires exact regenerated seed-span records",
        "Depth 4 remains gated",
    ):
        if phrase not in text:
            raise SystemExit(f"DEPTH3_FRONTIER_EXACT_DISCOVERY.md missing phrase: {phrase}")


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
