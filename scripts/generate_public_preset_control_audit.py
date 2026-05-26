#!/usr/bin/env python3
"""Generate the public preset control-separation audit.

This is a no-compute coordination artifact. It explains why the public-preset
promotion gate remains blocked by controls, then pre-registers bounded
ablation work for future dispatching-parallel-agents lanes.
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
REPORT_JSON = DOCS / "public_preset_control_audit.json"
REPORT_MD = DOCS / "PUBLIC_PRESET_CONTROL_AUDIT.md"
GENERATED_BY = "scripts/generate_public_preset_control_audit.py"

SOURCE_PATHS = {
    "public_preset_promotion_gate_sha256": DOCS / "public_preset_promotion_gate.json",
    "schema_native_public_dictionary_replication_sha256": DOCS
    / "schema_native_public_dictionary_replication.json",
    "schema_native_public_dictionaries_sha256": DOCS
    / "schema_native_public_dictionaries.json",
    "seed_table_preset_probe_sha256": DOCS / "seed_table_preset_probe.json",
    "expander_salt_ensemble_sha256": DOCS / "expander_salt_ensemble.json",
    "mechanism_experiment_ranking_sha256": DOCS / "mechanism_experiment_ranking.json",
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


def negative_rows(rows: list[dict[str, Any]], mode: str | None = None) -> list[dict[str, Any]]:
    return [
        row
        for row in rows
        if (mode is None or row.get("mode") == mode)
        and int(row.get("delta_bytes", 0)) < 0
    ]


def strongest(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not rows:
        return None
    return min(rows, key=lambda row: int(row.get("delta_bytes", 0)))


def group_names(rows: list[dict[str, Any]]) -> list[str]:
    return sorted({row["independence_group"] for row in rows})


def summarize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "name": row["name"],
            "mode": row["mode"],
            "control_kind": row["control_kind"],
            "independence_group": row["independence_group"],
            "schema_family": row["schema_family"],
            "input_bytes": row["input_bytes"],
            "delta_bytes": row["delta_bytes"],
            "selected_span_count": row["selected_span_count"],
            "metadata_bytes": row["metadata_bytes"],
            "dictionary_entry_count": row["dictionary_entry_count"],
            "telomere_project_token_hits": row.get("telomere_project_token_hits", 0),
            "selected_entry_family_counts": row.get("selected_entry_family_counts", {}),
        }
        for row in sorted(rows, key=lambda item: (item["control_kind"], item["name"]))
    ]


def standards_mode_rows(replication: dict[str, Any]) -> list[dict[str, Any]]:
    return [row for row in replication["rows"] if row["mode"] == "standards-public-v1"]


def audit_findings(inputs: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    replication = inputs["schema_native_public_dictionary_replication"]
    schema = summary(replication)
    gate = summary(inputs["public_preset_promotion_gate"])
    discovery = summary(inputs["schema_native_public_dictionaries"])
    seed_table = summary(inputs["seed_table_preset_probe"])
    salt = summary(inputs["expander_salt_ensemble"])

    standards_negative = negative_rows(replication["rows"], "standards-public-v1")
    standards_controls = [
        row for row in standards_negative if "control" in row["control_kind"]
    ]
    standards_ordinary = [
        row for row in standards_negative if row["control_kind"] == "ordinary-structured"
    ]
    generic_negative = negative_rows(
        replication["rows"], "generic-public-token-dictionary-v1"
    )
    v0_negative = negative_rows(replication["rows"], "schema-v0-family-on-replication")
    strongest_control = strongest(standards_controls)
    strongest_ordinary = strongest(standards_ordinary)

    return [
        {
            "finding_id": "paired-shadow-controls-fail",
            "status": "blocks-promotion",
            "question": "Do paired shadow controls stay null under the standards preset?",
            "evidence": (
                f"{len(standards_controls)} standards control rows shrink across "
                f"{schema['standards_control_negative_groups']} groups: "
                f"{', '.join(schema['standards_control_negative_group_names'])}."
            ),
            "interpretation": (
                "The preset is finding structure in paired shadows, so current wins "
                "cannot be treated as semantic natural-corpus proof."
            ),
            "next_test": (
                "Add family-matched, vocabulary-disjoint shadows for every winning "
                "ordinary group and require zero negative control groups."
            ),
            "source_rows": summarize_rows(standards_controls),
        },
        {
            "finding_id": "ordinary-signal-is-real-but-not-clean",
            "status": "promising-but-contaminated",
            "question": "Is there a substantial ordinary held-out signal?",
            "evidence": (
                f"{len(standards_ordinary)} standards ordinary rows shrink across "
                f"{schema['standards_ordinary_negative_groups']} groups; strongest "
                f"ordinary case {strongest_ordinary['name'] if strongest_ordinary else 'none'} "
                f"has delta {strongest_ordinary['delta_bytes'] if strongest_ordinary else 0} bytes."
            ),
            "interpretation": (
                "The public preset direction is the strongest current non-depth signal, "
                "but it is not separated from controls."
            ),
            "next_test": (
                "Run leave-family-out and token-frequency-matched controls before "
                "any format or registry proposal."
            ),
            "source_rows": summarize_rows(standards_ordinary),
        },
        {
            "finding_id": "generic-baseline-explains-part-of-signal",
            "status": "requires-ablation",
            "question": "Are wins specific to standards dictionaries or generic token tables?",
            "evidence": (
                f"Generic public token dictionary has {len(generic_negative)} negative "
                f"rows across {schema['generic_ordinary_negative_groups']} ordinary groups."
            ),
            "interpretation": (
                "Some savings may come from generic token coverage rather than a "
                "domain-specific public preset."
            ),
            "next_test": (
                "Compare standards rows against entry-count, byte-count, and token-frequency "
                "matched generic tables."
            ),
            "source_rows": summarize_rows(generic_negative),
        },
        {
            "finding_id": "wrong-random-salt-baselines-remain-null",
            "status": "supports-mechanism-interest",
            "question": "Do random, wrong-family, SHA-256, or salted baselines explain the signal?",
            "evidence": (
                f"wrong-family ordinary groups {schema['wrong_family_ordinary_negative_groups']}; "
                f"random-table ordinary groups {schema['random_table_ordinary_negative_groups']}; "
                f"SHA-256 selected spans {schema['sha256_selected_spans']}; "
                f"salt selected rows {salt['salted_selected_span_rows']}."
            ),
            "interpretation": (
                "The signal is not explained by plain SHA-256 or random/salted trials; "
                "the live problem is control specificity."
            ),
            "next_test": (
                "Keep random and salted null controls in every future public-preset run."
            ),
            "source_rows": [],
        },
        {
            "finding_id": "project-token-leakage-watch",
            "status": "watch",
            "question": "Are Telomere/project-specific tokens dominating selected spans?",
            "evidence": (
                f"standards project-token hits {schema['standards_project_token_hits']} "
                f"with share {schema['standards_project_token_hit_share']}; "
                f"leakage_dominates={schema['leakage_dominates']}."
            ),
            "interpretation": (
                "Current evidence says leakage does not dominate, but project-token "
                "ablation is required before a public registry claim."
            ),
            "next_test": (
                "Remove project-specific entries, rerun the standards rows, and require "
                "ordinary/control separation to remain improved."
            ),
            "source_rows": [],
        },
        {
            "finding_id": "format-boundary-closed",
            "status": "blocks-format-support",
            "question": "Can public presets be added to `.tlmr` yet?",
            "evidence": (
                f"public preset promotion met={gate['promotion_met']}; "
                f"format promotion allowed={gate['format_promotion_allowed']}; "
                f"seed table ordinary groups={seed_table['canonical_ordinary_heldout_negative_groups']}; "
                f"discovery promotion met={discovery['promotion_met']}."
            ),
            "interpretation": (
                "The preset idea remains research-only; `.tlmr` registry or preset "
                "metadata would be premature."
            ),
            "next_test": (
                "Only draft registry semantics after control separation and "
                "SEARCH_FRONTIER_GATE format promotion both pass."
            ),
            "source_rows": [],
        },
    ]


def ablation_plan() -> list[dict[str, Any]]:
    return [
        {
            "ablation_id": "paired-shadow-expansion",
            "parallel_group": "corpus-transform",
            "purpose": "Build multiple vocabulary-disjoint paired shadows for every ordinary winning family.",
            "success_rule": "ordinary negative groups stay >=3 and paired shadow negative groups become 0",
            "failure_rule": "paired shadows continue to shrink or shrink at comparable density",
            "budget": "metadata-only plan now; future generated run must stay bounded to the frozen replication corpus bank",
            "suggested_artifact": "docs/PUBLIC_PRESET_CONTROL_ABLATION.md",
        },
        {
            "ablation_id": "dictionary-size-equalization",
            "parallel_group": "compute-economics",
            "purpose": "Compare standards dictionaries against entry-count, byte-count, and token-frequency matched public tables.",
            "success_rule": "standards preset beats all matched generic baselines after metadata",
            "failure_rule": "matched generic tables reproduce the same negative groups",
            "budget": "no broad seed search; reuse existing frozen spans and dictionary-entry manifests",
            "suggested_artifact": "docs/PUBLIC_PRESET_CONTROL_ABLATION.md",
        },
        {
            "ablation_id": "project-token-removal",
            "parallel_group": "corpus-transform",
            "purpose": "Remove Telomere/project-specific entries before counting standards wins.",
            "success_rule": "ordinary/control separation improves or stays clean without project-token entries",
            "failure_rule": "ordinary wins collapse or controls remain negative",
            "budget": "bounded dictionary-filter rerun only",
            "suggested_artifact": "docs/PUBLIC_PRESET_CONTROL_ABLATION.md",
        },
        {
            "ablation_id": "leave-family-out",
            "parallel_group": "format-policy",
            "purpose": "Pre-register public preset family identity so held-out rows cannot benefit from trained same-family literals.",
            "success_rule": "family identity is decoder-public and ordinary wins survive leave-family-out splits",
            "failure_rule": "wins require entries derived from the compressed family or file-local training",
            "budget": "registry-design note before any format change",
            "suggested_artifact": "docs/PUBLIC_PRESET_REGISTRY_REQUIREMENTS.md",
        },
        {
            "ablation_id": "control-density-normalization",
            "parallel_group": "compute-economics",
            "purpose": "Normalize selected-span density by input bytes, dictionary bytes, and metadata bytes.",
            "success_rule": "ordinary density remains materially above control density after normalization",
            "failure_rule": "control density is comparable to ordinary density",
            "budget": "read-only analysis of existing rows first",
            "suggested_artifact": "docs/PUBLIC_PRESET_CONTROL_ABLATION.md",
        },
    ]


def build_report() -> dict[str, Any]:
    inputs = {
        key.removesuffix("_sha256"): load_json(path)
        for key, path in SOURCE_PATHS.items()
    }
    replication = inputs["schema_native_public_dictionary_replication"]
    schema = summary(replication)
    gate = summary(inputs["public_preset_promotion_gate"])
    findings = audit_findings(inputs)
    blocking_findings = [
        finding for finding in findings if finding["status"].startswith("blocks")
    ]
    standards_negative = negative_rows(replication["rows"], "standards-public-v1")
    standards_controls = [
        row for row in standards_negative if "control" in row["control_kind"]
    ]
    standards_ordinary = [
        row for row in standards_negative if row["control_kind"] == "ordinary-structured"
    ]
    generic_negative = negative_rows(
        replication["rows"], "generic-public-token-dictionary-v1"
    )
    by_control_kind: dict[str, list[str]] = defaultdict(list)
    for row in standards_negative:
        by_control_kind[row["control_kind"]].append(row["name"])

    strongest_control = strongest(standards_controls)
    strongest_ordinary = strongest(standards_ordinary)

    return {
        "generated_by": GENERATED_BY,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format_version": 1,
        "scope": {
            "kind": "public preset control audit",
            "performs_seed_search": False,
            "launches_agents": False,
            "makes_compression_claim": False,
            "is_format_support": False,
            "is_natural_corpus_proof": False,
            "overrides_public_preset_gate": False,
        },
        "source_hashes": source_hashes(),
        "summary": {
            "audit_status": "blocked_by_paired_shadow_controls",
            "finding_count": len(findings),
            "blocking_finding_count": len(blocking_findings),
            "standards_negative_rows": len(standards_negative),
            "standards_ordinary_negative_rows": len(standards_ordinary),
            "standards_control_negative_rows": len(standards_controls),
            "standards_ordinary_negative_groups": schema[
                "standards_ordinary_negative_groups"
            ],
            "standards_control_negative_groups": schema[
                "standards_control_negative_groups"
            ],
            "standards_control_negative_group_names": schema[
                "standards_control_negative_group_names"
            ],
            "generic_negative_rows": len(generic_negative),
            "generic_ordinary_negative_groups": schema[
                "generic_ordinary_negative_groups"
            ],
            "strongest_ordinary_case": strongest_ordinary["name"]
            if strongest_ordinary
            else "none",
            "strongest_ordinary_delta_bytes": strongest_ordinary["delta_bytes"]
            if strongest_ordinary
            else 0,
            "strongest_control_case": strongest_control["name"]
            if strongest_control
            else "none",
            "strongest_control_delta_bytes": strongest_control["delta_bytes"]
            if strongest_control
            else 0,
            "standards_project_token_hit_share": schema[
                "standards_project_token_hit_share"
            ],
            "leakage_dominates": schema["leakage_dominates"],
            "public_preset_gate_promotion_met": gate["promotion_met"],
            "public_preset_blocked_gate_ids": gate["blocked_gate_ids"],
            "next_required_artifact": "docs/PUBLIC_PRESET_CONTROL_ABLATION.md",
            "claim_boundary": (
                "No Seed Search; not public preset promotion; not `.tlmr` format "
                "support; not natural-corpus proof."
            ),
            "conclusion": (
                "The public-preset signal is promising but currently falsified for "
                "promotion by paired shadow controls."
            ),
        },
        "negative_row_groups": {
            key: sorted(value) for key, value in sorted(by_control_kind.items())
        },
        "findings": findings,
        "ablation_plan": ablation_plan(),
    }


def write_report(payload: dict[str, Any]) -> None:
    REPORT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary_payload = payload["summary"]
    lines = [
        "# Public Preset Control Audit",
        "",
        f"Generated by `{GENERATED_BY}` from the public preset promotion gate and schema replication rows.",
        "This is a No Seed Search control audit. It performs no seed search, launches no agents, is not public preset promotion, is not `.tlmr` format support, is not natural-corpus proof, and is not a compression claim.",
        "",
        "## Summary",
        "",
        f"- Audit status: `{summary_payload['audit_status']}`",
        f"- Findings: `{summary_payload['finding_count']}`",
        f"- Blocking findings: `{summary_payload['blocking_finding_count']}`",
        f"- Standards ordinary negative groups: `{summary_payload['standards_ordinary_negative_groups']}`",
        f"- Standards control negative groups: `{summary_payload['standards_control_negative_groups']}`",
        f"- Standards control groups: `{', '.join(summary_payload['standards_control_negative_group_names'])}`",
        f"- Strongest ordinary case: `{summary_payload['strongest_ordinary_case']}` (`{summary_payload['strongest_ordinary_delta_bytes']}` bytes)",
        f"- Strongest control case: `{summary_payload['strongest_control_case']}` (`{summary_payload['strongest_control_delta_bytes']}` bytes)",
        f"- Generic ordinary negative groups: `{summary_payload['generic_ordinary_negative_groups']}`",
        f"- Project-token hit share: `{summary_payload['standards_project_token_hit_share']}`",
        f"- Public preset promotion met: `{summary_payload['public_preset_gate_promotion_met']}`",
        f"- Public preset blocked gates: `{', '.join(summary_payload['public_preset_blocked_gate_ids'])}`",
        "",
        summary_payload["conclusion"],
        "",
        "## Control Findings",
        "",
        "| finding | status | question | evidence | next test |",
        "| --- | --- | --- | --- | --- |",
    ]
    for finding in payload["findings"]:
        lines.append(
            f"| `{cell(finding['finding_id'])}` | `{cell(finding['status'])}` | "
            f"{cell(finding['question'])} | {cell(finding['evidence'])} | "
            f"{cell(finding['next_test'])} |"
        )

    lines.extend(["", "## Negative Row Groups", ""])
    for control_kind, names in payload["negative_row_groups"].items():
        lines.append(f"- `{control_kind}`: {', '.join(f'`{name}`' for name in names)}")

    lines.extend(["", "## Ablation Plan", ""])
    lines.extend(
        [
            "| ablation | group | purpose | success rule | failure rule |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for item in payload["ablation_plan"]:
        lines.append(
            f"| `{cell(item['ablation_id'])}` | `{cell(item['parallel_group'])}` | "
            f"{cell(item['purpose'])} | {cell(item['success_rule'])} | "
            f"{cell(item['failure_rule'])} |"
        )

    lines.extend(["", "## Source Row Details", ""])
    for finding in payload["findings"]:
        if not finding["source_rows"]:
            continue
        lines.extend([f"### {finding['finding_id']}", ""])
        lines.extend(
            [
                "| name | kind | group | family | delta | selected spans | dictionary entries | project-token hits |",
                "| --- | --- | --- | --- | ---: | ---: | ---: | ---: |",
            ]
        )
        for row in finding["source_rows"]:
            lines.append(
                f"| `{cell(row['name'])}` | `{cell(row['control_kind'])}` | "
                f"`{cell(row['independence_group'])}` | `{cell(row['schema_family'])}` | "
                f"{row['delta_bytes']} | {row['selected_span_count']} | "
                f"{row['dictionary_entry_count']} | {row['telomere_project_token_hits']} |"
            )
        lines.append("")

    lines.extend(
        [
            "## dispatching-parallel-agents Briefs",
            "",
            "- `corpus-transform`: design paired shadows and project-token removal controls.",
            "- `compute-economics`: normalize ordinary/control density against dictionary and metadata budgets.",
            "- `format-policy`: keep registry and `.tlmr` preset metadata blocked until this audit passes.",
            "",
            "## Source Artifacts",
            "",
            "The JSON `source_hashes` map pins this audit to the exact upstream evidence files below.",
        ]
    )
    for name, digest in payload["source_hashes"].items():
        lines.append(f"- `{name}`: `{digest}`")

    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_report() -> None:
    if not REPORT_JSON.exists() or not REPORT_MD.exists():
        raise SystemExit("generated public preset control audit files are missing")
    payload = load_json(REPORT_JSON)
    if payload.get("generated_by") != GENERATED_BY:
        raise SystemExit("public_preset_control_audit.json has wrong generated_by marker")
    if payload.get("source_hashes") != source_hashes():
        raise SystemExit("public_preset_control_audit.json source hashes are stale")
    expected = stable_projection(build_report())
    current = stable_projection(payload)
    if current != expected:
        raise SystemExit("public_preset_control_audit.json is stale; regenerate it")
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
            raise SystemExit(f"public preset control audit scope field must be false: {field}")
    summary_payload = payload["summary"]
    if summary_payload["audit_status"] != "blocked_by_paired_shadow_controls":
        raise SystemExit("public preset control audit must remain blocked by paired shadows")
    if summary_payload["standards_control_negative_groups"] <= 0:
        raise SystemExit("public preset control audit lost the control failure")
    if "control-separation" not in summary_payload["public_preset_blocked_gate_ids"]:
        raise SystemExit("public preset control audit must cite control-separation blocker")
    finding_ids = {finding["finding_id"] for finding in payload["findings"]}
    for required in (
        "paired-shadow-controls-fail",
        "ordinary-signal-is-real-but-not-clean",
        "generic-baseline-explains-part-of-signal",
        "format-boundary-closed",
    ):
        if required not in finding_ids:
            raise SystemExit(f"public preset control audit missing finding {required}")
    text = REPORT_MD.read_text(encoding="utf-8")
    for phrase in (
        "Public Preset Control Audit",
        "No Seed Search",
        "not `.tlmr` format support",
        "not natural-corpus proof",
        "Control Findings",
        "Ablation Plan",
        "paired-shadow-controls-fail",
        "dispatching-parallel-agents Briefs",
        "source_hashes",
    ):
        if phrase not in text:
            raise SystemExit(f"PUBLIC_PRESET_CONTROL_AUDIT.md missing phrase: {phrase}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="validate generated public preset control audit"
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
