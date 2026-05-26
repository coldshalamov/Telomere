#!/usr/bin/env python3
"""Generate the long-span bundle go/no-go gate from current evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
REPORT_JSON = DOCS / "long_span_bundle_gate.json"
REPORT_MD = DOCS / "LONG_SPAN_BUNDLE_GATE.md"
GENERATED_BY = "scripts/generate_long_span_bundle_gate.py"

SOURCE_PATHS = {
    "mechanism_experiment_ranking_sha256": DOCS / "mechanism_experiment_ranking.json",
    "search_frontier_gate_sha256": DOCS / "search_frontier_gate.json",
    "sidecar_break_even_sha256": DOCS / "sidecar_break_even.json",
    "exact_short_hit_bundle_economics_sha256": DOCS
    / "exact_short_hit_bundle_economics.json",
    "whole_stream_residual_vector_probe_sha256": DOCS
    / "whole_stream_residual_vector_probe.json",
    "seed_table_preset_probe_sha256": DOCS / "seed_table_preset_probe.json",
    "schema_native_public_dictionaries_sha256": DOCS
    / "schema_native_public_dictionaries.json",
    "schema_native_public_dictionary_replication_sha256": DOCS
    / "schema_native_public_dictionary_replication.json",
    "packed_sidecar_replication_sha256": DOCS / "packed_sidecar_replication.json",
    "match_discovery_sha256": DOCS / "match_discovery.json",
    "alignment_arity_discovery_sha256": DOCS / "alignment_arity_discovery.json",
    "transformed_match_discovery_sha256": DOCS / "transformed_match_discovery.json",
    "lead_exact_discovery_sha256": DOCS / "lead_exact_discovery.json",
}

PROMOTION_THRESHOLDS = {
    "max_forecast_gib_for_one_exact_hit": 1.0,
    "required_raw_suffix_prefix_len": 6,
    "required_ordinary_negative_groups": 3,
    "allowed_control_negative_groups": 0,
    "required_selected_span_total": 1,
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes() -> dict[str, str]:
    return {name: sha256(path) for name, path in SOURCE_PATHS.items()}


def summary(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("summary", {})
    return value if isinstance(value, dict) else {}


def mechanism_row(payload: dict[str, Any], lane_id: str) -> dict[str, Any]:
    for row in payload.get("rankings", []):
        if row.get("lane_id") == lane_id:
            return row
    raise KeyError(lane_id)


def gate_manifest() -> dict[str, Any]:
    return {
        "scope": "long-span bundle decision gate; no new seed enumeration is performed",
        "not_a_compression_claim": True,
        "not_format_support": True,
        "thresholds": PROMOTION_THRESHOLDS,
        "rules": [
            "long-span sweeps require the search frontier to be open",
            "strict raw-suffix economics require observed held-out prefixes at or beyond the raw-suffix break-even threshold",
            "short-hit bundle wins must survive comparable control-density checks",
            "sidecar and residual-vector claims require ordinary held-out negative groups with null controls",
            "public dictionary signals do not justify long-span raw-depth sweeps while harder replication controls fail",
        ],
    }


def manifest_hash() -> str:
    payload = json.dumps(gate_manifest(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def selected_span_total(inputs: dict[str, dict[str, Any]]) -> int:
    match = summary(inputs["match_discovery"])
    alignment = summary(inputs["alignment_arity_discovery"])
    transformed = summary(inputs["transformed_match_discovery"])
    lead_exact = summary(inputs["lead_exact_discovery"])
    search_gate = summary(inputs["search_frontier_gate"])
    return sum(
        int(value)
        for value in (
            search_gate.get("selected_span_total", 0),
            match.get("total_selected_spans", 0),
            alignment.get("total_selected_spans", 0),
            transformed.get("total_selected_spans", 0),
            lead_exact.get("total_selected_spans", 0),
        )
    )


def build_gate_checks(inputs: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    search = summary(inputs["search_frontier_gate"])
    sidecar = summary(inputs["sidecar_break_even"])
    exact_short = summary(inputs["exact_short_hit_bundle_economics"])
    whole_stream = summary(inputs["whole_stream_residual_vector_probe"])
    seed_table = summary(inputs["seed_table_preset_probe"])
    schema_replication = summary(inputs["schema_native_public_dictionary_replication"])
    packed_replication = summary(inputs["packed_sidecar_replication"])
    total_selected = selected_span_total(inputs)

    raw_suffix_prefix_met = (
        int(sidecar["max_observed_heldout_forced_prefix_len"])
        >= int(sidecar["minimum_raw_suffix_negative_prefix_len"])
    )
    exact_short_clean = (
        int(exact_short["full_stream_ordinary_negative_groups"])
        >= PROMOTION_THRESHOLDS["required_ordinary_negative_groups"]
        and int(exact_short["full_stream_control_negative_groups"])
        <= PROMOTION_THRESHOLDS["allowed_control_negative_groups"]
        and not bool(exact_short["control_density"]["control_density_comparable"])
    )
    whole_stream_clean = (
        int(whole_stream["ordinary_heldout_negative_groups"])
        >= PROMOTION_THRESHOLDS["required_ordinary_negative_groups"]
        and int(whole_stream["control_negative_groups"])
        <= PROMOTION_THRESHOLDS["allowed_control_negative_groups"]
    )
    schema_replication_clean = (
        int(schema_replication["standards_ordinary_negative_groups"])
        >= PROMOTION_THRESHOLDS["required_ordinary_negative_groups"]
        and int(schema_replication["standards_control_negative_groups"])
        <= PROMOTION_THRESHOLDS["allowed_control_negative_groups"]
        and bool(schema_replication["promotion_met"])
    )

    return [
        {
            "gate": "search-frontier-open",
            "requirement": "Search frontier allows broad raw depth before long-span sweeps.",
            "observed": search["recommended_status"],
            "met": bool(search["broad_depth_search_allowed"]),
            "consequence": "Do not run long-span raw-depth sweeps while the frontier gate is closed.",
        },
        {
            "gate": "forecast-scale",
            "requirement": "Best non-planted exact-hit forecast is below 1 GiB.",
            "observed": f"{search['best_non_planted_gib_for_one_expected_hit']} GiB",
            "met": float(search["best_non_planted_gib_for_one_expected_hit"])
            <= PROMOTION_THRESHOLDS["max_forecast_gib_for_one_exact_hit"],
            "consequence": "Long-span search is not compute-rational from the current forecast.",
        },
        {
            "gate": "selected-span-frontier",
            "requirement": "At least one profitable selected span exists in recent discovery artifacts.",
            "observed": f"{total_selected} selected spans",
            "met": total_selected >= PROMOTION_THRESHOLDS["required_selected_span_total"],
            "consequence": "Do not optimize long-span bundle packing before profitable spans exist.",
        },
        {
            "gate": "raw-suffix-break-even",
            "requirement": "Observed held-out forced prefixes reach strict raw-suffix break-even.",
            "observed": (
                f"observed prefix {sidecar['max_observed_heldout_forced_prefix_len']} "
                f"vs required {sidecar['minimum_raw_suffix_negative_prefix_len']}"
            ),
            "met": raw_suffix_prefix_met
            and int(sidecar["raw_suffix_viable_at_observed_prefix_rows"]) > 0,
            "consequence": "Prefix-4 movement remains steering evidence, not long-span bundle evidence.",
        },
        {
            "gate": "short-hit-controls",
            "requirement": "Short-hit bundling has ordinary wins with no comparable controls.",
            "observed": (
                f"{exact_short['full_stream_ordinary_negative_groups']} ordinary groups, "
                f"{exact_short['full_stream_control_negative_groups']} control groups, "
                f"control density comparable "
                f"{exact_short['control_density']['control_density_comparable']}"
            ),
            "met": exact_short_clean,
            "consequence": "Current exact short-hit density is too control-like to justify broad long-span work.",
        },
        {
            "gate": "whole-stream-residual",
            "requirement": "Whole-stream residual vectors produce ordinary negative groups with null controls.",
            "observed": (
                f"{whole_stream['ordinary_heldout_negative_groups']} ordinary groups, "
                f"{whole_stream['control_negative_groups']} control groups"
            ),
            "met": whole_stream_clean,
            "consequence": "Residual-vector evidence does not yet support long-span bundle promotion.",
        },
        {
            "gate": "seed-table-generalization",
            "requirement": "Seed-table/public dictionary evidence survives harder held-out controls.",
            "observed": (
                f"seed-table ordinary groups "
                f"{seed_table['canonical_ordinary_heldout_negative_groups']}; "
                f"schema replication controls "
                f"{schema_replication['standards_control_negative_groups']}; "
                f"claim {schema_replication['claim_level']}"
            ),
            "met": schema_replication_clean,
            "consequence": "Public dictionary signals stay research-only until replication controls pass.",
        },
        {
            "gate": "packed-replication",
            "requirement": "Packed sidecar replication produces full-stream negative ordinary groups.",
            "observed": (
                f"{packed_replication['full_stream_negative_rows']} full-stream rows, "
                f"{packed_replication['ordinary_heldout_negative_groups']} ordinary groups"
            ),
            "met": int(packed_replication["ordinary_heldout_negative_groups"])
            >= PROMOTION_THRESHOLDS["required_ordinary_negative_groups"],
            "consequence": "Descriptor packing remains narrow and does not justify broad long-span bundle sweeps.",
        },
    ]


def build_report() -> dict[str, Any]:
    inputs = {
        name.removesuffix("_sha256"): load_json(path)
        for name, path in SOURCE_PATHS.items()
    }
    checks = build_gate_checks(inputs)
    met_count = sum(1 for check in checks if check["met"])
    mechanism = inputs["mechanism_experiment_ranking"]
    long_span_row = mechanism_row(mechanism, "long-span-bundle-gate")
    search = summary(inputs["search_frontier_gate"])
    sidecar = summary(inputs["sidecar_break_even"])
    exact_short = summary(inputs["exact_short_hit_bundle_economics"])
    whole_stream = summary(inputs["whole_stream_residual_vector_probe"])
    schema_replication = summary(inputs["schema_native_public_dictionary_replication"])
    promotion_met = met_count == len(checks)
    summary_payload = {
        "gate_count": len(checks),
        "gate_met_count": met_count,
        "blocking_gates": [check["gate"] for check in checks if not check["met"]],
        "mechanism_rank": long_span_row["rank"],
        "mechanism_status": long_span_row["status"],
        "search_frontier_status": search["recommended_status"],
        "broad_depth_search_allowed": search["broad_depth_search_allowed"],
        "best_non_planted_gib_for_one_expected_hit": search[
            "best_non_planted_gib_for_one_expected_hit"
        ],
        "selected_span_total": selected_span_total(inputs),
        "minimum_raw_suffix_negative_prefix_len": sidecar[
            "minimum_raw_suffix_negative_prefix_len"
        ],
        "max_observed_heldout_forced_prefix_len": sidecar[
            "max_observed_heldout_forced_prefix_len"
        ],
        "raw_suffix_viable_at_observed_prefix_rows": sidecar[
            "raw_suffix_viable_at_observed_prefix_rows"
        ],
        "exact_short_verified_hits": exact_short["reconstructed_exact_hits"],
        "exact_short_ordinary_negative_groups": exact_short[
            "full_stream_ordinary_negative_groups"
        ],
        "exact_short_control_negative_groups": exact_short[
            "full_stream_control_negative_groups"
        ],
        "exact_short_control_density_comparable": exact_short["control_density"][
            "control_density_comparable"
        ],
        "whole_stream_ordinary_negative_groups": whole_stream[
            "ordinary_heldout_negative_groups"
        ],
        "schema_replication_claim_level": schema_replication["claim_level"],
        "schema_replication_control_negative_groups": schema_replication[
            "standards_control_negative_groups"
        ],
        "promotion_met": promotion_met,
        "recommendation": (
            "run_long_span_bundle_sweeps"
            if promotion_met
            else "hold_long_span_bundle_sweeps"
        ),
        "claim_level": (
            "long_span_bundle_gate_passed"
            if promotion_met
            else "long_span_bundle_gate_blocked_by_evidence"
        ),
        "stop_rule": (
            "Do not run broad long-span bundle sweeps until search frontier, "
            "raw-suffix break-even, selected-span, and control gates pass."
        ),
        "conclusion": (
            "Long-span bundle sweeps are justified by current evidence."
            if promotion_met
            else "Current evidence blocks broad long-span bundle sweeps."
        ),
    }
    return {
        "generated_by": GENERATED_BY,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "source_hashes": source_hashes(),
        "gate_manifest_sha256": manifest_hash(),
        "gate_manifest": gate_manifest(),
        "summary": summary_payload,
        "gate_checks": checks,
    }


def write_report(payload: dict[str, Any]) -> None:
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary_payload = payload["summary"]
    lines = [
        "# Telomere Long-Span Bundle Gate",
        "",
        f"Generated by `{GENERATED_BY}` from checked-in evidence artifacts.",
        "This is a no-run decision gate, not a compression claim and not `.tlmr` format support.",
        "",
        "## Summary",
        "",
        f"- Gate checks: `{summary_payload['gate_met_count']}` / `{summary_payload['gate_count']}`",
        f"- Recommendation: `{summary_payload['recommendation']}`",
        f"- Claim level: `{summary_payload['claim_level']}`",
        f"- Search frontier: `{summary_payload['search_frontier_status']}`",
        f"- Best non-planted forecast: `{summary_payload['best_non_planted_gib_for_one_expected_hit']}` GiB per expected exact hit",
        f"- Selected span total: `{summary_payload['selected_span_total']}`",
        f"- Raw-suffix strict prefix needed: `{summary_payload['minimum_raw_suffix_negative_prefix_len']}`",
        f"- Max observed held-out forced prefix: `{summary_payload['max_observed_heldout_forced_prefix_len']}`",
        f"- Exact short-hit ordinary/control groups: `{summary_payload['exact_short_ordinary_negative_groups']}` / `{summary_payload['exact_short_control_negative_groups']}`",
        f"- Schema replication claim level: `{summary_payload['schema_replication_claim_level']}`",
        f"- Promotion met: `{summary_payload['promotion_met']}`",
        "",
        summary_payload["conclusion"],
        "",
        "## Gate Checks",
        "",
        "| gate | met | observed | consequence |",
        "| --- | --- | --- | --- |",
    ]
    for check in payload["gate_checks"]:
        lines.append(
            f"| `{check['gate']}` | `{check['met']}` | {check['observed']} | {check['consequence']} |"
        )
    lines.extend(["", "## Stop Rule", ""])
    lines.append(f"- {summary_payload['stop_rule']}")
    lines.extend(["", "## Source Artifacts", ""])
    for name, digest in payload["source_hashes"].items():
        lines.append(f"- `{name}`: `{digest}`")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not REPORT_JSON.exists() or not REPORT_MD.exists():
        raise SystemExit("generated long-span bundle gate files are missing")
    payload = load_json(REPORT_JSON)
    if payload.get("generated_by") != GENERATED_BY:
        raise SystemExit("long_span_bundle_gate.json has wrong generated_by marker")
    if payload.get("source_hashes") != source_hashes():
        raise SystemExit("long-span bundle gate source hashes are stale")
    if payload.get("gate_manifest_sha256") != manifest_hash():
        raise SystemExit("long-span bundle gate manifest hash is stale")
    expected = build_report()["summary"]
    current = payload.get("summary", {})
    comparable_keys = [key for key in expected if key != "conclusion"]
    for key in comparable_keys:
        if current.get(key) != expected[key]:
            raise SystemExit(f"long-span bundle gate summary is stale: {key}")
    if len(payload.get("gate_checks", [])) != len(build_gate_checks({
        name.removesuffix("_sha256"): load_json(path)
        for name, path in SOURCE_PATHS.items()
    })):
        raise SystemExit("long-span bundle gate check matrix is incomplete")
    text = REPORT_MD.read_text(encoding="utf-8")
    for phrase in (
        "Telomere Long-Span Bundle Gate",
        f"Generated by `{GENERATED_BY}`",
        "no-run decision gate",
        "Best non-planted forecast",
        "Raw-suffix strict prefix needed",
        "Gate Checks",
        "Stop Rule",
    ):
        if phrase not in text:
            raise SystemExit(f"LONG_SPAN_BUNDLE_GATE.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate generated long-span bundle gate files",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.check:
        check_report()
        return
    write_report(build_report())


if __name__ == "__main__":
    main()
