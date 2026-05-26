#!/usr/bin/env python3
"""Probe depth-3 prefixes for selected transform-lead frontier rows."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import generate_lead_exact_discovery
import generate_manifold_report


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
LEAD_EXACT_JSON = DOCS / "lead_exact_discovery.json"
PROBE_JSON = DOCS / "lead_depth3_prefix_probe.json"
PROBE_MD = DOCS / "LEAD_DEPTH3_PREFIX_PROBE.md"

HASHER = "sha256"
BASELINE_MAX_SEED_LEN = 2
SEARCH_MAX_SEED_LEN = 3
SPAN_LEN = 8
SPAN_STEP = 1
SELECTED_ROW_LIMIT = 16
PREFIX_LENGTHS = (4, 5, 6, 8)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def lead_by_key() -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (lead["lead_source"], lead["display_name"]): lead
        for lead in generate_lead_exact_discovery.lead_manifest()
    }


def selected_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [
        row
        for row in payload["rows"]
        if row["role"] == "held-out" and row["prefix_ge_4_count"] > 0
    ]
    rows.sort(
        key=lambda row: (
            -row["prefix_ge_4_count"],
            -row["prefix_ge_3_count"],
            row["name"],
        )
    )
    return rows[:SELECTED_ROW_LIMIT]


def selected_manifest() -> list[dict[str, Any]]:
    fields = (
        "name",
        "family",
        "corpus",
        "role",
        "control_kind",
        "independence_group",
        "lead_source",
        "lead_name",
        "metadata_bytes",
        "input_bytes",
        "input_sha256",
        "transformed_sha256",
        "target_span_count",
        "prefix_ge_3_count",
        "prefix_ge_4_count",
        "prefix_ge_5_count",
        "prefix_ge_6_count",
        "exact_hit_count",
    )
    return [{field: row[field] for field in fields} for row in selected_rows(load_json(LEAD_EXACT_JSON))]


def selected_manifest_hash() -> str:
    payload = json.dumps(selected_manifest(), sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def row_bytes(row: dict[str, Any]) -> bytes:
    corpus = {
        "family": row["family"],
        "corpus": row["corpus"],
        "role": row["role"],
        "control_kind": row["control_kind"],
        "independence_group": row["independence_group"],
    }
    lead = lead_by_key()[(row["lead_source"], row["lead_name"])]
    source = generate_lead_exact_discovery.corpus_bytes(corpus)
    if hashlib.sha256(source).hexdigest() != row["input_sha256"]:
        raise RuntimeError(f"{row['name']}: input hash changed")
    transformed = generate_lead_exact_discovery.apply_lead(source, lead)
    if hashlib.sha256(transformed).hexdigest() != row["transformed_sha256"]:
        raise RuntimeError(f"{row['name']}: transformed hash changed")
    return transformed


def target_counters(data: bytes) -> dict[int, Counter[bytes]]:
    counters: dict[int, Counter[bytes]] = {
        prefix_len: Counter() for prefix_len in PREFIX_LENGTHS
    }
    for start in range(0, max(0, len(data) - SPAN_LEN + 1), SPAN_STEP):
        span = data[start : start + SPAN_LEN]
        for prefix_len in PREFIX_LENGTHS:
            counters[prefix_len][span[:prefix_len]] += 1
    return counters


def build_targets(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    targets = []
    for row in rows:
        data = row_bytes(row)
        targets.append(
            {
                "row": row,
                "input_sha256": row["input_sha256"],
                "transformed_sha256": hashlib.sha256(data).hexdigest(),
                "candidate_spans": generate_manifold_report.candidate_span_count(
                    len(data),
                    SPAN_LEN,
                    SPAN_STEP,
                ),
                "counters": target_counters(data),
            }
        )
    return targets


def enumerate_matching_prefixes(
    targets: list[dict[str, Any]],
) -> tuple[dict[int, set[bytes]], int, float]:
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
            "control_kind": row["control_kind"],
            "independence_group": row["independence_group"],
            "lead_source": row["lead_source"],
            "lead_name": row["lead_name"],
            "metadata_bytes": row["metadata_bytes"],
            "input_bytes": row["input_bytes"],
            "input_sha256": target["input_sha256"],
            "transformed_sha256": target["transformed_sha256"],
            "candidate_spans": target["candidate_spans"],
            "baseline_max_seed_len": BASELINE_MAX_SEED_LEN,
            "search_max_seed_len": SEARCH_MAX_SEED_LEN,
            "baseline_prefix_ge_4": row["prefix_ge_4_count"],
            "baseline_prefix_ge_5": row["prefix_ge_5_count"],
            "baseline_prefix_ge_6": row["prefix_ge_6_count"],
            "baseline_exact_hits": row["exact_hit_count"],
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
            result[f"{key}_delta_vs_depth2"] = (
                result[f"depth3_{key}"] - result[baseline_key]
            )
        results.append(result)
    return results


def sort_key(row: dict[str, Any]) -> tuple[int, int, int, int, str]:
    return (
        row["depth3_exact_hits"],
        row["depth3_prefix_ge_6"],
        row["depth3_prefix_ge_5"],
        row["depth3_prefix_ge_4"],
        row["name"],
    )


def summarize(results: list[dict[str, Any]], seed_total: int, elapsed_ms: float) -> dict[str, Any]:
    rows_with_prefix5 = [row for row in results if row["depth3_prefix_ge_5"] > 0]
    rows_with_prefix5_uplift = [
        row for row in results if row["prefix_ge_5_delta_vs_depth2"] > 0
    ]
    rows_with_exact = [row for row in results if row["depth3_exact_hits"] > 0]
    best = max(results, key=sort_key, default=None)
    conclusion = (
        "Selected leads gained depth-3 prefix >=5 movement; promote affected rows to bounded compression follow-up."
        if rows_with_prefix5_uplift or rows_with_exact
        else "Selected leads did not move past the current prefix-4 frontier at depth 3."
    )
    return {
        "selected_rows": len(results),
        "enumerated_seed_count": seed_total,
        "enumeration_ms": elapsed_ms,
        "rows_with_depth3_prefix5": len(rows_with_prefix5),
        "rows_with_depth3_prefix5_uplift": len(rows_with_prefix5_uplift),
        "rows_with_depth3_exact_hits": len(rows_with_exact),
        "total_depth3_exact_hits": sum(row["depth3_exact_hits"] for row in results),
        "best_case": best["name"] if best else None,
        "best_case_depth3_prefix_ge_5": best["depth3_prefix_ge_5"] if best else 0,
        "best_case_depth3_exact_hits": best["depth3_exact_hits"] if best else 0,
        "conclusion": conclusion,
    }


def build_report() -> dict[str, Any]:
    rows = selected_rows(load_json(LEAD_EXACT_JSON))
    targets = build_targets(rows)
    matched, seed_total, elapsed_ms = enumerate_matching_prefixes(targets)
    results = analyze_targets(targets, matched)
    return {
        "generated_by": "scripts/generate_lead_depth3_prefix_probe.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "artifact_hashes": {
            "lead_exact_discovery_sha256": sha256(LEAD_EXACT_JSON),
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
        "# Telomere Lead Depth-3 Prefix Probe",
        "",
        "Generated by `scripts/generate_lead_depth3_prefix_probe.py`.",
        "This is a selected-lead depth-3 prefix diagnostic, not `.tlmr` format support and not a compression claim.",
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
        f"Rows with depth-3 prefix >=5: `{summary['rows_with_depth3_prefix5']}`.",
        f"Rows with prefix >=5 uplift vs depth 2: `{summary['rows_with_depth3_prefix5_uplift']}`.",
        f"Rows with exact hits: `{summary['rows_with_depth3_exact_hits']}`.",
        f"Total exact hits: `{summary['total_depth3_exact_hits']}`.",
        f"Best case: `{summary['best_case']}`.",
        f"Best case prefix >=5: `{summary['best_case_depth3_prefix_ge_5']}`.",
        f"Best case exact hits: `{summary['best_case_depth3_exact_hits']}`.",
        "",
        "## Frontier Rows",
        "",
        "| row | source | p4 d2 | p4 d3 | p5 d2 | p5 d3 | p5 delta | p6 d3 | exact d3 |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in payload["results"]:
        lines.append(
            "| {name} | {lead_source} | {baseline_prefix_ge_4} | {depth3_prefix_ge_4} | "
            "{baseline_prefix_ge_5} | {depth3_prefix_ge_5} | {prefix_ge_5_delta_vs_depth2:+} | "
            "{depth3_prefix_ge_6} | {depth3_exact_hits} |".format(**row)
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- This artifact enumerates depth-3 seeds only for selected-lead held-out rows that already had prefix-4 evidence.",
            "- Prefix movement is a triage signal only; compression claims require a separate bounded compression follow-up.",
            "- If this artifact finds no prefix >=5 or exact-hit movement, broad depth-3 work remains gated.",
        ]
    )
    PROBE_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not PROBE_JSON.exists() or not PROBE_MD.exists():
        raise SystemExit("generated lead depth-3 prefix probe files are missing")
    payload = load_json(PROBE_JSON)
    if payload.get("generated_by") != "scripts/generate_lead_depth3_prefix_probe.py":
        raise SystemExit("lead_depth3_prefix_probe.json has wrong generated_by marker")
    if payload.get("artifact_hashes", {}).get("lead_exact_discovery_sha256") != sha256(
        LEAD_EXACT_JSON
    ):
        raise SystemExit("lead depth-3 prefix probe artifact hash is stale")
    if payload.get("selected_manifest_sha256") != selected_manifest_hash():
        raise SystemExit("lead depth-3 prefix probe selected manifest hash is stale")
    if payload.get("summary", {}).get("selected_rows") != len(selected_manifest()):
        raise SystemExit("lead depth-3 prefix probe selected row count is stale")
    text = PROBE_MD.read_text(encoding="utf-8")
    for phrase in (
        "Telomere Lead Depth-3 Prefix Probe",
        "selected-lead depth-3 prefix diagnostic",
        "Prefix movement is a triage signal only",
        "broad depth-3 work remains gated",
    ):
        if phrase not in text:
            raise SystemExit(f"LEAD_DEPTH3_PREFIX_PROBE.md missing phrase: {phrase}")


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
