#!/usr/bin/env python3
"""Generate a gated depth-4 shard plan from current depth-3 evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
DEPTH3_FRONTIER_JSON = DOCS / "depth3_frontier_exact_discovery.json"
NEARMISS_JSON = DOCS / "nearmiss_forecast.json"
THEORY_JSON = DOCS / "theory.json"
SHARD_JSON = DOCS / "depth4_shard_plan.json"
SHARD_MD = DOCS / "DEPTH4_SHARD_PLAN.md"

HASHER = "sha256"
TARGET_SEED_LEN = 4
SHARD_PREFIX_BYTES = 1
SHARD_COUNT = 256
PREFIX_LENGTHS = (5, 6, 7, 8)
SPAN_LEN = 8


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def seed_count(max_seed_len: int) -> int:
    return sum(256**length for length in range(1, max_seed_len + 1))


def seed_len_offset(seed_len: int) -> int:
    return sum(256**length for length in range(1, seed_len))


def artifact_hashes() -> dict[str, str]:
    return {
        "depth3_frontier_exact_discovery_sha256": sha256(DEPTH3_FRONTIER_JSON),
        "nearmiss_forecast_sha256": sha256(NEARMISS_JSON),
        "theory_sha256": sha256(THEORY_JSON),
    }


def manifest() -> dict[str, Any]:
    return {
        "hasher": HASHER,
        "target_seed_len": TARGET_SEED_LEN,
        "canonical_seed_order": "1-byte seeds first, then 2-byte, then 3-byte, then 4-byte, each bucket big-endian",
        "shard_prefix_bytes": SHARD_PREFIX_BYTES,
        "shard_count": SHARD_COUNT,
        "shard_rule": "split the 4-byte seed bucket by its first byte",
        "target_block_hashing": False,
        "match_rule": "compare SHA-256(seed) prefixes directly against raw target bytes and regenerate every exact hit",
        "scope": "planning artifact only; no depth-4 seeds are enumerated by this script",
    }


def manifest_hash() -> str:
    payload = json.dumps(manifest(), sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def expected_hits(candidate_spans: int, seed_total: int, prefix_len: int) -> float:
    return candidate_spans * seed_total / float(2 ** (8 * prefix_len))


def poisson_probability_at_least_one(expected: float) -> float:
    return 1.0 - math.exp(-expected)


def build_shards(ms_per_depth3_seed: float) -> list[dict[str, Any]]:
    seeds_per_shard = 256 ** (TARGET_SEED_LEN - SHARD_PREFIX_BYTES)
    base = seed_len_offset(TARGET_SEED_LEN)
    shards = []
    for prefix in range(SHARD_COUNT):
        start_value = prefix * seeds_per_shard
        end_value = (prefix + 1) * seeds_per_shard
        shard_seed_count = end_value - start_value
        shards.append(
            {
                "shard_id": f"seed4-prefix-{prefix:02x}",
                "seed_len": TARGET_SEED_LEN,
                "seed_prefix_hex": f"{prefix:02x}",
                "seed_value_start_inclusive": start_value,
                "seed_value_end_exclusive": end_value,
                "seed_index_start_inclusive": base + start_value,
                "seed_index_end_exclusive": base + end_value,
                "seed_count": shard_seed_count,
                "estimated_ms_from_depth3_frontier_rate": round(
                    shard_seed_count * ms_per_depth3_seed,
                    3,
                ),
            }
        )
    return shards


def build_report() -> dict[str, Any]:
    depth3 = load_json(DEPTH3_FRONTIER_JSON)
    nearmiss = load_json(NEARMISS_JSON)
    theory = load_json(THEORY_JSON)
    depth3_summary = depth3["summary"]
    frontier_spans = int(depth3_summary["target_span_count"])
    depth3_seeds = int(depth3_summary["enumerated_seed_count"])
    depth3_ms = float(depth3_summary["enumeration_ms"])
    ms_per_seed = depth3_ms / depth3_seeds if depth3_seeds else 0.0
    depth4_bucket_seeds = 256**TARGET_SEED_LEN
    depth4_total_seeds = seed_count(TARGET_SEED_LEN)
    incremental_depth4_ms = depth4_bucket_seeds * ms_per_seed
    total_depth4_ms = depth4_total_seeds * ms_per_seed
    prefix_expectations = [
        {
            "prefix_len": prefix_len,
            "expected_hits_frontier_depth4_bucket": expected_hits(
                frontier_spans,
                depth4_bucket_seeds,
                prefix_len,
            ),
            "probability_at_least_one_frontier_depth4_bucket": poisson_probability_at_least_one(
                expected_hits(frontier_spans, depth4_bucket_seeds, prefix_len)
            ),
        }
        for prefix_len in PREFIX_LENGTHS
    ]
    exact_expectation = next(
        item
        for item in prefix_expectations
        if item["prefix_len"] == SPAN_LEN
    )
    promotion_met = (
        depth3_summary["rows_with_depth3_prefix6"] > 0
        or depth3_summary["total_exact_hits"] > 0
        or depth3_summary["total_selected_spans"] > 0
    )
    recommended_status = "ready-to-shard" if promotion_met else "gated"
    conclusion = (
        "Depth-4 shard execution is ready because the depth-3 frontier found prefix>=6, exact hits, or selected spans."
        if promotion_met
        else "Depth-4 shard execution remains gated because the depth-3 frontier found only prefix movement and no exact records."
    )
    shards = build_shards(ms_per_seed)
    return {
        "generated_by": "scripts/generate_depth4_shard_plan.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "artifact_hashes": artifact_hashes(),
        "manifest_sha256": manifest_hash(),
        "manifest": manifest(),
        "source_depth3_summary": {
            "frontier_rows": depth3_summary["frontier_rows"],
            "physical_payload_count": depth3_summary["physical_payload_count"],
            "target_span_count": frontier_spans,
            "enumerated_seed_count": depth3_seeds,
            "enumeration_ms": depth3_ms,
            "rows_with_depth3_prefix5_uplift": depth3_summary[
                "rows_with_depth3_prefix5_uplift"
            ],
            "rows_with_depth3_prefix6": depth3_summary["rows_with_depth3_prefix6"],
            "total_exact_hits": depth3_summary["total_exact_hits"],
            "total_selected_spans": depth3_summary["total_selected_spans"],
        },
        "source_forecast_summary": {
            "best_non_planted_case": nearmiss["summary"]["best_non_planted_case"],
            "best_non_planted_gib_for_one_expected_hit": nearmiss["summary"][
                "best_non_planted_gib_for_one_expected_hit"
            ],
            "theory_conclusion": theory["conclusion"],
        },
        "depth4_estimates": {
            "seed_len_4_bucket_seeds": depth4_bucket_seeds,
            "seed_len_1_through_4_total_seeds": depth4_total_seeds,
            "ms_per_seed_from_depth3_frontier": ms_per_seed,
            "estimated_incremental_depth4_ms": round(incremental_depth4_ms, 3),
            "estimated_incremental_depth4_hours": round(
                incremental_depth4_ms / 1000.0 / 3600.0,
                4,
            ),
            "estimated_total_depth1_to_4_ms": round(total_depth4_ms, 3),
            "estimated_total_depth1_to_4_hours": round(
                total_depth4_ms / 1000.0 / 3600.0,
                4,
            ),
            "frontier_candidate_spans": frontier_spans,
            "prefix_expectations": prefix_expectations,
            "exact8_probability_at_least_one": exact_expectation[
                "probability_at_least_one_frontier_depth4_bucket"
            ],
        },
        "promotion_gate": {
            "recommended_status": recommended_status,
            "promotion_met_by_depth3_frontier": promotion_met,
            "required_before_running_all_shards": [
                "depth3 frontier prefix>=6 movement",
                "or depth3 frontier exact hits",
                "or depth3 frontier selected spans",
                "or a new independent transform/corpus lead with stronger evidence",
            ],
            "stop_rules": [
                "run a small pilot shard first",
                "stop if observed prefix>=6 is below random expectation and exact hits remain zero",
                "stop if memory or runtime exceeds the shard budget by more than 2x",
                "do not interpret prefix-only movement as compression",
            ],
            "conclusion": conclusion,
        },
        "shard_summary": {
            "shard_count": len(shards),
            "seed_count_per_shard": shards[0]["seed_count"] if shards else 0,
            "estimated_ms_per_shard": shards[0][
                "estimated_ms_from_depth3_frontier_rate"
            ]
            if shards
            else 0,
        },
        "shards": shards,
    }


def write_report(payload: dict[str, Any]) -> None:
    SHARD_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    estimates = payload["depth4_estimates"]
    gate = payload["promotion_gate"]
    shard_summary = payload["shard_summary"]
    source = payload["source_depth3_summary"]
    lines = [
        "# Telomere Depth-4 Shard Plan",
        "",
        "Generated by `scripts/generate_depth4_shard_plan.py`.",
        "This is a gated compute plan, not a depth-4 run and not a compression claim.",
        "",
        f"Recommended status: `{gate['recommended_status']}`.",
        f"Depth-3 frontier exact hits: `{source['total_exact_hits']}`.",
        f"Depth-3 frontier selected spans: `{source['total_selected_spans']}`.",
        f"Depth-3 frontier prefix>=6 rows: `{source['rows_with_depth3_prefix6']}`.",
        f"Depth-4 shard count: `{shard_summary['shard_count']}`.",
        f"Seed count per shard: `{shard_summary['seed_count_per_shard']}`.",
        f"Estimated time per shard from depth-3 frontier rate: `{shard_summary['estimated_ms_per_shard']}` ms.",
        f"Estimated full incremental depth-4 time: `{estimates['estimated_incremental_depth4_hours']}` hours.",
        "",
        "## Conclusion",
        "",
        gate["conclusion"],
        "",
        "## Expected Frontier Hits",
        "",
        "| prefix length | expected hits | probability >=1 |",
        "| ---: | ---: | ---: |",
    ]
    for row in estimates["prefix_expectations"]:
        lines.append(
            "| {prefix_len} | {expected:.6g} | {prob:.6g} |".format(
                prefix_len=row["prefix_len"],
                expected=row["expected_hits_frontier_depth4_bucket"],
                prob=row["probability_at_least_one_frontier_depth4_bucket"],
            )
        )
    lines.extend(
        [
            "",
            "## Shard Contract",
            "",
            "- Canonical seed order is preserved: 1-byte, then 2-byte, then 3-byte, then 4-byte seeds, each bucket big-endian.",
            "- The 4-byte bucket is split by the first seed byte into 256 deterministic shards.",
            "- Target block hashing remains `false`; generated SHA-256(seed) prefixes are compared directly against target bytes.",
            "- Every exact hit must be regenerated before it can become a candidate record.",
            "- A pilot shard must run before all-shard execution.",
            "",
            "## First Shards",
            "",
            "| shard | seed index start | seed index end | seed count | estimated ms |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for shard in payload["shards"][:16]:
        lines.append(
            "| {shard_id} | {seed_index_start_inclusive} | {seed_index_end_exclusive} | {seed_count} | {estimated_ms_from_depth3_frontier_rate} |".format(
                **shard
            )
        )
    lines.extend(
        [
            "",
            "## Stop Rules",
            "",
        ]
    )
    lines.extend(f"- {rule}" for rule in gate["stop_rules"])
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Full depth-4 has about 256 times the 4-byte-bucket work of depth 3 for each comparable frontier.",
            "- The current frontier makes prefix>=6 movement plausible, but exact 8-byte hits remain very unlikely under the random-suffix model.",
            "- This artifact exists so depth-4 work is explicit, sharded, resumable, and gated by evidence.",
        ]
    )
    SHARD_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not SHARD_JSON.exists() or not SHARD_MD.exists():
        raise SystemExit("generated depth-4 shard plan files are missing")
    payload = load_json(SHARD_JSON)
    if payload.get("generated_by") != "scripts/generate_depth4_shard_plan.py":
        raise SystemExit("depth4_shard_plan.json has wrong generated_by marker")
    if payload.get("artifact_hashes") != artifact_hashes():
        raise SystemExit("depth4 shard plan artifact hashes are stale")
    if payload.get("manifest_sha256") != manifest_hash():
        raise SystemExit("depth4 shard plan manifest hash is stale")
    if payload.get("shard_summary", {}).get("shard_count") != SHARD_COUNT:
        raise SystemExit("depth4 shard plan shard count is stale")
    if len(payload.get("shards", [])) != SHARD_COUNT:
        raise SystemExit("depth4 shard plan shard payload is incomplete")
    text = SHARD_MD.read_text(encoding="utf-8")
    for phrase in (
        "Telomere Depth-4 Shard Plan",
        "gated compute plan",
        "not a compression claim",
        "Target block hashing remains `false`",
        "A pilot shard must run before all-shard execution",
        "exact 8-byte hits remain very unlikely",
    ):
        if phrase not in text:
            raise SystemExit(f"DEPTH4_SHARD_PLAN.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate generated plan")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.check:
        check_report()
        return
    write_report(build_report())


if __name__ == "__main__":
    main()
