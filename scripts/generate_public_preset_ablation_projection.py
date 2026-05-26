#!/usr/bin/env python3
"""Generate read-only public-preset ablation projections.

This artifact does not rerun seed search. It projects how existing standards
public-preset rows would behave if selected project/common entries or
same-family entries were removed, and compares standards rows to generic public
token baselines.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
REPORT_JSON = DOCS / "public_preset_ablation_projection.json"
REPORT_MD = DOCS / "PUBLIC_PRESET_ABLATION_PROJECTION.md"
GENERATED_BY = "scripts/generate_public_preset_ablation_projection.py"

SOURCE_PATHS = {
    "public_preset_control_ablation_sha256": DOCS / "public_preset_control_ablation.json",
    "public_preset_control_audit_sha256": DOCS / "public_preset_control_audit.json",
    "public_preset_promotion_gate_sha256": DOCS / "public_preset_promotion_gate.json",
    "schema_native_public_dictionary_replication_sha256": DOCS
    / "schema_native_public_dictionary_replication.json",
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


def generic_by_name(replication: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        row["name"]: row
        for row in replication["rows"]
        if row["mode"] == "generic-public-token-dictionary-v1"
    }


def average_net_savings(row: dict[str, Any]) -> float:
    if row["selected_span_count"] <= 0 or row["delta_bytes"] >= 0:
        return 0.0
    return -float(row["delta_bytes"]) / float(row["selected_span_count"])


def adjusted_delta(row: dict[str, Any], removed_hits: int) -> int:
    return int(round(row["delta_bytes"] + removed_hits * average_net_savings(row)))


def projection_rows(replication: dict[str, Any]) -> list[dict[str, Any]]:
    generic = generic_by_name(replication)
    rows = []
    for row in standards_rows(replication):
        counts = row.get("selected_entry_family_counts", {})
        project_hits = int(row.get("telomere_project_token_hits", 0))
        same_family_hits = int(counts.get(row["schema_family"], 0))
        non_common_hits = sum(
            int(value) for key, value in counts.items() if key != "common"
        )
        generic_delta = int(generic.get(row["name"], {}).get("delta_bytes", 0))
        generic_selected = int(generic.get(row["name"], {}).get("selected_span_count", 0))
        project_adjusted = adjusted_delta(row, project_hits)
        family_adjusted = adjusted_delta(row, same_family_hits)
        non_common_adjusted = adjusted_delta(row, non_common_hits)
        rows.append(
            {
                "name": row["name"],
                "control_kind": row["control_kind"],
                "independence_group": row["independence_group"],
                "schema_family": row["schema_family"],
                "input_bytes": row["input_bytes"],
                "delta_bytes": row["delta_bytes"],
                "original_negative": row["delta_bytes"] < 0,
                "selected_span_count": row["selected_span_count"],
                "selected_covered_bytes": row["selected_covered_bytes"],
                "project_token_hits": project_hits,
                "same_family_hits": same_family_hits,
                "non_common_hits": non_common_hits,
                "generic_delta_bytes": generic_delta,
                "generic_selected_span_count": generic_selected,
                "standards_incremental_delta_vs_generic": row["delta_bytes"] - generic_delta,
                "average_net_savings_per_span": round(average_net_savings(row), 6),
                "project_token_removed_delta_projection": project_adjusted,
                "project_token_removed_negative": project_adjusted < 0,
                "same_family_removed_delta_projection": family_adjusted,
                "same_family_removed_negative": family_adjusted < 0,
                "non_common_removed_delta_projection": non_common_adjusted,
                "non_common_removed_negative": non_common_adjusted < 0,
                "projection_note": (
                    "Read-only proportional projection from existing selected spans; "
                    "not exact decode proof."
                ),
            }
        )
    return rows


def group_counts(rows: list[dict[str, Any]], field: str) -> dict[str, int]:
    groups: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        if row[field]:
            groups[row["control_kind"]].add(row["independence_group"])
    return {key: len(value) for key, value in sorted(groups.items())}


def count_negative(rows: list[dict[str, Any]], field: str) -> int:
    return sum(1 for row in rows if row[field])


def build_report() -> dict[str, Any]:
    inputs = {
        key.removesuffix("_sha256"): load_json(path)
        for key, path in SOURCE_PATHS.items()
    }
    gate = summary(inputs["public_preset_promotion_gate"])
    ablation = summary(inputs["public_preset_control_ablation"])
    replication = inputs["schema_native_public_dictionary_replication"]
    rows = projection_rows(replication)
    negative_rows = [row for row in rows if row["delta_bytes"] < 0]
    ordinary_rows = [row for row in rows if row["control_kind"] == "ordinary-structured"]
    control_rows = [row for row in rows if "control" in row["control_kind"]]
    generic_explained = [
        row for row in rows if row["generic_delta_bytes"] < 0 and row["delta_bytes"] < 0
    ]
    project_survivors = [
        row
        for row in ordinary_rows
        if row["project_token_removed_negative"]
    ]
    family_survivors = [
        row
        for row in ordinary_rows
        if row["same_family_removed_negative"]
    ]
    control_family_survivors = [
        row
        for row in control_rows
        if row["same_family_removed_negative"]
    ]

    return {
        "generated_by": GENERATED_BY,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "scope": {
            "kind": "public preset ablation projection",
            "performs_seed_search": False,
            "launches_agents": False,
            "makes_compression_claim": False,
            "is_decode_proof": False,
            "is_format_support": False,
            "is_natural_corpus_proof": False,
            "overrides_public_preset_gate": False,
        },
        "source_hashes": source_hashes(),
        "summary": {
            "projection_status": "read_only_projection_not_decode_proof",
            "row_count": len(rows),
            "negative_row_count": len(negative_rows),
            "ordinary_row_count": len(ordinary_rows),
            "control_row_count": len(control_rows),
            "project_token_removed_ordinary_negative_rows": len(project_survivors),
            "project_token_removed_ordinary_negative_groups": len(
                {row["independence_group"] for row in project_survivors}
            ),
            "same_family_removed_ordinary_negative_rows": len(family_survivors),
            "same_family_removed_ordinary_negative_groups": len(
                {row["independence_group"] for row in family_survivors}
            ),
            "same_family_removed_control_negative_rows": len(control_family_survivors),
            "same_family_removed_control_negative_groups": len(
                {row["independence_group"] for row in control_family_survivors}
            ),
            "generic_explained_negative_rows": len(generic_explained),
            "generic_explained_negative_groups": len(
                {row["independence_group"] for row in generic_explained}
            ),
            "public_preset_promotion_met": gate["promotion_met"],
            "control_ablation_failed_current_count": ablation[
                "failed_current_ablation_count"
            ],
            "next_required_artifact": "docs/PUBLIC_PRESET_CONTROL_RERUN.md",
            "claim_boundary": (
                "No Seed Search; proportional projection only; not exact decode proof; "
                "not public preset promotion; not `.tlmr` support."
            ),
            "conclusion": (
                "Existing rows suggest project/common-token removal may leave several "
                "ordinary wins, and proportional same-family removal would clear the "
                "current paired-shadow controls while preserving ordinary projected "
                "wins. This is a strong reason to run an exact bounded rerun, not a "
                "promotion claim."
            ),
        },
        "negative_group_counts": {
            "original": group_counts(rows, "original_negative"),
            "project_token_removed": group_counts(rows, "project_token_removed_negative"),
            "same_family_removed": group_counts(rows, "same_family_removed_negative"),
            "non_common_removed": group_counts(rows, "non_common_removed_negative"),
        },
        "projection_rows": rows,
        "rerun_requirements": [
            {
                "requirement_id": "exact-project-token-removal-rerun",
                "parallel_group": "corpus-transform",
                "why": "projection is not decode proof and project/common tokens may explain part of the signal",
                "success_rule": "exact rerun keeps ordinary negative groups >=3 and paired-shadow groups ==0",
            },
            {
                "requirement_id": "exact-leave-family-out-rerun",
                "parallel_group": "format-policy",
                "why": "same-family projection appears to clear current controls, but it is not exact decode proof",
                "success_rule": "held-out ordinary wins survive with decoder-public leave-family-out registry rules",
            },
            {
                "requirement_id": "matched-generic-rerun",
                "parallel_group": "compute-economics",
                "why": "generic token dictionaries already explain two negative ordinary groups",
                "success_rule": "standards preset beats entry-count, byte-count, and frequency-matched generic baselines",
            },
        ],
    }


def write_report(payload: dict[str, Any]) -> None:
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary_payload = payload["summary"]
    lines = [
        "# Public Preset Ablation Projection",
        "",
        f"Generated by `{GENERATED_BY}` from the public-preset control ablation and schema replication rows.",
        "This is a No Seed Search projection. It performs no seed search, launches no agents, is not exact decode proof, is not public preset promotion, is not `.tlmr` format support, and is not natural-corpus proof.",
        "",
        "## Summary",
        "",
        f"- Projection status: `{summary_payload['projection_status']}`",
        f"- Rows: `{summary_payload['row_count']}`",
        f"- Original negative rows: `{summary_payload['negative_row_count']}`",
        f"- Project-token removed ordinary negative rows: `{summary_payload['project_token_removed_ordinary_negative_rows']}`",
        f"- Project-token removed ordinary negative groups: `{summary_payload['project_token_removed_ordinary_negative_groups']}`",
        f"- Same-family removed ordinary negative rows: `{summary_payload['same_family_removed_ordinary_negative_rows']}`",
        f"- Same-family removed ordinary negative groups: `{summary_payload['same_family_removed_ordinary_negative_groups']}`",
        f"- Same-family removed control negative rows: `{summary_payload['same_family_removed_control_negative_rows']}`",
        f"- Generic-explained negative rows: `{summary_payload['generic_explained_negative_rows']}`",
        f"- Public preset promotion met: `{summary_payload['public_preset_promotion_met']}`",
        "",
        summary_payload["conclusion"],
        "",
        "## Projection Rows",
        "",
        "| row | kind | group | delta | project-removed | same-family-removed | generic delta | avg savings/span |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in sorted(payload["projection_rows"], key=lambda item: item["delta_bytes"]):
        lines.append(
            f"| `{cell(row['name'])}` | `{cell(row['control_kind'])}` | "
            f"`{cell(row['independence_group'])}` | {row['delta_bytes']} | "
            f"{row['project_token_removed_delta_projection']} | "
            f"{row['same_family_removed_delta_projection']} | "
            f"{row['generic_delta_bytes']} | {row['average_net_savings_per_span']} |"
        )

    lines.extend(["", "## Rerun Requirements", ""])
    lines.extend(
        [
            "| requirement | group | why | success rule |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in payload["rerun_requirements"]:
        lines.append(
            f"| `{cell(item['requirement_id'])}` | `{cell(item['parallel_group'])}` | "
            f"{cell(item['why'])} | {cell(item['success_rule'])} |"
        )

    lines.extend(
        [
            "",
            "## dispatching-parallel-agents Brief",
            "",
            "- `corpus-transform`: convert project/common-token projection into an exact bounded rerun.",
            "- `format-policy`: define leave-family-out registry constraints before any `.tlmr` work.",
            "- `compute-economics`: compare standards gains against matched generic dictionaries.",
            "",
            "## Source Artifacts",
            "",
            "The JSON `source_hashes` map pins this projection to the exact upstream evidence files below.",
        ]
    )
    for name, digest in payload["source_hashes"].items():
        lines.append(f"- `{name}`: `{digest}`")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not REPORT_JSON.exists() or not REPORT_MD.exists():
        raise SystemExit("generated public preset ablation projection files are missing")
    payload = load_json(REPORT_JSON)
    if payload.get("generated_by") != GENERATED_BY:
        raise SystemExit("public_preset_ablation_projection.json has wrong generated_by marker")
    if payload.get("source_hashes") != source_hashes():
        raise SystemExit("public_preset_ablation_projection.json source hashes are stale")
    expected = stable_projection(build_report())
    current = stable_projection(payload)
    if current != expected:
        raise SystemExit("public_preset_ablation_projection.json is stale; regenerate it")
    scope = payload.get("scope", {})
    for field in (
        "performs_seed_search",
        "launches_agents",
        "makes_compression_claim",
        "is_decode_proof",
        "is_format_support",
        "is_natural_corpus_proof",
        "overrides_public_preset_gate",
    ):
        if scope.get(field) is not False:
            raise SystemExit(f"public preset ablation projection scope field must be false: {field}")
    summary_payload = payload["summary"]
    if summary_payload["public_preset_promotion_met"]:
        raise SystemExit("public preset ablation projection cannot promote the preset")
    if summary_payload["projection_status"] != "read_only_projection_not_decode_proof":
        raise SystemExit("public preset ablation projection must remain read-only")
    if summary_payload["same_family_removed_control_negative_groups"] != 0:
        raise SystemExit("projection should clear current paired-shadow controls")
    if summary_payload["same_family_removed_ordinary_negative_groups"] < 3:
        raise SystemExit("projection should leave enough ordinary groups to justify exact rerun")
    text = REPORT_MD.read_text(encoding="utf-8")
    for phrase in (
        "Public Preset Ablation Projection",
        "No Seed Search",
        "not exact decode proof",
        "not `.tlmr` format support",
        "Projection Rows",
        "Rerun Requirements",
        "dispatching-parallel-agents Brief",
        "source_hashes",
    ):
        if phrase not in text:
            raise SystemExit(f"PUBLIC_PRESET_ABLATION_PROJECTION.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="validate generated public preset projection"
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
