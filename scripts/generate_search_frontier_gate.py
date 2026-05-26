#!/usr/bin/env python3
"""Generate the current search-frontier go/no-go gate from evidence artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
REPORT_JSON = DOCS / "search_frontier_gate.json"
REPORT_MD = DOCS / "SEARCH_FRONTIER_GATE.md"

SOURCE_PATHS = {
    "theory_sha256": DOCS / "theory.json",
    "nearmiss_forecast_sha256": DOCS / "nearmiss_forecast.json",
    "prefix_ladder_sha256": DOCS / "prefix_ladder.json",
    "depth3_prefix_probe_sha256": DOCS / "depth3_prefix_probe.json",
    "depth3_compression_followup_sha256": DOCS / "depth3_compression_followup.json",
    "lead_depth3_prefix_probe_sha256": DOCS / "lead_depth3_prefix_probe.json",
    "lead_depth3_compression_followup_sha256": DOCS
    / "lead_depth3_compression_followup.json",
    "depth3_frontier_exact_discovery_sha256": DOCS
    / "depth3_frontier_exact_discovery.json",
    "depth4_shard_plan_sha256": DOCS / "depth4_shard_plan.json",
    "depth4_pilot_shard_sha256": DOCS / "depth4_pilot_shard.json",
    "heldout_corpus_expansion_sha256": DOCS / "heldout_corpus_expansion.json",
    "match_discovery_sha256": DOCS / "match_discovery.json",
    "alignment_arity_discovery_sha256": DOCS / "alignment_arity_discovery.json",
    "transformed_match_discovery_sha256": DOCS / "transformed_match_discovery.json",
    "lead_exact_discovery_sha256": DOCS / "lead_exact_discovery.json",
}

PROMOTION_THRESHOLDS = {
    "forecast_gib_for_one_exact_hit": 1.0,
    "ordinary_prefix5_group_count": 3,
    "ordinary_selected_group_count": 2,
    "depth3_prefix6_rows": 1,
    "depth3_exact_hits": 1,
    "depth3_selected_spans": 1,
    "depth4_pilot_prefix6_rows": 1,
    "depth4_pilot_exact_hits": 1,
    "depth4_pilot_selected_spans": 1,
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact_hashes() -> dict[str, str]:
    return {name: sha256(path) for name, path in SOURCE_PATHS.items()}


def gate_manifest() -> dict[str, Any]:
    return {
        "scope": "search-frontier decision gate; no seed enumeration is performed",
        "span_len": 8,
        "hasher": "sha256",
        "canonical_seed_order": "1-byte seeds first, then 2-byte, then 3-byte, then 4-byte, each bucket big-endian",
        "target_block_hashing": False,
        "thresholds": PROMOTION_THRESHOLDS,
        "rules": [
            "treat prefix-4 as steering evidence only",
            "require prefix>=5 movement before exact-search escalation",
            "require prefix>=6, exact hits, selected spans, or sub-1-GiB forecast before broad depth-4 execution",
            "require selected exact spans after metadata before format promotion",
            "keep paired shadow, binary, and high-entropy controls from inflating ordinary-corpus proof",
        ],
    }


def manifest_hash() -> str:
    payload = json.dumps(gate_manifest(), sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(payload).hexdigest()


def summary_u64(payload: dict[str, Any], key: str) -> int:
    value = payload.get("summary", {}).get(key, 0)
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return 0


def build_gate_checks(inputs: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    near = inputs["nearmiss"]["summary"]
    ladder = inputs["prefix_ladder"]["summary"]
    depth3_frontier = inputs["depth3_frontier"]["summary"]
    depth4_plan = inputs["depth4_plan"]["depth4_estimates"]
    depth4_pilot = inputs["depth4_pilot"]["summary"]
    heldout = inputs["heldout_expansion"]["summary"]
    match = inputs["match_discovery"]["summary"]
    alignment = inputs["alignment_arity"]["summary"]
    transformed = inputs["transformed_match"]["summary"]
    lead_exact = inputs["lead_exact"]["summary"]
    depth3_followup = inputs["depth3_followup"]["summary"]
    lead_depth3_followup = inputs["lead_depth3_followup"]["summary"]

    total_selected = sum(
        int(value)
        for value in (
            match["total_selected_spans"],
            alignment["total_selected_spans"],
            transformed["total_selected_spans"],
            lead_exact["total_selected_spans"],
            depth3_frontier["total_selected_spans"],
            depth3_followup["total_depth3_selected_spans"],
            lead_depth3_followup["total_depth3_selected_spans"],
            depth4_pilot["total_selected_spans"],
        )
    )
    total_exact = sum(
        int(value)
        for value in (
            match["total_exact_hits"],
            alignment["total_positive_exact_hits"],
            transformed["total_exact_hits"],
            lead_exact["total_exact_hits"],
            depth3_frontier["total_exact_hits"],
            depth4_pilot["total_exact_hits"],
        )
    )
    forecast_gib = float(near["best_non_planted_gib_for_one_expected_hit"])

    return [
        {
            "gate": "forecast-scale",
            "requirement": "best non-planted exact-hit forecast below 1 GiB",
            "observed": f"{forecast_gib:.3f} GiB",
            "met": forecast_gib <= PROMOTION_THRESHOLDS["forecast_gib_for_one_exact_hit"],
            "consequence": "Do not broaden raw exact search while the best forecast remains hundreds of GiB per expected hit.",
        },
        {
            "gate": "prefix-ladder",
            "requirement": "held-out/control rows reach prefix>=5 before exact-search escalation",
            "observed": f"{ladder['heldout_rows_with_prefix5']} rows",
            "met": int(ladder["heldout_rows_with_prefix5"]) > 0,
            "consequence": "Treat prefix-4 as transform-design telemetry, not compression evidence.",
        },
        {
            "gate": "heldout-expansion",
            "requirement": "new ordinary held-out groups produce prefix>=5 movement while controls stay null",
            "observed": (
                f"{heldout['ordinary_prefix5_group_count']} ordinary groups, "
                f"{heldout['control_prefix5_group_count']} control groups"
            ),
            "met": int(heldout["ordinary_prefix5_group_count"])
            >= PROMOTION_THRESHOLDS["ordinary_prefix5_group_count"]
            and int(heldout["control_prefix5_group_count"]) == 0,
            "consequence": "Keep replication corpora in the frontier artifact instead of staling the expensive corpus matrices.",
        },
        {
            "gate": "selected-spans",
            "requirement": "profitable selected exact spans appear after metadata accounting",
            "observed": f"{total_selected} selected spans and {total_exact} positive/exact promotion hits",
            "met": total_selected > 0,
            "consequence": "Do not promote transform metadata or packed sidecar format work without selected exact spans.",
        },
        {
            "gate": "depth3-frontier",
            "requirement": "depth-3 frontier finds prefix>=6, exact hits, or selected spans",
            "observed": (
                f"{depth3_frontier['rows_with_depth3_prefix6']} prefix>=6 rows, "
                f"{depth3_frontier['total_exact_hits']} exact hits, "
                f"{depth3_frontier['total_selected_spans']} selected spans"
            ),
            "met": any(
                int(value) > 0
                for value in (
                    depth3_frontier["rows_with_depth3_prefix6"],
                    depth3_frontier["total_exact_hits"],
                    depth3_frontier["total_selected_spans"],
                )
            ),
            "consequence": "Keep broad depth-3 and depth-4 work gated; prefix>=5 alone did not become compression.",
        },
        {
            "gate": "depth4-pilot",
            "requirement": "pilot shard finds prefix>=6, exact hits, or selected spans before all shards",
            "observed": (
                f"{depth4_pilot['rows_with_depth4_prefix6']} prefix>=6 rows, "
                f"{depth4_pilot['total_exact_hits']} exact hits, "
                f"{depth4_pilot['total_selected_spans']} selected spans"
            ),
            "met": any(
                int(value) > 0
                for value in (
                    depth4_pilot["rows_with_depth4_prefix6"],
                    depth4_pilot["total_exact_hits"],
                    depth4_pilot["total_selected_spans"],
                )
            ),
            "consequence": "Do not run the remaining depth-4 shards from the current frontier.",
        },
        {
            "gate": "depth4-expectation",
            "requirement": "full depth-4 exact probability is high enough to justify full execution",
            "observed": f"{depth4_plan['exact8_probability_at_least_one']:.6g} probability",
            "met": float(depth4_plan["exact8_probability_at_least_one"]) >= 0.5,
            "consequence": "The current full-shard probability is too small to justify compute without a stronger frontier.",
        },
    ]


def build_report() -> dict[str, Any]:
    inputs = {
        "theory": load_json(SOURCE_PATHS["theory_sha256"]),
        "nearmiss": load_json(SOURCE_PATHS["nearmiss_forecast_sha256"]),
        "prefix_ladder": load_json(SOURCE_PATHS["prefix_ladder_sha256"]),
        "depth3_prefix": load_json(SOURCE_PATHS["depth3_prefix_probe_sha256"]),
        "depth3_followup": load_json(
            SOURCE_PATHS["depth3_compression_followup_sha256"]
        ),
        "lead_depth3_prefix": load_json(
            SOURCE_PATHS["lead_depth3_prefix_probe_sha256"]
        ),
        "lead_depth3_followup": load_json(
            SOURCE_PATHS["lead_depth3_compression_followup_sha256"]
        ),
        "depth3_frontier": load_json(
            SOURCE_PATHS["depth3_frontier_exact_discovery_sha256"]
        ),
        "depth4_plan": load_json(SOURCE_PATHS["depth4_shard_plan_sha256"]),
        "depth4_pilot": load_json(SOURCE_PATHS["depth4_pilot_shard_sha256"]),
        "heldout_expansion": load_json(
            SOURCE_PATHS["heldout_corpus_expansion_sha256"]
        ),
        "match_discovery": load_json(SOURCE_PATHS["match_discovery_sha256"]),
        "alignment_arity": load_json(
            SOURCE_PATHS["alignment_arity_discovery_sha256"]
        ),
        "transformed_match": load_json(
            SOURCE_PATHS["transformed_match_discovery_sha256"]
        ),
        "lead_exact": load_json(SOURCE_PATHS["lead_exact_discovery_sha256"]),
    }
    checks = build_gate_checks(inputs)
    near = inputs["nearmiss"]["summary"]
    frontier = inputs["depth3_frontier"]["summary"]
    depth4 = inputs["depth4_plan"]["depth4_estimates"]
    pilot = inputs["depth4_pilot"]["summary"]
    heldout = inputs["heldout_expansion"]["summary"]
    alignment = inputs["alignment_arity"]["summary"]
    selected_total = sum(
        summary_u64(inputs[name], key)
        for name, key in (
            ("match_discovery", "total_selected_spans"),
            ("alignment_arity", "total_selected_spans"),
            ("transformed_match", "total_selected_spans"),
            ("lead_exact", "total_selected_spans"),
            ("depth3_frontier", "total_selected_spans"),
            ("depth4_pilot", "total_selected_spans"),
        )
    )
    gate_met_count = sum(1 for check in checks if check["met"])
    blocking_gates = [check["gate"] for check in checks if not check["met"]]
    summary = {
        "recommended_status": "hold-broad-depth-search",
        "broad_depth_search_allowed": False,
        "depth4_all_shards_allowed": False,
        "corpus_matrix_promotion_allowed": False,
        "format_promotion_allowed": False,
        "gate_met_count": gate_met_count,
        "gate_count": len(checks),
        "blocking_gates": blocking_gates,
        "best_non_planted_case": near["best_non_planted_case"],
        "best_non_planted_gib_for_one_expected_hit": near[
            "best_non_planted_gib_for_one_expected_hit"
        ],
        "frontier_rows": frontier["frontier_rows"],
        "depth3_frontier_prefix6_rows": frontier["rows_with_depth3_prefix6"],
        "depth3_frontier_exact_hits": frontier["total_exact_hits"],
        "depth3_frontier_selected_spans": frontier["total_selected_spans"],
        "depth4_exact8_probability": depth4["exact8_probability_at_least_one"],
        "depth4_pilot_prefix6_rows": pilot["rows_with_depth4_prefix6"],
        "depth4_pilot_exact_hits": pilot["total_exact_hits"],
        "depth4_pilot_selected_spans": pilot["total_selected_spans"],
        "heldout_expansion_corpus_count": heldout["corpus_count"],
        "heldout_expansion_prefix5_rows": heldout["rows_with_prefix_ge_5"],
        "heldout_expansion_exact_hit_rows": heldout["rows_with_exact_hits"],
        "heldout_expansion_selected_span_rows": heldout["rows_with_selected_spans"],
        "selected_span_total": selected_total,
        "unprofitable_short_exact_hits": alignment["total_unprofitable_exact_hits"],
        "positive_alignment_exact_hits": alignment["total_positive_exact_hits"],
        "next_action": (
            "Design a materially new byte-to-seed mechanism or stronger reversible "
            "frontier generator; do not spend on broad raw depth search from the "
            "current prefix-only frontier."
        ),
    }
    return {
        "generated_by": "scripts/generate_search_frontier_gate.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "artifact_hashes": artifact_hashes(),
        "gate_manifest_sha256": manifest_hash(),
        "gate_manifest": gate_manifest(),
        "summary": summary,
        "gate_checks": checks,
    }


def write_report(payload: dict[str, Any]) -> None:
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary = payload["summary"]
    lines = [
        "# Telomere Search Frontier Gate",
        "",
        "Generated by `scripts/generate_search_frontier_gate.py`.",
        "This is a go/no-go decision artifact, not a compression claim and not a seed enumeration run.",
        "It is not `.tlmr` format support.",
        "",
        f"Recommended status: **{summary['recommended_status']}**.",
        f"Best non-planted case: `{summary['best_non_planted_case']}`.",
        f"Best non-planted forecast: `{summary['best_non_planted_gib_for_one_expected_hit']}` GiB for one expected exact hit.",
        f"Depth-4 exact-8 probability on the current frontier: `{summary['depth4_exact8_probability']:.6g}`.",
        f"Selected span total across current frontier artifacts: `{summary['selected_span_total']}`.",
        f"Unprofitable short exact hits from alignment/arity controls: `{summary['unprofitable_short_exact_hits']}`.",
        "",
        "## Decision",
        "",
        "- Broad raw depth search is **not allowed** from the current frontier.",
        "- Full depth-4 shard execution is **not allowed** from the current frontier.",
        "- Corpus-matrix promotion is **not allowed** solely from the current held-out expansion null.",
        "- Format-transform promotion is **not allowed** without selected exact spans after metadata.",
        f"- Next action: {summary['next_action']}",
        "",
        "## Gate Checks",
        "",
        "| gate | requirement | observed | met | consequence |",
        "| --- | --- | --- | --- | --- |",
    ]
    for check in payload["gate_checks"]:
        lines.append(
            "| {gate} | {requirement} | {observed} | {met} | {consequence} |".format(
                **check
            )
        )
    lines.extend(
        [
            "",
            "## Rules",
            "",
            "- Target block hashing: `false`.",
            "- Canonical seed order: 1-byte seeds first, then 2-byte, then 3-byte, then 4-byte, each bucket big-endian.",
            "- Prefix-4 is steering evidence only.",
            "- Prefix movement alone is not compression evidence.",
            "- Prefix>=5 is a follow-up signal, not a compression win.",
            "- Prefix>=6, exact hits, selected spans, or sub-1-GiB forecast are required before broad depth-4 execution.",
            "- Promotion requires exact regenerated seed-span records.",
            "- Selected exact spans after metadata are required before `.tlmr` format promotion.",
            "- Paired shadow, binary, and high-entropy controls cannot inflate ordinary-corpus proof.",
            "- Stop rule: stop broadening raw depth search while all gate checks remain false.",
            "",
            "## Source Artifacts",
            "",
        ]
    )
    for name, digest in payload["artifact_hashes"].items():
        lines.append(f"- `{name}`: `{digest}`")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not REPORT_JSON.exists() or not REPORT_MD.exists():
        raise SystemExit("generated search frontier gate files are missing")
    payload = load_json(REPORT_JSON)
    if payload.get("generated_by") != "scripts/generate_search_frontier_gate.py":
        raise SystemExit("search_frontier_gate.json has wrong generated_by marker")
    if payload.get("artifact_hashes") != artifact_hashes():
        raise SystemExit("search frontier gate artifact hashes are stale")
    if payload.get("gate_manifest_sha256") != manifest_hash():
        raise SystemExit("search frontier gate manifest hash is stale")
    if len(payload.get("gate_checks", [])) != 7:
        raise SystemExit("search frontier gate check count is stale")
    text = REPORT_MD.read_text(encoding="utf-8")
    for phrase in (
        "Telomere Search Frontier Gate",
        "go/no-go decision artifact",
        "not `.tlmr` format support",
        "Target block hashing: `false`",
        "Canonical seed order",
        "Broad raw depth search is **not allowed**",
        "Full depth-4 shard execution is **not allowed**",
        "Prefix-4 is steering evidence only",
        "Prefix movement alone is not compression evidence",
        "sub-1-GiB forecast",
        "Promotion requires exact regenerated seed-span records",
        "Selected exact spans after metadata",
        "Stop rule",
    ):
        if phrase not in text:
            raise SystemExit(f"SEARCH_FRONTIER_GATE.md missing phrase: {phrase}")


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
