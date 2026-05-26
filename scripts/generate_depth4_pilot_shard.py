#!/usr/bin/env python3
"""Run one deterministic depth-4 pilot shard over the frozen depth-3 frontier."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import generate_depth3_frontier_exact_discovery
import generate_depth4_shard_plan


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
DEPTH3_FRONTIER_JSON = DOCS / "depth3_frontier_exact_discovery.json"
DEPTH4_SHARD_PLAN_JSON = DOCS / "depth4_shard_plan.json"
PILOT_JSON = DOCS / "depth4_pilot_shard.json"
PILOT_MD = DOCS / "DEPTH4_PILOT_SHARD.md"

HASHER = "sha256"
TARGET_SEED_LEN = 4
PILOT_SHARD_PREFIXES = (0x00,)
PREFIX_LADDER = (5, 6, 7, 8)
SEED_RECORD_OVERHEAD_BYTES = 4
EXACT_RECORD_LIMIT = 16


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_hashes() -> dict[str, str]:
    return {
        "depth3_frontier_exact_discovery_sha256": sha256(DEPTH3_FRONTIER_JSON),
        "depth4_shard_plan_sha256": sha256(DEPTH4_SHARD_PLAN_JSON),
    }


def seed_len_offset(seed_len: int) -> int:
    return sum(256**length for length in range(1, seed_len))


def manifest() -> dict[str, Any]:
    return {
        "hasher": HASHER,
        "target_seed_len": TARGET_SEED_LEN,
        "pilot_shard_prefixes_hex": [f"{prefix:02x}" for prefix in PILOT_SHARD_PREFIXES],
        "seed_order": "4-byte seed bucket in big-endian order within each first-byte shard",
        "prefix_ladder": PREFIX_LADDER,
        "seed_record_overhead_bytes": SEED_RECORD_OVERHEAD_BYTES,
        "target_block_hashing": False,
        "match_rule": "compare SHA-256(seed) prefixes directly against raw frontier target bytes",
        "scope": "bounded pilot shard only; not full depth-4 execution and not a compression claim",
    }


def manifest_hash() -> str:
    payload = json.dumps(manifest(), sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def depth3_result_by_name(depth3: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["frontier_name"]: row for row in depth3["results"]}


def depth4_target(target: dict[str, Any]) -> dict[str, Any]:
    counters: dict[int, Counter[bytes]] = {prefix_len: Counter() for prefix_len in PREFIX_LADDER}
    for span, starts in target["span_occurrences"].items():
        for prefix_len in PREFIX_LADDER:
            if prefix_len <= len(span):
                counters[prefix_len][span[:prefix_len]] += len(starts)
    return {
        **target,
        "depth4_counters": counters,
    }


def build_targets(depth3: dict[str, Any]) -> list[dict[str, Any]]:
    targets = generate_depth3_frontier_exact_discovery.build_targets(
        depth3["frontier_manifest"]
    )
    return [depth4_target(target) for target in targets]


def iter_seed4_shard(prefix: int):
    base = bytes([prefix])
    for suffix in range(256**3):
        yield base + suffix.to_bytes(3, "big")


def enumerate_depth4_shards(
    targets: list[dict[str, Any]],
) -> tuple[
    dict[int, set[bytes]],
    dict[tuple[int, bytes], dict[str, Any]],
    list[dict[str, Any]],
    int,
    float,
]:
    target_prefix_sets: dict[int, set[bytes]] = {}
    target_span_sets: dict[int, set[bytes]] = {}
    for target in targets:
        for prefix_len, counter in target["depth4_counters"].items():
            target_prefix_sets.setdefault(prefix_len, set()).update(counter.keys())
        span_len = int(target["row"]["span_len"])
        target_span_sets.setdefault(span_len, set()).update(target["span_occurrences"].keys())

    matched_prefixes: dict[int, set[bytes]] = {
        prefix_len: set() for prefix_len in target_prefix_sets
    }
    exact_seed_by_span: dict[tuple[int, bytes], dict[str, Any]] = {}
    target_prefix_items = tuple(sorted(target_prefix_sets.items()))
    target_span_items = tuple(sorted(target_span_sets.items()))
    base_index = seed_len_offset(TARGET_SEED_LEN)
    seed_total = 0
    shard_summaries: list[dict[str, Any]] = []
    started = time.perf_counter()

    for prefix in PILOT_SHARD_PREFIXES:
        shard_started = time.perf_counter()
        shard_matched = {prefix_len: set() for prefix_len in target_prefix_sets}
        shard_exact_before = len(exact_seed_by_span)
        for suffix, seed in enumerate(iter_seed4_shard(prefix)):
            seed_index = base_index + prefix * (256**3) + suffix
            seed_total += 1
            digest = hashlib.sha256(seed).digest()
            for prefix_len, prefixes in target_prefix_items:
                candidate = digest[:prefix_len]
                if candidate in prefixes:
                    matched_prefixes[prefix_len].add(candidate)
                    shard_matched[prefix_len].add(candidate)
            for span_len, spans in target_span_items:
                span = digest[:span_len]
                key = (span_len, span)
                if span in spans and key not in exact_seed_by_span:
                    exact_seed_by_span[key] = {
                        "seed_index": seed_index,
                        "seed_len": TARGET_SEED_LEN,
                        "seed_hex": seed.hex(),
                    }
        shard_elapsed_ms = round((time.perf_counter() - shard_started) * 1000.0, 3)
        shard_summaries.append(
            {
                "shard_id": f"seed4-prefix-{prefix:02x}",
                "seed_prefix_hex": f"{prefix:02x}",
                "seed_count": 256**3,
                "enumeration_ms": shard_elapsed_ms,
                "matched_unique_prefix_counts": {
                    str(prefix_len): len(values)
                    for prefix_len, values in sorted(shard_matched.items())
                },
                "new_exact_span_keys": len(exact_seed_by_span) - shard_exact_before,
            }
        )

    elapsed_ms = round((time.perf_counter() - started) * 1000.0, 3)
    return matched_prefixes, exact_seed_by_span, shard_summaries, seed_total, elapsed_ms


def count_matches(counter: Counter[bytes], matched: set[bytes]) -> int:
    return sum(count for prefix, count in counter.items() if prefix in matched)


def analyze_targets(
    targets: list[dict[str, Any]],
    depth3_results: dict[str, dict[str, Any]],
    matched_prefixes: dict[int, set[bytes]],
    exact_seed_by_span: dict[tuple[int, bytes], dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for target in targets:
        row = target["row"]
        depth3 = depth3_results[row["frontier_name"]]
        exact_hits = generate_depth3_frontier_exact_discovery.exact_hits_for_target(
            target, exact_seed_by_span
        )
        selected = generate_depth3_frontier_exact_discovery.weighted_interval_selection(
            exact_hits
        )
        literal_bytes_replaced = sum(hit["span_len"] for hit in selected)
        encoded_seed_bytes = sum(hit["encoded_len"] for hit in selected)
        net_seed_delta = encoded_seed_bytes - literal_bytes_replaced
        net_with_metadata = net_seed_delta + int(row["metadata_bytes"])
        result = {
            **{
                key: depth3.get(key, row.get(key))
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
                    "input_bytes",
                    "target_span_count",
                    "dedup_span_count",
                    "depth3_prefix_ge_5",
                    "depth3_prefix_ge_6",
                    "depth3_exact_hits",
                    "depth3_selected_span_count",
                )
            },
            "depth4_prefix_ge_5": 0,
            "depth4_prefix_ge_6": 0,
            "depth4_prefix_ge_7": 0,
            "depth4_prefix_ge_8": 0,
            "depth4_exact_hits": len(exact_hits),
            "depth4_positive_exact_hits": sum(
                1 for hit in exact_hits if hit["savings_bytes"] > 0
            ),
            "depth4_selected_span_count": len(selected),
            "literal_bytes_replaced": literal_bytes_replaced,
            "encoded_seed_bytes": encoded_seed_bytes,
            "net_seed_delta_bytes": net_seed_delta,
            "net_with_metadata_bytes": net_with_metadata,
            "metadata_profitable": bool(selected) and net_with_metadata < 0,
            "exact_hit_records": exact_hits[:EXACT_RECORD_LIMIT],
            "selected_records": selected[:EXACT_RECORD_LIMIT],
        }
        for prefix_len in PREFIX_LADDER:
            result[f"depth4_prefix_ge_{prefix_len}"] = count_matches(
                target["depth4_counters"][prefix_len],
                matched_prefixes.get(prefix_len, set()),
            )
        result["prefix_ge_6_delta_vs_depth3"] = (
            result["depth4_prefix_ge_6"] - int(depth3.get("depth3_prefix_ge_6", 0))
        )
        result["exact_hit_delta_vs_depth3"] = (
            result["depth4_exact_hits"] - int(depth3.get("depth3_exact_hits", 0))
        )
        rows.append(result)
    rows.sort(
        key=lambda item: (
            item["metadata_profitable"],
            item["depth4_selected_span_count"],
            item["depth4_positive_exact_hits"],
            item["depth4_exact_hits"],
            item["depth4_prefix_ge_8"],
            item["depth4_prefix_ge_7"],
            item["depth4_prefix_ge_6"],
            item["depth4_prefix_ge_5"],
            -item["net_with_metadata_bytes"],
        ),
        reverse=True,
    )
    return rows


def summarize(rows: list[dict[str, Any]], seed_total: int, elapsed_ms: float) -> dict[str, Any]:
    prefix5 = [row for row in rows if row["depth4_prefix_ge_5"] > 0]
    prefix6 = [row for row in rows if row["depth4_prefix_ge_6"] > 0]
    prefix7 = [row for row in rows if row["depth4_prefix_ge_7"] > 0]
    exact = [row for row in rows if row["depth4_exact_hits"] > 0]
    selected = [row for row in rows if row["depth4_selected_span_count"] > 0]
    profitable = [row for row in rows if row["metadata_profitable"]]
    best = rows[0] if rows else None
    return {
        "frontier_rows": len(rows),
        "pilot_shard_count": len(PILOT_SHARD_PREFIXES),
        "enumerated_seed_count": seed_total,
        "enumeration_ms": elapsed_ms,
        "target_span_count": sum(int(row["target_span_count"]) for row in rows),
        "rows_with_depth4_prefix5": len(prefix5),
        "rows_with_depth4_prefix6": len(prefix6),
        "rows_with_depth4_prefix7": len(prefix7),
        "rows_with_exact_hits": len(exact),
        "rows_with_selected_spans": len(selected),
        "metadata_profitable_rows": len(profitable),
        "total_exact_hits": sum(row["depth4_exact_hits"] for row in rows),
        "total_positive_exact_hits": sum(row["depth4_positive_exact_hits"] for row in rows),
        "total_selected_spans": sum(row["depth4_selected_span_count"] for row in rows),
        "best_case": best["frontier_name"] if best else None,
        "best_case_depth4_prefix_ge_6": best["depth4_prefix_ge_6"] if best else 0,
        "best_case_exact_hits": best["depth4_exact_hits"] if best else 0,
        "best_case_selected_spans": best["depth4_selected_span_count"] if best else 0,
        "best_case_net_with_metadata_bytes": best["net_with_metadata_bytes"] if best else 0,
        "conclusion": (
            "Depth-4 pilot shard produced metadata-profitable selected seed-span rows."
            if profitable
            else (
                "Depth-4 pilot shard produced exact hits, but none selected under current economics."
                if exact
                else (
                    "Depth-4 pilot shard produced prefix movement only; exact seed-span records remain absent."
                    if prefix6
                    else "Depth-4 pilot shard stayed null at prefix>=6 and exact levels."
                )
            )
        ),
    }


def build_report() -> dict[str, Any]:
    depth3 = load_json(DEPTH3_FRONTIER_JSON)
    depth4_plan = load_json(DEPTH4_SHARD_PLAN_JSON)
    targets = build_targets(depth3)
    matched, exact_by_span, shard_summaries, seed_total, elapsed_ms = enumerate_depth4_shards(
        targets
    )
    rows = analyze_targets(targets, depth3_result_by_name(depth3), matched, exact_by_span)
    return {
        "generated_by": "scripts/generate_depth4_pilot_shard.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "artifact_hashes": artifact_hashes(),
        "manifest_sha256": manifest_hash(),
        "manifest": manifest(),
        "source_depth4_gate": depth4_plan["promotion_gate"],
        "matched_unique_prefix_counts": {
            str(prefix_len): len(values) for prefix_len, values in sorted(matched.items())
        },
        "shards": shard_summaries,
        "frontier_manifest": depth3["frontier_manifest"],
        "results": rows,
        "summary": summarize(rows, seed_total, elapsed_ms),
    }


def write_report(payload: dict[str, Any]) -> None:
    PILOT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary = payload["summary"]
    lines = [
        "# Telomere Depth-4 Pilot Shard",
        "",
        "Generated by `scripts/generate_depth4_pilot_shard.py`.",
        "This is one deterministic depth-4 pilot shard, not full depth-4 execution and not a compression claim.",
        "",
        f"Pilot shards: `{summary['pilot_shard_count']}`.",
        f"Enumerated seeds: `{summary['enumerated_seed_count']}`.",
        f"Enumeration time: `{summary['enumeration_ms']}` ms.",
        f"Frontier rows: `{summary['frontier_rows']}`.",
        f"Target spans: `{summary['target_span_count']}`.",
        f"Rows with depth-4 prefix >=5: `{summary['rows_with_depth4_prefix5']}`.",
        f"Rows with depth-4 prefix >=6: `{summary['rows_with_depth4_prefix6']}`.",
        f"Rows with depth-4 prefix >=7: `{summary['rows_with_depth4_prefix7']}`.",
        f"Rows with exact hits: `{summary['rows_with_exact_hits']}`.",
        f"Rows with selected spans: `{summary['rows_with_selected_spans']}`.",
        f"Metadata-profitable rows: `{summary['metadata_profitable_rows']}`.",
        f"Total exact hits: `{summary['total_exact_hits']}`.",
        f"Total selected spans: `{summary['total_selected_spans']}`.",
        "",
        "## Conclusion",
        "",
        summary["conclusion"],
        "",
        "## Search Contract",
        "",
        "- Target block hashing: `false`.",
        "- Generated SHA-256(seed) prefixes are compared directly against raw frontier target bytes.",
        "- Every exact hit is regenerated from the seed before it is counted.",
        "- The full depth-4 bucket remains gated unless pilot evidence crosses the promotion gate.",
        "",
        "## Top Rows",
        "",
        "| row | shard p6 | shard p7 | exact | selected | net metadata |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in payload["results"][:16]:
        lines.append(
            "| {frontier_name} | {depth4_prefix_ge_6} | {depth4_prefix_ge_7} | "
            "{depth4_exact_hits} | {depth4_selected_span_count} | "
            "{net_with_metadata_bytes} |".format(**row)
        )
    lines.extend(
        [
            "",
            "## Shards",
            "",
            "| shard | seeds | ms | p5 | p6 | p7 | p8 | exact span keys |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for shard in payload["shards"]:
        counts = shard["matched_unique_prefix_counts"]
        lines.append(
            "| {shard_id} | {seed_count} | {enumeration_ms} | {p5} | {p6} | {p7} | {p8} | {exact} |".format(
                shard_id=shard["shard_id"],
                seed_count=shard["seed_count"],
                enumeration_ms=shard["enumeration_ms"],
                p5=counts.get("5", 0),
                p6=counts.get("6", 0),
                p7=counts.get("7", 0),
                p8=counts.get("8", 0),
                exact=shard["new_exact_span_keys"],
            )
        )
    PILOT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not PILOT_JSON.exists() or not PILOT_MD.exists():
        raise SystemExit("generated depth4 pilot shard files are missing")
    payload = load_json(PILOT_JSON)
    if payload.get("generated_by") != "scripts/generate_depth4_pilot_shard.py":
        raise SystemExit("depth4_pilot_shard.json has wrong generated_by marker")
    if payload.get("artifact_hashes") != artifact_hashes():
        raise SystemExit("depth4 pilot shard artifact hashes are stale")
    if payload.get("manifest_sha256") != manifest_hash():
        raise SystemExit("depth4 pilot shard manifest hash is stale")
    if len(payload.get("shards", [])) != len(PILOT_SHARD_PREFIXES):
        raise SystemExit("depth4 pilot shard count is stale")
    text = PILOT_MD.read_text(encoding="utf-8")
    for phrase in (
        "Telomere Depth-4 Pilot Shard",
        "one deterministic depth-4 pilot shard",
        "Target block hashing: `false`",
        "Every exact hit is regenerated",
        "full depth-4 bucket remains gated",
    ):
        if phrase not in text:
            raise SystemExit(f"DEPTH4_PILOT_SHARD.md missing phrase: {phrase}")


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
