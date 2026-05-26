#!/usr/bin/env python3
"""Probe the depth-3 generated-prefix frontier on current held-out near misses."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import generate_fifth_byte_residual
import generate_manifold_report


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
PREFIX_LADDER_JSON = DOCS / "prefix_ladder.json"
PROBE_JSON = DOCS / "depth3_prefix_probe.json"
PROBE_MD = DOCS / "DEPTH3_PREFIX_PROBE.md"

HASHER = "sha256"
BASELINE_MAX_SEED_LEN = 2
SEARCH_MAX_SEED_LEN = 3
SPAN_LEN = 8
SPAN_STEP = 1
SELECTED_ROW_LIMIT = 24
PREFIX_LENGTHS = (3, 4, 5, 6, 8)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def selected_rows(prefix_ladder: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        row
        for row in prefix_ladder["best_rows"]
        if row["role"] != "discovery" and row["prefix_ge_4_count"] > 0
    ][:SELECTED_ROW_LIMIT]


def selected_manifest() -> list[dict[str, Any]]:
    prefix_ladder = load_json(PREFIX_LADDER_JSON)
    fields = (
        "name",
        "family",
        "corpus",
        "role",
        "transform",
        "input_bytes",
        "prefix_ge_3_count",
        "prefix_ge_4_count",
        "prefix_ge_5_count",
        "prefix_ge_6_count",
        "exact_span_hits",
    )
    return [{field: row[field] for field in fields} for row in selected_rows(prefix_ladder)]


def selected_manifest_hash() -> str:
    payload = json.dumps(selected_manifest(), sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def target_counters(data: bytes) -> dict[int, Counter[bytes]]:
    counters: dict[int, Counter[bytes]] = {prefix_len: Counter() for prefix_len in PREFIX_LENGTHS}
    for start in range(0, max(0, len(data) - SPAN_LEN + 1), SPAN_STEP):
        span = data[start : start + SPAN_LEN]
        for prefix_len in PREFIX_LENGTHS:
            counters[prefix_len][span[:prefix_len]] += 1
    return counters


def build_targets(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    targets = []
    for row in rows:
        data = generate_fifth_byte_residual.transformed_bytes_for_row(row)
        if len(data) != row["input_bytes"]:
            raise RuntimeError(f"{row['name']}: reconstructed row length changed")
        targets.append(
            {
                "row": row,
                "input_sha256": hashlib.sha256(data).hexdigest(),
                "candidate_spans": generate_manifold_report.candidate_span_count(
                    len(data),
                    SPAN_LEN,
                    SPAN_STEP,
                ),
                "counters": target_counters(data),
            }
        )
    return targets


def enumerate_matching_prefixes(targets: list[dict[str, Any]]) -> tuple[dict[int, set[bytes]], int, float]:
    target_sets: dict[int, set[bytes]] = {
        prefix_len: set().union(
            *(set(target["counters"][prefix_len].keys()) for target in targets)
        )
        for prefix_len in PREFIX_LENGTHS
    }
    matched: dict[int, set[bytes]] = {prefix_len: set() for prefix_len in PREFIX_LENGTHS}
    started = time.perf_counter()
    seed_total = 0
    for seed in generate_manifold_report.iter_seed_bytes(SEARCH_MAX_SEED_LEN):
        seed_total += 1
        digest = hashlib.sha256(seed).digest()[:SPAN_LEN]
        for prefix_len in PREFIX_LENGTHS:
            prefix = digest[:prefix_len]
            if prefix in target_sets[prefix_len]:
                matched[prefix_len].add(prefix)
    elapsed_ms = round((time.perf_counter() - started) * 1000.0, 3)
    return matched, seed_total, elapsed_ms


def count_matches(counter: Counter[bytes], matched: set[bytes]) -> int:
    return sum(count for prefix, count in counter.items() if prefix in matched)


def analyze_targets(
    targets: list[dict[str, Any]],
    matched: dict[int, set[bytes]],
) -> list[dict[str, Any]]:
    results = []
    for target in targets:
        row = target["row"]
        result = {
            "name": row["name"],
            "family": row["family"],
            "corpus": row["corpus"],
            "role": row["role"],
            "transform": row["transform"],
            "input_bytes": row["input_bytes"],
            "input_sha256": target["input_sha256"],
            "candidate_spans": target["candidate_spans"],
            "baseline_max_seed_len": BASELINE_MAX_SEED_LEN,
            "search_max_seed_len": SEARCH_MAX_SEED_LEN,
            "baseline_prefix_ge_3": row["prefix_ge_3_count"],
            "baseline_prefix_ge_4": row["prefix_ge_4_count"],
            "baseline_prefix_ge_5": row["prefix_ge_5_count"],
            "baseline_prefix_ge_6": row["prefix_ge_6_count"],
            "baseline_exact_hits": row["exact_span_hits"],
        }
        for prefix_len in PREFIX_LENGTHS:
            key = "exact_hits" if prefix_len == SPAN_LEN else f"prefix_ge_{prefix_len}"
            result[f"depth3_{key}"] = count_matches(
                target["counters"][prefix_len],
                matched[prefix_len],
            )
            baseline_key = (
                "baseline_exact_hits"
                if prefix_len == SPAN_LEN
                else f"baseline_prefix_ge_{prefix_len}"
            )
            result[f"{key}_delta_vs_depth2"] = result[f"depth3_{key}"] - result[baseline_key]
        results.append(result)
    return results


def sort_key(row: dict[str, Any]) -> tuple[int, int, int, int, int, str]:
    return (
        row["depth3_exact_hits"],
        row["depth3_prefix_ge_6"],
        row["depth3_prefix_ge_5"],
        row["depth3_prefix_ge_4"],
        row["depth3_prefix_ge_3"],
        row["name"],
    )


def summarize(results: list[dict[str, Any]], seed_total: int, elapsed_ms: float) -> dict[str, Any]:
    heldout = [row for row in results if row["role"] == "held-out"]
    rows_with_prefix5 = [row for row in heldout if row["depth3_prefix_ge_5"] > 0]
    rows_with_prefix5_uplift = [
        row for row in heldout if row["prefix_ge_5_delta_vs_depth2"] > 0
    ]
    rows_with_exact = [row for row in heldout if row["depth3_exact_hits"] > 0]
    best = max(results, key=sort_key, default=None)
    conclusion = (
        "Depth-3 prefix enumeration produced held-out prefix >=5 movement; "
        "promote only the affected rows to bounded compression runs."
        if rows_with_prefix5_uplift or rows_with_exact
        else "Depth-3 prefix enumeration did not move the current held-out frontier past prefix >=4."
    )
    return {
        "selected_rows": len(results),
        "heldout_rows": len(heldout),
        "enumerated_seed_count": seed_total,
        "enumeration_ms": elapsed_ms,
        "heldout_rows_with_prefix5": len(rows_with_prefix5),
        "heldout_rows_with_prefix5_uplift": len(rows_with_prefix5_uplift),
        "heldout_rows_with_exact_hits": len(rows_with_exact),
        "heldout_exact_hits": sum(row["depth3_exact_hits"] for row in heldout),
        "best_case": best["name"] if best else None,
        "best_case_prefix_ge_5": best["depth3_prefix_ge_5"] if best else 0,
        "best_case_exact_hits": best["depth3_exact_hits"] if best else 0,
        "conclusion": conclusion,
    }


def build_report() -> dict[str, Any]:
    rows = selected_rows(load_json(PREFIX_LADDER_JSON))
    targets = build_targets(rows)
    matched, seed_total, elapsed_ms = enumerate_matching_prefixes(targets)
    results = analyze_targets(targets, matched)
    return {
        "generated_by": "scripts/generate_depth3_prefix_probe.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "artifact_hashes": {
            "prefix_ladder_sha256": sha256(PREFIX_LADDER_JSON),
        },
        "selected_manifest_sha256": selected_manifest_hash(),
        "hasher": HASHER,
        "baseline_max_seed_len": BASELINE_MAX_SEED_LEN,
        "search_max_seed_len": SEARCH_MAX_SEED_LEN,
        "span_len": SPAN_LEN,
        "span_step": SPAN_STEP,
        "selected_row_limit": SELECTED_ROW_LIMIT,
        "prefix_lengths": list(PREFIX_LENGTHS),
        "matched_unique_prefix_counts": {
            str(prefix_len): len(matched[prefix_len]) for prefix_len in PREFIX_LENGTHS
        },
        "results": sorted(results, key=sort_key, reverse=True),
        "summary": summarize(results, seed_total, elapsed_ms),
    }


def write_report(payload: dict[str, Any]) -> None:
    PROBE_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary = payload["summary"]
    lines = [
        "# Telomere Depth-3 Prefix Probe",
        "",
        "Generated by `scripts/generate_depth3_prefix_probe.py`.",
        "This is a search-farther prefix diagnostic, not `.tlmr` format support and not a compression claim.",
        "",
        f"Baseline max seed len: `{payload['baseline_max_seed_len']}`.",
        f"Search max seed len: `{payload['search_max_seed_len']}`.",
        f"Selected frontier rows: `{summary['selected_rows']}`.",
        f"Enumerated seeds: `{summary['enumerated_seed_count']}`.",
        f"Enumeration time: `{summary['enumeration_ms']}` ms.",
        "",
        "## Summary",
        "",
        summary["conclusion"],
        f"Held-out rows with depth-3 prefix >=5: `{summary['heldout_rows_with_prefix5']}`.",
        f"Held-out rows with prefix >=5 uplift vs depth 2: `{summary['heldout_rows_with_prefix5_uplift']}`.",
        f"Held-out rows with exact hits: `{summary['heldout_rows_with_exact_hits']}`.",
        f"Held-out exact hits: `{summary['heldout_exact_hits']}`.",
        f"Best case: `{summary['best_case']}` with prefix>=5 `{summary['best_case_prefix_ge_5']}` and exact hits `{summary['best_case_exact_hits']}`.",
        "",
        "## Frontier Rows",
        "",
        "| case | family | transform | depth2 p4 | depth3 p4 | depth2 p5 | depth3 p5 | p5 delta | depth3 exact |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in payload["results"]:
        lines.append(
            "| {name} | {family} | {transform} | {baseline_prefix_ge_4} | "
            "{depth3_prefix_ge_4} | {baseline_prefix_ge_5} | {depth3_prefix_ge_5} | "
            "{prefix_ge_5_delta_vs_depth2:+} | {depth3_exact_hits} |".format(**row)
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- This probe enumerates the depth-3 seed space once and checks only prefixes that occur in current held-out prefix-4 frontier rows.",
            "- Prefix >=5 movement is a promotion signal for bounded depth-3 compression runs, not proof of compression by itself.",
            "- Exact 8-byte hits are the compression-relevant event; prefix-only rows remain search economics evidence.",
            "- Null results mean blind depth-3 expansion remains gated by the near-miss forecast.",
        ]
    )
    PROBE_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not PROBE_JSON.exists() or not PROBE_MD.exists():
        raise SystemExit("generated depth-3 prefix probe files are missing")
    payload = load_json(PROBE_JSON)
    if payload.get("generated_by") != "scripts/generate_depth3_prefix_probe.py":
        raise SystemExit("depth3_prefix_probe.json has wrong generated_by marker")
    if payload.get("artifact_hashes", {}).get("prefix_ladder_sha256") != sha256(PREFIX_LADDER_JSON):
        raise SystemExit("depth3_prefix_probe.json prefix ladder hash is stale")
    if payload.get("selected_manifest_sha256") != selected_manifest_hash():
        raise SystemExit("depth3_prefix_probe.json selected manifest hash is stale")
    if payload.get("search_max_seed_len") != SEARCH_MAX_SEED_LEN:
        raise SystemExit("depth3_prefix_probe.json search depth is stale")
    if len(payload.get("results", [])) != len(selected_manifest()):
        raise SystemExit("depth3_prefix_probe.json result count is stale")
    text = PROBE_MD.read_text(encoding="utf-8")
    for phrase in (
        "search-farther prefix diagnostic",
        "Held-out rows with depth-3 prefix >=5",
        "promotion signal for bounded depth-3 compression runs",
        "not `.tlmr` format support",
    ):
        if phrase not in text:
            raise SystemExit(f"DEPTH3_PREFIX_PROBE.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate generated depth-3 prefix probe")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.check:
        check_report()
        return
    write_report(build_report())


if __name__ == "__main__":
    main()
