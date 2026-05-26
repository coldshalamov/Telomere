#!/usr/bin/env python3
"""Generate the public preset control ablation manifest.

This is a no-compute coordination artifact with read-only calculations over the
existing schema replication rows. It pre-registers the bounded ablations needed
to separate public-preset signal from paired-shadow and generic-token controls.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
REPORT_JSON = DOCS / "public_preset_control_ablation.json"
REPORT_MD = DOCS / "PUBLIC_PRESET_CONTROL_ABLATION.md"
GENERATED_BY = "scripts/generate_public_preset_control_ablation.py"

SOURCE_PATHS = {
    "public_preset_control_audit_sha256": DOCS / "public_preset_control_audit.json",
    "public_preset_promotion_gate_sha256": DOCS / "public_preset_promotion_gate.json",
    "schema_native_public_dictionary_replication_sha256": DOCS
    / "schema_native_public_dictionary_replication.json",
    "schema_native_public_dictionaries_sha256": DOCS
    / "schema_native_public_dictionaries.json",
    "seed_table_preset_probe_sha256": DOCS / "seed_table_preset_probe.json",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes() -> dict[str, str]:
    return {name: sha256(path) for name, path in SOURCE_PATHS.items()}


def stable_projection(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if key != "generated_at"}


def summary(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("summary", {})
    return value if isinstance(value, dict) else {}


def cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def standards_rows(replication: dict[str, Any]) -> list[dict[str, Any]]:
    return [row for row in replication["rows"] if row["mode"] == "standards-public-v1"]


def negative(row: dict[str, Any]) -> bool:
    return int(row.get("delta_bytes", 0)) < 0


def density(row: dict[str, Any], numerator: str) -> float:
    input_bytes = max(1, int(row["input_bytes"]))
    return round(float(row.get(numerator, 0)) / input_bytes * 1024.0, 6)


def density_rows(replication: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for row in standards_rows(replication):
        rows.append(
            {
                "name": row["name"],
                "control_kind": row["control_kind"],
                "independence_group": row["independence_group"],
                "schema_family": row["schema_family"],
                "input_bytes": row["input_bytes"],
                "delta_bytes": row["delta_bytes"],
                "negative": negative(row),
                "selected_span_count": row["selected_span_count"],
                "selected_covered_bytes": row["selected_covered_bytes"],
                "dictionary_entry_count": row["dictionary_entry_count"],
                "metadata_bytes": row["metadata_bytes"],
                "selected_spans_per_kib": density(row, "selected_span_count"),
                "covered_bytes_per_kib": density(row, "selected_covered_bytes"),
                "savings_bytes_per_kib": round(
                    -float(min(0, row["delta_bytes"])) / max(1, row["input_bytes"]) * 1024.0,
                    6,
                ),
                "project_token_hits_per_kib": density(row, "telomere_project_token_hits"),
                "telomere_project_token_hits": row.get("telomere_project_token_hits", 0),
                "selected_entry_family_counts": row.get("selected_entry_family_counts", {}),
            }
        )
    return rows


def aggregate_by_kind(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[row["control_kind"]].append(row)
    aggregates = []
    for kind, items in sorted(groups.items()):
        negatives = [item for item in items if item["negative"]]
        aggregates.append(
            {
                "control_kind": kind,
                "row_count": len(items),
                "negative_row_count": len(negatives),
                "negative_group_count": len(
                    {item["independence_group"] for item in negatives}
                ),
                "mean_selected_spans_per_kib": round(
                    mean(item["selected_spans_per_kib"] for item in items), 6
                ),
                "mean_savings_bytes_per_kib": round(
                    mean(item["savings_bytes_per_kib"] for item in items), 6
                ),
                "best_case": min(items, key=lambda item: item["delta_bytes"])["name"],
                "best_delta_bytes": min(item["delta_bytes"] for item in items),
                "negative_groups": sorted(
                    {item["independence_group"] for item in negatives}
                ),
            }
        )
    return aggregates


def ablation_rows(
    audit: dict[str, Any],
    density_summary: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    audit_summary = summary(audit)
    by_kind = {row["control_kind"]: row for row in density_summary}
    ordinary = by_kind["ordinary-structured"]
    shadow = by_kind["paired-shadow-control"]
    generic_failure = audit_summary["generic_ordinary_negative_groups"] > 0
    shadow_failure = audit_summary["standards_control_negative_groups"] > 0
    density_ratio = round(
        ordinary["mean_savings_bytes_per_kib"]
        / max(0.000001, shadow["mean_savings_bytes_per_kib"]),
        6,
    )
    return [
        {
            "ablation_id": "paired-shadow-expansion",
            "status": "required",
            "parallel_group": "corpus-transform",
            "current_result": "failed" if shadow_failure else "passed",
            "current_evidence": (
                f"{audit_summary['standards_control_negative_groups']} paired-shadow "
                f"groups are negative: {', '.join(audit_summary['standards_control_negative_group_names'])}."
            ),
            "rerun_design": (
                "Add at least one vocabulary-disjoint paired shadow for every ordinary "
                "negative group before counting public-preset wins."
            ),
            "success_rule": "ordinary negative groups >= 3 and paired-shadow negative groups == 0",
            "failure_rule": "any paired-shadow control group remains negative",
            "compute_budget": "bounded to frozen replication corpora and existing preset families",
        },
        {
            "ablation_id": "dictionary-size-equalization",
            "status": "required",
            "parallel_group": "compute-economics",
            "current_result": "failed" if generic_failure else "passed",
            "current_evidence": (
                f"generic public token dictionary has {audit_summary['generic_ordinary_negative_groups']} "
                "ordinary negative groups."
            ),
            "rerun_design": (
                "Compare standards dictionaries against entry-count, byte-count, and "
                "frequency-matched generic public dictionaries."
            ),
            "success_rule": "standards preset keeps >=3 ordinary groups and beats every matched generic baseline",
            "failure_rule": "matched generic baselines reproduce the same negative groups",
            "compute_budget": "reuse existing target spans; no broad seed search",
        },
        {
            "ablation_id": "project-token-removal",
            "status": "required",
            "parallel_group": "corpus-transform",
            "current_result": "watch",
            "current_evidence": (
                f"project-token hit share is {audit_summary['standards_project_token_hit_share']}; "
                f"leakage_dominates={audit_summary['leakage_dominates']}."
            ),
            "rerun_design": (
                "Remove Telomere/project-specific entries from standards presets and rerun "
                "ordinary plus paired-shadow rows."
            ),
            "success_rule": "ordinary/control separation improves or remains clean after token removal",
            "failure_rule": "ordinary wins collapse or controls remain negative",
            "compute_budget": "bounded dictionary-filter rerun only",
        },
        {
            "ablation_id": "leave-family-out",
            "status": "required",
            "parallel_group": "format-policy",
            "current_result": "not-yet-run",
            "current_evidence": (
                "existing rows use public family presets; leave-family-out registry semantics "
                "are not yet proven."
            ),
            "rerun_design": (
                "Pre-register decoder-public family identity and forbid entries derived "
                "from the compressed family in held-out tests."
            ),
            "success_rule": "held-out wins survive without same-family leakage",
            "failure_rule": "wins require family entries that would be equivalent to training on the target family",
            "compute_budget": "registry-design artifact before implementation",
        },
        {
            "ablation_id": "control-density-normalization",
            "status": "read-only-current",
            "parallel_group": "compute-economics",
            "current_result": "failed" if density_ratio < 2.0 else "promising",
            "current_evidence": (
                f"ordinary mean savings/KiB={ordinary['mean_savings_bytes_per_kib']}; "
                f"paired-shadow mean savings/KiB={shadow['mean_savings_bytes_per_kib']}; "
                f"ratio={density_ratio}."
            ),
            "rerun_design": (
                "Normalize every future public-preset row by input bytes, dictionary entries, "
                "metadata bytes, selected spans, and selected covered bytes."
            ),
            "success_rule": "ordinary/control savings density ratio >= 2.0 and control groups == 0",
            "failure_rule": "control density is comparable to ordinary density",
            "compute_budget": "read-only analysis over existing rows first",
        },
    ]


def build_report() -> dict[str, Any]:
    inputs = {
        key.removesuffix("_sha256"): load_json(path)
        for key, path in SOURCE_PATHS.items()
    }
    audit = inputs["public_preset_control_audit"]
    gate = inputs["public_preset_promotion_gate"]
    replication = inputs["schema_native_public_dictionary_replication"]
    densities = density_rows(replication)
    density_summary = aggregate_by_kind(densities)
    ablations = ablation_rows(audit, density_summary)
    failed_count = sum(1 for row in ablations if row["current_result"] == "failed")
    required_count = sum(1 for row in ablations if row["status"] == "required")
    shadow_rows = [
        row for row in densities if row["control_kind"] == "paired-shadow-control"
    ]
    ordinary_rows = [
        row for row in densities if row["control_kind"] == "ordinary-structured"
    ]

    return {
        "generated_by": GENERATED_BY,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "scope": {
            "kind": "public preset control ablation manifest",
            "performs_seed_search": False,
            "launches_agents": False,
            "makes_compression_claim": False,
            "is_format_support": False,
            "is_natural_corpus_proof": False,
            "overrides_public_preset_gate": False,
        },
        "source_hashes": source_hashes(),
        "summary": {
            "ablation_count": len(ablations),
            "required_ablation_count": required_count,
            "failed_current_ablation_count": failed_count,
            "paired_shadow_row_count": len(shadow_rows),
            "ordinary_row_count": len(ordinary_rows),
            "paired_shadow_negative_row_count": sum(1 for row in shadow_rows if row["negative"]),
            "ordinary_negative_row_count": sum(1 for row in ordinary_rows if row["negative"]),
            "public_preset_promotion_met": summary(gate)["promotion_met"],
            "control_audit_status": summary(audit)["audit_status"],
            "next_status": "run_bounded_ablation_generator_before_promotion",
            "claim_boundary": (
                "No Seed Search; ablation manifest only; not public preset promotion; "
                "not `.tlmr` format support; not natural-corpus proof."
            ),
            "conclusion": (
                "Public preset controls need paired-shadow expansion, dictionary-size "
                "equalization, project-token removal, leave-family-out policy, and "
                "density normalization before promotion can reopen."
            ),
        },
        "density_summary": density_summary,
        "ablation_plan": ablations,
        "row_density_samples": [
            row
            for row in sorted(densities, key=lambda item: item["delta_bytes"])[:12]
        ],
        "dispatch_briefs": [
            {
                "parallel_group": "corpus-transform",
                "scope": "paired-shadow-expansion and project-token-removal",
                "output_contract": "return a generated artifact proposal and exact check command; no broad seed search",
            },
            {
                "parallel_group": "compute-economics",
                "scope": "dictionary-size-equalization and control-density-normalization",
                "output_contract": "report ordinary/control density deltas and metadata budgets",
            },
            {
                "parallel_group": "format-policy",
                "scope": "leave-family-out preset registry rules",
                "output_contract": "draft registry constraints only if gates pass; do not change .tlmr",
            },
        ],
    }


def write_report(payload: dict[str, Any]) -> None:
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary_payload = payload["summary"]
    lines = [
        "# Public Preset Control Ablation",
        "",
        f"Generated by `{GENERATED_BY}` from the control audit and schema replication rows.",
        "This is a No Seed Search ablation manifest. It performs no seed search, launches no agents, is not public preset promotion, is not `.tlmr` format support, is not natural-corpus proof, and is not a compression claim.",
        "",
        "## Summary",
        "",
        f"- Ablations: `{summary_payload['ablation_count']}`",
        f"- Required ablations: `{summary_payload['required_ablation_count']}`",
        f"- Failed current ablations: `{summary_payload['failed_current_ablation_count']}`",
        f"- Ordinary rows: `{summary_payload['ordinary_row_count']}`",
        f"- Ordinary negative rows: `{summary_payload['ordinary_negative_row_count']}`",
        f"- Paired-shadow rows: `{summary_payload['paired_shadow_row_count']}`",
        f"- Paired-shadow negative rows: `{summary_payload['paired_shadow_negative_row_count']}`",
        f"- Public preset promotion met: `{summary_payload['public_preset_promotion_met']}`",
        f"- Control audit status: `{summary_payload['control_audit_status']}`",
        f"- Next status: `{summary_payload['next_status']}`",
        "",
        summary_payload["conclusion"],
        "",
        "## Ablation Matrix",
        "",
        "| ablation | status | result | group | current evidence | success rule | failure rule |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in payload["ablation_plan"]:
        lines.append(
            f"| `{cell(row['ablation_id'])}` | `{cell(row['status'])}` | "
            f"`{cell(row['current_result'])}` | `{cell(row['parallel_group'])}` | "
            f"{cell(row['current_evidence'])} | {cell(row['success_rule'])} | "
            f"{cell(row['failure_rule'])} |"
        )

    lines.extend(["", "## Density Summary", ""])
    lines.extend(
        [
            "| kind | rows | negative rows | negative groups | mean selected/KiB | mean savings/KiB | best case | best delta |",
            "| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: |",
        ]
    )
    for row in payload["density_summary"]:
        lines.append(
            f"| `{cell(row['control_kind'])}` | {row['row_count']} | "
            f"{row['negative_row_count']} | {row['negative_group_count']} | "
            f"{row['mean_selected_spans_per_kib']} | {row['mean_savings_bytes_per_kib']} | "
            f"`{cell(row['best_case'])}` | {row['best_delta_bytes']} |"
        )

    lines.extend(["", "## Strongest Row Samples", ""])
    lines.extend(
        [
            "| row | kind | group | delta | selected/KiB | savings/KiB | project-token hits/KiB |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in payload["row_density_samples"]:
        lines.append(
            f"| `{cell(row['name'])}` | `{cell(row['control_kind'])}` | "
            f"`{cell(row['independence_group'])}` | {row['delta_bytes']} | "
            f"{row['selected_spans_per_kib']} | {row['savings_bytes_per_kib']} | "
            f"{row['project_token_hits_per_kib']} |"
        )

    lines.extend(["", "## dispatching-parallel-agents Briefs", ""])
    for brief in payload["dispatch_briefs"]:
        lines.extend(
            [
                f"### {brief['parallel_group']}",
                "",
                f"- Scope: {brief['scope']}",
                f"- Output contract: {brief['output_contract']}",
                "",
            ]
        )

    lines.extend(
        [
            "## Source Artifacts",
            "",
            "The JSON `source_hashes` map pins this manifest to the exact upstream evidence files below.",
        ]
    )
    for name, digest in payload["source_hashes"].items():
        lines.append(f"- `{name}`: `{digest}`")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not REPORT_JSON.exists() or not REPORT_MD.exists():
        raise SystemExit("generated public preset control ablation files are missing")
    payload = load_json(REPORT_JSON)
    if payload.get("generated_by") != GENERATED_BY:
        raise SystemExit("public_preset_control_ablation.json has wrong generated_by marker")
    if payload.get("source_hashes") != source_hashes():
        raise SystemExit("public_preset_control_ablation.json source hashes are stale")
    expected = stable_projection(build_report())
    current = stable_projection(payload)
    if current != expected:
        raise SystemExit("public_preset_control_ablation.json is stale; regenerate it")
    scope = payload.get("scope", {})
    for field in (
        "performs_seed_search",
        "launches_agents",
        "makes_compression_claim",
        "is_format_support",
        "is_natural_corpus_proof",
        "overrides_public_preset_gate",
    ):
        if scope.get(field) is not False:
            raise SystemExit(f"public preset control ablation scope field must be false: {field}")
    summary_payload = payload["summary"]
    if summary_payload["public_preset_promotion_met"]:
        raise SystemExit("public preset control ablation cannot promote the preset")
    if summary_payload["paired_shadow_negative_row_count"] <= 0:
        raise SystemExit("public preset control ablation lost paired-shadow failure")
    ablation_ids = {row["ablation_id"] for row in payload["ablation_plan"]}
    for required in (
        "paired-shadow-expansion",
        "dictionary-size-equalization",
        "project-token-removal",
        "leave-family-out",
        "control-density-normalization",
    ):
        if required not in ablation_ids:
            raise SystemExit(f"public preset control ablation missing {required}")
    text = REPORT_MD.read_text(encoding="utf-8")
    for phrase in (
        "Public Preset Control Ablation",
        "No Seed Search",
        "not `.tlmr` format support",
        "not natural-corpus proof",
        "Ablation Matrix",
        "Density Summary",
        "paired-shadow-expansion",
        "dispatching-parallel-agents Briefs",
        "source_hashes",
    ):
        if phrase not in text:
            raise SystemExit(f"PUBLIC_PRESET_CONTROL_ABLATION.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="validate generated public preset ablation"
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
