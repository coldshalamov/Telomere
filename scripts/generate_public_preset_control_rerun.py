#!/usr/bin/env python3
"""Generate the exact bounded public-preset control rerun.

This artifact resolves the read-only projection by rerunning the frozen schema
replication corpus bank with filtered public-preset variants. It performs no
broad seed search: candidates are exact byte-entry matches from decoder-public
dictionary entries, then weighted interval selection is applied as in the
upstream replication generator.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import generate_schema_native_public_dictionaries as schema_native
import generate_schema_native_public_dictionary_replication as replication


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
REPORT_JSON = DOCS / "public_preset_control_rerun.json"
REPORT_MD = DOCS / "PUBLIC_PRESET_CONTROL_RERUN.md"
GENERATED_BY = "scripts/generate_public_preset_control_rerun.py"

SOURCE_PATHS = {
    "public_preset_ablation_projection_sha256": DOCS
    / "public_preset_ablation_projection.json",
    "public_preset_control_ablation_sha256": DOCS / "public_preset_control_ablation.json",
    "public_preset_control_audit_sha256": DOCS / "public_preset_control_audit.json",
    "public_preset_promotion_gate_sha256": DOCS / "public_preset_promotion_gate.json",
    "schema_native_public_dictionary_replication_sha256": DOCS
    / "schema_native_public_dictionary_replication.json",
    "schema_native_replication_generator_sha256": ROOT
    / "scripts"
    / "generate_schema_native_public_dictionary_replication.py",
    "schema_native_dictionary_generator_sha256": ROOT
    / "scripts"
    / "generate_schema_native_public_dictionaries.py",
}

CONTROL_KINDS = {
    "binary-control",
    "negative-control",
    "paired-shadow-control",
}

VARIANTS = [
    {
        "variant_id": "standards-baseline",
        "description": "Recompute standards-public-v1 as the exact baseline.",
        "parallel_group": "corpus-transform",
        "success_rule": "reference only; expected to preserve the current control failure",
    },
    {
        "variant_id": "standards-no-project-tokens",
        "description": "Remove entries containing Telomere/project-specific leakage tokens.",
        "parallel_group": "corpus-transform",
        "success_rule": "ordinary negative groups >=3, control negative groups ==0, and project-token hits ==0",
    },
    {
        "variant_id": "standards-no-common-entries",
        "description": "Remove every common-family entry and keep target-family standards entries.",
        "parallel_group": "corpus-transform",
        "success_rule": "ordinary negative groups >=3 and control negative groups ==0",
    },
    {
        "variant_id": "standards-family-only-no-project",
        "description": "Keep target-family standards entries but remove project-token entries and common entries.",
        "parallel_group": "corpus-transform",
        "success_rule": "ordinary negative groups >=3, control negative groups ==0, and project-token hits ==0",
    },
    {
        "variant_id": "standards-leave-family-out",
        "description": "Use common entries plus all standards families except the compressed corpus family.",
        "parallel_group": "format-policy",
        "success_rule": "ordinary negative groups >=3 and control negative groups ==0",
    },
    {
        "variant_id": "standards-leave-family-out-no-project",
        "description": "Leave the compressed family out and also remove every project-token entry.",
        "parallel_group": "format-policy",
        "success_rule": "ordinary negative groups >=3, control negative groups ==0, and project-token hits ==0",
    },
    {
        "variant_id": "generic-common-baseline",
        "description": "Recompute the generic common-token baseline for matched-control context.",
        "parallel_group": "compute-economics",
        "success_rule": "reference only; standards variants must beat this baseline before promotion",
    },
]


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


def unseeded_standards_entries(corpus: dict[str, Any]) -> list[dict[str, Any]]:
    return replication.entries_for_family(corpus["schema_family"], include_common=True)


def is_project_entry(item: dict[str, Any]) -> bool:
    value = bytes.fromhex(item["value_hex"]).lower()
    return any(token in value for token in replication.PROJECT_LEAKAGE_TOKENS)


def variant_unseeded_entries(corpus: dict[str, Any], variant_id: str) -> list[dict[str, Any]]:
    family = corpus["schema_family"]
    if variant_id == "standards-baseline":
        return unseeded_standards_entries(corpus)
    if variant_id == "standards-no-project-tokens":
        return [
            item
            for item in unseeded_standards_entries(corpus)
            if not is_project_entry(item)
        ]
    if variant_id == "standards-no-common-entries":
        return [
            item
            for item in unseeded_standards_entries(corpus)
            if "common" not in item["families"]
        ]
    if variant_id == "standards-family-only-no-project":
        return [
            item
            for item in replication.entries_for_family(family, include_common=False)
            if not is_project_entry(item)
        ]
    if variant_id == "standards-leave-family-out":
        entries = list(replication.common_entries())
        entries.extend(
            item
            for item in replication.standards_entries()
            if family not in item["families"]
        )
        return entries
    if variant_id == "standards-leave-family-out-no-project":
        entries = list(replication.common_entries())
        entries.extend(
            item
            for item in replication.standards_entries()
            if family not in item["families"]
        )
        return [item for item in entries if not is_project_entry(item)]
    if variant_id == "generic-common-baseline":
        return replication.common_entries()
    raise ValueError(variant_id)


def variant_entries(corpus: dict[str, Any], variant_id: str) -> list[dict[str, Any]]:
    return schema_native.with_seed_slots(variant_unseeded_entries(corpus, variant_id))


def variant_preset_id(corpus: dict[str, Any], variant_id: str) -> str:
    family = corpus["schema_family"]
    if variant_id.startswith("standards-leave-family-out"):
        return f"{variant_id}:not-{family}"
    return f"{variant_id}:{family}"


def analyze_row(corpus: dict[str, Any], variant: dict[str, Any]) -> dict[str, Any]:
    variant_id = variant["variant_id"]
    data = replication.corpus_bytes(corpus)
    entries = variant_entries(corpus, variant_id)
    candidates = schema_native.find_candidates(data, entries)
    span_metrics = schema_native.target_span_metrics(data, entries)
    selected = schema_native.weighted_selection(candidates)
    selected_record_bytes = sum(row["encoded_len"] for row in selected)
    literal_bytes = schema_native.literal_record_bytes(len(data), selected)
    metadata_bytes = (
        schema_native.V2_HEADER_AND_LAYER_BYTES
        + schema_native.PRESET_SELECTOR_BYTES
        + schema_native.PRESET_VERSION_BYTES
        if selected
        else 0
    )
    encoded_bytes = (
        len(data)
        if not selected
        else literal_bytes + selected_record_bytes + metadata_bytes
    )
    delta_bytes = encoded_bytes - len(data)
    project_hits, leakage_flags = replication.leakage_audit(entries, selected)
    return {
        **corpus,
        "row_id": f"{variant_id}:{corpus['name']}",
        "variant_id": variant_id,
        "preset_id": variant_preset_id(corpus, variant_id),
        "input_bytes": len(data),
        "input_sha256": hashlib.sha256(data).hexdigest(),
        "dictionary_entry_count": len(entries),
        **span_metrics,
        "candidate_hits": len(candidates),
        "positive_exact_hit_count": sum(
            1 for row in candidates if row["savings_bytes"] > 0
        ),
        "selected_span_count": len(selected),
        "selected_covered_bytes": sum(row["span_len"] for row in selected),
        "literal_record_bytes": literal_bytes if selected else 0,
        "selected_record_bytes": selected_record_bytes,
        "metadata_bytes": metadata_bytes,
        "encoded_bytes": encoded_bytes,
        "delta_bytes": delta_bytes,
        "net_with_metadata_bytes": delta_bytes,
        "delta_pct": round(delta_bytes / len(data) * 100, 4) if data else 0.0,
        "exact_decode": schema_native.prove_decode(data, entries, selected),
        "corrupt_rejection": schema_native.corrupt_rejection_verified(
            entries, selected
        ),
        "selected_span_sample": selected[: schema_native.SELECTED_SAMPLE_LIMIT],
        "selected_entry_family_counts": replication.selected_entry_family_counts(
            entries, selected
        ),
        "telomere_project_token_hits": project_hits,
        "leakage_flags": leakage_flags,
    }


def build_rows() -> list[dict[str, Any]]:
    corpora = replication.replication_corpus_manifest()
    rows = []
    for variant in VARIANTS:
        rows.extend(analyze_row(corpus, variant) for corpus in corpora)
    return rows


def negative_groups(rows: list[dict[str, Any]], *, controls: bool) -> set[str]:
    groups = set()
    for row in rows:
        if row["delta_bytes"] >= 0:
            continue
        is_control = row["control_kind"] in CONTROL_KINDS
        if is_control == controls:
            if not controls and not row["promotion_eligible"]:
                continue
            groups.add(row["independence_group"])
    return groups


def variant_status(
    variant_id: str,
    ordinary_group_count: int,
    control_group_count: int,
    project_token_hits: int,
    all_decode: bool,
    all_corrupt: bool,
) -> str:
    if not all_decode or not all_corrupt:
        return "failed_decode_or_corrupt_proof"
    if variant_id in {"standards-baseline", "generic-common-baseline"}:
        return "reference_only"
    if control_group_count > 0:
        return "failed_control_gate"
    if ordinary_group_count < replication.PROMOTION_ORDINARY_GROUPS:
        return "failed_promotion_floor"
    if variant_id.endswith("no-project") or "no-project" in variant_id:
        if project_token_hits > 0:
            return "failed_project_token_removal"
    return "qualified_for_followup"


def summarize_variant(variant: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    variant_rows = [row for row in rows if row["variant_id"] == variant["variant_id"]]
    ordinary = negative_groups(variant_rows, controls=False)
    controls = negative_groups(variant_rows, controls=True)
    best = min(variant_rows, key=lambda row: row["delta_bytes"])
    all_decode = all(row["exact_decode"] for row in variant_rows)
    all_corrupt = all(row["corrupt_rejection"] for row in variant_rows)
    project_hits = sum(row["telomere_project_token_hits"] for row in variant_rows)
    status = variant_status(
        variant["variant_id"],
        len(ordinary),
        len(controls),
        project_hits,
        all_decode,
        all_corrupt,
    )
    return {
        "variant_id": variant["variant_id"],
        "description": variant["description"],
        "parallel_group": variant["parallel_group"],
        "success_rule": variant["success_rule"],
        "status": status,
        "row_count": len(variant_rows),
        "negative_row_count": sum(1 for row in variant_rows if row["delta_bytes"] < 0),
        "ordinary_negative_group_count": len(ordinary),
        "ordinary_negative_group_names": sorted(ordinary),
        "control_negative_group_count": len(controls),
        "control_negative_group_names": sorted(controls),
        "selected_span_count": sum(row["selected_span_count"] for row in variant_rows),
        "project_token_hits": project_hits,
        "all_exact_decode": all_decode,
        "all_corrupt_rejections": all_corrupt,
        "best_case": best["name"],
        "best_delta_bytes": best["delta_bytes"],
        "mean_dictionary_entry_count": round(
            sum(row["dictionary_entry_count"] for row in variant_rows)
            / max(1, len(variant_rows)),
            6,
        ),
    }


def group_summary_by_variant(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [summarize_variant(variant, rows) for variant in VARIANTS]


def rows_by_variant(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["variant_id"]].append(row)
    return dict(grouped)


def best_negative_rows(rows: list[dict[str, Any]], limit: int = 18) -> list[dict[str, Any]]:
    return sorted(
        [row for row in rows if row["delta_bytes"] < 0],
        key=lambda row: (
            row["delta_bytes"],
            row["variant_id"],
            row["name"],
        ),
    )[:limit]


def source_inputs() -> dict[str, dict[str, Any]]:
    return {
        key.removesuffix("_sha256"): load_json(path)
        for key, path in SOURCE_PATHS.items()
        if path.suffix == ".json"
    }


def build_report() -> dict[str, Any]:
    inputs = source_inputs()
    projection = summary(inputs["public_preset_ablation_projection"])
    gate = summary(inputs["public_preset_promotion_gate"])
    rows = build_rows()
    variants = group_summary_by_variant(rows)
    by_variant = {row["variant_id"]: row for row in variants}
    no_project = by_variant["standards-no-project-tokens"]
    leave_family_out = by_variant["standards-leave-family-out"]
    leave_family_out_no_project = by_variant["standards-leave-family-out-no-project"]

    public_preset_promotion_met = any(
        row["status"] == "qualified_for_followup" for row in variants
    )
    projection_resolved = (
        no_project["control_negative_group_count"] > 0
        and leave_family_out["ordinary_negative_group_count"]
        < replication.PROMOTION_ORDINARY_GROUPS
        and leave_family_out_no_project["ordinary_negative_group_count"] == 0
    )

    return {
        "generated_by": GENERATED_BY,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "scope": {
            "kind": "exact bounded public preset control rerun",
            "performs_seed_search": False,
            "performs_exact_dictionary_rerun": True,
            "launches_agents": False,
            "makes_compression_claim": False,
            "is_format_support": False,
            "is_natural_corpus_proof": False,
            "overrides_public_preset_gate": False,
        },
        "source_hashes": source_hashes(),
        "summary": {
            "rerun_status": "exact_rerun_blocks_public_preset_promotion",
            "variant_count": len(VARIANTS),
            "row_count": len(rows),
            "projection_same_family_removed_ordinary_negative_groups": projection[
                "same_family_removed_ordinary_negative_groups"
            ],
            "projection_same_family_removed_control_negative_groups": projection[
                "same_family_removed_control_negative_groups"
            ],
            "no_project_ordinary_negative_groups": no_project[
                "ordinary_negative_group_count"
            ],
            "no_project_control_negative_groups": no_project[
                "control_negative_group_count"
            ],
            "leave_family_out_ordinary_negative_groups": leave_family_out[
                "ordinary_negative_group_count"
            ],
            "leave_family_out_control_negative_groups": leave_family_out[
                "control_negative_group_count"
            ],
            "leave_family_out_no_project_ordinary_negative_groups": leave_family_out_no_project[
                "ordinary_negative_group_count"
            ],
            "leave_family_out_no_project_control_negative_groups": leave_family_out_no_project[
                "control_negative_group_count"
            ],
            "public_preset_promotion_met": public_preset_promotion_met,
            "upstream_public_preset_promotion_met": gate["promotion_met"],
            "projection_resolved": projection_resolved,
            "next_status": "blocked_until_new_decoder_public_preset_or_external_corpus",
            "claim_boundary": (
                "No Seed Search; exact dictionary rerun only; not public preset "
                "promotion; not `.tlmr` format support; not natural-corpus proof."
            ),
            "conclusion": (
                "The bounded exact rerun blocks promotion: project-token removal "
                "keeps paired-shadow controls negative, leave-family-out clears "
                "controls but falls below the three-group ordinary floor, and "
                "leave-family-out plus project-token removal removes the signal."
            ),
        },
        "variant_summaries": variants,
        "rows_by_variant": rows_by_variant(rows),
        "best_negative_rows": best_negative_rows(rows),
        "decision": {
            "status": "blocked",
            "stop_rules": [
                "Do not promote public preset metadata to `.tlmr`.",
                "Do not describe the projection as decode proof.",
                "Do not claim public dictionary presets prove natural-corpus compression.",
                "Reopen only with a new decoder-public preset design or externally sourced corpus bank that passes the same controls.",
            ],
            "parallel_agent_next_steps": [
                {
                    "parallel_group": "corpus-transform",
                    "task": "Design a non-project vocabulary corpus bank before any further preset wins are counted.",
                },
                {
                    "parallel_group": "format-policy",
                    "task": "Keep preset/version metadata research-only until leave-family-out wins exceed the promotion floor.",
                },
                {
                    "parallel_group": "compute-economics",
                    "task": "Require standards variants to beat generic/common controls under identical metadata charges.",
                },
            ],
        },
    }


def write_report(payload: dict[str, Any]) -> None:
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary_payload = payload["summary"]
    lines = [
        "# Public Preset Control Rerun",
        "",
        f"Generated by `{GENERATED_BY}` from the public-preset projection and schema replication generators.",
        "This is a No Seed Search exact dictionary rerun. It launches no agents, is not a compression claim, is not public preset promotion, is not `.tlmr` format support, and is not natural-corpus proof.",
        "",
        "## Summary",
        "",
        f"- Rerun status: `{summary_payload['rerun_status']}`",
        f"- Variants: `{summary_payload['variant_count']}`",
        f"- Rows: `{summary_payload['row_count']}`",
        f"- Projection same-family ordinary/control groups: `{summary_payload['projection_same_family_removed_ordinary_negative_groups']}` / `{summary_payload['projection_same_family_removed_control_negative_groups']}`",
        f"- Exact no-project ordinary/control groups: `{summary_payload['no_project_ordinary_negative_groups']}` / `{summary_payload['no_project_control_negative_groups']}`",
        f"- Exact leave-family-out ordinary/control groups: `{summary_payload['leave_family_out_ordinary_negative_groups']}` / `{summary_payload['leave_family_out_control_negative_groups']}`",
        f"- Exact leave-family-out plus no-project ordinary/control groups: `{summary_payload['leave_family_out_no_project_ordinary_negative_groups']}` / `{summary_payload['leave_family_out_no_project_control_negative_groups']}`",
        f"- Public preset promotion met: `{summary_payload['public_preset_promotion_met']}`",
        f"- Projection resolved: `{summary_payload['projection_resolved']}`",
        f"- Next status: `{summary_payload['next_status']}`",
        "",
        summary_payload["conclusion"],
        "",
        "## Projection vs Exact Rerun",
        "",
        "| check | ordinary negative groups | control negative groups | interpretation |",
        "| --- | ---: | ---: | --- |",
        (
            "| proportional same-family projection | "
            f"{summary_payload['projection_same_family_removed_ordinary_negative_groups']} | "
            f"{summary_payload['projection_same_family_removed_control_negative_groups']} | "
            "read-only projection; not decode proof |"
        ),
        (
            "| exact no-project rerun | "
            f"{summary_payload['no_project_ordinary_negative_groups']} | "
            f"{summary_payload['no_project_control_negative_groups']} | "
            "signal remains, but paired-shadow controls still fail |"
        ),
        (
            "| exact leave-family-out rerun | "
            f"{summary_payload['leave_family_out_ordinary_negative_groups']} | "
            f"{summary_payload['leave_family_out_control_negative_groups']} | "
            "controls clear, but ordinary signal falls below the promotion floor |"
        ),
        (
            "| exact leave-family-out plus no-project rerun | "
            f"{summary_payload['leave_family_out_no_project_ordinary_negative_groups']} | "
            f"{summary_payload['leave_family_out_no_project_control_negative_groups']} | "
            "cleanest variant removes the signal |"
        ),
        "",
        "## Variant Gate Summary",
        "",
        "| variant | status | ordinary groups | control groups | selected spans | project-token hits | best case | best delta |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- | ---: |",
    ]
    for row in payload["variant_summaries"]:
        lines.append(
            f"| `{cell(row['variant_id'])}` | `{cell(row['status'])}` | "
            f"{row['ordinary_negative_group_count']} | {row['control_negative_group_count']} | "
            f"{row['selected_span_count']} | {row['project_token_hits']} | "
            f"`{cell(row['best_case'])}` | {row['best_delta_bytes']} |"
        )

    lines.extend(["", "## Strongest Exact Rows", ""])
    lines.extend(
        [
            "| variant | row | kind | group | delta | selected | project hits | decode |",
            "| --- | --- | --- | --- | ---: | ---: | ---: | --- |",
        ]
    )
    for row in payload["best_negative_rows"]:
        lines.append(
            f"| `{cell(row['variant_id'])}` | `{cell(row['name'])}` | "
            f"`{cell(row['control_kind'])}` | `{cell(row['independence_group'])}` | "
            f"{row['delta_bytes']} | {row['selected_span_count']} | "
            f"{row['telomere_project_token_hits']} | `{row['exact_decode']}` |"
        )

    lines.extend(["", "## Decision", ""])
    lines.append(f"- Status: `{payload['decision']['status']}`")
    for rule in payload["decision"]["stop_rules"]:
        lines.append(f"- Stop rule: {rule}")

    lines.extend(["", "## dispatching-parallel-agents Brief", ""])
    for item in payload["decision"]["parallel_agent_next_steps"]:
        lines.append(f"- `{item['parallel_group']}`: {item['task']}")

    lines.extend(
        [
            "",
            "## Source Artifacts",
            "",
            "The JSON `source_hashes` map pins this rerun to the exact upstream evidence and generator files below.",
        ]
    )
    for name, digest in payload["source_hashes"].items():
        lines.append(f"- `{name}`: `{digest}`")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not REPORT_JSON.exists() or not REPORT_MD.exists():
        raise SystemExit("generated public preset control rerun files are missing")
    payload = load_json(REPORT_JSON)
    if payload.get("generated_by") != GENERATED_BY:
        raise SystemExit("public_preset_control_rerun.json has wrong generated_by marker")
    if payload.get("source_hashes") != source_hashes():
        raise SystemExit("public_preset_control_rerun.json source hashes are stale")
    expected = stable_projection(build_report())
    current = stable_projection(payload)
    if current != expected:
        raise SystemExit("public_preset_control_rerun.json is stale; regenerate it")
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
            raise SystemExit(f"public preset control rerun scope field must be false: {field}")
    summary_payload = payload["summary"]
    if summary_payload["public_preset_promotion_met"]:
        raise SystemExit("public preset control rerun cannot promote the preset")
    if summary_payload["no_project_control_negative_groups"] <= 0:
        raise SystemExit("project-token removal should still expose control failures")
    if (
        summary_payload["leave_family_out_ordinary_negative_groups"]
        >= replication.PROMOTION_ORDINARY_GROUPS
    ):
        raise SystemExit("leave-family-out rerun unexpectedly meets promotion floor")
    if summary_payload["leave_family_out_no_project_ordinary_negative_groups"] != 0:
        raise SystemExit("leave-family-out plus no-project should remove current signal")
    if not summary_payload["projection_resolved"]:
        raise SystemExit("public preset control rerun must resolve the projection")
    for rows in payload["rows_by_variant"].values():
        if not all(row.get("exact_decode") for row in rows):
            raise SystemExit("public preset control rerun rows must decode exactly")
        if not all(row.get("corrupt_rejection") for row in rows):
            raise SystemExit("public preset control rerun rows must reject corrupt records")
    text = REPORT_MD.read_text(encoding="utf-8")
    for phrase in (
        "Public Preset Control Rerun",
        "No Seed Search",
        "not `.tlmr` format support",
        "Projection vs Exact Rerun",
        "Variant Gate Summary",
        "Strongest Exact Rows",
        "Projection resolved",
        "dispatching-parallel-agents Brief",
        "source_hashes",
    ):
        if phrase not in text:
            raise SystemExit(f"PUBLIC_PRESET_CONTROL_RERUN.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="validate generated public preset rerun"
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
